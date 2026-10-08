from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def rol_requerido(*roles_permitidos):
    """
    Restringe una vista a usuarios cuyo Usuario.id_rol.nombre_rol esté
    dentro de roles_permitidos. Los superusuarios siempre pasan.

    Si el usuario no tiene permiso, se le redirige al panel con un
    mensaje de error en vez de mostrarle una página de error técnica.

    Uso:
        @login_required
        @rol_requerido("administrador")
        def gestionar_usuarios(request):
            ...
    """

    def decorador(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            rol = getattr(request.user, "id_rol", None)
            if rol and rol.nombre_rol in roles_permitidos:
                return view_func(request, *args, **kwargs)

            messages.error(request, "No tienes permiso para acceder a ese módulo.")
            return redirect("usuarios:dashboard")

        return _wrapped

    return decorador
