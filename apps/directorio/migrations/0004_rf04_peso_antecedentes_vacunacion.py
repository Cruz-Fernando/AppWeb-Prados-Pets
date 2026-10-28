import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("directorio", "0003_add_color_and_codigo_mascota"),
    ]

    operations = [
        migrations.AddField(
            model_name="mascota",
            name="peso",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=7,
                null=True,
                validators=[django.core.validators.MinValueValidator(0.01)],
                verbose_name="Peso (kg)",
            ),
        ),
        migrations.CreateModel(
            name="Vacunacion",
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
                ("vacuna", models.CharField(max_length=120, verbose_name="Vacuna")),
                ("fecha", models.DateField(verbose_name="Fecha de aplicación")),
                ("observaciones", models.TextField(blank=True)),
                (
                    "mascota",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="antecedentes_vacunacion",
                        to="directorio.mascota",
                    ),
                ),
            ],
            options={
                "verbose_name": "Antecedente de vacunación",
                "verbose_name_plural": "Antecedentes de vacunación",
                "ordering": ["-fecha", "-pk"],
            },
        ),
    ]
