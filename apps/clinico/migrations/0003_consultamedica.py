import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clinico", "0002_hospitalizacion_diagnostico_presuntivo_and_more"),
        ("directorio", "0005_alter_mascota_codigo_mascota"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConsultaMedica",
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
                ("fecha_consulta", models.DateTimeField(auto_now_add=True)),
                ("anamnesis", models.TextField(verbose_name="Anamnesis")),
                (
                    "peso",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=7,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0.01)],
                        verbose_name="Peso (kg)",
                    ),
                ),
                (
                    "temperatura",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=4,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Temperatura (°C)",
                    ),
                ),
                (
                    "frecuencia_cardiaca",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Frecuencia cardíaca (lpm)",
                    ),
                ),
                (
                    "frecuencia_respiratoria",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Frecuencia respiratoria (rpm)",
                    ),
                ),
                ("examen_general", models.TextField(blank=True, verbose_name="Examen general")),
                ("sistema_tegumentario", models.TextField(blank=True, verbose_name="Sistema tegumentario")),
                ("sistema_cardiovascular", models.TextField(blank=True, verbose_name="Sistema cardiovascular")),
                ("sistema_respiratorio", models.TextField(blank=True, verbose_name="Sistema respiratorio")),
                ("sistema_digestivo", models.TextField(blank=True, verbose_name="Sistema digestivo")),
                ("sistema_genitourinario", models.TextField(blank=True, verbose_name="Sistema genitourinario")),
                ("sistema_musculoesqueletico", models.TextField(blank=True, verbose_name="Sistema musculoesquelético")),
                ("sistema_nervioso", models.TextField(blank=True, verbose_name="Sistema nervioso")),
                ("sistema_linfatico", models.TextField(blank=True, verbose_name="Sistema linfático")),
                (
                    "mascota",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historial_clinico",
                        to="directorio.mascota",
                    ),
                ),
                (
                    "profesional",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="consultas_clinicas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Consulta médica",
                "verbose_name_plural": "Consultas médicas",
                "ordering": ["-fecha_consulta", "-pk"],
            },
        ),
    ]
