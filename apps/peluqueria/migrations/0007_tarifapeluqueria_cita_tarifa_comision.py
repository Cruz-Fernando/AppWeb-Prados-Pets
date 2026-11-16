from decimal import Decimal

from django.db import migrations, models

TABLA = 'peluqueria_citapeluqueria'
COMISION = Decimal('0.40')


def _campo_condicion():
    return models.CharField(blank=True, default='', max_length=100)


def _campo_comision():
    return models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)


def _agregar_si_falta(nombre, fabrica):
    def agregar(apps, schema_editor):
        conexion = schema_editor.connection
        with conexion.cursor() as cursor:
            existentes = {c.name for c in conexion.introspection.get_table_description(cursor, TABLA)}
        if nombre not in existentes:
            campo = fabrica()
            campo.set_attributes_from_name(nombre)
            schema_editor.add_field(apps.get_model('peluqueria', 'CitaPeluqueria'), campo)
    return agregar


def rellenar_valores(apps, schema_editor):
    q = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {q(TABLA)} SET {q('condicion_pelaje')} = '' "
            f"WHERE {q('condicion_pelaje')} IS NULL"
        )
        cursor.execute(
            f"UPDATE {q(TABLA)} SET {q('comision_groomer')} = {q('precio')} * %s "
            f"WHERE {q('comision_groomer')} IS NULL OR {q('comision_groomer')} = 0",
            [COMISION],
        )


class Migration(migrations.Migration):

    dependencies = [
        ('peluqueria', '0006_citapeluqueria_intervalo_recordatorio_dias'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='citapeluqueria',
                    name='condicion_pelaje',
                    field=_campo_condicion(),
                ),
            ],
            database_operations=[
                migrations.RunPython(_agregar_si_falta('condicion_pelaje', _campo_condicion), migrations.RunPython.noop),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='citapeluqueria',
                    name='comision_groomer',
                    field=_campo_comision(),
                ),
            ],
            database_operations=[
                migrations.RunPython(_agregar_si_falta('comision_groomer', _campo_comision), migrations.RunPython.noop),
            ],
        ),
        migrations.RunPython(rellenar_valores, migrations.RunPython.noop),
    ]