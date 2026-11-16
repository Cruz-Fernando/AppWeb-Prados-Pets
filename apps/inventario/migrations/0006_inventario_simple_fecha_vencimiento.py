# Inventario simple: cada producto tiene su cantidad y UNA fecha de vencimiento.
#
# - Agrega Producto.fecha_vencimiento (admite vacío: segura para la base
#   compartida; el código que no la conoce sigue funcionando).
# - Copia a cada producto la fecha más próxima de los lotes que aún tienen
#   unidades. La tabla de lotes NO se borra (historial y compatibilidad).

from django.db import migrations, models


def copiar_fechas_de_lotes(apps, schema_editor):
    Producto = apps.get_model('inventario', 'Producto')
    StockLote = apps.get_model('inventario', 'StockLote')
    fechas = {}
    for lote in (StockLote.objects.filter(cantidad__gt=0, fecha_vencimiento__isnull=False)
                 .order_by('fecha_vencimiento')):
        fechas.setdefault(lote.producto_id, lote.fecha_vencimiento)
    for producto_id, fecha in fechas.items():
        Producto.objects.filter(pk=producto_id, fecha_vencimiento__isnull=True).update(fecha_vencimiento=fecha)


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0005_descuento_automatico_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='fecha_vencimiento',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha de vencimiento'),
        ),
        migrations.RunPython(copiar_fechas_de_lotes, migrations.RunPython.noop),
    ]