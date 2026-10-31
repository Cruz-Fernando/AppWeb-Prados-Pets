from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Hospitalizacion
from .forms import HospitalizacionForm

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