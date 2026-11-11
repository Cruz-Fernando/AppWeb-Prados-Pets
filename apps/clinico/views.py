from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.agendamiento.models import Cita
from apps.directorio.models import Mascota
from apps.peluqueria.models import CitaPeluqueria

from . import presentacion
from .forms import (
    AltaForm,
    AnularRegistroForm,
    EvolucionForm,
    HospitalizacionForm,
    RegistroClinicoForm,
)
from .models import (
    ConsultaMedica,
    EvolucionHospitalaria,
    Hospitalizacion,
    RegistroClinico,
    TrazaClinica,
)
from .pdf import render_pdf
from .recordatorios import calcular_recordatorios
from .registros import TIPOS, obtener_tipo


@login_required
def recordatorios(request):
    hoy = timezone.localdate()
    puede_editar_intervalos = (
        request.user.is_superuser
        or getattr(request.user, 'es_administrador', False)
    )

    if request.method == 'POST' and 'guardar_intervalo_recordatorio' in request.POST:
        if not puede_editar_intervalos:
            return HttpResponseForbidden(
                'Solo el patrocinador o un administrador puede cambiar los intervalos.'
            )

        tipo = request.POST.get('tipo_recordatorio')
        cita_id = request.POST.get('cita_id', '')
        intervalo_texto = request.POST.get('intervalo_recordatorio_dias', '')
        if tipo not in ('vacunacion', 'bano') or not cita_id.isdigit():
            return HttpResponseForbidden('La cita seleccionada no es válida.')

        try:
            intervalo_dias = int(intervalo_texto)
        except (TypeError, ValueError):
            messages.error(request, 'El intervalo debe ser un número entero de días.')
            return redirect('clinico:recordatorios')
        if intervalo_dias < 1:
            messages.error(request, 'El intervalo debe ser de al menos 1 día.')
            return redirect('clinico:recordatorios')

        if tipo == 'vacunacion':
            cita = get_object_or_404(
                Cita,
                pk=int(cita_id),
                tipo_servicio='vacunacion',
            )
        else:
            cita = get_object_or_404(
                CitaPeluqueria,
                pk=int(cita_id),
                servicio='BANO',
                mascota__isnull=False,
            )

        cita.intervalo_recordatorio_dias = intervalo_dias
        cita.save(update_fields=['intervalo_recordatorio_dias'])
        messages.success(request, 'El intervalo del recordatorio fue actualizado.')
        return redirect('clinico:recordatorios')

    # Una sola regla para la pantalla y el panel principal (apps/clinico/recordatorios.py)
    datos = calcular_recordatorios(hoy)

    return render(request, 'clinico/recordatorios.html', {
        'vacunas_programadas': datos['vacunas'],
        'banos_programados': datos['banos'],
        'recordatorios_hoy': datos['hoy'],
        'puede_editar_intervalos': puede_editar_intervalos,
    })




# ===========================================================================
# Permisos y trazabilidad
# ===========================================================================

def _rol(user):
    rol = getattr(user, 'id_rol', None)
    return (getattr(rol, 'nombre_rol', '') or '').lower()


def _es_admin(user):
    return user.is_superuser or getattr(user, 'es_administrador', False)


def puede_registrar(user):
    """Crear o editar registros clínicos, ingresar y dar de alta: médicos y admin."""
    return _es_admin(user) or _rol(user) == 'veterinario'


def puede_evolucionar(user):
    """Notas de evolución en hospitalización: también el personal auxiliar."""
    return puede_registrar(user) or _rol(user) == 'auxiliar'


def puede_editar(user, registro):
    return not registro.anulado and (
        _es_admin(user) or (puede_registrar(user) and registro.profesional_id == user.pk)
    )


def _ip(request):
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return (reenviada.split(',')[0].strip() or request.META.get('REMOTE_ADDR')) or None


def registrar_traza(request, mascota, accion, descripcion, **extra):
    return TrazaClinica.objects.create(
        mascota=mascota,
        usuario=request.user if request.user.is_authenticated else None,
        accion=accion,
        descripcion=descripcion[:255],
        ip=_ip(request),
        **extra,
    )


