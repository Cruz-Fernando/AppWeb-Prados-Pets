from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('peluqueria', '0007_tarifapeluqueria_cita_tarifa_comision'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TarifaPeluqueria',
        ),
    ]
