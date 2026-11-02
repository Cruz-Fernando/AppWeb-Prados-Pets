from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

from apps.directorio.models import Mascota

from .registros import TIPO_CHOICES, obtener_tipo


MUCOSAS_CHOICES = [
    ("rosadas", "Rosadas"),
    ("palidas", "Pálidas"),
    ("congestivas", "Congestivas"),
    ("cianoticas", "Cianóticas"),
    ("ictericas", "Ictéricas"),
]

CONDICION_CORPORAL_CHOICES = [
    ("1", "1/5 · Caquéctico"),
    ("2", "2/5 · Delgado"),
    ("3", "3/5 · Ideal"),
    ("4", "4/5 · Sobrepeso"),
    ("5", "5/5 · Obeso"),
]

HIDRATACION_CHOICES = [
    ("normal", "Normal (< 5 %)"),
    ("leve", "Leve (5–6 %)"),
    ("moderada", "Moderada (7–9 %)"),
    ("severa", "Severa (≥ 10 %)"),
]


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
    CONDICION_ALTA_CHOICES = [
        ('mejorado', 'Mejorado'),
        ('curado', 'Curado / Recuperado'),
        ('voluntaria', 'Alta voluntaria (solicitud del propietario)'),
        ('remitido', 'Remitido a otra clínica'),
        ('fallecido', 'Fallecido'),
    ]
    PRONOSTICO_CHOICES = [
        ('favorable', 'Favorable'),
        ('reservado', 'Reservado'),
        ('grave', 'Grave'),
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

    # Ingreso
    profesional_ingreso = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='hospitalizaciones_ingresadas', verbose_name="Médico que ingresa",
    )
    area = models.CharField(max_length=60, blank=True, verbose_name="Área / jaula",
                            help_text="Ej: Jaula 3, Aislamiento, UCI")
    pronostico = models.CharField(max_length=15, choices=PRONOSTICO_CHOICES, blank=True,
                                  verbose_name="Pronóstico")

    # Alta / egreso
    profesional_alta = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='hospitalizaciones_egresadas', verbose_name="Médico que da el alta",
    )
    condicion_alta = models.CharField(max_length=15, choices=CONDICION_ALTA_CHOICES, blank=True,
                                      verbose_name="Condición al egreso")
    resumen_alta = models.TextField(blank=True, verbose_name="Resumen de la estancia (epicrisis)")
    indicaciones_alta = models.TextField(blank=True, verbose_name="Indicaciones para casa")
    proximo_control = models.DateField(null=True, blank=True, verbose_name="Próximo control")

    class Meta:
        verbose_name = "Hospitalización"
        verbose_name_plural = "Hospitalizaciones"
        ordering = ['-fecha_ingreso']

    def __str__(self):
        return f"{self.mascota.nombre} - {self.get_estado_display()}"

    @property
    def numero(self):
        return f"HO-{self.pk:05d}" if self.pk else "HO-—"

    @property
    def activa(self):
        return self.estado == 'ACTIVO'

    @property
    def dias_estancia(self):
        fin = self.fecha_alta or timezone.now()
        return max((fin - self.fecha_ingreso).days, 0) + 1


class EvolucionHospitalaria(models.Model):
    """Ronda / nota de evolución de un paciente internado."""

    ESTADO_CHOICES = [
        ('estable', 'Estable'),
        ('mejorando', 'Mejorando'),
        ('sin_cambios', 'Sin cambios'),
        ('empeorando', 'Empeorando'),
        ('critico', 'Crítico'),
    ]
    APETITO_CHOICES = [
        ('normal', 'Normal'),
        ('disminuido', 'Disminuido'),
        ('anorexia', 'Anorexia'),
        ('asistida', 'Alimentación asistida'),
        ('ayuno', 'En ayuno (indicado)'),
    ]

    hospitalizacion = models.ForeignKey(Hospitalizacion, on_delete=models.CASCADE,
                                        related_name='evoluciones')
    profesional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='evoluciones_hospitalarias')
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha y hora")

    peso = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                               validators=[MinValueValidator(0.01)], verbose_name="Peso (kg)")
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True,
                                      validators=[MinValueValidator(30), MaxValueValidator(45)],
                                      verbose_name="Temperatura (°C)")
    frecuencia_cardiaca = models.PositiveSmallIntegerField(null=True, blank=True,
                                                           verbose_name="F. cardíaca (lpm)")
    frecuencia_respiratoria = models.PositiveSmallIntegerField(null=True, blank=True,
                                                               verbose_name="F. respiratoria (rpm)")
    mucosas = models.CharField(max_length=15, choices=MUCOSAS_CHOICES, blank=True,
                               verbose_name="Mucosas")

    estado_general = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='estable',
                                      verbose_name="Estado general")
    apetito = models.CharField(max_length=15, choices=APETITO_CHOICES, blank=True,
                               verbose_name="Apetito")
    orina = models.BooleanField(default=False, verbose_name="Orinó")
    defeca = models.BooleanField(default=False, verbose_name="Defecó")
    vomito = models.BooleanField(default=False, verbose_name="Vómito")

    fluidoterapia = models.CharField(max_length=255, blank=True, verbose_name="Fluidoterapia",
                                     help_text="Solución, velocidad (ml/h)")
    medicamentos = models.TextField(blank=True, verbose_name="Medicamentos administrados")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones / plan")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        verbose_name = "Evolución hospitalaria"
        verbose_name_plural = "Evoluciones hospitalarias"

    def __str__(self):
        return f"Evolución {self.hospitalizacion.numero} · {self.fecha:%d/%m/%Y %H:%M}"


