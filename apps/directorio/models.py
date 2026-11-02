from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Dueno(models.Model):
    id_dueno = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=255)
    correo = models.EmailField(blank=True)
    fecha_registro = models.DateField(auto_now_add=True)
    es_recurrente = models.BooleanField(default=False)
    numero_visitas = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Dueño"
        verbose_name_plural = "Dueños"

    def __str__(self):
        return self.nombre_completo


class Mascota(models.Model):
    ESPECIE_CHOICES = [
        ("perro", "Perro"),
        ("gato", "Gato"),
        ("ave", "Ave"),
        ("roedor", "Roedor"),
        ("conejo", "Conejo"),
        ("otro", "Otro"),
    ]

    TAMANO_CHOICES = [
        ("pequeno", "Pequeño"),
        ("mediano", "Mediano"),
        ("grande", "Grande"),
    ]

    SEXO_CHOICES = [
        ("M", "Masculino"),
        ("F", "Femenino"),
    ]

    id_mascota = models.AutoField(primary_key=True)
    codigo_mascota = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        verbose_name="Código",
    )
    id_dueno = models.ForeignKey(Dueno, on_delete=models.CASCADE, related_name="mascotas")
    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=20, choices=ESPECIE_CHOICES)
    raza = models.CharField(max_length=100, blank=True)
    tamano = models.CharField(max_length=20, choices=TAMANO_CHOICES, blank=True)
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES, blank=True)
    color = models.CharField(max_length=80, blank=True, verbose_name="Color")
    fecha_nacimiento = models.DateField(null=True, blank=True)
    peso = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.01)],
        verbose_name="Peso (kg)",
    )
    condicion_pelaje = models.CharField(max_length=100, blank=True)
    fecha_registro = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"

    def __str__(self):
        return f"{self.nombre} [{self.codigo_mascota}] ({self.id_dueno.nombre_completo})"

    
    # ------------------------------------------------------------------
    def _generar_codigo(self):
        import random
        import string
        
        
        hoy = timezone.now()
        prefijo_fecha = hoy.strftime("%y%m")
        chars = string.ascii_uppercase + string.digits
        
        while True:
            sufijo = "".join(random.choices(chars, k=4))
            codigo = f"M{prefijo_fecha}-{sufijo}"
            if not Mascota.objects.filter(codigo_mascota=codigo).exists():
                return codigo

    def save(self, *args, **kwargs):
        if not self.codigo_mascota:
            self.codigo_mascota = self._generar_codigo()
        super().save(*args, **kwargs)


class Vacunacion(models.Model):
    mascota = models.ForeignKey(
        Mascota,
        on_delete=models.CASCADE,
        related_name="antecedentes_vacunacion",
    )
    vacuna = models.CharField(max_length=120, verbose_name="Vacuna")
    fecha = models.DateField(verbose_name="Fecha de aplicación")
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "Antecedente de vacunación"
        verbose_name_plural = "Antecedentes de vacunación"

    def __str__(self):
        return f"{self.vacuna} — {self.mascota.nombre} ({self.fecha})"