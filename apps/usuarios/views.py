from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RolForm, UsuarioCreacionForm, UsuarioRolForm
from .models import Rol, Usuario
from .permissions import rol_requerido


# ---------------------------------------------------------------------
# Login con límite de intentos (protección contra fuerza bruta)
# ---------------------------------------------------------------------
MAX_INTENTOS_LOGIN = 5
BLOQUEO_LOGIN_SEGUNDOS = 15 * 60


def _ip_cliente(request):
    # Detrás del proxy de Railway, el último valor de X-Forwarded-For es el
    # que agrega el proxy más cercano (el más confiable).
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


class LoginSeguroView(LoginView):
    """
    LoginView de Django + bloqueo temporal tras MAX_INTENTOS_LOGIN fallos
    seguidos para la misma combinación IP + usuario. Si el usuario ya tiene
    sesión, lo manda directo al panel en vez de mostrar el login otra vez.
    """

    template_name = "usuarios/login.html"
    redirect_authenticated_user = True

    def _clave(self, request):
        usuario = (request.POST.get("username") or "").strip().lower()
        return f"login_fallos:{_ip_cliente(request)}:{usuario}"

    def post(self, request, *args, **kwargs):
        clave = self._clave(request)
        if cache.get(clave, 0) >= MAX_INTENTOS_LOGIN:
            form = self.get_form()
            form.add_error(
                None,
                "Demasiados intentos fallidos. Espera 15 minutos antes de volver a intentarlo.",
            )
            return self.render_to_response(
                self.get_context_data(form=form, bloqueado=True), status=429
            )
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        clave = self._clave(self.request)
        try:
            cache.add(clave, 0, BLOQUEO_LOGIN_SEGUNDOS)
            cache.incr(clave)
        except ValueError:  # la clave expiró justo entre add() e incr()
            cache.set(clave, 1, BLOQUEO_LOGIN_SEGUNDOS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._clave(self.request))
        return super().form_valid(form)


@login_required
def dashboard(request):
    context = {
        "es_administrador": request.user.es_administrador,
    }
    return render(request, "usuarios/dashboard.html", context)


# Roles base: el código los referencia por nombre, así que no se pueden
# renombrar ni eliminar (se rompería el control de acceso).
ROLES_BASE = ("administrador", "veterinario", "auxiliar", "groomer", "domiciliario")


def _administradores_activos(excluyendo_pk=None):
    """Usuarios activos con acceso total (superusuario o rol administrador)."""
    qs = Usuario.objects.filter(estado="activo").filter(
        Q(is_superuser=True) | Q(id_rol__nombre_rol="administrador")
    )
    if excluyendo_pk is not None:
        qs = qs.exclude(pk=excluyendo_pk)
    return qs


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
    # Se guarda el nombre original: el ModelForm modifica `rol` en memoria al validar.
    nombre_original = rol.nombre_rol
    if request.method == "POST":
        form = RolForm(request.POST, instance=rol)
        if form.is_valid():
            nuevo_nombre = form.cleaned_data["nombre_rol"]
            if nombre_original in ROLES_BASE and nuevo_nombre != nombre_original:
                form.add_error(
                    "nombre_rol",
                    f"El rol base '{nombre_original}' no se puede renombrar: "
                    "el sistema depende de ese nombre para los permisos.",
                )
            else:
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
    if rol.nombre_rol in ROLES_BASE:
        messages.error(
            request,
            f"El rol base '{rol.nombre_rol}' no se puede eliminar: el sistema depende de él.",
        )
        return redirect("usuarios:roles_lista")
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
            nuevo_rol = form.cleaned_data["id_rol"]
            nuevo_estado = form.cleaned_data["estado"]
            seguira_siendo_admin = usuario.is_superuser or nuevo_rol.nombre_rol == "administrador"
            sigue_activo = nuevo_estado == "activo"

            if usuario == request.user and not (seguira_siendo_admin and sigue_activo):
                form.add_error(
                    None,
                    "No puedes quitarte tu propio rol de administrador ni desactivar tu propia "
                    "cuenta: te quedarías sin acceso. Pídeselo a otro administrador.",
                )
            elif not (seguira_siendo_admin and sigue_activo) and not _administradores_activos(
                excluyendo_pk=usuario.pk
            ).exists():
                form.add_error(
                    None,
                    "Debe quedar al menos un administrador activo en el sistema.",
                )
            else:
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
    if (
        usuario.es_administrador
        and usuario.estado == "activo"
        and not _administradores_activos(excluyendo_pk=usuario.pk).exists()
    ):
        messages.error(request, "No se puede eliminar al último administrador activo.")
        return redirect("usuarios:usuarios_lista")

    if request.method == "POST":
        nombre = usuario.username
        usuario.delete()
        messages.success(request, f"Usuario '{nombre}' eliminado correctamente.")
        return redirect("usuarios:usuarios_lista")

    return render(
        request, "usuarios/usuario_confirmar_eliminar.html", {"usuario": usuario}
    )
