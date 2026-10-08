from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.Model):
    """Roles del sistema: administrador, veterinario, auxiliar, groomer, domiciliario."""

    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre_rol


class Usuario(AbstractUser):
    """
    Usuario del sistema (personal de la clínica), extiende el modelo de auth
    de Django en vez de crear autenticación desde cero.

    Mapeo con el diagrama entidad-relación:
      - nombre_usuario -> username (heredado)
      - contrasena_hash -> password (heredado, Django lo hashea automáticamente)
      - correo -> email (heredado)

    HU02: todo usuario registrado debe tener un rol asignado (id_rol ya no
    admite NULL — ver migración 0003_usuario_rol_obligatorio). El campo
    "estado" es la fuente de verdad de acceso: al guardar, se sincroniza
    con is_active (heredado de Django), para que un usuario "inactivo"
    realmente no pueda iniciar sesión.
    """

    id_usuario = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(
        Rol, on_delete=models.PROTECT, related_name="usuarios"
    )
    nombre_completo = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    estado = models.CharField(max_length=20, default="activo")
    fecha_creacion = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.nombre_completo or self.username

    @property
    def es_administrador(self):
        """True si el usuario es superusuario o su rol asignado es 'administrador'."""
        if self.is_superuser:
            return True
        return bool(self.id_rol and self.id_rol.nombre_rol == "administrador")

    def save(self, *args, **kwargs):
        if self.is_superuser and self.id_rol_id is None:
            # createsuperuser no pide id_rol (no está en REQUIRED_FIELDS),
            # pero id_rol ya es obligatorio. Un superusuario es, en la
            # práctica, administrador, así que se le asigna ese rol solo
            # para que el comando estándar de Django siga funcionando.
            self.id_rol = Rol.objects.get_or_create(
                nombre_rol="administrador",
                defaults={
                    "descripcion": "Acceso total al sistema, incluida la gestión de usuarios y roles."
                },
            )[0]

        # "estado" es el campo que el administrador controla desde la UI de
        # Prados Pets; is_active es lo que Django realmente usa para permitir
        # o no el login. Los mantenemos sincronizados en un solo lugar para
        # que no puedan quedar desalineados.
        self.is_active = self.estado == "activo"

        # is_staff es lo que Django Admin exige para entrar (hoy en día,
        # solo Directorio vive ahí). Un usuario con rol "administrador"
        # debe poder verlo todo, igual que un superusuario; cualquier otro
        # rol no necesita acceso al admin. Se recalcula aquí, en un solo
        # lugar, para que no se pueda desalinear sin importar si el cambio
        # viene del alta de usuario, de la edición de rol o del propio
        # Django Admin.
        self.is_staff = self.is_superuser or (
            self.id_rol_id is not None and self.id_rol.nombre_rol == "administrador"
        )

        super().save(*args, **kwargs)
