"""
Insumos que gasta cada servicio de peluquería (PB-17 / RF10).

Qué se gasta lo configura el personal en Inventario › Insumos por servicio
(modelo inventario.InsumoServicio). Al agendar la cita se descuentan del
inventario; si la cita se cancela, vuelven al inventario.

Un insumo con tamaño vacío aplica a todas las mascotas. Si para el mismo
producto hay una regla general y otra del tamaño de la mascota, manda la del
tamaño (por ejemplo: champú ×1 en general, ×2 para perros grandes).
"""

from apps.inventario.models import InsumoServicio
from apps.inventario.services import descontar_stock, disponibilidad, devolver_movimientos


def insumos_para(servicio, tamano):
    """Lista [(producto, cantidad)] que gasta el servicio para ese tamaño de mascota."""
    tamano = (tamano or '').upper()
    elegidos = {}
    reglas = (InsumoServicio.objects.filter(servicio=servicio, tamano__in=['', tamano],
                                            producto__activo=True)
              .select_related('producto').order_by('tamano'))   # '' primero, el tamaño después
    for regla in reglas:
        elegidos[regla.producto_id] = (regla.producto, regla.cantidad)
    return list(elegidos.values())


def descontar_insumos_cita(cita, usuario=None):
    """Descuenta del inventario los insumos de la cita. Lanza StockInsuficiente si algo no alcanza."""
    movimientos = []
    for producto, cantidad in insumos_para(cita.servicio, cita.tamano):
        movimientos.append(descontar_stock(
            producto.pk, cantidad,
            tipo='SALIDA_PELUQUERIA',
            usuario=usuario,
            observacion=f"Peluquería #{cita.pk} · {cita.get_servicio_display()} · {cita.nombre_mascota}",
            cita_peluqueria=cita,
        ))
    return movimientos


def devolver_insumos_cita(cita, usuario=None):
    """Regresa al inventario lo que se descontó por la cita (se usa al cancelarla)."""
    return devolver_movimientos(list(cita.insumos_usados), usuario=usuario,
                                motivo=f"Cita de peluquería #{cita.pk} cancelada")


def vista_previa():
    """
    Para el formulario de agendar: qué se descontará en cada servicio y tamaño.
    {'BANO': {'': [...], 'GRANDE': [...]}, ...} con nombre, cantidad y disponible.
    """
    previa = {}
    for regla in InsumoServicio.objects.filter(producto__activo=True).select_related('producto'):
        previa.setdefault(regla.servicio, {}).setdefault(regla.tamano, []).append({
            'producto': regla.producto_id,
            'nombre': regla.producto.nombre,
            'cantidad': regla.cantidad,
            'disponible': disponibilidad(regla.producto)[0],
        })
    return previa