from django.contrib import admin

from .models import CitaPeluqueria


def _puede_configurar_peluqueria(request):
    usuario = request.user
    return usuario.is_authenticated and (
        usuario.is_superuser or getattr(usuario, 'es_administrador', False)
    )


@admin.register(CitaPeluqueria)
class CitaPeluqueriaAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_mascota', 'raza', 'tamano', 'condicion_pelaje', 'servicio',
        'groomer', 'precio', 'comision_groomer', 'fecha_hora',
    )
    list_filter = ('servicio', 'tamano', 'fecha_hora')
    search_fields = ('nombre_mascota', 'raza', 'groomer__nombre_completo')
    readonly_fields = ('comision_groomer',)

    def has_module_permission(self, request):
        return _puede_configurar_peluqueria(request)

    def has_view_permission(self, request, obj=None):
        return _puede_configurar_peluqueria(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
