"""
Descuento automático del stock (PB-17 / RF10).

Una sola puerta para sacar y devolver mercancía del inventario, la usen la
consulta clínica o la peluquería:

  - descontar_stock(...)        saca unidades y deja el movimiento en el Kardex.
  - devolver_movimientos(...)   regresa al inventario lo que salió (anulación
                                de un registro o cancelación de una cita).

Reglas:
  - Nunca se deja el stock en negativo: si no alcanza, se lanza
    StockInsuficiente y no se descuenta nada.
  - Se sale primero del lote que vence antes (FEFO). Los lotes vencidos no se
    usan. Las unidades sin lote (creadas a mano) se usan al final.
  - Todo ocurre dentro de una transacción con bloqueo de fila, para que dos
    personas guardando al mismo tiempo no descuenten la misma unidad.
"""

from django.db import transaction
from django.utils import timezone

from .models import MovimientoInventario, Producto, StockLote


class StockInsuficiente(Exception):
    """No hay unidades disponibles para el descuento pedido."""

    def __init__(self, producto, pedido, disponible, vencidas=0):
        self.producto = producto
        self.pedido = pedido
        self.disponible = disponible
        self.vencidas = vencidas
        mensaje = (
            f"No hay stock suficiente de «{producto.nombre}»: pediste {pedido} "
            f"y hay {disponible} disponible{'s' if disponible != 1 else ''}."
        )
        if vencidas:
            mensaje += f" Hay {vencidas} unidad{'es' if vencidas != 1 else ''} vencida{'s' if vencidas != 1 else ''} que no se pueden usar."
        super().__init__(mensaje)


def disponibilidad(producto, hoy=None):
    """
    Devuelve (disponible, vencidas) sin modificar nada.

    disponible = unidades de lotes vigentes + unidades sin lote,
    sin pasar nunca del stock_actual del producto.
    """
    hoy = hoy or timezone.localdate()
    lotes = list(producto.lotes.filter(cantidad__gt=0))
    en_lotes = sum(l.cantidad for l in lotes)
    vencidas = sum(l.cantidad for l in lotes if l.fecha_vencimiento and l.fecha_vencimiento < hoy)
    sin_lote = max(producto.stock_actual - en_lotes, 0)
    disponible = min(en_lotes - vencidas + sin_lote, producto.stock_actual)
    return max(disponible, 0), vencidas


def _orden_fefo(lote):
    # Primero los que tienen fecha (el que vence antes), después los que no tienen fecha.
    return (lote.fecha_vencimiento is None, lote.fecha_vencimiento or timezone.localdate(), lote.fecha_ingreso, lote.pk)


@transaction.atomic
def descontar_stock(producto_id, cantidad, *, tipo='SALIDA_CLINICA', usuario=None,
                    observacion='', registro_clinico=None, cita_peluqueria=None):
    """
    Saca `cantidad` unidades del producto y registra el movimiento.

    Devuelve el MovimientoInventario creado. Lanza StockInsuficiente si no alcanza.
    """
    cantidad = int(cantidad)
    if cantidad < 1:
        raise ValueError("La cantidad a descontar debe ser 1 o más.")

    hoy = timezone.localdate()
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    lotes = list(StockLote.objects.select_for_update().filter(producto=producto, cantidad__gt=0))

    en_lotes = sum(l.cantidad for l in lotes)
    vigentes = sorted((l for l in lotes if not (l.fecha_vencimiento and l.fecha_vencimiento < hoy)), key=_orden_fefo)
    vencidas = en_lotes - sum(l.cantidad for l in vigentes)
    sin_lote = max(producto.stock_actual - en_lotes, 0)
    disponible = max(min(en_lotes - vencidas + sin_lote, producto.stock_actual), 0)
    if cantidad > disponible:
        raise StockInsuficiente(producto, cantidad, disponible, vencidas)

    usados, falta = [], cantidad
    for lote in vigentes:
        if not falta:
            break
        toma = min(lote.cantidad, falta)
        lote.cantidad -= toma
        lote.save(update_fields=['cantidad'])
        usados.append({'lote': lote.pk, 'numero': lote.numero_lote, 'cantidad': toma})
        falta -= toma
    # Lo que falte sale de las unidades sin lote (ya se comprobó que alcanzan)

    producto.stock_actual -= cantidad
    producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])

    if usados:
        detalle_lotes = ', '.join(f"lote {u['numero']} ×{u['cantidad']}" for u in usados)
        observacion = f"{observacion} ({detalle_lotes})" if observacion else detalle_lotes

    return MovimientoInventario.objects.create(
        producto=producto,
        tipo=tipo,
        cantidad=cantidad,
        precio_unitario_historico=producto.precio_venta,
        monto_total=producto.precio_venta * cantidad,
        usuario=usuario,
        observacion=observacion[:255],
        registro_clinico=registro_clinico,
        cita_peluqueria=cita_peluqueria,
        consulta_medica_id=registro_clinico.pk if registro_clinico else None,
        lotes=usados or None,
    )


