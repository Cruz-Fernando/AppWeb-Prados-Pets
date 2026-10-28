from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from xhtml2pdf import pisa

from apps.directorio.models import Mascota

from .models import CitaPeluqueria

Usuario = get_user_model()

# Duración estimada del servicio según el tamaño de la mascota (minutos).
DURACION_POR_TAMANO = {'PEQUENO': 60, 'MEDIANO': 90, 'GRANDE': 120}


def _mascota_a_dict(m):
    """Datos de la mascota que consume el buscador (JS) de la plantilla."""
    return {
        'id':              m.id_mascota,
        'nombre':          m.nombre,
        'especie':         m.especie,
        'especie_display': m.get_especie_display(),
        'raza':            m.raza or 'No especificada',
        'tamano':          m.tamano,
        'tamano_display':  m.get_tamano_display() if m.tamano else '',
        'dueno':           m.id_dueno.nombre_completo,
        'telefono':        m.id_dueno.telefono,
    }


def _formatear_precio(valor):
    return '$' + f'{valor:,}'.replace(',', '.') + ' COP'


def _parsear_fecha_hora(texto):
    """Convierte el texto del formulario en datetime con zona horaria, o None."""
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            naive = datetime.strptime((texto or '').strip(), fmt)
        except ValueError:
            continue
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return None


def _groomer_ocupado(groomer, inicio, duracion_min):
    """True si el groomer ya tiene una cita que se cruza con [inicio, inicio+duración)."""
    fin = inicio + timedelta(minutes=duracion_min)
    # Solo se revisan las citas que pueden cruzarse (±1 día alcanza: máx. 2 h por cita)
    candidatas = CitaPeluqueria.objects.filter(
        groomer=groomer,
        fecha_hora__gte=inicio - timedelta(days=1),
        fecha_hora__lt=fin,
    )
    for c in candidatas:
        c_fin = c.fecha_hora + timedelta(minutes=c.duracion_estimada_min or 60)
        if c.fecha_hora < fin and inicio < c_fin:
            return True
    return False


@login_required
def panel_peluqueria(request):
    groomers = Usuario.objects.filter(
        id_rol__nombre_rol='groomer', estado='activo'
    ).order_by('nombre_completo')

    # Tras guardar, la página se recarga (con el mensaje de éxito visible) y
    # el navegador descarga el comprobante a partir de este enlace.
    descargar_url = None
    descargar = request.GET.get('descargar', '')
    if descargar.isdigit() and CitaPeluqueria.objects.filter(pk=int(descargar)).exists():
        descargar_url = reverse('peluqueria:comprobante_pdf', args=[int(descargar)])

    return render(request, 'peluqueria/agendar_peluqueria.html', {
        'groomers': groomers,
        'descargar_url': descargar_url,
        'ahora_min': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
        'borrador': request.session.pop('peluqueria_borrador', None),
    })


@login_required
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
        resultados = [_mascota_a_dict(m) for m in mascotas]
    return JsonResponse(resultados, safe=False)


