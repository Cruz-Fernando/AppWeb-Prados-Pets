# Intervalo del recordatorio de baño (lo usa la pantalla clínico › Recordatorios).
#
# En la base compartida (Supabase) la columna ya existe —se creó con una migración
# que nunca se subió al repositorio—, así que aquí solo se crea si falta. En una
# base nueva (pruebas o base local) se crea normalmente.

import django.core.validators
from django.db import migrations, models

TABLA = 'peluqueria_citapeluqueria'
COLUMNA = 'intervalo_recordatorio_dias'
DEFECTO = 30


def _nuevo_campo():
    campo = models.PositiveIntegerField(
        default=DEFECTO,
        validators=[django.core.validators.MinValueValidator(1)],
        verbose_name='Intervalo de recordatorio (días)',
    )
    campo.set_attributes_from_name(COLUMNA)
    return campo


def crear_columna_si_falta(apps, schema_editor):
    conexion = schema_editor.connection
    with conexion.cursor() as cursor:
        columnas = [c.name for c in conexion.introspection.get_table_description(cursor, TABLA)]
    CitaPeluqueria = apps.get_model('peluqueria', 'CitaPeluqueria')
    if COLUMNA not in columnas:
        schema_editor.add_field(CitaPeluqueria, _nuevo_campo())
    else:
        # Ya existe (base compartida): solo se rellenan filas vacías, por si las hubiera.
        with conexion.cursor() as cursor:
            cursor.execute(
                f'UPDATE {schema_editor.quote_name(TABLA)} '
                f'SET {schema_editor.quote_name(COLUMNA)} = %s '
                f'WHERE {schema_editor.quote_name(COLUMNA)} IS NULL',
                [DEFECTO],
            )


class Migration(migrations.Migration):

    dependencies = [
        ('peluqueria', '0005_merge_estado_y_precio'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='citapeluqueria',
                    name=COLUMNA,
                    field=models.PositiveIntegerField(
                        default=DEFECTO,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name='Intervalo de recordatorio (días)',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunPython(crear_columna_si_falta, migrations.RunPython.noop),
            ],
        ),
    ]