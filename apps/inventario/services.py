"""
Movimientos del inventario (simple: cada producto tiene su cantidad y una fecha).

Una sola puerta para sumar y restar unidades, la usen la consulta clínica, la
peluquería o la pantalla de Inventario:

  - descontar_stock(...)          resta unidades (consulta y peluquería, PB-17).
  - devolver_movimientos(...)     regresa lo que salió (anulación o cancelación).
  - registrar_entrada(...)        Añadir: suma unidades (compra o reposición).
  - registrar_salida_manual(...)  Quitar: resta unidades con su motivo.
  - retirar_producto(...)         saca el producto del inventario.

Reglas:
  - El stock nunca queda en negativo: si no alcanza, StockInsuficiente.
  - Un producto vencido no se descuenta solo en consultas ni en peluquería
    (sí se puede quitar a mano, por ejemplo para darlo de baja).
  - Todo queda en el Kardex y ocurre con bloqueo de fila, para que dos personas
    guardando al mismo tiempo no descuenten la misma unidad.
"""

from django.db import transaction
from django.utils import timezone

from .models import MovimientoInventario, Producto


class StockInsuficiente(Exception):
    """No hay unidades disponibles para el descuento pedido."""

    def __init__(self, producto, pedido, disponible, vencidas=0):
        self.producto = producto
        self.pedido = pedido
        self.disponible = disponible
        self.vencidas = vencidas
        if vencidas and not disponible:
            mensaje = (f"«{producto.nombre}» está vencido (venció el "
                       f"{producto.fecha_vencimiento:%d/%m/%Y}) y no se puede usar. "
                       "Dalo de baja en Inventario o actualiza su fecha si llegó mercancía nueva.")
        else:
            mensaje = (f"No hay stock suficiente de «{producto.nombre}»: pediste {pedido} "
                       f"y hay {disponible} disponible{'s' if disponible != 1 else ''}.")
        super().__init__(mensaje)


def disponibilidad(producto, hoy=None):
    """
    Devuelve (disponible, vencidas) sin modificar nada.
    Si el producto está vencido, todo su stock cuenta como vencido.
    """
    hoy = hoy or timezone.localdate()
    if producto.fecha_vencimiento and producto.fecha_vencimiento < hoy:
        return 0, producto.stock_actual
    return producto.stock_actual, 0


def _movimiento(producto, tipo, cantidad, precio, usuario, observacion, **extra):
    return MovimientoInventario.objects.create(
        producto=producto, tipo=tipo, cantidad=cantidad,
        precio_unitario_historico=precio, monto_total=precio * cantidad,
        usuario=usuario, observacion=(observacion or '')[:255], **extra,
    )


def _costo(producto):
    """Valor de una unidad que sale por baja: costo de compra (o precio de venta si no hay costo)."""
    return producto.precio_compra if producto.precio_compra and producto.precio_compra > 0 else producto.precio_venta


def _cantidad_valida(cantidad):
    cantidad = int(cantidad)
    if cantidad < 1:
        raise ValueError("La cantidad debe ser 1 o más.")
    return cantidad


# ---------------------------------------------------------------------------
# Descuento automático (consulta y peluquería · PB-17)
# ---------------------------------------------------------------------------

@transaction.atomic
def descontar_stock(producto_id, cantidad, *, tipo='SALIDA_CLINICA', usuario=None,
                    observacion='', registro_clinico=None, cita_peluqueria=None):
    """Resta unidades del producto y deja el movimiento. Lanza StockInsuficiente."""
    cantidad = _cantidad_valida(cantidad)
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    disponible, vencidas = disponibilidad(producto)
    if cantidad > disponible:
        raise StockInsuficiente(producto, cantidad, disponible, vencidas)

    producto.stock_actual -= cantidad
    producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])
    return _movimiento(
        producto, tipo, cantidad, producto.precio_venta, usuario, observacion,
        registro_clinico=registro_clinico,
        cita_peluqueria=cita_peluqueria,
        consulta_medica_id=registro_clinico.pk if registro_clinico else None,
    )


@transaction.atomic
def devolver_movimientos(movimientos, *, usuario=None, motivo=''):
    """Regresa al inventario las salidas indicadas que aún no se hayan devuelto."""
    entradas = []
    pendientes = (MovimientoInventario.objects.select_for_update()
                  .filter(pk__in=[m.pk for m in movimientos], devuelto=False, tipo__startswith='SALIDA'))
    for salida in pendientes:
        producto = Producto.objects.select_for_update().get(pk=salida.producto_id)
        producto.stock_actual += salida.cantidad
        producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])
        salida.devuelto = True
        salida.save(update_fields=['devuelto'])

        texto = f"Devolución de la salida #{salida.pk}" + (f": {motivo}" if motivo else "")
        entradas.append(_movimiento(
            producto, 'ENTRADA_DEVOLUCION', salida.cantidad, salida.precio_unitario_historico,
            usuario, texto,
            registro_clinico=salida.registro_clinico,
            cita_peluqueria=salida.cita_peluqueria,
            consulta_medica_id=salida.consulta_medica_id,
        ))
    return entradas