@login_required
def guardar_cita(request):
    if request.method != 'POST':
        return redirect('peluqueria:panel_peluqueria')

    errores = []

    # --- Mascota (debe elegirse del desplegable del buscador) ---
    mascota = None
    mascota_id = (request.POST.get('mascota_id') or '').strip()
    if not mascota_id.isdigit():
        errores.append('Debe buscar y seleccionar una mascota de la lista desplegable antes de agendar.')
    else:
        mascota = Mascota.objects.select_related('id_dueno').filter(id_mascota=int(mascota_id)).first()
        if mascota is None:
            errores.append('Debe seleccionar una mascota válida del sistema.')

    # --- Servicio ---
    servicio = request.POST.get('servicio')
    if servicio not in dict(CitaPeluqueria.SERVICIO_CHOICES):
        errores.append('Selecciona un tipo de servicio válido.')

    # --- Fecha y hora (obligatoria y no pasada) ---
    fecha_hora = _parsear_fecha_hora(request.POST.get('fecha_hora'))
    if fecha_hora is None:
        errores.append('Indica una fecha y hora válidas para la cita.')
    elif fecha_hora < timezone.now().replace(second=0, microsecond=0):
        errores.append('No se pueden agendar citas de peluquería en fechas u horas pasadas.')

    # --- Precio (solo números, mayor que cero) ---
    digitos = ''.join(ch for ch in (request.POST.get('precio') or '') if ch.isdigit())
    precio = int(digitos) if digitos else 0
    if precio <= 0:
        errores.append('Ingresa el precio del servicio (debe ser mayor que cero).')
    elif precio > 99_999_999:
        errores.append('El precio ingresado es demasiado alto.')

    # --- Groomer (debe ser un usuario activo con rol groomer) ---
    groomer = None
    groomer_id = (request.POST.get('groomer_id') or '').strip()
    if not groomer_id.isdigit():
        errores.append('Selecciona el groomer responsable.')
    else:
        groomer = Usuario.objects.filter(
            pk=int(groomer_id), id_rol__nombre_rol='groomer', estado='activo'
        ).first()
        if groomer is None:
            errores.append('El groomer seleccionado no es válido.')

    # --- Duración según tamaño, y disponibilidad del groomer ---
    tamano = ((mascota.tamano if mascota else '') or 'pequeno').upper()
    duracion_min = DURACION_POR_TAMANO.get(tamano, 60)
    if groomer and fecha_hora and _groomer_ocupado(groomer, fecha_hora, duracion_min):
        errores.append(
            f'{groomer.nombre_completo or groomer.username} ya tiene una cita de peluquería '
            'que se cruza con ese horario. Elige otra hora u otro groomer.'
        )

    if errores:
        for e in errores:
            messages.error(request, e)
        # Se conserva lo escrito para no obligar a llenar todo otra vez
        request.session['peluqueria_borrador'] = {
            'mascota': _mascota_a_dict(mascota) if mascota else None,
            'servicio': servicio or '',
            'groomer_id': groomer_id,
            'fecha_hora': (request.POST.get('fecha_hora') or '')[:16],
            'precio': precio,
            'observaciones': request.POST.get('observaciones', ''),
        }
        return redirect('peluqueria:panel_peluqueria')

    cita = CitaPeluqueria.objects.create(
        mascota=mascota,
        nombre_mascota=mascota.nombre,
        raza=mascota.raza or 'No especificada',
        tamano=tamano,
        servicio=servicio,
        fecha_hora=fecha_hora,
        duracion_estimada_min=duracion_min,
        precio=precio,
        observaciones=request.POST.get('observaciones', ''),
        groomer=groomer,
    )
    messages.success(request, '¡Cita de peluquería agendada! El comprobante PDF se está descargando.')
    return redirect(f"{reverse('peluqueria:panel_peluqueria')}?descargar={cita.pk}")


@login_required
def comprobante_pdf(request, pk):
    cita = get_object_or_404(
        CitaPeluqueria.objects.select_related('mascota__id_dueno', 'groomer'), pk=pk
    )
    mascota = cita.mascota
    if mascota is None:
        return HttpResponse(
            'La mascota de esta cita ya no existe en el directorio; no se puede generar el comprobante.',
            status=404,
        )
    cita.precio_formateado = _formatear_precio(cita.precio)

    response = HttpResponse(content_type='application/pdf')
    nombre_archivo = ''.join(ch for ch in mascota.nombre if ch.isalnum()) or 'mascota'
    response['Content-Disposition'] = f'attachment; filename="Comprobante_Spa_{nombre_archivo}.pdf"'
    template = get_template('peluqueria/pdf_cita.html')
    html = template.render({'cita': cita, 'mascota': mascota, 'groomer': cita.groomer})
    status = pisa.CreatePDF(html, dest=response)
    if status.err:
        return HttpResponse('Error al generar el PDF.', status=500)
    return response
