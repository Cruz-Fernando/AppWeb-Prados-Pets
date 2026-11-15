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

# Duraciones que se pueden elegir en el formulario (minutos). Es la única lista que
# acepta el servidor: lo que se ve en pantalla es exactamente lo que se guarda y sale en el PDF.
DURACIONES_PERMITIDAS = (30, 45, 60, 75, 90, 105, 120, 150, 180)

PRECIO_MAXIMO = 99_999_999


def _etiqueta_duracion(minutos):
    """45 -> '45 minutos', 60 -> '1 hora', 90 -> '1 h 30 min', 120 -> '2 horas'."""
    horas, resto = divmod(minutos, 60)
    if not horas:
        return f'{resto} minutos'
    if not resto:
        return '1 hora' if horas == 1 else f'{horas} horas'
    return f'{horas} h {resto} min'


OPCIONES_DURACION = [(m, _etiqueta_duracion(m)) for m in DURACIONES_PERMITIDAS]


def _duracion_por_defecto(tamano):
    """Duración sugerida (minutos) para el tamaño de la mascota; 60 si no tiene tamaño."""
    return DURACION_POR_TAMANO.get((tamano or 'pequeno').upper(), 60)


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
        'condicion_pelaje': m.condicion_pelaje,
        'dueno':           m.id_dueno.nombre_completo,
        'telefono':        m.id_dueno.telefono,
    }


def _formatear_precio(valor):
    try:
        if isinstance(valor, str):
            valor = float(valor.replace('$', '').replace(' COP', '').replace('.', ''))
        return '$' + f'{valor:,.0f}'.replace(',', '.') + ' COP'
    except (ValueError, TypeError):
        return str(valor)


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


def _guardar_borrador(request, mascota=None):
    """Guarda en sesión lo que el usuario escribió, para devolverlo al formulario si algo falla."""
    request.session['peluqueria_borrador'] = {
        'mascota':       _mascota_a_dict(mascota) if mascota else None,
        'servicio':      request.POST.get('servicio', ''),
        'condicion_pelaje': request.POST.get('condicion_pelaje', ''),
        'groomer_id':    request.POST.get('groomer_id', ''),
        'fecha_hora':    request.POST.get('fecha_hora', ''),
        'duracion_min':  request.POST.get('duracion_min', ''),
        'precio':        request.POST.get('precio', ''),
        'observaciones': request.POST.get('observaciones', ''),
    }


