from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse

from apps.directorio.forms import MascotaForm
from .models import Dueno, Mascota


@login_required
def registrar_dueno(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()

        try:
            Dueno.objects.create(
                nombre_completo=nombre,
                telefono=telefono,
                direccion=direccion,
            )
            messages.success(request, '¡Dueño registrado con éxito!')
            return redirect('registrar_dueno')

        except IntegrityError:
            messages.error(
                request,
                f"Error [ERR-001]: El número de teléfono '{telefono}' ya está registrado. "
                "Causa: el teléfono debe ser único. Solución: verifica el número o usa uno diferente."
            )
            # Conservamos lo escrito para no obligar a retipear todo
            return render(request, 'directorio/dueno_form.html', {
                'nombre': nombre, 'telefono': telefono, 'direccion': direccion,
            })

    return render(request, 'directorio/dueno_form.html')


@login_required
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
                }
                for m in mascotas
            ],
        })

    return render(request, 'directorio/buscar.html', {'q': q, 'duenos': duenos, 'mascotas': mascotas})


@login_required
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

