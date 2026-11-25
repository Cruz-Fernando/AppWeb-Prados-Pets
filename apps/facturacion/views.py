"""
Facturación · Ganancias por groomer.

- El administrador y el auxiliar ven a todos los groomers.
- El groomer ve solo lo suyo.
- Las citas que ya pasaron y siguen «Programadas» se cierran aquí como
  Realizada (cuenta para la comisión) o Cancelada (no cuenta y devuelve los
  insumos al inventario, por la señal de peluquería).
"""

from datetime import date
from urllib.parse import urlencode

import openpyxl
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl.styles import Alignment, Font, PatternFill

from apps.peluqueria.cancelacion import CancelacionNoPermitida, cancelar_cita_peluqueria
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.permissions import obtener_rol, rol_requerido

from .ganancias import PERIODOS, rango_de, resumen

Usuario = get_user_model()

ROLES_FACTURACION = ('administrador', 'auxiliar', 'groomer')


def _es_groomer(usuario):
    return not usuario.is_superuser and obtener_rol(usuario) == 'groomer'


def _fecha(texto):
    try:
        return date.fromisoformat((texto or '').strip())
    except ValueError:
        return None


def _filtros(request):
    """Lee periodo, fechas y groomer de la URL. El groomer solo puede verse a sí mismo."""
    periodo = request.GET.get('periodo') or 'semana'
    if periodo not in dict(PERIODOS):
        periodo = 'semana'
    desde, hasta = rango_de(periodo, _fecha(request.GET.get('desde')), _fecha(request.GET.get('hasta')))

    groomers = Usuario.objects.filter(id_rol__nombre_rol='groomer').order_by('nombre_completo', 'username')
    if _es_groomer(request.user):
        groomer = request.user
    else:
        gid = (request.GET.get('groomer') or '').strip()
        groomer = groomers.filter(pk=gid).first() if gid.isdigit() else None
    return periodo, desde, hasta, groomer, groomers


def _query(periodo, desde, hasta, groomer):
    datos = {'periodo': periodo}
    if periodo == 'rango':
        datos.update(desde=desde.isoformat(), hasta=hasta.isoformat())
    if groomer is not None:
        datos['groomer'] = groomer.pk
    return urlencode(datos)


@login_required
@rol_requerido(*ROLES_FACTURACION)
def panel(request):
    periodo, desde, hasta, groomer, groomers = _filtros(request)
    datos = resumen(desde, hasta, groomer=groomer)
    puede_cerrar = not _es_groomer(request.user)
    return render(request, 'facturacion/panel.html', {
        'periodos': PERIODOS,
        'periodo': periodo,
        'desde': desde,
        'hasta': hasta,
        'groomer': groomer,
        'groomers': groomers,
        'es_groomer': _es_groomer(request.user),
        'puede_cerrar': puede_cerrar,
        'r': datos,
        'query': _query(periodo, desde, hasta, groomer),
        'hoy': timezone.localdate(),
    })


@login_required
@rol_requerido(*ROLES_FACTURACION)
@require_POST
def cerrar_servicio(request, pk):
    """Marca una cita como Realizada o Cancelada desde Facturación."""
    cita = get_object_or_404(CitaPeluqueria, pk=pk)
    volver = f"{reverse('facturacion:panel')}?{request.POST.get('query', '')}"

    if _es_groomer(request.user):
        messages.error(request, 'Solo el administrador o el auxiliar pueden cerrar servicios.')
        return redirect(volver)
    if cita.estado != 'Programada':
        messages.error(request, f'La cita #{cita.pk} ya estaba {cita.estado.lower()}.')
        return redirect(volver)

    accion = request.POST.get('accion')
    if accion == 'realizada':
        cita.estado = 'Realizada'
        cita.save()
        messages.success(request, f'Servicio de {cita.nombre_mascota} marcado como realizado: '
                                  f'suma ${cita.comision_groomer:,.0f} de comisión.'.replace(',', '.'))
    elif accion == 'cancelada':
        motivo = (request.POST.get('motivo') or '').strip() or 'Cancelada desde Facturación'
        try:
            cancelar_cita_peluqueria(cita, motivo)   # misma regla que el calendario (PB-11)
        except CancelacionNoPermitida as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f'Servicio de {cita.nombre_mascota} cancelado: no suma comisión.')
    else:
        messages.error(request, 'Acción no válida.')
    return redirect(volver)


@login_required
@rol_requerido(*ROLES_FACTURACION)
def exportar_excel(request):
    periodo, desde, hasta, groomer, _ = _filtros(request)
    datos = resumen(desde, hasta, groomer=groomer)

    wb = openpyxl.Workbook()
    titulo = Font(bold=True, size=13)
    encabezado = Font(bold=True, color="FFFFFF")
    relleno = PatternFill(start_color="7C3AED", end_color="7C3AED", fill_type="solid")
    pesos = '"$"#,##0'

    ws = wb.active
    ws.title = "Por groomer"
    ws.append([f"Ganancias por groomer · {desde:%d/%m/%Y} a {hasta:%d/%m/%Y}"])
    ws["A1"].font = titulo
    ws.append([])
    columnas = ["Groomer", "Servicios realizados", "Facturado", "Comisión groomer (40 %)",
                "Queda a la clínica", "Por cerrar", "Agendados", "Cancelados"]
    ws.append(columnas)
    for celda in ws[3]:
        celda.font, celda.fill, celda.alignment = encabezado, relleno, Alignment(horizontal="center")
    for f in datos.filas:
        ws.append([f.nombre, f.servicios, float(f.facturado), float(f.comision), float(f.clinica),
                   f.por_cerrar, f.agendados, f.cancelados])
    ws.append(["TOTAL", datos.servicios, float(datos.facturado), float(datos.comision), float(datos.clinica),
               datos.por_cerrar, datos.agendados, sum(f.cancelados for f in datos.filas)])
    for celda in ws[ws.max_row]:
        celda.font = Font(bold=True)
    for fila in ws.iter_rows(min_row=4, min_col=3, max_col=5):
        for celda in fila:
            celda.number_format = pesos
    for letra, ancho in zip("ABCDEFGH", (28, 20, 16, 24, 20, 12, 12, 12)):
        ws.column_dimensions[letra].width = ancho

    estados = {'ganado': 'Realizada', 'por_cerrar': 'Por cerrar', 'agendado': 'Agendada', 'cancelado': 'Cancelada'}
    det = wb.create_sheet("Detalle de servicios")
    det.append(["Fecha", "Hora", "Groomer", "Mascota", "Servicio", "Precio", "Comisión", "Estado"])
    for celda in det[1]:
        celda.font, celda.fill = encabezado, relleno
    for c in datos.citas:
        local = timezone.localtime(c.fecha_hora)
        det.append([local.strftime('%d/%m/%Y'), local.strftime('%H:%M'),
                    (c.groomer.nombre_completo or c.groomer.username) if c.groomer else 'Sin groomer',
                    c.nombre_mascota, c.get_servicio_display(), c.precio,
                    float(c.comision_calculada), estados[c.estado_cobro]])
    for fila in det.iter_rows(min_row=2, min_col=6, max_col=7):
        for celda in fila:
            celda.number_format = pesos
    for letra, ancho in zip("ABCDEFGH", (12, 8, 26, 20, 30, 12, 12, 12)):
        det.column_dimensions[letra].width = ancho

    respuesta = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    respuesta['Content-Disposition'] = (
        f'attachment; filename="Ganancias_groomers_{desde:%Y%m%d}_{hasta:%Y%m%d}.xlsx"')
    wb.save(respuesta)
    return respuesta