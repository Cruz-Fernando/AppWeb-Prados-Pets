from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RolForm, UsuarioCreacionForm, UsuarioRolForm
from .models import Rol, Usuario
from .permissions import rol_requerido


@login_required
def dashboard(request):
    context = {
        "es_administrador": request.user.es_administrador,
    }
    return render(request, "usuarios/dashboard.html", context)


# ---------------------------------------------------------------------
# HU02 — "Como administrador, quiero gestionar roles y permisos,
# para controlar qué ve cada tipo de usuario."
# ---------------------------------------------------------------------


@login_required
@rol_requerido("administrador")
def roles_lista(request):
    roles = Rol.objects.order_by("nombre_rol")
    return render(request, "usuarios/roles_lista.html", {"roles": roles})


@login_required
@rol_requerido("administrador")
def rol_nuevo(request):
    if request.method == "POST":
        form = RolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Rol creado correctamente.")
            return redirect("usuarios:roles_lista")
    else:
        form = RolForm()
    return render(request, "usuarios/rol_form.html", {"form": form, "modo": "nuevo"})


@login_required
@rol_requerido("administrador")
def rol_editar(request, pk):
    rol = get_object_or_404(Rol, pk=pk)
    if request.method == "POST":
        form = RolForm(request.POST, instance=rol)
        if form.is_valid():
            form.save()
            messages.success(request, "Rol actualizado correctamente.")
            return redirect("usuarios:roles_lista")
    else:
        form = RolForm(instance=rol)
    return render(
        request, "usuarios/rol_form.html", {"form": form, "modo": "editar", "rol": rol}
    )


@login_required
@rol_requerido("administrador")
def rol_eliminar(request, pk):
    rol = get_object_or_404(Rol, pk=pk)
    if request.method == "POST":
        try:
            rol.delete()
            messages.success(request, f"Rol '{rol.nombre_rol}' eliminado.")
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar '{rol.nombre_rol}': todavía hay usuarios "
                "con ese rol asignado. Reasígnalos primero.",
            )
        return redirect("usuarios:roles_lista")
    return render(request, "usuarios/rol_confirmar_eliminar.html", {"rol": rol})


@login_required
@rol_requerido("administrador")
def usuarios_lista(request):
    usuarios = Usuario.objects.select_related("id_rol").order_by("username")
    return render(request, "usuarios/usuarios_lista.html", {"usuarios": usuarios})


@login_required
@rol_requerido("administrador")
def usuario_nuevo(request):
    if request.method == "POST":
        form = UsuarioCreacionForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request, f"Usuario '{usuario.username}' registrado correctamente."
            )
            return redirect("usuarios:usuarios_lista")
    else:
        form = UsuarioCreacionForm()
    return render(request, "usuarios/usuario_nuevo.html", {"form": form})


@login_required
@rol_requerido("administrador")
def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == "POST":
        form = UsuarioRolForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect("usuarios:usuarios_lista")
    else:
        form = UsuarioRolForm(instance=usuario)
    return render(
        request, "usuarios/usuario_form.html", {"form": form, "usuario": usuario}
    )


@login_required
@rol_requerido("administrador")
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if usuario == request.user:
        messages.error(request, "No puedes eliminar tu propia cuenta de usuario.")
        return redirect("usuarios:usuarios_lista")

    if request.method == "POST":
        nombre = usuario.username
        usuario.delete()
        messages.success(request, f"Usuario '{nombre}' eliminado correctamente.")
        return redirect("usuarios:usuarios_lista")

    return render(
        request, "usuarios/usuario_confirmar_eliminar.html", {"usuario": usuario}
    )

