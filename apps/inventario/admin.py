from django.contrib import admin
from .models import (
    CategoriaProducto, 
    Proveedor, 
    Servicio, 
    Producto, 
    Medicamento, 
    StockLote, 
    MovimientoInventario, 
    Venta, 
    DetalleVenta
)


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit_identificacion', 'telefono', 'email')
    search_fields = ('nombre', 'nit_identificacion')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'precio', 'activo')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'codigo_barras', 'nombre', 'categoria', 'precio_compra', 'precio_venta', 'stock_actual', 'stock_minimo', 'activo')
    list_filter = ('categoria', 'activo', 'proveedor')
    search_fields = ('codigo', 'codigo_barras', 'nombre')


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'principio_activo', 'concentracion', 'presentacion', 'requiere_receta')
    list_filter = ('requiere_receta', 'presentacion')
    search_fields = ('producto__nombre', 'principio_activo')


@admin.register(StockLote)
class StockLoteAdmin(admin.ModelAdmin):
    list_display = ('numero_lote', 'producto', 'fecha_vencimiento', 'cantidad', 'fecha_ingreso')
    list_filter = ('fecha_vencimiento',)
    search_fields = ('numero_lote', 'producto__nombre')


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'cantidad', 'precio_unitario_historico', 'monto_total', 'fecha', 'usuario')
    list_filter = ('tipo', 'fecha')
    search_fields = ('producto__nombre', 'observacion')


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'usuario', 'total')
    list_filter = ('fecha',)
    inlines = [DetalleVentaInline]