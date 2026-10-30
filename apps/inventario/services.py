from django.db import transaction
from .models import Producto, MovimientoInventario


def descontar_stock_consulta(producto_id, cantidad, consulta_id, usuario=None):
    """
    Función helper para descontar inventario desde el módulo clínico.
    """
    with transaction.atomic():
        producto = Producto.objects.select_for_update().get(id=producto_id)
        
        if producto.stock_actual < cantidad:
            raise ValueError(f"Stock insuficiente de {producto.nombre}. Disponible: {producto.stock_actual}")
            
        producto.stock_actual -= cantidad
        producto.save()
        
        movimiento = MovimientoInventario.objects.create(
            producto=producto,
            tipo='SALIDA_CLINICA',
            cantidad=cantidad,
            precio_unitario_historico=producto.precio_venta,
            monto_total=producto.precio_venta * cantidad,
            usuario=usuario,
            consulta_medica_id=consulta_id,
            observacion=f"Uso en Consulta Clínica #{consulta_id}"
        )
        return movimiento