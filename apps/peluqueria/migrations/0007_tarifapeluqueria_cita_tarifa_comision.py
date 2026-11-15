from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


def calcular_comisiones_existentes(apps, schema_editor):
    CitaPeluqueria = apps.get_model('peluqueria', 'CitaPeluqueria')
    for cita in CitaPeluqueria.objects.all().iterator():
        cita.comision_groomer = Decimal(cita.precio) * Decimal('0.40')
        cita.save(update_fields=['comision_groomer'])


class Migration(migrations.Migration):

    dependencies = [
        ('peluqueria', '0006_citapeluqueria_intervalo_recordatorio_dias'),
    ]

    operations = [
        migrations.AddField(
            model_name='citapeluqueria',
            name='condicion_pelaje',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='citapeluqueria',
            name='comision_groomer',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.CreateModel(
            name='TarifaPeluqueria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raza', models.CharField(blank=True, help_text='Déjalo vacío para aplicar a todas las razas.', max_length=100)),
                ('tamano', models.CharField(choices=[('PEQUENO', 'Pequeño (1 - 10 kg)'), ('MEDIANO', 'Mediano (11 - 25 kg)'), ('GRANDE', 'Grande (Más de 25 kg)')], max_length=10)),
                ('condicion_pelaje', models.CharField(max_length=100)),
                ('servicio', models.CharField(choices=[('BANO', 'Solamente Baño'), ('CORTE', 'Corte Despuntado (Solo tijera)'), ('COMPLETO', 'Corte Total (Máquina y tijera)')], max_length=20)),
                ('precio', models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name='Precio (COP)')),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Tarifa de peluquería',
                'verbose_name_plural': 'Tarifas de peluquería',
                'ordering': ['raza', 'tamano', 'condicion_pelaje', 'servicio'],
            },
        ),
        migrations.AddConstraint(
            model_name='tarifapeluqueria',
            constraint=models.UniqueConstraint(fields=('raza', 'tamano', 'condicion_pelaje', 'servicio'), name='uniq_tarifa_pelu_raza_tamano_cond_serv'),
        ),
        migrations.RunPython(calcular_comisiones_existentes, migrations.RunPython.noop),
    ]