def _sin_permiso(request, mensaje='No tienes permiso para realizar esta acción.'):
    messages.error(request, mensaje)
    return render(request, '403.html', status=403)


def _nombre(user):
    if not user:
        return 'Sistema'
    return getattr(user, 'nombre_completo', '') or user.get_full_name() or user.username


def _a_texto(valor):
    """Representación legible de un valor para la bitácora de cambios."""
    if valor in (None, ''):
        return '—'
    if isinstance(valor, datetime):
        return timezone.localtime(valor).strftime('%d/%m/%Y %H:%M') if timezone.is_aware(valor) \
            else valor.strftime('%d/%m/%Y %H:%M')
    if isinstance(valor, date):
        return valor.strftime('%d/%m/%Y')
    if isinstance(valor, time):
        return valor.strftime('%H:%M')
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    if hasattr(valor, 'name') and hasattr(valor, 'url'):  # archivo
        return valor.name or '—'
    return str(valor)


def _fallecido(mascota):
    return (
        RegistroClinico.objects.filter(mascota=mascota, tipo='eutanasia', anulado=False).exists()
        or Hospitalizacion.objects.filter(mascota=mascota, condicion_alta='fallecido').exists()
    )


# ===========================================================================
# Historia clínica
# ===========================================================================

@login_required
def seleccionar_mascota_historial(request):
    q = request.GET.get('q', '').strip()
    mascotas = (
        Mascota.objects.select_related('id_dueno')
        .annotate(
            total_registros=Count('registros_clinicos', filter=Q(registros_clinicos__anulado=False),
                                  distinct=True),
            ultima_atencion=Max('registros_clinicos__fecha_atencion'),
        )
        .order_by('nombre')
    )
    if q:
        mascotas = mascotas.filter(
            Q(nombre__icontains=q) | Q(codigo_mascota__icontains=q)
            | Q(id_dueno__nombre_completo__icontains=q) | Q(id_dueno__telefono__icontains=q)
        )
    internados = set(Hospitalizacion.objects.filter(estado='ACTIVO').values_list('mascota_id', flat=True))
    return render(request, 'clinico/seleccionar_mascota.html', {
        'mascotas': mascotas, 'q': q, 'internados': internados,
    })


def _linea_de_tiempo(mascota, filtro_tipo=''):
    """Une registros, hospitalizaciones y consultas del formato anterior, por fecha."""
    eventos = []

    registros = (RegistroClinico.objects.filter(mascota=mascota)
                 .select_related('profesional', 'hospitalizacion'))
    if filtro_tipo and filtro_tipo not in ('hospitalizacion',):
        registros = registros.filter(tipo=filtro_tipo)
    if filtro_tipo != 'hospitalizacion':
        for r in registros:
            eventos.append({
                'clase': 'registro', 'fecha': r.fecha_atencion, 'obj': r,
                'tipo': r.definicion, 'resumen': presentacion.resumen_corto(r),
            })

    if filtro_tipo in ('', 'hospitalizacion'):
        for h in mascota.hospitalizaciones.select_related('profesional_ingreso').annotate(
                n_evol=Count('evoluciones')):
            eventos.append({'clase': 'hospitalizacion', 'fecha': h.fecha_ingreso, 'obj': h})

    if filtro_tipo in ('', 'consulta_general'):
        for c in ConsultaMedica.objects.filter(mascota=mascota).select_related('profesional'):
            eventos.append({'clase': 'consulta_antigua', 'fecha': c.fecha_consulta, 'obj': c})

    eventos.sort(key=lambda e: e['fecha'], reverse=True)
    return eventos


