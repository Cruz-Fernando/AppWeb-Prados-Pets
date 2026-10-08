# Migración manual HU06-fix
# La tabla 'agendamiento_cita' ya existe en Supabase con las columnas
# 'hora' y 'motivo'. Esta migración:
#   1. Agrega las columnas nuevas (hora_inicio, hora_fin, motivo_cancelacion,
#      tipo_servicio, fecha_anterior, hora_anterior) con db_column explícito
#      donde el nombre en BD difiere del nombre en Django.
#   2. NO renombra 'hora' ni 'motivo' en la BD para evitar errores;
#      los campos nuevos usan db_column para apuntar a la columna real.
#   3. Actualiza Meta options y la constraint.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agendamiento', '0001_initial'),
        ('directorio', '0003_add_color_and_codigo_mascota'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -----------------------------------------------------------------
        # 1. Quitar la constraint vieja (referencia a 'hora' que ya no existirá)
        # -----------------------------------------------------------------
        migrations.RemoveConstraint(
            model_name='cita',
            name='unique_cita_veterinario_horario',
        ),

        # -----------------------------------------------------------------
        # 2. Renombrar campo Django 'hora' → 'hora_inicio'
        #    El db_column queda como 'hora' (la columna real en Supabase)
        # -----------------------------------------------------------------
        migrations.AlterField(
            model_name='cita',
            name='hora',
            field=models.TimeField(db_column='hora'),
        ),
        migrations.RenameField(
            model_name='cita',
            old_name='hora',
            new_name='hora_inicio',
        ),
        # Aseguramos que db_column='hora' se conserve tras el rename
        migrations.AlterField(
            model_name='cita',
            name='hora_inicio',
            field=models.TimeField(db_column='hora'),
        ),

        # -----------------------------------------------------------------
        # 3. Renombrar campo Django 'motivo' → 'motivo_cancelacion'
        #    El db_column queda como 'motivo'
        # -----------------------------------------------------------------
        migrations.AlterField(
            model_name='cita',
            name='motivo',
            field=models.CharField(blank=True, max_length=255, db_column='motivo'),
        ),
        migrations.RenameField(
            model_name='cita',
            old_name='motivo',
            new_name='motivo_cancelacion',
        ),
        migrations.AlterField(
            model_name='cita',
            name='motivo_cancelacion',
            field=models.CharField(blank=True, max_length=255, db_column='motivo'),
        ),

        # -----------------------------------------------------------------
        # 4. Agregar columnas nuevas
        # -----------------------------------------------------------------
        migrations.AddField(
            model_name='cita',
            name='hora_fin',
            field=models.TimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='cita',
            name='tipo_servicio',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('consulta_general', 'Consulta General'),
                    ('vacunacion', 'Vacunación'),
                    ('desparasitacion', 'Desparasitación'),
                    ('sedacion', 'Sedación'),
                    ('cirugia', 'Cirugía'),
                    ('eutanasia', 'Eutanasia'),
                    ('peluqueria', 'Peluquería / Spa'),
                    ('control', 'Control Post-Operatorio'),
                    ('otro', 'Otro'),
                ],
                default='consulta_general',
            ),
        ),
        migrations.AddField(
            model_name='cita',
            name='fecha_anterior',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='cita',
            name='hora_anterior',
            field=models.TimeField(null=True, blank=True),
        ),

        # -----------------------------------------------------------------
        # 5. Actualizar FKs con db_column correcto (ya definido en el modelo)
        # -----------------------------------------------------------------
        migrations.AlterField(
            model_name='cita',
            name='mascota',
            field=models.ForeignKey(
                db_column='id_mascota_id',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='citas',
                to='directorio.mascota',
            ),
        ),
        migrations.AlterField(
            model_name='cita',
            name='veterinario',
            field=models.ForeignKey(
                db_column='id_usuario_creo_id',
                limit_choices_to={'id_rol__nombre_rol': 'veterinario'},
                on_delete=django.db.models.deletion.PROTECT,
                related_name='citas_asignadas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # -----------------------------------------------------------------
        # 6. Actualizar Meta options
        # -----------------------------------------------------------------
        migrations.AlterModelOptions(
            name='cita',
            options={
                'ordering': ['fecha', 'hora_inicio'],
                'verbose_name': 'Cita',
                'verbose_name_plural': 'Citas',
            },
        ),

        # -----------------------------------------------------------------
        # 7. Recrear constraint con el nombre de campo correcto
        # -----------------------------------------------------------------
        migrations.AddConstraint(
            model_name='cita',
            constraint=models.UniqueConstraint(
                condition=models.Q(('estado', 'cancelada'), _negated=True),
                fields=['veterinario', 'fecha', 'hora_inicio'],
                name='unique_cita_veterinario_horario',
            ),
        ),
    ]
