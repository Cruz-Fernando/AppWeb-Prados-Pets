"""
PB-19 / RF13 · Factura consolidada y movimientos de caja.

- Factura: una sola factura por atención, con lo de consulta, peluquería y
  productos. Se arma como borrador y al cobrarla queda «pagada»: recibe su
  número consecutivo, descuenta el stock y crea el ingreso en caja.
  Nunca se borra una factura cobrada: se anula con motivo.
- ItemFactura: cada línea. Una cita (de consulta o de peluquería) y cada
  salida de insumos de una consulta se facturan una sola vez: lo garantiza
  la base de datos con las restricciones de «ítem vigente».
- MovimientoCaja: entradas y salidas de dinero (ingresos por factura,
  gastos como el arriendo, y la reversa cuando se anula una factura).

La lógica (agregar ítems, cobrar, anular) vive en servicios.py.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint

CERO = Decimal('0.00')


def _dinero(**extra):
    return models.DecimalField(max_digits=12, decimal_places=2, default=CERO,
                               validators=[MinValueValidator(CERO)], **extra)


class Factura(models.Model):
    BORRADOR, PAGADA, ANULADA = 'borrador', 'pagada', 'anulada'
    ESTADOS = [
        (BORRADOR, 'Borrador'),
        (PAGADA, 'Pagada'),
        (ANULADA, 'Anulada'),
    ]
    MEDIOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('NEQUI', 'Nequi'),
        ('DAVIPLATA', 'Daviplata'),
        ('TRANSFERENCIA', 'Transferencia bancaria'),
        ('TARJETA', 'Tarjeta débito o crédito'),
    ]

    # Consecutivo: se asigna al cobrar (los borradores no tienen número).
    numero = models.PositiveIntegerField(null=True, blank=True, unique=True, verbose_name='Número')
    dueno = models.ForeignKey('directorio.Dueno', on_delete=models.PROTECT, related_name='facturas',
                              verbose_name='Propietario')
    estado = models.CharField(max_length=10, choices=ESTADOS, default=BORRADOR, db_index=True)
    fecha = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de cobro')
    medio_pago = models.CharField(max_length=15, choices=MEDIOS_PAGO, blank=True, verbose_name='Medio de pago')

    subtotal = _dinero()
    descuento = _dinero()
    total = _dinero()

    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True,
                                   related_name='facturas_creadas')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                related_name='facturas_cobradas', verbose_name='Facturó')
    creada_en = models.DateTimeField(auto_now_add=True)

    motivo_anulacion = models.CharField(max_length=255, blank=True)
    anulada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name='facturas_anuladas')
    anulada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-creada_en', '-pk']

    def __str__(self):
        return f'Factura {self.numero_display} · {self.dueno}'

    @property
    def numero_display(self):
        return f'N.° {self.numero:05d}' if self.numero else 'Borrador'

    @property
    def es_borrador(self):
        return self.estado == self.BORRADOR

    def recalcular(self):
        """Suma los ítems; el descuento nunca deja el total en negativo."""
        self.subtotal = sum((i.subtotal for i in self.items.all()), CERO)
        self.descuento = min(self.descuento or CERO, self.subtotal)
        self.total = self.subtotal - self.descuento


class ItemFactura(models.Model):
    CONSULTA, PELUQUERIA, PRODUCTO = 'CONSULTA', 'PELUQUERIA', 'PRODUCTO'
    TIPOS = [
        (CONSULTA, 'Consulta'),
        (PELUQUERIA, 'Peluquería'),
        (PRODUCTO, 'Producto'),
    ]

    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='items')
    tipo = models.CharField(max_length=12, choices=TIPOS)
    descripcion = models.CharField(max_length=255)
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = _dinero()
    subtotal = _dinero()

    # Referencias opcionales (de dónde sale el ítem)
    cita = models.ForeignKey('agendamiento.Cita', on_delete=models.PROTECT, null=True, blank=True,
                             related_name='items_factura')
    cita_peluqueria = models.ForeignKey('peluqueria.CitaPeluqueria', on_delete=models.PROTECT, null=True,
                                        blank=True, related_name='items_factura')
    servicio = models.ForeignKey('inventario.Servicio', on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='items_factura')
    producto = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='items_factura')
    # Salida de inventario del ítem: la de la consulta (insumo ya descontado)
    # o la que se crea al cobrar (producto vendido en la factura).
    movimiento = models.ForeignKey('inventario.MovimientoInventario', on_delete=models.PROTECT, null=True,
                                   blank=True, related_name='items_factura')
    # True: producto vendido en la factura (se descuenta al cobrar y vuelve al anular).
    # False en los insumos de una consulta: ya salieron del inventario con el registro clínico.
    descuenta_stock = models.BooleanField(default=False)
    # Deja de estar vigente si la factura se anula: la cita o el insumo se pueden volver a facturar.
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Ítem de factura'
        verbose_name_plural = 'Ítems de factura'
        ordering = ['pk']
        constraints = [
            UniqueConstraint(fields=['cita'], condition=Q(vigente=True, cita__isnull=False),
                             name='factura_cita_una_vez'),
            UniqueConstraint(fields=['cita_peluqueria'], condition=Q(vigente=True, cita_peluqueria__isnull=False),
                             name='factura_peluqueria_una_vez'),
            UniqueConstraint(fields=['movimiento'], condition=Q(vigente=True, movimiento__isnull=False),
                             name='factura_movimiento_una_vez'),
        ]

    def __str__(self):
        return f'{self.cantidad} × {self.descripcion}'

    def save(self, *args, **kwargs):
        self.subtotal = (self.precio_unitario or CERO) * self.cantidad
        super().save(*args, **kwargs)


class MovimientoCaja(models.Model):
    INGRESO, EGRESO = 'INGRESO', 'EGRESO'
    TIPOS = [(INGRESO, 'Ingreso'), (EGRESO, 'Egreso')]
    CATEGORIAS = [
        ('FACTURA', 'Factura'),
        ('ARRIENDO', 'Arriendo'),
        ('SERVICIOS_PUBLICOS', 'Servicios públicos'),
        ('NOMINA', 'Nómina'),
        ('COMPRAS', 'Compras'),
        ('OTRO', 'Otro'),
    ]
    # Lo que se puede registrar a mano como gasto (FACTURA lo pone el sistema).
    CATEGORIAS_GASTO = [c for c in CATEGORIAS if c[0] != 'FACTURA']

    tipo = models.CharField(max_length=7, choices=TIPOS)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    fecha = models.DateField(db_index=True)
    descripcion = models.CharField(max_length=255)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                related_name='movimientos_caja')
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, null=True, blank=True,
                                related_name='movimientos_caja')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de caja'
        verbose_name_plural = 'Movimientos de caja'
        ordering = ['fecha', 'pk']

    def __str__(self):
        return f'{self.get_tipo_display()} {self.monto} · {self.descripcion}'

    @property
    def es_ingreso(self):
        return self.tipo == self.INGRESO

    @property
    def con_signo(self):
        return self.monto if self.es_ingreso else -self.monto
