from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse

from apps.directorio.forms import MascotaForm, VacunacionForm
from apps.usuarios.permissions import rol_requerido
from .models import Dueno, Mascota


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def registrar_dueno(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        correo = request.POST.get('correo', '').strip()

        try:
            dueno = Dueno(
                nombre_completo=nombre,
                telefono=telefono,
                direccion=direccion,
            )
            if hasattr(dueno, 'correo'):
                dueno.correo = correo
            dueno.save()

            messages.success(request, '¡Dueño registrado con éxito!')
            return redirect('registrar_dueno')

        except IntegrityError:
            messages.error(
                request,
                f"Error [ERR-001]: El número de teléfono '{telefono}' ya está registrado. "
                "Causa: el teléfono debe ser único. Solución: verifica el número o usa uno diferente."
            )
            return render(request, 'directorio/dueno_form.html', {
                'nombre': nombre,
                'telefono': telefono,
                'direccion': direccion,
                'correo': correo,
            })

    return render(request, 'directorio/dueno_form.html')


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def editar_dueno(request, dueno_id):
    """
    SW-02 / RF04 / PB-06: Edición de propietarios.
    Actualiza nombre, teléfono, dirección y correo verificando unicidad de teléfono.
    """
    dueno = get_object_or_404(Dueno, pk=dueno_id)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        correo = request.POST.get('correo', '').strip()

        try:
            dueno.nombre_completo = nombre
            dueno.telefono = telefono
            dueno.direccion = direccion
            if hasattr(dueno, 'correo'):
                dueno.correo = correo
            dueno.save()

            messages.success(request, '¡Propietario actualizado con éxito!')
            return redirect('buscar_directorio')

        except IntegrityError:
            messages.error(
                request,
                f"Error: El número de teléfono '{telefono}' ya está registrado con otro propietario. Debe ser único."
            )
            return render(request, 'directorio/dueno_form.html', {
                'dueno': dueno,
                'nombre': nombre,
                'telefono': telefono,
                'direccion': direccion,
                'correo': correo,
                'es_edicion': True,
            })

    return render(request, 'directorio/dueno_form.html', {
        'dueno': dueno,
        'nombre': dueno.nombre_completo,
        'telefono': dueno.telefono,
        'direccion': dueno.direccion,
        'correo': getattr(dueno, 'correo', ''),
        'es_edicion': True,
    })


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def lista_duenos(request):
    """Listado completo y numerado de dueños registrados."""
    duenos = Dueno.objects.all().order_by('id_dueno')
    return render(request, 'directorio/lista_duenos.html', {'duenos': duenos})


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def lista_mascotas(request):
    """Listado completo y numerado de mascotas registradas con su dueño."""
    mascotas = Mascota.objects.select_related('id_dueno').all().order_by('id_mascota')
    return render(request, 'directorio/lista_mascotas.html', {'mascotas': mascotas})


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def registrar_mascota(request):
    if request.method == 'POST':
        form = MascotaForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                form.add_error(None, 'No se pudo guardar la mascota. El registro generado ya existe o hay un conflicto con los datos. Intenta nuevamente.')
            else:
                messages.success(request, '¡Mascota registrada con éxito!')
                return redirect('buscar_directorio')
    else:
        form = MascotaForm()

    return render(request, 'directorio/mascota_form.html', {'form': form})


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def editar_mascota(request, mascota_id):
    mascota = get_object_or_404(
        Mascota.objects.select_related('id_dueno'),
        id_mascota=mascota_id,
    )
    form = MascotaForm(instance=mascota)
    vacunacion_form = VacunacionForm()

    if request.method == 'POST' and 'guardar_vacunacion' in request.POST:
        vacunacion_form = VacunacionForm(request.POST)
        if vacunacion_form.is_valid():
            antecedente = vacunacion_form.save(commit=False)
            antecedente.mascota = mascota
            antecedente.save()
            messages.success(request, 'Antecedente de vacunación registrado.')
            return redirect('editar_mascota', mascota_id=mascota.id_mascota)
    elif request.method == 'POST':
        form = MascotaForm(request.POST, instance=mascota)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                form.add_error(
                    None,
                    'No se pudo actualizar la mascota por un conflicto con los datos. Intenta nuevamente.',
                )
            else:
                messages.success(request, '¡Mascota actualizada con éxito!')
                return redirect('editar_mascota', mascota_id=mascota.id_mascota)

    return render(request, 'directorio/mascota_form.html', {
        'form': form,
        'mascota': mascota,
        'vacunacion_form': vacunacion_form,
        'antecedentes_vacunacion': mascota.antecedentes_vacunacion.all(),
    })


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def buscar_directorio(request):
    """
    HU05 — "Como recepcionista, quiero buscar un dueño o mascota,
    para atenderlo rápidamente."

    Sirve tanto la página completa (para GET normal / sin JS) como
    respuestas JSON para la búsqueda en tiempo real vía fetch().
    """
    q = request.GET.get('q', '').strip()
    duenos = Dueno.objects.none()
    mascotas = Mascota.objects.none()

    if q:
        duenos = Dueno.objects.filter(
            Q(nombre_completo__icontains=q) | Q(telefono__icontains=q)
        ).order_by('nombre_completo')[:20]

        mascotas = Mascota.objects.select_related('id_dueno').filter(
            Q(nombre__icontains=q)
            | Q(id_dueno__nombre_completo__icontains=q)
            | Q(id_dueno__telefono__icontains=q)
        ).order_by('nombre')[:20]

    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if es_ajax:
        return JsonResponse({
            'duenos': [
                {
                    'id': d.id_dueno,
                    'nombre_completo': d.nombre_completo,
                    'telefono': d.telefono,
                    'direccion': d.direccion,
                    'url_edicion': reverse('editar_dueno', args=[d.id_dueno]),
                }
                for d in duenos
            ],
            'mascotas': [
                {
                    'id': m.id_mascota,
                    'nombre': m.nombre,
                    'especie': m.get_especie_display(),
                    'dueno_nombre': m.id_dueno.nombre_completo,
                    'dueno_telefono': m.id_dueno.telefono,
                    'url_edicion': reverse('editar_mascota', args=[m.id_mascota]),
                }
                for m in mascotas
            ],
        })

    return render(request, 'directorio/buscar.html', {'q': q, 'duenos': duenos, 'mascotas': mascotas})


@login_required
@rol_requerido('administrador', 'veterinario', 'recepcionista')
def autocomplete_duenos(request):
    q = request.GET.get('q', '').strip()
    resultados = []
    if q:
        duenos = Dueno.objects.filter(
            Q(nombre_completo__icontains=q) | Q(telefono__icontains=q)
        ).order_by('nombre_completo')[:15]
        for d in duenos:
            texto = f"{d.nombre_completo} ({d.telefono})" if d.telefono else d.nombre_completo
            resultados.append({
                'id': d.id_dueno,
                'texto': texto,
            })
    return JsonResponse({'resultados': resultados})