@transaction.atomic
def devolver_movimientos(movimientos, *, usuario=None, motivo=''):
    """
    Regresa al inventario las salidas indicadas que aún no se hayan devuelto.

    Cada unidad vuelve al mismo lote del que salió (si el lote ya no existe,
    queda como unidad sin lote). Devuelve la lista de movimientos de entrada.
    """
    entradas = []
    pendientes = (MovimientoInventario.objects.select_for_update()
                  .filter(pk__in=[m.pk for m in movimientos], devuelto=False, tipo__startswith='SALIDA'))
    for salida in pendientes:
        producto = Producto.objects.select_for_update().get(pk=salida.producto_id)
        for usado in salida.lotes or []:
            lote = StockLote.objects.select_for_update().filter(pk=usado.get('lote'), producto=producto).first()
            if lote:
                lote.cantidad += int(usado.get('cantidad') or 0)
                lote.save(update_fields=['cantidad'])
        producto.stock_actual += salida.cantidad
        producto.save(update_fields=['stock_actual', 'fecha_actualizacion'])

        salida.devuelto = True
        salida.save(update_fields=['devuelto'])

        texto = f"Devolución de la salida #{salida.pk}"
        if motivo:
            texto += f": {motivo}"
        entradas.append(MovimientoInventario.objects.create(
            producto=producto,
            tipo='ENTRADA_DEVOLUCION',
            cantidad=salida.cantidad,
            precio_unitario_historico=salida.precio_unitario_historico,
            monto_total=salida.monto_total,
            usuario=usuario,
            observacion=texto[:255],
            registro_clinico=salida.registro_clinico,
            cita_peluqueria=salida.cita_peluqueria,
            consulta_medica_id=salida.consulta_medica_id,
            lotes=salida.lotes,
        ))
    return entradas


def avisos_stock_bajo(movimientos):
    """Textos para avisar qué productos quedaron en o por debajo del stock mínimo."""
    avisos = []
    vistos = set()
    for mov in movimientos:
        if mov.producto_id in vistos:
            continue
        vistos.add(mov.producto_id)
        producto = Producto.objects.get(pk=mov.producto_id)
        if producto.necesita_reposicion:
            avisos.append(
                f"«{producto.nombre}» quedó con {producto.stock_actual} unidad"
                f"{'es' if producto.stock_actual != 1 else ''} (mínimo {producto.stock_minimo}). Conviene reponerlo."
            )
    return avisos


def descontar_stock_consulta(producto_id, cantidad, consulta_id, usuario=None):
    """
    Compatibilidad con el código anterior: descuenta por una consulta clínica.
    Lanza ValueError si no hay stock suficiente (como antes).
    """
    try:
        return descontar_stock(producto_id, cantidad, tipo='SALIDA_CLINICA', usuario=usuario,
                               observacion=f"Uso en Consulta Clínica #{consulta_id}")
    except StockInsuficiente as error:
        raise ValueError(str(error)) from error