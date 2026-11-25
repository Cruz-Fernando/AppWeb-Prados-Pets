"""
PB-19 / RF13 · Reglas de la factura consolidada y de la caja.

Flujo: borrador → (agregar o quitar ítems) → cobrar → pagada → (anular).

- Consulta: se agrega una Cita del dueño con el precio que escribe quien factura.
- Peluquería: se agrega una CitaPeluqueria del dueño con el precio que ya tiene.
- Insumos de consulta: las salidas de inventario de sus registros clínicos.
  Ya se descontaron al guardar la consulta, así que aquí solo se cobran.
- Productos vendidos en la factura: se descuentan al cobrar (inventario/
  services.py) y vuelven al inventario si la factura se anula.
- Cada cita y cada salida de insumos se factura una sola vez (restricciones
  de ItemFactura). Una factura anulada las libera.
- Al cobrar: número consecutivo, citas a «realizada»/«atendida» e ingreso en
  caja. Al anular: devuelve el stock y crea el egreso que reversa el ingreso.
  Nada se borra, salvo un borrador que se descarta (no movió dinero ni stock).

Todo ocurre dentro de transaction.atomic y con bloqueo de fila.
"""

import re
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, connection, transaction
from django.db.models import Max, Q, Sum
from django.utils import timezone

from apps.agendamiento.models import Cita
from apps.inventario.models import MovimientoInventario, Producto, Servicio
from apps.inventario.services import StockInsuficiente, descontar_stock, devolver_movimientos, disponibilidad
from apps.peluqueria.models import CitaPeluqueria

from .models import CERO, Factura, ItemFactura, MovimientoCaja

MONTO_MAXIMO = Decimal('99999999')
CANTIDAD_MAXIMA = 999
MAX_PENDIENTES = 50
# Clave del candado de PostgreSQL que reparte los números de factura.
_CANDADO_CONSECUTIVO = 190013


class FacturaError(Exception):
    """La operación no se puede hacer; el mensaje es para el usuario."""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def parsear_monto(texto, nombre='El valor', permitir_cero=False):
    """'$45.000', '45000' o '45.000,50' → Decimal. Lanza FacturaError si no es válido."""
    if isinstance(texto, Decimal):
        valor = texto
    else:
        limpio = re.sub(r'[\s$]|COP', '', str(texto or ''), flags=re.IGNORECASE)
        if ',' in limpio:                       # 45.000,50 → 45000.50
            limpio = limpio.replace('.', '').replace(',', '.')
        else:                                   # 45.000 → 45000 (punto de miles)
            limpio = limpio.replace('.', '')
        try:
            valor = Decimal(limpio)
        except InvalidOperation:
            raise FacturaError(f'{nombre} debe ser un número en pesos (ej.: 45.000).') from None
    if not valor.is_finite() or valor < 0 or (valor == 0 and not permitir_cero):
        raise FacturaError(f'{nombre} debe ser mayor que $0.' if not permitir_cero
                           else f'{nombre} no puede ser negativo.')
    if valor > MONTO_MAXIMO:
        raise FacturaError(f'{nombre} es demasiado alto (máximo $99.999.999).')
    return valor.quantize(Decimal('0.01'))


def _pesos(valor):
    return '$' + f'{valor:,.0f}'.replace(',', '.')


def _borrador_bloqueado(factura_id):
    factura = Factura.objects.select_for_update().get(pk=factura_id)
    if factura.estado != Factura.BORRADOR:
        raise FacturaError(f'La factura {factura.numero_display} ya está {factura.get_estado_display().lower()}: '
                           'no se puede modificar.')
    return factura


def _guardar_item(factura, **datos):
    try:
        with transaction.atomic():
            item = ItemFactura.objects.create(factura=factura, **datos)
    except IntegrityError:
        raise FacturaError('Ese servicio ya está en otra factura (borrador o pagada).') from None
    _actualizar_totales(factura)
    return item


def _actualizar_totales(factura):
    factura.recalcular()
    factura.save(update_fields=['subtotal', 'descuento', 'total'])