# ---------------------------------------------------------------------------
# Movimientos manuales desde la pantalla de Inventario
# ---------------------------------------------------------------------------

MOTIVOS_SALIDA = [
    ('USO_INTERNO', 'Uso interno de la clínica'),
    ('VENCIMIENTO', 'Vencimiento'),
    ('DANO', 'Daño o rotura'),
    ('PERDIDA', 'Pérdida o faltante'),
    ('VENTA', 'Venta en mostrador'),
    ('OTRO', 'Otro motivo'),
]


@transaction.atomic
def registrar_entrada(producto_id, cantidad, *, usuario=None, costo=None, fecha_vencimiento=None,
                      numero_lote='', nota=''):
    """
    Añadir: suma unidades (compra o reposición).
    Si se indica una fecha de vencimiento, pasa a ser la fecha del producto, con
    el lote indicado (o sin lote: el anterior ya no corresponde a esa fecha).
    Si solo se indica el lote, se actualiza el lote.
    """
    cantidad = _cantidad_valida(cantidad)
    numero_lote = (numero_lote or '').strip()
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    if costo is not None:
        producto.precio_compra = costo
    if fecha_vencimiento:
        producto.fecha_vencimiento = fecha_vencimiento
        producto.numero_lote = numero_lote or None
    elif numero_lote:
        producto.numero_lote = numero_lote
    producto.stock_actual += cantidad
    producto.save()
    texto = nota or "Reabastecimiento de stock"
    if numero_lote:
        texto += f" · Lote {numero_lote}"
    return _movimiento(producto, 'ENTRADA_COMPRA', cantidad, producto.precio_compra, usuario, texto)


@transaction.atomic
def registrar_salida_manual(producto_id, cantidad, *, motivo, usuario=None, nota=''):
    """
    Quitar: resta unidades con su motivo (uso interno, vencimiento, daño,
    pérdida, venta...). Aquí sí se puede quitar un producto vencido.
    """
    cantidad = _cantidad_valida(cantidad)
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    if cantidad > producto.stock_actual:
        raise StockInsuficiente(producto, cantidad, producto.stock_actual)

    producto.stock_actual -= cantidad
    producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])
    etiqueta = dict(MOTIVOS_SALIDA).get(motivo, 'Otro motivo')
    tipo = 'SALIDA_VENTA' if motivo == 'VENTA' else 'AJUSTE_MERMA'
    return _movimiento(producto, tipo, cantidad, _costo(producto), usuario,
                       f"Salida manual · {etiqueta}" + (f" · {nota}" if nota else ""))


@transaction.atomic
def retirar_producto(producto_id, *, usuario=None, motivo='OTRO', nota=''):
    """
    Saca un producto del inventario. No se borra: su historial queda en el
    Kardex y se puede reactivar. Si aún tenía unidades, se dan de baja todas.
    Devuelve el movimiento de baja, o None si no tenía stock.
    """
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    movimiento = None
    if producto.stock_actual > 0:
        etiqueta = dict(MOTIVOS_SALIDA).get(motivo, 'Otro motivo')
        movimiento = _movimiento(producto, 'AJUSTE_MERMA', producto.stock_actual, _costo(producto), usuario,
                                 f"Producto retirado del inventario · {etiqueta}" + (f" · {nota}" if nota else ""))
        producto.stock_actual = 0
    producto.activo = False
    producto.save(update_fields=['stock_actual', 'activo', 'fecha_actualizacion'])
    return movimiento


def avisos_stock_bajo(movimientos):
    """Textos para avisar qué productos quedaron agotados, en stock crítico o bajo (PB-21)."""
    from .alertas import aviso_tras_salida

    avisos, vistos = [], set()
    for mov in movimientos:
        if mov.producto_id in vistos:
            continue
        vistos.add(mov.producto_id)
        aviso = aviso_tras_salida(Producto.objects.get(pk=mov.producto_id))
        if aviso:
            avisos.append(aviso)
    return avisos


def descontar_stock_consulta(producto_id, cantidad, consulta_id, usuario=None):
    """Compatibilidad con el código anterior. Lanza ValueError si no hay stock suficiente."""
    try:
        return descontar_stock(producto_id, cantidad, tipo='SALIDA_CLINICA', usuario=usuario,
                               observacion=f"Uso en Consulta Clínica #{consulta_id}")
    except StockInsuficiente as error:
        raise ValueError(str(error)) from error