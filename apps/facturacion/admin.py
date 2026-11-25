from django.contrib import admin

from .models import Factura, ItemFactura, MovimientoCaja


class SoloLectura(admin.ModelAdmin):
    """Las facturas y la caja se manejan desde la aplicación: aquí solo se consultan (nada se borra)."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ItemFacturaInline(admin.TabularInline):
    model = ItemFactura
    extra = 0
    can_delete = False
    fields = ('tipo', 'descripcion', 'cantidad', 'precio_unitario', 'subtotal', 'vigente')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Factura)
class FacturaAdmin(SoloLectura):
    list_display = ('numero_display', 'dueno', 'estado', 'fecha', 'medio_pago', 'total')
    list_filter = ('estado', 'medio_pago')
    search_fields = ('numero', 'dueno__nombre_completo', 'dueno__telefono')
    inlines = [ItemFacturaInline]


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(SoloLectura):
    list_display = ('fecha', 'tipo', 'categoria', 'monto', 'descripcion', 'factura')
    list_filter = ('tipo', 'categoria')
    search_fields = ('descripcion',)
