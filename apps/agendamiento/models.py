from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone

from apps.directorio.models import Mascota


class Cita(models.Model):
    """
    HU06: Agendamiento de Consultas Médicas.
    HU06-fix:
      - TIPO_SERVICIO_CHOICES: lista cerrada de servicios reales de la clínica.
      - clean(): valida que la fecha no sea anterior a hoy.
    """

    ESTADO_CHOICES = [
        ("programada", "Programada"),
        ("atendida", "Atendida"),
        ("cancelada", "Cancelada"),
    ]

    TIPO_SERVICIO_CHOICES = [
        ("consulta_general", "Consulta General"),
        ("vacunacion", "Vacunación"),
        ("desparasitacion", "Desparasitación"),
        ("sedacion", "Sedación"),
        ("cirugia", "Cirugía"),
        ("eutanasia", "Eutanasia"),
        ("peluqueria", "Peluquería / Spa"),
        ("control", "Control Post-Operatorio"),
        ("otro", "Otro"),
    ]

    id_cita = models.AutoField(primary_key=True)
    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name="citas",
        db_column="id_mascota_id",
    )
    veterinario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="citas_asignadas",
        limit_choices_to={"id_rol__nombre_rol": "veterinario"},
        db_column="id_usuario_creo_id",
    )
    tipo_servicio = models.CharField(
        max_length=30,
        choices=TIPO_SERVICIO_CHOICES,
        default="consulta_general",
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="programada")
    fecha_anterior = models.DateField(null=True, blank=True)
    hora_anterior = models.TimeField(null=True, blank=True)
    motivo_cancelacion = models.CharField(max_length=255, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ["fecha", "hora_inicio"]
        constraints = [
            UniqueConstraint(
                fields=["veterinario", "fecha", "hora_inicio"],
                condition=~Q(estado="cancelada"),
                name="unique_cita_veterinario_horario",
            )
        ]

    def __str__(self):
        return f"{self.mascota.nombre} - {self.fecha} {self.hora_inicio} ({self.veterinario})"

    def clean(self):
        hoy = timezone.now().date()

        # Bloquear fechas pasadas
        if self.fecha and self.fecha < hoy:
            raise ValidationError(
                {"fecha": "No se pueden agendar citas en fechas pasadas. Selecciona hoy o una fecha futura."}
            )

        # RF24: sin cruces de horario para el mismo veterinario
        if self.veterinario_id and self.fecha and self.hora_inicio:
            conflicto = (
                Cita.objects.filter(
                    veterinario_id=self.veterinario_id,
                    fecha=self.fecha,
                    hora_inicio=self.hora_inicio,
                )
                .exclude(estado="cancelada")
                .exclude(pk=self.pk)
            )
            if conflicto.exists():
                raise ValidationError(
                    "Este veterinario ya tiene una cita programada en esa fecha y hora."
                )