def _proximos_eventos(mascota):
    """Próximas vacunas, desparasitaciones y controles a partir de hoy."""
    hoy = timezone.localdate()
    proximos = []
    claves = {
        'vacunacion': ('proxima_dosis', 'Vacuna'),
        'desparasitacion': ('proxima_aplicacion', 'Desparasitación'),
        'cirugia': ('retiro_puntos', 'Retiro de puntos'),
    }
    vistos = set()
    for r in RegistroClinico.objects.filter(mascota=mascota, anulado=False).order_by('-fecha_atencion'):
        clave, etiqueta = claves.get(r.tipo, (None, None))
        fechas = []
        if clave and r.detalle.get(clave):
            nombre = r.detalle.get('vacuna') or r.detalle.get('producto') or r.detalle.get('procedimiento') or ''
            fechas.append((r.detalle[clave], f"{etiqueta}: {nombre}".strip(': ')))
        if r.proximo_control:
            fechas.append((r.proximo_control.isoformat(), f"Control · {r.definicion.nombre if r.definicion else ''}"))
        for iso, texto in fechas:
            try:
                fecha = date.fromisoformat(iso)
            except (TypeError, ValueError):
                continue
            if fecha >= hoy and (texto, fecha) not in vistos:
                vistos.add((texto, fecha))
                proximos.append({'fecha': fecha, 'texto': texto, 'registro': r,
                                 'dias': (fecha - hoy).days})
    return sorted(proximos, key=lambda p: p['fecha'])[:6]


@login_required
def historial_clinico(request, mascota_id):
    mascota = get_object_or_404(Mascota.objects.select_related('id_dueno'), id_mascota=mascota_id)
    vista = request.GET.get('vista', 'linea')
    filtro = request.GET.get('tipo', '')

    registros_validos = RegistroClinico.objects.filter(mascota=mascota, anulado=False)
    conteo = dict(registros_validos.values_list('tipo').annotate(n=Count('id')))
    ultimo_con_vitales = registros_validos.exclude(peso__isnull=True).order_by('-fecha_atencion').first()

    contexto = {
        'mascota': mascota,
        'tipos': TIPOS,
        'tipos_con_conteo': [(t, conteo.get(t.clave, 0)) for t in TIPOS],
        'vista': vista,
        'filtro': filtro,
        'conteo': conteo,
        'total': sum(conteo.values()),
        'hosp_activa': mascota.hospitalizaciones.filter(estado='ACTIVO').first(),
        'n_hospitalizaciones': mascota.hospitalizaciones.count(),
        'proximos': _proximos_eventos(mascota),
        'ultimo_peso': ultimo_con_vitales,
        'fallecido': _fallecido(mascota),
        'puede_registrar': puede_registrar(request.user),
    }
    if vista == 'traza':
        contexto['trazas'] = mascota.trazas_clinicas.select_related(
            'usuario', 'registro', 'hospitalizacion')[:300]
    else:
        contexto['eventos'] = _linea_de_tiempo(mascota, filtro)
    return render(request, 'clinico/historial_clinico.html', contexto)


@login_required
def nuevo_registro(request, mascota_id, tipo):
    mascota = get_object_or_404(Mascota.objects.select_related('id_dueno'), id_mascota=mascota_id)
    definicion = obtener_tipo(tipo)
    if not definicion:
        raise Http404('Tipo de registro no válido')
    if not puede_registrar(request.user):
        return _sin_permiso(request, 'Solo médicos veterinarios o administradores pueden registrar en la historia clínica.')

    initial = {}
    hosp_id = request.GET.get('hosp')
    if hosp_id and hosp_id.isdigit():
        initial['hospitalizacion'] = hosp_id

    form = RegistroClinicoForm(request.POST or None, request.FILES or None,
                               tipo=definicion, mascota=mascota, initial=initial)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            registro = form.save(commit=False)
            registro.profesional = request.user
            registro.save()
            registrar_traza(request, mascota, 'crear',
                            f"{registro.numero} · {definicion.nombre}: {registro.motivo}", registro=registro)

            if definicion.clave == 'eutanasia':
                for h in mascota.hospitalizaciones.filter(estado='ACTIVO'):
                    h.estado, h.condicion_alta = 'ALTA', 'fallecido'
                    h.fecha_alta = registro.fecha_atencion
                    h.profesional_alta = request.user
                    h.resumen_alta = h.resumen_alta or f"Eutanasia registrada en {registro.numero}."
                    h.save()
                    registrar_traza(request, mascota, 'alta',
                                    f"{h.numero} cerrada por eutanasia ({registro.numero})", hospitalizacion=h)

        messages.success(request, f"{definicion.nombre} registrada en la historia clínica ({registro.numero}).")
        if 'guardar_pdf' in request.POST:
            return redirect(f"{reverse('clinico:registro_detalle', args=[registro.pk])}?pdf=1")
        return redirect('clinico:registro_detalle', pk=registro.pk)
    if request.method == 'POST':
        messages.error(request, 'Revisa los campos marcados en rojo.')

    return render(request, 'clinico/registro_form.html', {
        'mascota': mascota, 'tipo': definicion, 'form': form, 'fallecido': _fallecido(mascota),
    })


