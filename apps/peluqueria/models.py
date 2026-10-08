from django.conf import settings
from django.db import models


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

    nombre_mascota      = models.CharField(max_length=100)
    raza                = models.CharField(max_length=100)
    tamano              = models.CharField(max_length=10, choices=TAMANO_CHOICES, default='MEDIANO')
    servicio            = models.CharField(max_length=20, choices=SERVICIO_CHOICES, default='BANO')
    fecha_hora          = models.DateTimeField()
    duracion_estimada_min = models.IntegerField(default=60)
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

    class Meta:
        verbose_name        = 'Cita de Peluquería'
        verbose_name_plural = 'Citas de Peluquería'
        ordering            = ['fecha_hora']

    def __str__(self):
        groomer_nombre = self.groomer.nombre_completo if self.groomer else 'Sin asignar'
        return f"Cita Peluquería: {self.nombre_mascota} — {self.get_servicio_display()} ({groomer_nombre})"
