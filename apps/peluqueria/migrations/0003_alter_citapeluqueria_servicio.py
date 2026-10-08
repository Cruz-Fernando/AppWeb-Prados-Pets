from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('peluqueria', '0002_alter_citapeluqueria_options_citapeluqueria_groomer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='citapeluqueria',
            name='servicio',
            field=models.CharField(choices=[('BANO', 'Solamente Baño'), ('CORTE', 'Corte Despuntado (Solo tijera)'), ('COMPLETO', 'Corte Total (Máquina y tijera)')], default='BANO', max_length=20),
        ),
    ]
