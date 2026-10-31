from django.db import models
from apps.directorio.models import Mascota

class Hospitalizacion(models.Model):
    ESTADO_CHOICES = [
        ('ACTIVO', 'Internado / En Tratamiento'),
        ('ALTA', 'Dado de Alta'),
    ]
    
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name='hospitalizaciones')
    motivo = models.CharField(max_length=255, verbose_name="Motivo de Ingreso")
    
    # Signos Vitales y Triaje
    peso_actual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Peso (kg)")
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name="Temperatura (°C)")
    frecuencia_cardiaca = models.IntegerField(null=True, blank=True, verbose_name="Frec. Cardíaca (lpm)")
    frecuencia_respiratoria = models.IntegerField(null=True, blank=True, verbose_name="Frec. Respiratoria (rpm)")
    mucosas = models.CharField(max_length=100, null=True, blank=True, verbose_name="Estado de Mucosas")
    
    # Valoración
    diagnostico_presuntivo = models.TextField(blank=True, null=True, verbose_name="Diagnóstico Presuntivo")
    tratamiento_inicial = models.TextField(blank=True, null=True, verbose_name="Tratamiento Inicial")
    observaciones = models.TextField(blank=True, null=True, help_text="Notas clínicas adicionales.")
    
    # Documentos
    documento_consentimiento = models.FileField(upload_to='hospitalizacion/consentimientos/', null=True, blank=True, verbose_name="Consentimiento Informado")
    examenes_adjuntos = models.FileField(upload_to='hospitalizacion/examenes/', null=True, blank=True, verbose_name="Exámenes Clínicos")

    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_alta = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='ACTIVO')

    class Meta:
        verbose_name = "Hospitalización"
        verbose_name_plural = "Hospitalizaciones"
        ordering = ['-fecha_ingreso']

    def __str__(self):
        return f"{self.mascota.nombre} - {self.get_estado_display()}"