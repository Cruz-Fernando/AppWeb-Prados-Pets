import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0003_servicio_duracion_minutos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="detalleventa",
            options={
                "verbose_name": "Detalle de Venta",
                "verbose_name_plural": "Detalles de Ventas",
            },
        ),
        migrations.AlterModelOptions(
            name="venta",
            options={"verbose_name": "Venta", "verbose_name_plural": "Ventas"},
        ),
        migrations.AlterField(
            model_name="medicamento",
            name="concentracion",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Concentración"
            ),
        ),
        migrations.AlterField(
            model_name="medicamento",
            name="presentacion",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="Presentación"
            ),
        ),
        migrations.AlterField(
            model_name="medicamento",
            name="principio_activo",
            field=models.CharField(
                blank=True, max_length=200, null=True, verbose_name="Principio Activo"
            ),
        ),
        migrations.AlterField(
            model_name="medicamento",
            name="requiere_receta",
            field=models.BooleanField(
                default=False, verbose_name="Requiere Receta Médica"
            ),
        ),
        migrations.AlterField(
            model_name="producto",
            name="activo",
            field=models.BooleanField(default=True, verbose_name="Activo"),
        ),
        migrations.AlterField(
            model_name="producto",
            name="codigo",
            field=models.CharField(
                db_index=True, max_length=100, unique=True, verbose_name="Código"
            ),
        ),
        migrations.AlterField(
            model_name="producto",
            name="descripcion",
            field=models.TextField(blank=True, null=True, verbose_name="Descripción"),
        ),
        migrations.AlterField(
            model_name="producto",
            name="nombre",
            field=models.CharField(max_length=200, verbose_name="Nombre"),
        ),
        migrations.AlterField(
            model_name="producto",
            name="precio_venta",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                verbose_name="Precio de Venta",
            ),
        ),
        migrations.AlterField(
            model_name="producto",
            name="stock_minimo",
            field=models.PositiveIntegerField(default=5, verbose_name="Stock Mínimo"),
        ),
        migrations.AlterField(
            model_name="proveedor",
            name="direccion",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="servicio",
            name="activo",
            field=models.BooleanField(default=True, verbose_name="Activo"),
        ),
        migrations.AlterField(
            model_name="servicio",
            name="codigo",
            field=models.CharField(max_length=50, unique=True, verbose_name="Código"),
        ),
        migrations.AlterField(
            model_name="servicio",
            name="descripcion",
            field=models.TextField(blank=True, null=True, verbose_name="Descripción"),
        ),
        migrations.AlterField(
            model_name="servicio",
            name="duracion_minutos",
            field=models.PositiveIntegerField(
                default=30, verbose_name="Duración (Minutos)"
            ),
        ),
        migrations.AlterField(
            model_name="servicio",
            name="nombre",
            field=models.CharField(max_length=200, verbose_name="Nombre"),
        ),
        migrations.AlterField(
            model_name="servicio",
            name="precio",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                verbose_name="Precio",
            ),
        ),
        migrations.AlterField(
            model_name="stocklote",
            name="cantidad",
            field=models.PositiveIntegerField(default=0, verbose_name="Cantidad"),
        ),
        migrations.AlterField(
            model_name="stocklote",
            name="fecha_vencimiento",
            field=models.DateField(
                blank=True, null=True, verbose_name="Fecha de Vencimiento"
            ),
        ),
        migrations.AlterField(
            model_name="stocklote",
            name="numero_lote",
            field=models.CharField(max_length=100, verbose_name="Número de Lote"),
        ),
        migrations.AlterField(
            model_name="venta",
            name="usuario",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]