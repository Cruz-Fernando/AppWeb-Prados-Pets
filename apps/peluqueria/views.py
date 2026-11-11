import re
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.agendamiento.recomendaciones import RECOMENDACIONES_PELUQUERIA
from apps.directorio.models import Mascota
from apps.usuarios.permissions import rol_requerido
from config.pdf import render_pdf

from .models import CitaPeluqueria

Usuario = get_user_model()

# Mismos roles que ven «Peluquería» en el menú lateral.
ROLES_PELUQUERIA = ('administrador', 'groomer', 'auxiliar')

# Duración sugerida del servicio según el tamaño de la mascota (minutos).
DURACION_POR_TAMANO = {'PEQUENO': 60, 'MEDIANO': 90, 'GRANDE': 120}

# Duraciones que se pueden elegir en el formulario (minutos). Es la única lista que
# acepta el servidor: lo que se ve en pantalla es exactamente lo que se guarda y sale en el PDF.
DURACIONES_PERMITIDAS = (30, 45, 60, 75, 90, 105, 120, 150, 180)

# Tope del precio en COP: evita desbordar el campo entero y errores de digitación (ceros de más).
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


def _parsear_precio(texto):
    """'$50.000 COP' -> 50000. Devuelve 0 si el texto no trae ningún dígito."""
    digitos = re.sub(r'\D', '', texto or '')
    return int(digitos) if digitos else 0


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
    # Solo se revisan las citas que pueden cruzarse (±1 día alcanza: máx. 3 h por cita)
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
@rol_requerido(*ROLES_PELUQUERIA)
def panel_peluqueria(request):

    groomers = Usuario.objects.filter(
        id_rol__nombre_rol='groomer', estado='activo'
    ).order_by('nombre_completo')

    # Tras guardar, la página se recarga (con el mensaje de éxito visible) y
    # el navegador descarga el comprobante a partir de este enlace.
    descargar_url = None
    cita_creada = None
    descargar = request.GET.get('descargar', '')
    if descargar.isdigit():
        cita_creada = CitaPeluqueria.objects.select_related('groomer').filter(pk=int(descargar)).first()
        if cita_creada:
            descargar_url = reverse('peluqueria:comprobante_pdf', args=[cita_creada.pk])

    return render(request, 'peluqueria/agendar_peluqueria.html', {
        'groomers': groomers,
        'opciones_duracion': OPCIONES_DURACION,
        'servicios': CitaPeluqueria.SERVICIO_CHOICES,
        'descargar_url': descargar_url,
        'cita_creada': cita_creada,
        'ahora_min': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
        'borrador': request.session.pop('peluqueria_borrador', None),
    })


@login_required
@rol_requerido(*ROLES_PELUQUERIA)
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
@rol_requerido(*ROLES_PELUQUERIA)
def guardar_cita(request):
    if request.method != 'POST':
        return redirect('peluqueria:panel_peluqueria')

    # 1. Mascota: debe existir en el directorio
    mascota = None
    mascota_id = (request.POST.get('mascota_id') or '').strip()
    if mascota_id.isdigit():
        mascota = Mascota.objects.select_related('id_dueno').filter(id_mascota=int(mascota_id)).first()
    if mascota is None:
        return _rechazar(
            request,
            'Debes buscar y seleccionar una mascota de la lista desplegable antes de agendar.',
        )

    # 2. Servicio: solo los que ofrece la peluquería
    servicio = (request.POST.get('servicio') or '').strip()
    if servicio not in dict(CitaPeluqueria.SERVICIO_CHOICES):
        return _rechazar(request, 'Selecciona un tipo de servicio válido.', mascota)

    # 3. Groomer: debe ser un usuario activo con rol de groomer
    groomer = None
    groomer_id = (request.POST.get('groomer_id') or '').strip()
    if groomer_id.isdigit():
        groomer = Usuario.objects.filter(
            pk=int(groomer_id), id_rol__nombre_rol='groomer', estado='activo'
        ).first()
    if groomer is None:
        return _rechazar(request, 'Selecciona un groomer activo para la cita.', mascota)

    # 4. Fecha y hora (con zona horaria) y que no sea pasada
    fecha_hora = _parsear_fecha_hora(request.POST.get('fecha_hora'))
    if fecha_hora is None:
        return _rechazar(request, 'Indica una fecha y hora válidas para la cita.', mascota)
    if fecha_hora < timezone.now():
        return _rechazar(
            request,
            'No se pueden agendar citas de peluquería en fechas u horas pasadas.',
            mascota,
        )

    # 5. Duración: la que eligió el usuario (si es válida); si no eligió, la sugerida por tamaño
    duracion_txt = (request.POST.get('duracion_min') or '').strip()
    if duracion_txt:
        if not duracion_txt.isdigit() or int(duracion_txt) not in DURACIONES_PERMITIDAS:
            return _rechazar(request, 'La duración elegida no es válida.', mascota)
        duracion_min = int(duracion_txt)
    else:
        duracion_min = _duracion_por_defecto(mascota.tamano)

    # 6. Precio: número entero de pesos, mayor que cero
    precio = _parsear_precio(request.POST.get('precio'))
    if precio <= 0:
        return _rechazar(request, 'Ingresa el precio del servicio (debe ser mayor a $0).', mascota)
    if precio > PRECIO_MAXIMO:
        return _rechazar(
            request,
            f'El precio no puede superar {_formatear_precio(PRECIO_MAXIMO)}.',
            mascota,
        )

    # 7. El groomer no puede tener dos citas que se crucen
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
@rol_requerido(*ROLES_PELUQUERIA)
def comprobante_pdf(request, pk):
    """Comprobante de la cita de peluquería con la marca de Prados Pets."""
    cita = get_object_or_404(CitaPeluqueria.objects.select_related('groomer', 'mascota__id_dueno'), pk=pk)

    # La mascota viene del vínculo de la cita; las citas antiguas (sin vínculo) se buscan por nombre
    mascota = cita.mascota or Mascota.objects.filter(nombre=cita.nombre_mascota).first()

    # El precio y la duración salen de lo guardado en la cita: el PDF siempre coincide con la pantalla
    duracion = cita.duracion_estimada_min or 60
    inicio = timezone.localtime(cita.fecha_hora)
    return render_pdf(request, 'peluqueria/pdf_cita.html', {
        'cita': cita,
        'mascota': mascota,
        'dueno': mascota.id_dueno if mascota else None,
        'groomer': cita.groomer,
        'inicio': inicio,
        'entrega': inicio + timedelta(minutes=duracion),
        'duracion_texto': _etiqueta_duracion(duracion),
        'precio_formateado': _formatear_precio(cita.precio) if cita.precio else 'Valor no especificado',
        'recomendaciones': RECOMENDACIONES_PELUQUERIA,
    }, f'Peluqueria_{cita.pk:05d}_{slugify(cita.nombre_mascota)}')