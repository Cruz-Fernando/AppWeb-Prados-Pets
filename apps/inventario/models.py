from django.db import models


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Venta")
    stock_minimo = models.PositiveIntegerField(default=5, verbose_name="Stock Mínimo")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def stock_total(self):
        return sum(lote.cantidad for lote in self.lotes.all())


class Medicamento(models.Model):
    producto = models.OneToOneField(
        Producto, on_delete=models.CASCADE, related_name="medicamento", primary_key=True
    )
    principio_activo = models.CharField(max_length=150, blank=True, null=True, verbose_name="Principio Activo")
    concentracion = models.CharField(max_length=50, blank=True, null=True, verbose_name="Concentración")
    presentacion = models.CharField(max_length=100, blank=True, null=True, verbose_name="Presentación")
    requiere_receta = models.BooleanField(default=False, verbose_name="Requiere Receta Médica")

    def __str__(self):
        return f"Medicamento: {self.producto.nombre}"


class Servicio(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    duracion_minutos = models.PositiveIntegerField(default=30, verbose_name="Duración (Minutos)")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    def __str__(self):
        return f"Servicio: {self.codigo} - {self.nombre}"


class StockLote(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="lotes")
    numero_lote = models.CharField(max_length=50, verbose_name="Número de Lote")
    fecha_vencimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Vencimiento")
    cantidad = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    fecha_ingreso = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Lote {self.numero_lote} ({self.producto.nombre}): {self.cantidad} uds"