def ya_facturado(**referencia):
    """True si la cita / salida ya está en una factura vigente (borrador o pagada)."""
    return ItemFactura.objects.filter(vigente=True, **referencia).exists()


# ---------------------------------------------------------------------------
# Borrador
# ---------------------------------------------------------------------------

def crear_borrador(dueno, usuario):
    """Abre un borrador para el dueño; si ya tiene uno abierto, se continúa ese."""
    existente = Factura.objects.filter(dueno=dueno, estado=Factura.BORRADOR).order_by('pk').first()
    if existente:
        return existente, False
    return Factura.objects.create(dueno=dueno, creada_por=usuario), True


def pendientes(dueno):
    """Lo del dueño que aún no está en ninguna factura vigente."""
    consultas = (Cita.objects.filter(mascota__id_dueno=dueno).exclude(estado='cancelada')
                 .exclude(items_factura__vigente=True)
                 .select_related('mascota', 'veterinario').order_by('-fecha', '-hora_inicio')[:MAX_PENDIENTES])
    peluquerias = (CitaPeluqueria.objects.filter(mascota__id_dueno=dueno).exclude(estado='Cancelada')
                   .exclude(items_factura__vigente=True)
                   .select_related('mascota', 'groomer').order_by('-fecha_hora')[:MAX_PENDIENTES])
    insumos = (MovimientoInventario.objects
               .filter(tipo='SALIDA_CLINICA', devuelto=False,
                       registro_clinico__mascota__id_dueno=dueno, registro_clinico__anulado=False)
               .exclude(items_factura__vigente=True)
               .select_related('producto', 'registro_clinico__mascota').order_by('-fecha', '-pk')[:MAX_PENDIENTES])
    return {'consultas': list(consultas), 'peluquerias': list(peluquerias), 'insumos': list(insumos)}


@transaction.atomic
def agregar_consulta(factura, cita_id, precio):
    factura = _borrador_bloqueado(factura.pk)
    cita = Cita.objects.select_for_update().select_related('mascota').filter(pk=cita_id).first()
    if cita is None or cita.mascota.id_dueno_id != factura.dueno_id:
        raise FacturaError('Esa consulta no es de una mascota de este propietario.')
    if cita.estado == 'cancelada':
        raise FacturaError('Una consulta cancelada no se puede facturar.')
    if ya_facturado(cita=cita):
        raise FacturaError('Esa consulta ya está en otra factura (borrador o pagada).')
    precio = parsear_monto(precio, 'El precio de la consulta')
    return _guardar_item(
        factura, tipo=ItemFactura.CONSULTA, cita=cita, cantidad=1, precio_unitario=precio,
        descripcion=f'{cita.get_tipo_servicio_display()} · {cita.mascota.nombre} · {cita.fecha:%d/%m/%Y}',
    )


@transaction.atomic
def agregar_peluqueria(factura, cita_id):
    factura = _borrador_bloqueado(factura.pk)
    cita = CitaPeluqueria.objects.select_for_update().filter(pk=cita_id).first()
    if cita is None or cita.mascota is None or cita.mascota.id_dueno_id != factura.dueno_id:
        raise FacturaError('Esa cita de peluquería no es de una mascota de este propietario.')
    if cita.estado == 'Cancelada':
        raise FacturaError('Una cita de peluquería cancelada no se puede facturar.')
    if ya_facturado(cita_peluqueria=cita):
        raise FacturaError('Esa cita de peluquería ya está en otra factura (borrador o pagada).')
    if not cita.precio:
        raise FacturaError('La cita de peluquería no tiene precio registrado.')
    fecha = timezone.localtime(cita.fecha_hora)
    return _guardar_item(
        factura, tipo=ItemFactura.PELUQUERIA, cita_peluqueria=cita, cantidad=1,
        precio_unitario=Decimal(cita.precio),
        descripcion=f'Peluquería: {cita.get_servicio_display()} · {cita.nombre_mascota} · {fecha:%d/%m/%Y}',
    )


