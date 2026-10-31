from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from apps.directorio.models import Mascota
from .models import Hospitalizacion
from .forms import ConsultaMedicaForm, HospitalizacionForm


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