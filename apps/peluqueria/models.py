from decimal import Decimal

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

from apps.directorio.models import Mascota

# Comisión del groomer sobre el precio del servicio (regla de la rama Abel).
COMISION_GROOMER_PORCENTAJE = Decimal('0.40')


class CitaPeluqueria(models.Model):
    TAMANO_CHOICES = [
        ('PEQUENO', 'Pequeño (1 - 10 kg)'),
        ('MEDIANO', 'Mediano (11 - 25 kg)'),
        ('GRANDE',  'Grande (Más de 25 kg)'),
    ]

    SERVICIO_CHOICES = [
        ('BANO',     'Solamente Baño'),
        ('CORTE',    'Corte Despuntado (Solo tijera)'),
        ('COMPLETO', 'Corte Total (Máquina y tijera)'),
    ]

    ESTADO_CHOICES = [
        ('Programada', 'Programada'),
        ('Realizada', 'Realizada'),
        ('Cancelada', 'Cancelada'),
    ]

    # Vínculo con la mascota del directorio (null para citas antiguas, que
    # solo guardaban el nombre como texto).
    mascota             = models.ForeignKey(
        Mascota,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='citas_peluqueria',
    )
    nombre_mascota      = models.CharField(max_length=100)
    raza                = models.CharField(max_length=100)
    tamano              = models.CharField(max_length=10, choices=TAMANO_CHOICES, default='MEDIANO')
    servicio            = models.CharField(max_length=20, choices=SERVICIO_CHOICES, default='BANO')
    fecha_hora          = models.DateTimeField()
    duracion_estimada_min = models.IntegerField(default=60)
    # Precio del servicio en pesos colombianos (COP), sin decimales.
    precio              = models.PositiveIntegerField(default=0)
    observaciones       = models.TextField(blank=True, null=True)
    # HU21-fix: groomer responsable de la cita
    groomer             = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='citas_peluqueria',
        limit_choices_to={'id_rol__nombre_rol': 'groomer'},
        verbose_name='Groomer responsable',
    )
    creado_en           = models.DateTimeField(auto_now_add=True)

    # Columnas que agregó la migración 0004_citapeluqueria_estado_and_more (rama duvan).
    # Deben estar en el modelo: la base de datos ya las tiene y "estado" no admite NULL.
    estado              = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Programada',
        verbose_name='Estado de la Cita',
    )
    motivo_cancelacion  = models.TextField(
        blank=True,
        null=True,
        verbose_name='Motivo de Cancelación',
    )

    # Cada cuántos días se recuerda el próximo baño (pantalla clínico › Recordatorios).
    intervalo_recordatorio_dias = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        verbose_name='Intervalo de recordatorio (días)',
    )

    # Columnas que agregó la migración 0007 de la rama Abel. La base compartida
    # (Supabase) ya las tiene y NO admiten NULL: si faltan en el modelo, guardar
    # una cita de peluquería da error 500 (IntegrityError en condicion_pelaje).
    condicion_pelaje    = models.CharField(max_length=100, blank=True, default='')
    comision_groomer    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name        = 'Cita de Peluquería'
        verbose_name_plural = 'Citas de Peluquería'
        ordering            = ['fecha_hora']

    def __str__(self):
        groomer_nombre = self.groomer.nombre_completo if self.groomer else 'Sin asignar'
        return f"Cita Peluquería: {self.nombre_mascota} — {self.get_servicio_display()} ({groomer_nombre})"

    def save(self, *args, **kwargs):
        # La comisión se recalcula siempre a partir del precio.
        self.comision_groomer = Decimal(self.precio or 0) * COMISION_GROOMER_PORCENTAJE
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'precio' in update_fields:
            kwargs['update_fields'] = set(update_fields) | {'comision_groomer'}
        super().save(*args, **kwargs)