@login_required
def registro_detalle(request, pk):
    registro = get_object_or_404(
        RegistroClinico.objects.select_related('mascota__id_dueno', 'profesional', 'anulado_por',
                                               'actualizado_por', 'hospitalizacion'),
        pk=pk,
    )
    return render(request, 'clinico/registro_detalle.html', {
        'r': registro,
        'mascota': registro.mascota,
        'tipo': registro.definicion,
        'vitales': presentacion.vitales(registro),
        'evaluacion': presentacion.evaluacion(registro),
        'especificos': presentacion.detalle_legible(registro),
        'trazas': registro.trazas.select_related('usuario'),
        'puede_editar': puede_editar(request.user, registro),
        'puede_anular': puede_editar(request.user, registro),
        'form_anular': AnularRegistroForm(),
        'auto_pdf': request.GET.get('pdf') == '1',
    })


@login_required
def editar_registro(request, pk):
    registro = get_object_or_404(RegistroClinico.objects.select_related('mascota__id_dueno'), pk=pk)
    if not puede_editar(request.user, registro):
        return _sin_permiso(request, 'Solo quien creó el registro o un administrador puede editarlo (y no si está anulado).')

    definicion = registro.definicion
    detalle_antes = dict(registro.detalle or {})
    form = RegistroClinicoForm(request.POST or None, request.FILES or None, instance=registro,
                               tipo=definicion, mascota=registro.mascota)

    if request.method == 'POST' and form.is_valid():
        specs = {c.nombre: c for c in definicion.campos}
        cambios = {}
        for nombre in form.changed_data:
            campo = form.fields[nombre]
            if nombre.startswith(form.PREFIJO):
                spec = specs[nombre[len(form.PREFIJO):]]
                antes = detalle_antes.get(spec.nombre)
                if (antes or None) == (form._a_json(form.cleaned_data.get(nombre)) or None):
                    continue
                antes = form._a_python(spec, antes)
            else:
                antes = form.initial.get(nombre)
            despues = form.cleaned_data.get(nombre)

            if hasattr(campo, 'queryset'):
                antes = campo.queryset.model.objects.filter(pk=antes).first() if antes else None
            elif getattr(campo, 'choices', None):
                opciones = dict(campo.choices)
                antes, despues = opciones.get(antes, antes), opciones.get(despues, despues)
            cambios[str(campo.label)] = [_a_texto(antes), _a_texto(despues)]

        with transaction.atomic():
            registro = form.save(commit=False)
            registro.actualizado_por = request.user
            registro.save()
            if cambios:
                registrar_traza(request, registro.mascota, 'editar',
                                f"{registro.numero}: {len(cambios)} campo(s) modificado(s)",
                                registro=registro, cambios=cambios)
        messages.success(request, 'Registro actualizado. Los cambios quedaron en la trazabilidad.'
                         if cambios else 'No hubo cambios que guardar.')
        return redirect('clinico:registro_detalle', pk=registro.pk)

    return render(request, 'clinico/registro_form.html', {
        'mascota': registro.mascota, 'tipo': definicion, 'form': form, 'registro': registro,
    })


@login_required
@require_POST
def anular_registro(request, pk):
    registro = get_object_or_404(RegistroClinico, pk=pk)
    if not puede_editar(request.user, registro):
        return _sin_permiso(request)
    form = AnularRegistroForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Debes indicar el motivo de la anulación.')
        return redirect('clinico:registro_detalle', pk=pk)

    registro.anulado = True
    registro.anulado_por = request.user
    registro.anulado_en = timezone.now()
    registro.motivo_anulacion = form.cleaned_data['motivo_anulacion']
    registro.save(update_fields=['anulado', 'anulado_por', 'anulado_en', 'motivo_anulacion', 'actualizado_en'])
    registrar_traza(request, registro.mascota, 'anular',
                    f"{registro.numero} anulado: {registro.motivo_anulacion}", registro=registro)
    messages.success(request, f"{registro.numero} fue anulado. Sigue visible en la historia para trazabilidad.")
    return redirect('clinico:registro_detalle', pk=pk)


