from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Categoría de Producto"
        verbose_name_plural = "Categorías de Productos"

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    nombre = models.CharField(max_length=150)
    nit_identificacion = models.CharField(max_length=50, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))], 
        verbose_name="Precio"
    )
    duracion_minutos = models.PositiveIntegerField(default=30, verbose_name="Duración (Minutos)")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# PB-21 / RF11 · Umbrales de stock del acta (no dependen del stock mínimo del producto):
#   0 unidades = agotado · 1 unidad (menos de 2) = CRÍTICO · 2 a 4 (menos de 5) = BAJO
UMBRAL_STOCK_CRITICO = 2
UMBRAL_STOCK_BAJO = 5


class Producto(models.Model):
    codigo = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="Código")
    codigo_barras = models.CharField(max_length=100, blank=True, null=True)
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    categoria = models.ForeignKey(
        CategoriaProducto, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='productos'
    )
    proveedor = models.ForeignKey(
        Proveedor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='productos'
    )
    
    precio_compra = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    precio_venta = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))], 
        verbose_name="Precio de Venta"
    )
    
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5, verbose_name="Stock Mínimo")
    # Inventario simple: cada producto tiene su cantidad y, si aplica, UNA fecha de
    # vencimiento (la más próxima de lo que hay). Sin lotes.
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de vencimiento")
    # PB-21: lote de las unidades que vencen en esa fecha. Admite vacío (NULL) para
    # que el código de otras ramas que no lo conoce pueda seguir guardando productos.
    numero_lote = models.CharField(max_length=100, null=True, blank=True, verbose_name="Número de lote")
    
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def nivel_stock(self):
        """PB-21: 'agotado', 'critico' (menos de 2), 'bajo' (menos de 5) o '' si está bien."""
        if self.stock_actual == 0:
            return 'agotado'
        if self.stock_actual < UMBRAL_STOCK_CRITICO:
            return 'critico'
        if self.stock_actual < UMBRAL_STOCK_BAJO:
            return 'bajo'
        return ''

    @property
    def necesita_reposicion(self):
        """Menos de 5 unidades (umbral del acta, PB-21)."""
        return self.stock_actual < UMBRAL_STOCK_BAJO

    @property
    def valor_total_inventario(self):
        return self.stock_actual * self.precio_compra

    @property
    def vencido(self):
        from django.utils import timezone
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate())

    @property
    def dias_para_vencer(self):
        from django.utils import timezone
        return (self.fecha_vencimiento - timezone.localdate()).days if self.fecha_vencimiento else None


class Medicamento(models.Model):
    producto = models.OneToOneField(
        Producto, 
        on_delete=models.CASCADE, 
        primary_key=True, 
        related_name='medicamento'
    )
    principio_activo = models.CharField(max_length=200, blank=True, null=True, verbose_name="Principio Activo")
    concentracion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Concentración")
    presentacion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Presentación")
    requiere_receta = models.BooleanField(default=False, verbose_name="Requiere Receta Médica")

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"

    def __str__(self):
        return f"Medicamento: {self.producto.nombre}"


class StockLote(models.Model):
    """
    YA NO SE USA. El inventario ahora es simple: cantidad + una fecha por producto.
    Se conserva la tabla para no romper la base compartida ni el historial; sus
    fechas se copiaron a Producto.fecha_vencimiento (migración 0006).
    """
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='lotes')
    numero_lote = models.CharField(max_length=100, verbose_name="Número de Lote")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    cantidad = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lote de Stock"
        verbose_name_plural = "Lotes de Stock"

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.producto.nombre}"


class MovimientoInventario(models.Model):
    TIPO_MOVIMIENTO = [
        ('ENTRADA_COMPRA', 'Entrada por Compra / Reposición'),
        ('ENTRADA_DEVOLUCION', 'Entrada por Devolución (anulación o cancelación)'),
        ('SALIDA_VENTA', 'Salida por Venta'),
        ('SALIDA_CLINICA', 'Salida por Uso en Consulta Clínica'),
        ('SALIDA_PELUQUERIA', 'Salida por Servicio de Peluquería'),
        ('AJUSTE_MERMA', 'Ajuste / Pérdida / Vencimiento'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO)
    cantidad = models.PositiveIntegerField()
    precio_unitario_historico = models.DecimalField(max_digits=12, decimal_places=2)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField(max_length=255, blank=True, null=True)
    consulta_medica_id = models.IntegerField(null=True, blank=True)

    # PB-17 / RF10: de dónde salió el descuento automático.
    # Todos admiten NULL o tienen valor por defecto EN LA BASE (db_default), para
    # que el código que aún no los conoce (otra rama o el despliegue) pueda seguir
    # guardando movimientos en la base compartida sin error.
    registro_clinico = models.ForeignKey(
        'clinico.RegistroClinico', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimientos_inventario', verbose_name="Registro clínico",
    )
    cita_peluqueria = models.ForeignKey(
        'peluqueria.CitaPeluqueria', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimientos_inventario', verbose_name="Cita de peluquería",
    )
    # Histórico: lotes afectados en movimientos anteriores. Ya no se llena.
    lotes = models.JSONField(null=True, blank=True, verbose_name="Lotes afectados")
    # True cuando la salida ya se devolvió al inventario (anulación o cancelación)
    devuelto = models.BooleanField(default=False, db_default=False)

    @property
    def es_entrada(self):
        return self.tipo.startswith('ENTRADA')

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ['-fecha']

    def save(self, *args, **kwargs):
        if not self.monto_total:
            self.monto_total = self.cantidad * self.precio_unitario_historico
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre} ({self.cantidad})"


class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Ventas"

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"


class InsumoServicio(models.Model):
    """
    Insumos que gasta cada servicio de peluquería (PB-17 / RF10).

    Al agendar el servicio se descuentan del inventario. Si el tamaño se deja
    vacío, el insumo aplica a mascotas de cualquier tamaño.
    """
    SERVICIOS = [
        ('BANO', 'Solamente Baño'),
        ('CORTE', 'Corte Despuntado (Solo tijera)'),
        ('COMPLETO', 'Corte Total (Máquina y tijera)'),
    ]
    TAMANOS = [
        ('', 'Todos los tamaños'),
        ('PEQUENO', 'Pequeño (1 - 10 kg)'),
        ('MEDIANO', 'Mediano (11 - 25 kg)'),
        ('GRANDE', 'Grande (Más de 25 kg)'),
    ]

    servicio = models.CharField(max_length=20, choices=SERVICIOS, verbose_name="Servicio")
    tamano = models.CharField(max_length=10, choices=TAMANOS, blank=True, default='',
                              verbose_name="Tamaño de la mascota")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='usos_en_servicios',
                                 verbose_name="Producto")
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)],
                                           verbose_name="Cantidad por servicio")

    class Meta:
        verbose_name = "Insumo por servicio"
        verbose_name_plural = "Insumos por servicio"
        ordering = ['servicio', 'tamano', 'producto__nombre']
        constraints = [
            models.UniqueConstraint(fields=['servicio', 'tamano', 'producto'],
                                    name='uniq_insumo_servicio_tamano_producto'),
        ]

    def __str__(self):
        return f"{self.get_servicio_display()} · {self.cantidad} × {self.producto.nombre}"