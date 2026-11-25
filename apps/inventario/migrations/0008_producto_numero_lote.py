# PB-21 / RF11: número de lote en el producto (inventario simple: un lote, el
# de la fecha de vencimiento del producto).
#
# - Agrega Producto.numero_lote (admite NULL: segura para la base compartida;
#   el código de otras ramas que no la conoce sigue guardando productos).
# - Si un lote antiguo (StockLote) con unidades tiene la misma fecha que el
#   producto, se copia su número. StockLote no se toca.

from django.db import migrations, models


def copiar_numero_de_lotes(apps, schema_editor):
    Producto = apps.get_model('inventario', 'Producto')
    StockLote = apps.get_model('inventario', 'StockLote')
    lotes = (StockLote.objects.filter(cantidad__gt=0, fecha_vencimiento__isnull=False)
             .exclude(numero_lote='').order_by('fecha_vencimiento', 'pk'))
    vistos = set()
    for lote in lotes:
        if lote.producto_id in vistos:
            continue
        vistos.add(lote.producto_id)
        Producto.objects.filter(
            pk=lote.producto_id, fecha_vencimiento=lote.fecha_vencimiento, numero_lote__isnull=True,
        ).update(numero_lote=lote.numero_lote[:100])


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0007_merge_rama_duvan'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='numero_lote',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Número de lote'),
        ),
        migrations.RunPython(copiar_numero_de_lotes, migrations.RunPython.noop),
    ]