class RegistroClinico(models.Model):
    """
    Registro de la historia clínica de una mascota (una atención).

    Los campos comunes son columnas; lo propio de cada tipo vive en `detalle`
    según el catálogo de registros.py. Un registro nunca se borra: se anula
    con motivo, y cada cambio queda en TrazaClinica.
    """

    mascota = models.ForeignKey(Mascota, on_delete=models.PROTECT,
                                related_name='registros_clinicos')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    profesional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name='registros_clinicos')
    fecha_atencion = models.DateTimeField(default=timezone.now, verbose_name="Fecha y hora de atención")
    hospitalizacion = models.ForeignKey(Hospitalizacion, on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='registros',
                                        verbose_name="Durante la hospitalización")

    motivo = models.CharField(max_length=255, verbose_name="Motivo")
    anamnesis = models.TextField(blank=True, verbose_name="Anamnesis")

    # Constantes vitales
    peso = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True,
                               validators=[MinValueValidator(0.01)], verbose_name="Peso (kg)")
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True,
                                      validators=[MinValueValidator(30), MaxValueValidator(45)],
                                      verbose_name="Temperatura (°C)")
    frecuencia_cardiaca = models.PositiveSmallIntegerField(null=True, blank=True,
                                                           verbose_name="F. cardíaca (lpm)")
    frecuencia_respiratoria = models.PositiveSmallIntegerField(null=True, blank=True,
                                                               verbose_name="F. respiratoria (rpm)")
    tllc = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True,
                               validators=[MinValueValidator(0)], verbose_name="TLLC (seg)")
    mucosas = models.CharField(max_length=15, choices=MUCOSAS_CHOICES, blank=True,
                               verbose_name="Mucosas")
    condicion_corporal = models.CharField(max_length=2, choices=CONDICION_CORPORAL_CHOICES,
                                          blank=True, verbose_name="Condición corporal")
    hidratacion = models.CharField(max_length=10, choices=HIDRATACION_CHOICES, blank=True,
                                   verbose_name="Hidratación")

    # Evaluación y plan
    diagnostico_presuntivo = models.TextField(blank=True, verbose_name="Diagnóstico presuntivo")
    diagnostico_definitivo = models.TextField(blank=True, verbose_name="Diagnóstico definitivo")
    tratamiento = models.TextField(blank=True, verbose_name="Tratamiento realizado")
    prescripcion = models.TextField(blank=True, verbose_name="Fórmula médica",
                                    help_text="Medicamento – dosis – frecuencia – duración")
    recomendaciones = models.TextField(blank=True, verbose_name="Recomendaciones al propietario")
    proximo_control = models.DateField(null=True, blank=True, verbose_name="Próximo control")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    detalle = models.JSONField(default=dict, blank=True)
    adjunto = models.FileField(upload_to='clinico/registros/%Y/%m/', null=True, blank=True,
                               verbose_name="Documento adjunto",
                               help_text="Consentimiento firmado, resultados de laboratorio, imágenes...")

    # Anulación (los registros clínicos no se eliminan)
    anulado = models.BooleanField(default=False)
    anulado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='registros_anulados')
    anulado_en = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField(max_length=255, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                        null=True, blank=True, related_name='registros_editados')

    class Meta:
        ordering = ['-fecha_atencion', '-pk']
        verbose_name = "Registro clínico"
        verbose_name_plural = "Registros clínicos"
        indexes = [models.Index(fields=['mascota', 'tipo', '-fecha_atencion'])]

    def __str__(self):
        return f"{self.numero} · {self.get_tipo_display()} · {self.mascota.nombre}"

    @property
    def numero(self):
        return f"RC-{self.pk:06d}" if self.pk else "RC-—"

    @property
    def definicion(self):
        return obtener_tipo(self.tipo)

    @property
    def fue_editado(self):
        return self.actualizado_por_id is not None


class TrazaClinica(models.Model):
    """Bitácora inmutable: quién hizo qué, cuándo y desde dónde."""

    ACCION_CHOICES = [
        ('crear', 'Creó registro'),
        ('editar', 'Editó registro'),
        ('anular', 'Anuló registro'),
        ('pdf', 'Descargó PDF'),
        ('ingreso', 'Ingresó a hospitalización'),
        ('evolucion', 'Registró evolución'),
        ('alta', 'Dio de alta'),
    ]

    mascota = models.ForeignKey(Mascota, on_delete=models.PROTECT, related_name='trazas_clinicas')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, related_name='trazas_clinicas')
    accion = models.CharField(max_length=15, choices=ACCION_CHOICES)
    descripcion = models.CharField(max_length=255)
    cambios = models.JSONField(default=dict, blank=True)
    registro = models.ForeignKey(RegistroClinico, on_delete=models.SET_NULL, null=True,
                                 blank=True, related_name='trazas')
    hospitalizacion = models.ForeignKey(Hospitalizacion, on_delete=models.SET_NULL, null=True,
                                        blank=True, related_name='trazas')
    ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        verbose_name = "Traza clínica"
        verbose_name_plural = "Trazabilidad clínica"

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} · {self.get_accion_display()} · {self.mascota.nombre}"