# Une las dos migraciones 0004 de peluquería:
#   - 0004_cita_mascota_y_precio            (rama Pruebas_V2 / main)
#   - 0004_citapeluqueria_estado_and_more   (rama duvan: estado y motivo de cancelación)
# La base de datos compartida ya tiene aplicadas ambas, así que esta migración
# no hace cambios: solo deja el historial de migraciones en orden.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('peluqueria', '0004_cita_mascota_y_precio'),
        ('peluqueria', '0004_citapeluqueria_estado_and_more'),
    ]

    operations = []