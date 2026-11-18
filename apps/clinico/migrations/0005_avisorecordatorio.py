import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clinico", "0004_historia_clinica_trazabilidad"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AvisoRecordatorio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("vacunacion", "Vacunación"), ("bano", "Baño")], max_length=12)),
                ("cita_id", models.PositiveIntegerField()),
                ("fecha_recordatorio", models.DateField()),
                ("avisado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "avisado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="avisos_recordatorio",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Aviso de recordatorio",
                "verbose_name_plural": "Avisos de recordatorios",
                "indexes": [models.Index(fields=["fecha_recordatorio"], name="clinico_aviso_fecha_idx")],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("tipo", "cita_id", "fecha_recordatorio"), name="aviso_recordatorio_unico"
                    )
                ],
            },
        ),
    ]