def _rechazar(request, mensaje, mascota=None):
    """Muestra el error, conserva lo escrito y vuelve al formulario."""
    messages.error(request, mensaje)
    _guardar_borrador(request, mascota)
    return redirect('peluqueria:panel_peluqueria')


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
    if request.method == 'POST':
        mascota_id     = (request.POST.get('mascota_id') or '').strip()
        servicio       = request.POST.get('servicio')
        fecha_hora_str = request.POST.get('fecha_hora')
        groomer_id     = request.POST.get('groomer_id') or None

        if not mascota_id.isdigit():
            messages.error(
                request,
                'Debe buscar y seleccionar una mascota de la lista desplegable antes de agendar.',
            )
            return redirect('peluqueria:panel_peluqueria')

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
            mascota = Mascota.objects.select_related('id_dueno').get(id_mascota=int(mascota_id))
        except Mascota.DoesNotExist:
            messages.error(request, 'Debe seleccionar una mascota válida del sistema.')
            return redirect('peluqueria:panel_peluqueria')

        tamano = getattr(mascota, 'tamano', 'pequeno') or 'pequeno'
        duracion_min = 120 if tamano.upper() == 'GRANDE' else 90 if tamano.upper() == 'MEDIANO' else 60

        groomer = None
        if groomer_id:
            try:
                groomer = Usuario.objects.get(pk=groomer_id)
            except (Usuario.DoesNotExist, ValueError):
                pass

        if not fecha_hora or not groomer:
            messages.error(request, 'Debe seleccionar un groomer y una fecha/hora válida para agendar.')
            return redirect('peluqueria:panel_peluqueria')

        # 2. Rechazar fechas pasadas
        if fecha_hora < datetime.now():
            messages.error(request, 'No se puede agendar una cita de peluquería en una fecha u hora pasada.')
            return redirect('peluqueria:panel_peluqueria')

        fecha_hora_fin = fecha_hora + timedelta(minutes=duracion_min)
        
        citas_existentes_dia = CitaPeluqueria.objects.filter(
            groomer=groomer,
            fecha_hora__date=fecha_hora.date()
        ).exclude(estado='cancelada')

        for cita_ext in citas_existentes_dia:
            inicio_ext = cita_ext.fecha_hora
            fin_ext = inicio_ext + timedelta(minutes=cita_ext.duracion_estimada_min)
            
            if fecha_hora < fin_ext and fecha_hora_fin > inicio_ext:
                hora_ini_txt = inicio_ext.strftime("%I:%M %p")
                hora_fin_txt = fin_ext.strftime("%I:%M %p")
                messages.error(
                    request, 
                    f'El groomer ya tiene una cita ocupada en ese horario (de {hora_ini_txt} a {hora_fin_txt}).'
                )
                return redirect('peluqueria:panel_peluqueria')

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

        # Pasamos variables dinámicas a la sesión para usarlas en la vista comprobante_pdf 
        # (por si tu base de datos no tiene la columna 'precio' guardada de forma persistente).
        request.session[f'precio_cita_{cita.pk}'] = precio

    # 3. Condición del pelaje
    condicion_pelaje = (request.POST.get('condicion_pelaje') or '').strip()
    if not condicion_pelaje:
        return _rechazar(request, 'Escribe la condición del pelaje.', mascota)
    if len(condicion_pelaje) > 100:
        return _rechazar(
            request,
            'La condición del pelaje no puede superar 100 caracteres.',
            mascota,
        )

    # 4. Groomer: debe ser un usuario activo con rol de groomer
    groomer = None
    groomer_id = (request.POST.get('groomer_id') or '').strip()
    if groomer_id.isdigit():
        groomer = Usuario.objects.filter(
            pk=int(groomer_id), id_rol__nombre_rol='groomer', estado='activo'
        ).first()
    if groomer is None:
        return _rechazar(request, 'Selecciona un groomer activo para la cita.', mascota)

    # 5. Fecha y hora (con zona horaria) y que no sea pasada
    fecha_hora = _parsear_fecha_hora(request.POST.get('fecha_hora'))
    if fecha_hora is None:
        return _rechazar(request, 'Indica una fecha y hora válidas para la cita.', mascota)
    if fecha_hora < timezone.now():
        return _rechazar(
            request,
            'No se pueden agendar citas de peluquería en fechas u horas pasadas.',
            mascota,
        )

    # 6. Duración: la que eligió el usuario (si es válida); si no eligió, la sugerida por tamaño
    duracion_txt = (request.POST.get('duracion_min') or '').strip()
    if duracion_txt:
        if not duracion_txt.isdigit() or int(duracion_txt) not in DURACIONES_PERMITIDAS:
            return _rechazar(request, 'La duración elegida no es válida.', mascota)
        duracion_min = int(duracion_txt)
    else:
        duracion_min = _duracion_por_defecto(mascota.tamano)

    # 7. Tarifa: valor digitado por el usuario, en pesos colombianos.
    precio = _parsear_precio(request.POST.get('precio'))
    if precio <= 0:
        return _rechazar(request, 'Ingresa la tarifa del servicio (debe ser mayor a $0).', mascota)
    if precio > PRECIO_MAXIMO:
        return _rechazar(
            request,
            f'La tarifa no puede superar {_formatear_precio(PRECIO_MAXIMO)}.',
            mascota,
        )

    # 8. El groomer no puede tener dos citas que se crucen
    if _groomer_ocupado(groomer, fecha_hora, duracion_min):
        return _rechazar(
            request,
            f'{groomer.nombre_completo} ya tiene una cita de peluquería que se cruza con ese '
            'horario. Elige otra hora u otro groomer.',
            mascota,
        )

    cita = CitaPeluqueria.objects.create(
        mascota=mascota,
        nombre_mascota=mascota.nombre,
        raza=mascota.raza or 'No especificada',
        tamano=(mascota.tamano or 'pequeno').upper(),
        servicio=servicio,
        condicion_pelaje=condicion_pelaje,
        fecha_hora=fecha_hora,
        duracion_estimada_min=duracion_min,
        precio=precio,
        observaciones=(request.POST.get('observaciones') or '').strip(),
        groomer=groomer,
    )

    # Mostrar el mensaje de éxito y redireccionar pasando el parámetro ?descargar=ID
    messages.success(request, f'Cita agendada exitosamente para {mascota.nombre}.')
    return redirect(reverse('peluqueria:panel_peluqueria') + f'?descargar={cita.pk}')


@login_required
def comprobante_pdf(request, pk):
    """Genera el PDF del comprobante de la cita"""
    cita = get_object_or_404(CitaPeluqueria, pk=pk)
    
    # Buscamos la mascota en base de datos para pasarla al template
    mascota = Mascota.objects.filter(nombre=cita.nombre_mascota).first()
    
    # Textos dinámicos para el PDF
    duracion_min = cita.duracion_estimada_min or 60
    cita.duracion_texto = f'{duracion_min // 60} hora(s)' if duracion_min == 60 else f'{duracion_min} minutos'
    
    # Validamos si existe precio en la base de datos o si lo tenemos que rescatar de la sesión
    precio_guardado = getattr(cita, 'precio', None)
    if precio_guardado:
        cita.precio_formateado = _formatear_precio(precio_guardado)
    else:
        cita.precio_formateado = request.session.pop(f'precio_cita_{cita.pk}', 'Valor no especificado')

    # Configuración de respuesta
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Comprobante_Spa_{cita.nombre_mascota}.pdf"'
    
    # Renderizado y creación
    template = get_template('peluqueria/pdf_cita.html')
    html = template.render({'cita': cita, 'mascota': mascota, 'groomer': cita.groomer})
    status = pisa.CreatePDF(html, dest=response)
    
    if status.err:
        return HttpResponse('Error al generar el PDF.', status=500)
        
    return response