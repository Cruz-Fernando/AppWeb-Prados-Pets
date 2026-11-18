# Une la rama de main (0006_inventario_simple_fecha_vencimiento) con la de
# Duvan (0006_merge_20261116_1424). Su 0004 repite los mismos cambios que
# 0004_ajustes_catalogo_y_ventas, así que no hay operaciones nuevas.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0006_inventario_simple_fecha_vencimiento"),
        ("inventario", "0006_merge_20261116_1424"),
    ]

    operations = []
