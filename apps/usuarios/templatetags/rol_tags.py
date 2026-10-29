"""
Template tags de permisos de rol para Prados Pets.

Uso en plantillas:
    {% load rol_tags %}
    {% if user|puede:'directorio' %}...{% endif %}
"""
from django import template

register = template.Library()

# Mapa de módulo → roles que tienen acceso.
# 'administrador' siempre tiene acceso a todo (ver filtro `puede`).
_PERMISOS = {
    "directorio":      {"administrador", "recepcion", "auxiliar", "veterinario"},
    "citas":           {"administrador", "recepcion", "auxiliar", "veterinario"},
    "calendario":      {"administrador", "recepcion", "auxiliar", "veterinario", "groomer"},
    "hospitalizacion": {"administrador", "veterinario", "auxiliar"},
    "peluqueria":      {"administrador", "recepcion", "auxiliar", "groomer"},
    "dashboard":       {"administrador", "recepcion", "auxiliar", "veterinario", "groomer"},
    "sistema":         {"administrador"},
}


@register.filter(name="puede")
def puede(user, modulo: str) -> bool:
    """
    Devuelve True si el usuario tiene permiso para acceder al módulo.
    Superusuarios y administradores siempre tienen acceso a todo.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    rol = getattr(getattr(user, "id_rol", None), "nombre_rol", "").lower()
    if rol == "administrador":
        return True
    roles_permitidos = _PERMISOS.get(modulo, set())
    return rol in roles_permitidos


@register.simple_tag(takes_context=True)
def rol_actual(context) -> str:
    """Devuelve el nombre del rol del usuario actual (minúsculas)."""
    user = context.get("user")
    if not user or not user.is_authenticated:
        return ""
    return getattr(getattr(user, "id_rol", None), "nombre_rol", "").lower()