@transaction.atomic
def agregar_insumo(factura, movimiento_id):
    """Insumo o medicamento usado en una consulta (ya descontado del inventario)."""
    factura = _borrador_bloqueado(factura.pk)
    mov = (MovimientoInventario.objects.select_for_update()
           .select_related('producto', 'registro_clinico__mascota').filter(pk=movimiento_id).first())
    registro = mov.registro_clinico if mov else None
    if (mov is None or mov.tipo != 'SALIDA_CLINICA' or registro is None
            or registro.mascota.id_dueno_id != factura.dueno_id):
        raise FacturaError('Ese insumo no salió de una consulta de este propietario.')
    if mov.devuelto or registro.anulado:
        raise FacturaError('Ese insumo ya se devolvió al inventario (registro anulado): no se cobra.')
    if ya_facturado(movimiento=mov):
        raise FacturaError('Ese insumo ya está en otra factura (borrador o pagada).')
    fecha = timezone.localtime(registro.fecha_atencion)
    return _guardar_item(
        factura, tipo=ItemFactura.PRODUCTO, producto=mov.producto, movimiento=mov, descuenta_stock=False,
        cantidad=mov.cantidad, precio_unitario=mov.precio_unitario_historico,
        descripcion=f'{mov.producto.nombre} · usado en la consulta de {registro.mascota.nombre} ({fecha:%d/%m/%Y})',
    )


@transaction.atomic
def agregar_producto(factura, producto_id, cantidad):
    """Producto vendido en la factura: se descuenta del inventario al cobrar."""
    factura = _borrador_bloqueado(factura.pk)
    producto = Producto.objects.filter(pk=producto_id, activo=True).first()
    if producto is None:
        raise FacturaError('Elige un producto activo del inventario.')
    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        cantidad = 0
    if not 1 <= cantidad <= CANTIDAD_MAXIMA:
        raise FacturaError(f'La cantidad debe ser un número entero entre 1 y {CANTIDAD_MAXIMA}.')
    if not producto.precio_venta or producto.precio_venta <= 0:
        raise FacturaError(f'«{producto.nombre}» no tiene precio de venta. Regístralo en Inventario.')

    # Si el producto ya está en la factura, se suma a la misma línea
    item = factura.items.filter(producto=producto, descuenta_stock=True).first()
    total = cantidad + (item.cantidad if item else 0)
    disponible = disponibilidad(producto)[0]
    if total > disponible:
        raise FacturaError(f'No hay stock suficiente de «{producto.nombre}»: pediste {total} '
                           f'y hay {disponible} disponible{"s" if disponible != 1 else ""}.')
    if item:
        item.cantidad = total
        item.save(update_fields=['cantidad', 'subtotal'])
        _actualizar_totales(factura)
        return item
    return _guardar_item(factura, tipo=ItemFactura.PRODUCTO, producto=producto, descuenta_stock=True,
                         cantidad=cantidad, precio_unitario=producto.precio_venta, descripcion=producto.nombre)


@transaction.atomic
def agregar_servicio(factura, servicio_id, precio=None):
    """Servicio del catálogo (por ejemplo, una vacuna aplicada sin cita)."""
    factura = _borrador_bloqueado(factura.pk)
    servicio = Servicio.objects.filter(pk=servicio_id, activo=True).first()
    if servicio is None:
        raise FacturaError('Elige un servicio activo del catálogo.')
    precio = parsear_monto(precio if str(precio or '').strip() else servicio.precio, 'El precio del servicio')
    return _guardar_item(factura, tipo=ItemFactura.CONSULTA, servicio=servicio, cantidad=1,
                         precio_unitario=precio, descripcion=servicio.nombre)


@transaction.atomic
def quitar_item(factura, item_id):
    factura = _borrador_bloqueado(factura.pk)
    borrados, _ = factura.items.filter(pk=item_id).delete()
    if not borrados:
        raise FacturaError('Ese ítem ya no está en la factura.')
    _actualizar_totales(factura)


@transaction.atomic
def descartar_borrador(factura):
    """Un borrador no movió dinero ni stock: se puede descartar del todo."""
    factura = _borrador_bloqueado(factura.pk)
    factura.delete()


# ---------------------------------------------------------------------------
# Cobrar y anular
# ---------------------------------------------------------------------------

