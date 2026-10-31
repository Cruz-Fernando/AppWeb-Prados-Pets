from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages

def rol_requerido(*roles_permitidos):
    """
    Decorador que verifica si el usuario autenticado posee uno de los roles permitidos.
    Si no cumple con el rol, restringe el acceso y muestra un mensaje de advertencia.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')

            # El superadministrador de Django siempre tiene acceso completo
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Obtener el nombre del rol del usuario (ajustar si tu modelo usa 'rol', 'perfil.rol' o 'groups')
            user_rol = getattr(request.user, 'rol', None)
            if hasattr(user_rol, 'lower'):
                user_rol = user_rol.lower()

            # Normalizar los roles permitidos a minúsculas
            roles_normalizados = [r.lower() for r in roles_permitidos]

            if user_rol in roles_normalizados:
                return view_func(request, *args, **kwargs)

            # Respuesta cuando no tiene permiso
            messages.error(request, "No tienes permiso para acceder a este módulo.")
            return render(request, '403.html', status=403)

        return _wrapped_view
    return decorator