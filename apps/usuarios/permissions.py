from functools import wraps
 
from django.contrib import messages
from django.shortcuts import redirect, render
 
# Nombres que se usaron en algunas vistas pero que no existen como rol en la
# base de datos. Se traducen al rol real para no tener que cambiar cada vista.
# (En la clínica, quien hace la recepción tiene el rol «auxiliar».)
ALIAS_ROLES = {
    "recepcionista": "auxiliar",
}
 
 
def _normalizar(nombre_rol):
    nombre = (nombre_rol or "").strip().lower()
    return ALIAS_ROLES.get(nombre, nombre)
 
 
def obtener_rol(usuario):
    """Devuelve el nombre del rol del usuario en minúsculas ('' si no tiene).
 
    El rol vive en la FK ``Usuario.id_rol`` (modelo ``Rol``, campo
    ``nombre_rol``). Antes se leía ``usuario.rol``, que no existe, y por eso
    ningún usuario que no fuera superusuario pasaba el control de permisos.
    """
    rol = getattr(usuario, "id_rol", None)
    return _normalizar(getattr(rol, "nombre_rol", ""))
 
 
def tiene_rol(usuario, *roles_permitidos):
    """True si el usuario es superusuario o tiene alguno de los roles dados."""
    if not getattr(usuario, "is_authenticated", False):
        return False
    if usuario.is_superuser:
        return True
    permitidos = {_normalizar(r) for r in roles_permitidos}
    return obtener_rol(usuario) in permitidos
 
 
def rol_requerido(*roles_permitidos):
    """
    Decorador que verifica si el usuario autenticado posee uno de los roles permitidos.
    Si no cumple con el rol, restringe el acceso y muestra un mensaje de advertencia.
 
    Uso:
        @login_required
        @rol_requerido("administrador", "veterinario")
        def mi_vista(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')
 
            if tiene_rol(request.user, *roles_permitidos):
                return view_func(request, *args, **kwargs)
 
            # Respuesta cuando no tiene permiso
            messages.error(request, "No tienes permiso para acceder a este módulo.")
            return render(request, '403.html', status=403)
 
        return _wrapped_view
    return decorator 