@login_required
def registro_pdf(request, pk):
    registro = get_object_or_404(
        RegistroClinico.objects.select_related('mascota__id_dueno', 'profesional', 'anulado_por'), pk=pk)
    registrar_traza(request, registro.mascota, 'pdf', f"PDF de {registro.numero}", registro=registro)
    return render_pdf(request, 'clinico/pdf/registro.html', {
        'r': registro,
        'mascota': registro.mascota,
        'dueno': registro.mascota.id_dueno,
        'tipo': registro.definicion,
        'vitales': presentacion.vitales(registro),
        'evaluacion': presentacion.evaluacion(registro),
        'especificos': presentacion.detalle_legible(registro),
    }, f"{registro.numero}-{registro.tipo}-{registro.mascota.nombre}")


@login_required
def historia_pdf(request, mascota_id):
    mascota = get_object_or_404(Mascota.objects.select_related('id_dueno'), id_mascota=mascota_id)
    incluir_anulados = request.GET.get('anulados') == '1'
    registros = RegistroClinico.objects.filter(mascota=mascota).select_related('profesional')
    if not incluir_anulados:
        registros = registros.filter(anulado=False)
    registros = registros.order_by('fecha_atencion', 'pk')

    bloques = [{
        'r': r, 'tipo': r.definicion,
        'vitales': presentacion.vitales(r),
        'evaluacion': presentacion.evaluacion(r),
        'especificos': presentacion.detalle_legible(r),
    } for r in registros]

    hospitalizaciones = mascota.hospitalizaciones.select_related(
        'profesional_ingreso', 'profesional_alta').order_by('fecha_ingreso')
    registrar_traza(request, mascota, 'pdf', 'PDF de la historia clínica completa')
    return render_pdf(request, 'clinico/pdf/historia.html', {
        'mascota': mascota, 'dueno': mascota.id_dueno, 'bloques': bloques,
        'hospitalizaciones': hospitalizaciones,
        'consultas_antiguas': ConsultaMedica.objects.filter(mascota=mascota).select_related('profesional'),
        'fallecido': _fallecido(mascota),
    }, f"historia-clinica-{mascota.codigo_mascota}-{mascota.nombre}")


# ===========================================================================
# Hospitalización
# ===========================================================================

