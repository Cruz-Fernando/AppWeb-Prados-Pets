from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from apps.agendamiento.models import Cita
from apps.directorio.models import Mascota
from apps.peluqueria.models import CitaPeluqueria
from .models import Hospitalizacion
from .forms import ConsultaMedicaForm, HospitalizacionForm


def _fechas_recordatorio(fecha_base, intervalo_dias, hoy):
    fecha_recordatorio = fecha_base
    if fecha_recordatorio < hoy:
        dias_transcurridos = (hoy - fecha_recordatorio).days
        ciclos = (dias_transcurridos + intervalo_dias - 1) // intervalo_dias
        fecha_recordatorio += timedelta(days=ciclos * intervalo_dias)
    return fecha_recordatorio, fecha_recordatorio + timedelta(days=intervalo_dias)


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

    citas_vacunacion = Cita.objects.select_related(
        'mascota',
        'mascota__id_dueno',
    ).filter(
        tipo_servicio='vacunacion',
    ).exclude(estado='cancelada').order_by('fecha', 'hora_inicio')
    citas_bano = CitaPeluqueria.objects.select_related(
        'mascota',
        'mascota__id_dueno',
    ).filter(
        mascota__isnull=False,
        servicio='BANO',
    ).order_by('fecha_hora')

    vacunas_programadas = []
    recordatorios_hoy = []
    for cita in citas_vacunacion:
        fecha_recordatorio, fecha_siguiente = _fechas_recordatorio(
            cita.fecha,
            cita.intervalo_recordatorio_dias,
            hoy,
        )
        recordatorio = {
            'cita_id': cita.pk,
            'mascota': cita.mascota,
            'servicio': cita.get_tipo_servicio_display(),
            'fecha_recordatorio': fecha_recordatorio,
            'fecha_siguiente': fecha_siguiente,
            'intervalo_dias': cita.intervalo_recordatorio_dias,
            'tipo': 'Vacunación',
        }
        vacunas_programadas.append(recordatorio)
        if fecha_recordatorio == hoy:
            recordatorios_hoy.append(recordatorio)

    banos_programados = []
    for cita in citas_bano:
        fecha_base = timezone.localdate(cita.fecha_hora)
        fecha_recordatorio, fecha_siguiente = _fechas_recordatorio(
            fecha_base,
            cita.intervalo_recordatorio_dias,
            hoy,
        )
        recordatorio = {
            'cita_id': cita.pk,
            'mascota': cita.mascota,
            'servicio': cita.get_servicio_display(),
            'fecha_recordatorio': fecha_recordatorio,
            'fecha_siguiente': fecha_siguiente,
            'intervalo_dias': cita.intervalo_recordatorio_dias,
            'tipo': 'Baño',
        }
        banos_programados.append(recordatorio)
        if fecha_recordatorio == hoy:
            recordatorios_hoy.append(recordatorio)

    vacunas_programadas.sort(key=lambda item: item['fecha_recordatorio'])
    banos_programados.sort(key=lambda item: item['fecha_recordatorio'])

    return render(request, 'clinico/recordatorios.html', {
        'vacunas_programadas': vacunas_programadas,
        'banos_programados': banos_programados,
        'recordatorios_hoy': recordatorios_hoy,
        'puede_editar_intervalos': puede_editar_intervalos,
    })


@login_required
def seleccionar_mascota_historial(request):
    mascotas = Mascota.objects.select_related('id_dueno').order_by('nombre')
    return render(request, 'clinico/seleccionar_mascota.html', {'mascotas': mascotas})


@login_required
def historial_clinico(request, mascota_id):
    mascota = get_object_or_404(
        Mascota.objects.select_related('id_dueno'),
        id_mascota=mascota_id,
    )
    form = ConsultaMedicaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        consulta = form.save(commit=False)
        consulta.mascota = mascota
        consulta.profesional = request.user
        consulta.save()
        messages.success(request, 'La consulta quedó registrada en el historial clínico.')
        return redirect('clinico:historial_clinico', mascota_id=mascota.id_mascota)

    consultas = mascota.historial_clinico.select_related('profesional').all()
    return render(request, 'clinico/historial_clinico.html', {
        'mascota': mascota,
        'form': form,
        'consultas': consultas,
    })

@login_required
def hospitalizacion_lista(request):
    pacientes_internados = Hospitalizacion.objects.filter(estado='ACTIVO')
    return render(request, 'clinico/hospitalizacion.html', {'pacientes': pacientes_internados})

@login_required
def ingresar_paciente(request):
    if request.method == 'POST':
        form = HospitalizacionForm(request.POST, request.FILES) # request.FILES es vital para subir PDFs/Imágenes
        if form.is_valid():
            form.save()
            messages.success(request, 'Paciente ingresado a hospitalización correctamente.')
            return redirect('clinico:hospitalizacion')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = HospitalizacionForm()
    
    return render(request, 'clinico/hospitalizacion_form.html', {'form': form})