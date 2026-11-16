# PB-17 / RF10 · Descuento automático del stock por consulta y peluquería.
#
# Es segura para la base compartida (Supabase): las columnas nuevas de
# inventario_movimientoinventario admiten NULL o tienen valor por defecto en la
# base (devuelto = false), así que el despliegue que aún no tenga este código
# puede seguir guardando movimientos (reposición, carga Excel) sin error 500.

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clinico", "0004_historia_clinica_trazabilidad"),
        ("inventario", "0004_ajustes_catalogo_y_ventas"),
        ("peluqueria", "0008_remove_tarifapeluqueria"),
    ]

    operations = [
        migrations.AddField(
            model_name="movimientoinventario",
            name="cita_peluqueria",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="movimientos_inventario",
                to="peluqueria.citapeluqueria",
                verbose_name="Cita de peluquería",
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="devuelto",
            field=models.BooleanField(db_default=False, default=False),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="lotes",
            field=models.JSONField(
                blank=True, null=True, verbose_name="Lotes afectados"
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="registro_clinico",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="movimientos_inventario",
                to="clinico.registroclinico",
                verbose_name="Registro clínico",
            ),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("ENTRADA_COMPRA", "Entrada por Compra / Reposición"),
                    (
                        "ENTRADA_DEVOLUCION",
                        "Entrada por Devolución (anulación o cancelación)",
                    ),
                    ("SALIDA_VENTA", "Salida por Venta"),
                    ("SALIDA_CLINICA", "Salida por Uso en Consulta Clínica"),
                    ("SALIDA_PELUQUERIA", "Salida por Servicio de Peluquería"),
                    ("AJUSTE_MERMA", "Ajuste / Pérdida / Vencimiento"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="InsumoServicio",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "servicio",
                    models.CharField(
                        choices=[
                            ("BANO", "Solamente Baño"),
                            ("CORTE", "Corte Despuntado (Solo tijera)"),
                            ("COMPLETO", "Corte Total (Máquina y tijera)"),
                        ],
                        max_length=20,
                        verbose_name="Servicio",
                    ),
                ),
                (
                    "tamano",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("", "Todos los tamaños"),
                            ("PEQUENO", "Pequeño (1 - 10 kg)"),
                            ("MEDIANO", "Mediano (11 - 25 kg)"),
                            ("GRANDE", "Grande (Más de 25 kg)"),
                        ],
                        default="",
                        max_length=10,
                        verbose_name="Tamaño de la mascota",
                    ),
                ),
                (
                    "cantidad",
                    models.PositiveIntegerField(
                        default=1,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Cantidad por servicio",
                    ),
                ),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usos_en_servicios",
                        to="inventario.producto",
                        verbose_name="Producto",
                    ),
                ),
            ],
            options={
                "verbose_name": "Insumo por servicio",
                "verbose_name_plural": "Insumos por servicio",
                "ordering": ["servicio", "tamano", "producto__nombre"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("servicio", "tamano", "producto"),
                        name="uniq_insumo_servicio_tamano_producto",
                    )
                ],
            },
        ),
    ]