from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import get_template
from xhtml2pdf import pisa

from apps.directorio.models import Mascota

from .models import CitaPeluqueria

Usuario = get_user_model()


def panel_peluqueria(request):
    # Pasa los groomers activos al template para el select
    groomers = Usuario.objects.filter(
        id_rol__nombre_rol='groomer'
    ).order_by('nombre_completo')
    return render(request, 'peluqueria/agendar_peluqueria.html', {'groomers': groomers})


def buscar_mascota(request):
    """AJAX: busca mascotas y devuelve especie/tipo."""
    q = request.GET.get('q', '').strip()
    resultados = []
    if len(q) >= 2:
        mascotas = Mascota.objects.select_related('id_dueno').filter(
            Q(nombre__icontains=q)
            | Q(id_dueno__nombre_completo__icontains=q)
            | Q(id_dueno__telefono__icontains=q)
            | Q(codigo_mascota__icontains=q)
        )[:10]
        for m in mascotas:
            resultados.append({
                'id':              m.id_mascota,
                'nombre':          m.nombre,
                'especie':         m.especie,
                'especie_display': m.get_especie_display(),
                'raza':            m.raza or 'No especificada',
                'tamano':          m.tamano,
                'tamano_display':  m.get_tamano_display() if m.tamano else '',
                'dueno':           m.id_dueno.nombre_completo,
                'telefono':        m.id_dueno.telefono,
            })
    return JsonResponse(resultados, safe=False)


def guardar_cita(request):
    if request.method == 'POST':
        mascota_id     = request.POST.get('mascota_id')
        servicio       = request.POST.get('servicio')
        fecha_hora_str = request.POST.get('fecha_hora')
        groomer_id     = request.POST.get('groomer_id') or None

        fecha_hora = None
        if fecha_hora_str:
            for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S'):
                try:
                    fecha_hora = datetime.strptime(fecha_hora_str, fmt)
                    break
                except ValueError:
                    continue

        precio_raw = request.POST.get('precio', '$0')
        precio     = precio_raw.strip()

        try:
            mascota = Mascota.objects.select_related('id_dueno').get(id_mascota=mascota_id)
        except Mascota.DoesNotExist:
            messages.error(request, 'Debe seleccionar una mascota válida del sistema.')
            return redirect('peluqueria:panel_peluqueria')

        tamano = getattr(mascota, 'tamano', 'pequeno') or 'pequeno'
        duracion_min = 120 if tamano.upper() == 'GRANDE' else 90 if tamano.upper() == 'MEDIANO' else 60

        groomer = None
        if groomer_id:
            try:
                groomer = Usuario.objects.get(pk=groomer_id)
            except Usuario.DoesNotExist:
                pass

        cita = CitaPeluqueria.objects.create(
            nombre_mascota=mascota.nombre,
            raza=mascota.raza or 'No especificada',
            tamano=tamano.upper(),
            servicio=servicio,
            fecha_hora=fecha_hora,
            duracion_estimada_min=duracion_min,
            observaciones=request.POST.get('observaciones', ''),
            groomer=groomer,
        )
        cita.precio_formateado = precio
        cita.duracion_texto    = f'{duracion_min // 60} hora(s)' if duracion_min == 60 else f'{duracion_min} minutos'

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Comprobante_Spa_{mascota.nombre}.pdf"'
        template = get_template('peluqueria/pdf_cita.html')
        html     = template.render({'cita': cita, 'mascota': mascota, 'groomer': groomer})
        status   = pisa.CreatePDF(html, dest=response)
        if status.err:
            return HttpResponse('Error al generar el PDF.', status=500)
        return response

    return redirect('peluqueria:panel_peluqueria')
