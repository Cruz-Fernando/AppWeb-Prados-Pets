from django.db import models


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
        max_length=10,
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
    condicion_pelaje = models.CharField(max_length=100, blank=True)
    fecha_registro = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"

    def __str__(self):
        return f"{self.nombre} [{self.codigo_mascota}] ({self.id_dueno.nombre_completo})"

    # ------------------------------------------------------------------
    # Generación automática del código único de mascota (ej. M-A3X9)
    # ------------------------------------------------------------------
    def _generar_codigo(self):
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        while True:
            codigo = "M-" + "".join(random.choices(chars, k=4))
            if not Mascota.objects.filter(codigo_mascota=codigo).exists():
                return codigo

    def save(self, *args, **kwargs):
        if not self.codigo_mascota:
            self.codigo_mascota = self._generar_codigo()
        super().save(*args, **kwargs)
