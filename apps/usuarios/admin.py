from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Rol, Usuario


def _es_admin(request):
    """Solo administradores (o superusuario) pueden gestionar Usuarios y Roles."""
    return request.user.is_superuser or getattr(request.user, "es_administrador", False)


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    model = Usuario
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Prados Pets", {"fields": ("id_rol", "nombre_completo", "telefono", "estado")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Prados Pets", {"fields": ("id_rol", "nombre_completo", "telefono", "estado")}),
    )
    list_display = ("username", "nombre_completo", "id_rol", "estado", "is_active")

    # RF: "El sistema restringe el acceso a módulos según el rol asignado" (HU01)
    def has_module_permission(self, request):
        return _es_admin(request)

    def has_view_permission(self, request, obj=None):
        return _es_admin(request)

    def has_add_permission(self, request):
        return _es_admin(request)

    def has_change_permission(self, request, obj=None):
        return _es_admin(request)

    def has_delete_permission(self, request, obj=None):
        return _es_admin(request)


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre_rol", "descripcion")

    def has_module_permission(self, request):
        return _es_admin(request)

    def has_view_permission(self, request, obj=None):
        return _es_admin(request)

    def has_add_permission(self, request):
        return _es_admin(request)

    def has_change_permission(self, request, obj=None):
        return _es_admin(request)

    def has_delete_permission(self, request, obj=None):
        return _es_admin(request)