def _siguiente_numero():
    if connection.vendor == 'postgresql':
        # Candado de la transacción: dos cobros a la vez no toman el mismo número.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [_CANDADO_CONSECUTIVO])
    return (Factura.objects.aggregate(m=Max('numero'))['m'] or 0) + 1


def _revalidar(item):
    """Lo que pudo cambiar desde que se armó el borrador (una cita cancelada, un registro anulado)."""
    if item.cita_id:
        cita = Cita.objects.select_for_update().get(pk=item.cita_id)
        if cita.estado == 'cancelada':
            raise FacturaError(f'La consulta «{item.descripcion}» se canceló. Quítala de la factura.')
        return cita
    if item.cita_peluqueria_id:
        cita = CitaPeluqueria.objects.select_for_update().get(pk=item.cita_peluqueria_id)
        if cita.estado == 'Cancelada':
            raise FacturaError(f'La peluquería «{item.descripcion}» se canceló. Quítala de la factura.')
        return cita
    if item.movimiento_id and not item.descuenta_stock:
        mov = MovimientoInventario.objects.select_for_update().select_related('registro_clinico').get(
            pk=item.movimiento_id)
        if mov.devuelto or (mov.registro_clinico and mov.registro_clinico.anulado):
            raise FacturaError(f'El insumo «{item.descripcion}» volvió al inventario. Quítalo de la factura.')
    return None


@transaction.atomic
def cobrar(factura, *, medio_pago, descuento='0', usuario=None):
    factura = _borrador_bloqueado(factura.pk)
    items = list(factura.items.select_related('producto'))
    if not items:
        raise FacturaError('Agrega al menos un servicio o producto antes de cobrar.')
    if medio_pago not in dict(Factura.MEDIOS_PAGO):
        raise FacturaError('Elige el medio de pago.')

    factura.recalcular()
    factura.descuento = parsear_monto(descuento or '0', 'El descuento', permitir_cero=True)
    if factura.descuento > factura.subtotal:
        raise FacturaError(f'El descuento no puede superar el subtotal ({_pesos(factura.subtotal)}).')
    factura.total = factura.subtotal - factura.descuento

    citas = [c for c in (_revalidar(i) for i in items) if c is not None]

    factura.numero = _siguiente_numero()
    numero = factura.numero_display

    # Productos vendidos: se descuentan ahora (si algo no alcanza, no se cobra nada)
    for item in items:
        if item.descuenta_stock:
            try:
                item.movimiento = descontar_stock(
                    item.producto_id, item.cantidad, tipo='SALIDA_VENTA', usuario=usuario,
                    observacion=f'Factura {numero} · {factura.dueno.nombre_completo}')
            except StockInsuficiente as error:
                raise FacturaError(f'{error} Ajusta la cantidad o repón el producto antes de cobrar.') from None
            item.save(update_fields=['movimiento'])

    # El servicio se prestó: la consulta queda atendida y la peluquería realizada (cuenta la comisión)
    for cita in citas:
        if isinstance(cita, Cita) and cita.estado == 'programada':
            cita.estado = 'atendida'
            cita.save(update_fields=['estado'])
        elif isinstance(cita, CitaPeluqueria) and cita.estado == 'Programada':
            cita.estado = 'Realizada'
            cita.save()

    factura.estado = Factura.PAGADA
    factura.fecha = timezone.now()
    factura.medio_pago = medio_pago
    factura.usuario = usuario
    factura.save()

    if factura.total > 0:
        MovimientoCaja.objects.create(
            tipo=MovimientoCaja.INGRESO, categoria='FACTURA', monto=factura.total,
            fecha=timezone.localdate(), usuario=usuario, factura=factura,
            descripcion=f'Factura {numero} · {factura.dueno.nombre_completo} · {factura.get_medio_pago_display()}',
        )
    return factura