@login_required
def hospitalizacion_lista(request):
    activos = (Hospitalizacion.objects.filter(estado='ACTIVO')
               .select_related('mascota__id_dueno', 'profesional_ingreso')
               .annotate(n_evol=Count('evoluciones'), ultima_evol=Max('evoluciones__fecha'))
               .order_by('fecha_ingreso'))
    hace_30 = timezone.now() - timedelta(days=30)
    egresos = (Hospitalizacion.objects.filter(estado='ALTA', fecha_alta__gte=hace_30)
               .select_related('mascota__id_dueno').order_by('-fecha_alta')[:15])

    ahora = timezone.now()
    pacientes = list(activos)
    for p in pacientes:
        referencia = p.ultima_evol or p.fecha_ingreso
        p.horas_sin_evolucion = int((ahora - referencia).total_seconds() // 3600)

    return render(request, 'clinico/hospitalizacion.html', {
        'pacientes': pacientes,
        'egresos': egresos,
        'puede_registrar': puede_registrar(request.user),
        'criticos': sum(1 for p in pacientes if p.pronostico == 'grave'),
    })


@login_required
def ingresar_paciente(request):
    if not puede_registrar(request.user):
        return _sin_permiso(request, 'Solo médicos veterinarios o administradores pueden ingresar pacientes.')

    initial = {}
    if request.GET.get('mascota', '').isdigit():
        initial['mascota'] = request.GET['mascota']
    form = HospitalizacionForm(request.POST or None, request.FILES or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            hosp = form.save(commit=False)
            hosp.profesional_ingreso = request.user
            hosp.save()
            registrar_traza(request, hosp.mascota, 'ingreso',
                            f"{hosp.numero} · Ingreso: {hosp.motivo}", hospitalizacion=hosp)
        messages.success(request, f"{hosp.mascota.nombre} ingresó a hospitalización ({hosp.numero}).")
        return redirect('clinico:hospitalizacion_detalle', pk=hosp.pk)
    if request.method == 'POST':
        messages.error(request, 'Por favor, corrige los errores en el formulario.')

    return render(request, 'clinico/hospitalizacion_form.html', {'form': form})


@login_required
def hospitalizacion_detalle(request, pk):
    hosp = get_object_or_404(
        Hospitalizacion.objects.select_related('mascota__id_dueno', 'profesional_ingreso', 'profesional_alta'),
        pk=pk,
    )
    form = None
    if hosp.activa and puede_evolucionar(request.user):
        form = EvolucionForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            evol = form.save(commit=False)
            evol.hospitalizacion = hosp
            evol.profesional = request.user
            evol.save()
            registrar_traza(request, hosp.mascota, 'evolucion',
                            f"{hosp.numero} · Evolución {evol.fecha:%d/%m %H:%M}: {evol.get_estado_general_display()}",
                            hospitalizacion=hosp)
            messages.success(request, 'Evolución registrada.')
            return redirect('clinico:hospitalizacion_detalle', pk=pk)

    return render(request, 'clinico/hospitalizacion_detalle.html', {
        'h': hosp,
        'mascota': hosp.mascota,
        'form': form,
        'evoluciones': hosp.evoluciones.select_related('profesional'),
        'registros': hosp.registros.select_related('profesional'),
        'vitales_ingreso': presentacion.vitales(hosp),
        'tipos': TIPOS,
        'puede_registrar': puede_registrar(request.user),
    })


@login_required
def dar_alta(request, pk):
    hosp = get_object_or_404(Hospitalizacion.objects.select_related('mascota__id_dueno'), pk=pk)
    if not puede_registrar(request.user):
        return _sin_permiso(request, 'Solo médicos veterinarios o administradores pueden dar de alta.')
    if not hosp.activa:
        messages.info(request, 'Este paciente ya fue dado de alta.')
        return redirect('clinico:hospitalizacion_detalle', pk=pk)

    form = AltaForm(request.POST or None, instance=hosp)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            hosp = form.save(commit=False)
            hosp.estado = 'ALTA'
            hosp.fecha_alta = timezone.now()
            hosp.profesional_alta = request.user
            hosp.save()
            registrar_traza(request, hosp.mascota, 'alta',
                            f"{hosp.numero} · Alta: {hosp.get_condicion_alta_display()}", hospitalizacion=hosp)
        messages.success(request, f"{hosp.mascota.nombre} fue dado de alta. Ya puedes descargar la epicrisis.")
        return redirect('clinico:hospitalizacion_detalle', pk=pk)

    return render(request, 'clinico/hospitalizacion_alta.html', {'h': hosp, 'mascota': hosp.mascota, 'form': form})


@login_required
def hospitalizacion_pdf(request, pk):
    hosp = get_object_or_404(
        Hospitalizacion.objects.select_related('mascota__id_dueno', 'profesional_ingreso', 'profesional_alta'),
        pk=pk,
    )
    registrar_traza(request, hosp.mascota, 'pdf', f"PDF de {hosp.numero}", hospitalizacion=hosp)
    return render_pdf(request, 'clinico/pdf/hospitalizacion.html', {
        'h': hosp,
        'mascota': hosp.mascota,
        'dueno': hosp.mascota.id_dueno,
        'vitales_ingreso': presentacion.vitales(hosp),
        'evoluciones': hosp.evoluciones.select_related('profesional').order_by('fecha'),
        'registros': hosp.registros.filter(anulado=False).select_related('profesional').order_by('fecha_atencion'),
    }, f"{hosp.numero}-{hosp.mascota.nombre}")