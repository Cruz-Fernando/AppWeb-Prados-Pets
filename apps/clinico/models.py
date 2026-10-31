from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

from apps.directorio.models import Mascota


class ConsultaMedica(models.Model):
    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name="historial_clinico",
    )
    profesional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultas_clinicas",
    )
    fecha_consulta = models.DateTimeField(auto_now_add=True)
    anamnesis = models.TextField(verbose_name="Anamnesis")
    peso = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        verbose_name="Peso (kg)",
    )
    temperatura = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name="Temperatura (°C)",
    )
    frecuencia_cardiaca = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Frecuencia cardíaca (lpm)",
    )
    frecuencia_respiratoria = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Frecuencia respiratoria (rpm)",
    )
    examen_general = models.TextField(blank=True, verbose_name="Examen general")
    sistema_tegumentario = models.TextField(blank=True, verbose_name="Sistema tegumentario")
    sistema_cardiovascular = models.TextField(blank=True, verbose_name="Sistema cardiovascular")
    sistema_respiratorio = models.TextField(blank=True, verbose_name="Sistema respiratorio")
    sistema_digestivo = models.TextField(blank=True, verbose_name="Sistema digestivo")
    sistema_genitourinario = models.TextField(blank=True, verbose_name="Sistema genitourinario")
    sistema_musculoesqueletico = models.TextField(blank=True, verbose_name="Sistema musculoesquelético")
    sistema_nervioso = models.TextField(blank=True, verbose_name="Sistema nervioso")
    sistema_linfatico = models.TextField(blank=True, verbose_name="Sistema linfático")

    class Meta:
        ordering = ["-fecha_consulta", "-pk"]
        verbose_name = "Consulta médica"
        verbose_name_plural = "Consultas médicas"

    def __str__(self):
        return f"Consulta de {self.mascota.nombre} ({self.fecha_consulta:%d/%m/%Y})"


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