from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.directorio.models import Mascota
from apps.peluqueria.models import CitaPeluqueria
from apps.usuarios.permissions import rol_requerido

from config.pdf import render_pdf

from . import calendario as cal
from .forms import CitaForm
from .models import Cita
from .recomendaciones import recomendaciones_cita


def _mascota_para_buscador(m):
    """Datos de una mascota tal como los usa el buscador del formulario de citas."""
    return {
        "id": m.id_mascota,
        "nombre_mascota": m.nombre,
        "especie": m.get_especie_display(),
        "especie_clave": m.especie,
        "raza": m.raza or "-",
        "codigo": m.codigo_mascota,
        "dueno": m.id_dueno.nombre_completo,
        "telefono": m.id_dueno.telefono,
        "label": f"{m.nombre} ({m.codigo_mascota}) — {m.id_dueno.nombre_completo}",
    }


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def agendar_cita(request):
    """HU06 / PB-08 / PC-07: Agendar consultas médicas con validación en Formulario."""
    if request.method == "POST":
        form = CitaForm(request.POST)
        if form.is_valid():
            try:
                cita = form.save()
            except IntegrityError:
                form.add_error(None, "Error de integridad: Ya existe una cita similar.")
            else:
                messages.success(request, "¡Cita agendada con éxito! El comprobante PDF se está descargando.")
                return redirect(f"{reverse('agendamiento:agendar_cita')}?descargar={cita.pk}")
    else:
        initial = {}
        # Permite abrir el formulario con la mascota ya elegida: ?mascota=<id>
        if request.GET.get("mascota", "").isdigit():
            initial["mascota"] = request.GET["mascota"]
        form = CitaForm(initial=initial)

    # Si el formulario vuelve con errores (o llega ?mascota=), la mascota elegida
    # se conserva en el buscador en vez de obligar a buscarla otra vez.
    mascota_id = str(form["mascota"].value() or "")
    mascota_previa = None
    if mascota_id.isdigit():
        m = Mascota.objects.select_related("id_dueno").filter(id_mascota=int(mascota_id)).first()
        mascota_previa = _mascota_para_buscador(m) if m else None

    # Tras agendar, la página se recarga (con el mensaje visible) y el
    # navegador descarga el comprobante a partir de este enlace.
    descargar_url = None
    cita_creada = None
    descargar = request.GET.get("descargar", "")
    if request.method == "GET" and descargar.isdigit():
        cita_creada = Cita.objects.select_related("mascota", "veterinario").filter(pk=int(descargar)).first()
        if cita_creada:
            descargar_url = reverse("agendamiento:cita_pdf", args=[cita_creada.pk])
    return render(request, "agendamiento/cita_form.html", {
        "form": form,
        "descargar_url": descargar_url,
        "cita_creada": cita_creada,
        "mascota_previa": mascota_previa,
        "servicios": Cita.TIPO_SERVICIO_CHOICES,
    })


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def buscar_mascotas_ajax(request):
    q = request.GET.get("q", "").strip()
    resultados = []
    if len(q) >= 2:
        mascotas = Mascota.objects.select_related("id_dueno").filter(
            Q(nombre__icontains=q)
            | Q(id_dueno__nombre_completo__icontains=q)
            | Q(id_dueno__telefono__icontains=q)
            | Q(codigo_mascota__icontains=q)
        )[:10]
        resultados = [_mascota_para_buscador(m) for m in mascotas]
    return JsonResponse({"resultados": resultados})


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def cita_pdf(request, pk):
    """Comprobante de la cita con la marca de Prados Pets."""
    cita = get_object_or_404(Cita.objects.select_related("mascota__id_dueno", "veterinario"), pk=pk)
    hora_fin = cita.hora_fin
    duracion = None
    if cita.hora_inicio and hora_fin:
        inicio = datetime.combine(cita.fecha, cita.hora_inicio)
        duracion = int((datetime.combine(cita.fecha, hora_fin) - inicio).total_seconds() // 60)
    return render_pdf(request, "agendamiento/cita_pdf.html", {
        "cita": cita,
        "mascota": cita.mascota,
        "dueno": cita.mascota.id_dueno,
        "veterinario": cita.veterinario,
        "tipo_servicio_display": cita.get_tipo_servicio_display(),
        "duracion_min": duracion,
        "recomendaciones": recomendaciones_cita(cita.tipo_servicio),
    }, f"Cita_{cita.pk:05d}_{slugify(cita.mascota.nombre)}")


MOTIVO_CANCELACION_MAX = 255


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
@require_POST
def cancelar_cita(request, pk):
    """
    RF05 / PB-11: Cancelación de citas de consulta (solo POST).

    La cita pasa a estado «cancelada» y conserva el motivo. Al quedar fuera
    de la restricción de unicidad y de las validaciones de cruce de horario,
    su franja queda libre para volver a agendarse.
    """
    cita = get_object_or_404(Cita, pk=pk)
    destino = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        destino = f"{reverse('agendamiento:calendario')}?fecha={cita.fecha.isoformat()}"

    motivo = request.POST.get("motivo_cancelacion", "").strip()

    if cita.estado == "cancelada":
        messages.info(request, "Esta cita ya estaba cancelada.")
    elif cita.estado == "atendida":
        messages.error(request, "No se puede cancelar una cita que ya fue atendida.")
    elif not motivo:
        messages.error(request, "Debes indicar el motivo de la cancelación.")
    elif len(motivo) > MOTIVO_CANCELACION_MAX:
        messages.error(
            request,
            f"El motivo no puede superar los {MOTIVO_CANCELACION_MAX} caracteres.",
        )
    else:
        cita.estado = "cancelada"
        cita.motivo_cancelacion = motivo
        cita.save(update_fields=["estado", "motivo_cancelacion"])
        messages.success(
            request,
            f"Cita de {cita.mascota.nombre} cancelada. El horario quedó disponible.",
        )
    return redirect(destino)


@login_required
@rol_requerido('administrador', 'veterinario', 'groomer', 'recepcionista')
def calendario(request):
    """HU08: Calendario visual diario y semanal."""
    vista = request.GET.get("vista", "semana")
    if vista not in ("semana", "dia"):
        vista = "semana"

    hoy = timezone.localdate()
    try:
        fecha = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError:
        fecha = hoy

    if vista == "dia":
        fechas = [fecha]
        paso = timedelta(days=1)
    else:
        lunes = cal.inicio_semana(fecha)
        fechas = [lunes + timedelta(days=i) for i in range(7)]
        paso = timedelta(days=7)

    desde, hasta = fechas[0], fechas[-1]
    citas = Cita.objects.select_related("mascota", "veterinario").filter(fecha__range=(desde, hasta))
    citas_pelu = CitaPeluqueria.objects.filter(fecha_hora__date__range=(desde, hasta))

    eventos = cal.eventos_desde_citas(citas) + cal.eventos_desde_peluqueria(citas_pelu)
    hora_inicio, hora_fin = cal.rango_horas(eventos)
    dias = cal.construir_dias(eventos, fechas, hora_inicio, hora_fin)

    direccion = request.GET.get("dir", "")
    if direccion not in ("prev", "next"):
        direccion = ""

    activos = [e for e in eventos if not e.cancelada]
    contexto = {
        "direccion": direccion,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
        "total_citas": len(activos),
        "total_canceladas": len(eventos) - len(activos),
        "vista": vista,
        "fecha": fecha,
        "dias": dias,
        "horas": list(range(hora_inicio, hora_fin)),
        "alto_grilla": (hora_fin - hora_inicio) * 64,
        "titulo_rango": cal.titulo_rango(vista, fechas),
        "fecha_anterior": (fecha - paso).isoformat(),
        "fecha_siguiente": (fecha + paso).isoformat(),
        "hoy": hoy.isoformat(),
        "total_consultas": sum(1 for e in activos if e.categoria == cal.CATEGORIA_CONSULTA),
        "total_peluqueria": sum(1 for e in activos if e.categoria == cal.CATEGORIA_PELUQUERIA),
    }
    return render(request, "agendamiento/calendario.html", contexto)