@transaction.atomic
def anular(factura, *, motivo, usuario=None):
    factura = Factura.objects.select_for_update().get(pk=factura.pk)
    if factura.estado == Factura.ANULADA:
        raise FacturaError(f'La factura {factura.numero_display} ya estaba anulada.')
    if factura.estado != Factura.PAGADA:
        raise FacturaError('Un borrador no se anula: descártalo.')
    motivo = (motivo or '').strip()
    if not motivo:
        raise FacturaError('Escribe el motivo de la anulación.')
    if len(motivo) > 255:
        raise FacturaError('El motivo no puede superar los 255 caracteres.')

    numero = factura.numero_display
    vendidos = [i.movimiento for i in factura.items.filter(descuenta_stock=True, movimiento__isnull=False)
                .select_related('movimiento')]
    devolver_movimientos(vendidos, usuario=usuario, motivo=f'Factura {numero} anulada')
    factura.items.update(vigente=False)        # sus citas e insumos se pueden volver a facturar

    cobrado = (factura.movimientos_caja.aggregate(
        i=Sum('monto', filter=Q(tipo=MovimientoCaja.INGRESO)),
        e=Sum('monto', filter=Q(tipo=MovimientoCaja.EGRESO))))
    neto = (cobrado['i'] or CERO) - (cobrado['e'] or CERO)
    if neto > 0:
        MovimientoCaja.objects.create(
            tipo=MovimientoCaja.EGRESO, categoria='FACTURA', monto=neto, fecha=timezone.localdate(),
            usuario=usuario, factura=factura, descripcion=f'Anulación de la factura {numero}: {motivo}'[:255],
        )

    factura.estado = Factura.ANULADA
    factura.motivo_anulacion = motivo
    factura.anulada_por = usuario
    factura.anulada_en = timezone.now()
    factura.save(update_fields=['estado', 'motivo_anulacion', 'anulada_por', 'anulada_en'])
    return factura


# ---------------------------------------------------------------------------
# Caja
# ---------------------------------------------------------------------------

@transaction.atomic
def registrar_gasto(*, categoria, monto, fecha, descripcion, usuario=None):
    if categoria not in dict(MovimientoCaja.CATEGORIAS_GASTO):
        raise FacturaError('Elige la categoría del gasto.')
    monto = parsear_monto(monto, 'El monto del gasto')
    if fecha is None:
        raise FacturaError('Indica la fecha del gasto.')
    if fecha > timezone.localdate():
        raise FacturaError('La fecha del gasto no puede ser futura.')
    descripcion = (descripcion or '').strip()
    if not descripcion:
        raise FacturaError('Describe el gasto (ej.: Arriendo de noviembre).')
    if len(descripcion) > 255:
        raise FacturaError('La descripción no puede superar los 255 caracteres.')
    return MovimientoCaja.objects.create(tipo=MovimientoCaja.EGRESO, categoria=categoria, monto=monto,
                                         fecha=fecha, descripcion=descripcion, usuario=usuario)


def _neto(qs):
    r = qs.aggregate(i=Sum('monto', filter=Q(tipo=MovimientoCaja.INGRESO)),
                     e=Sum('monto', filter=Q(tipo=MovimientoCaja.EGRESO)))
    return r['i'] or CERO, r['e'] or CERO


def resumen_caja(desde, hasta, categoria=''):
    """
    Movimientos del periodo con su saldo acumulado. El saldo arranca con lo
    que había antes de `desde`. Si se filtra por categoría, no hay saldo
    acumulado (solo los totales de esa categoría).
    """
    todos = MovimientoCaja.objects.all()
    periodo = todos.filter(fecha__range=(desde, hasta))
    if categoria:
        periodo = periodo.filter(categoria=categoria)
    movimientos = list(periodo.select_related('usuario', 'factura').order_by('fecha', 'pk'))

    ing_antes, egr_antes = _neto(todos.filter(fecha__lt=desde))
    saldo_inicial = ing_antes - egr_antes
    saldo = saldo_inicial
    for m in movimientos:
        saldo += m.con_signo
        m.saldo = saldo
    ingresos, egresos = _neto(periodo)
    return {
        'movimientos': movimientos,
        'ingresos': ingresos,
        'egresos': egresos,
        'neto': ingresos - egresos,
        'saldo_inicial': saldo_inicial,
        'saldo_final': saldo_inicial + ingresos - egresos,
        'con_saldo': not categoria,
    }
