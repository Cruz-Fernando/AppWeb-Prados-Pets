"""
=============================================================================
AVISO IMPORTANTE DE SEGURIDAD — USO EXCLUSIVO EN DESARROLLO Y PRUEBAS
=============================================================================
Este comando crea o actualiza las cuentas de prueba para cada uno de los roles
del sistema con contraseñas conocidas en texto plano para facilitar el testeo
local del equipo durante el sprint.

ADVERTENCIA:
- NO UTILIZAR EN PRODUCCIÓN.
- Las contraseñas aquí descritas son débiles y públicas a nivel de código fuente.
- En producción, las cuentas reales deben crearse con contraseñas robustas y
  procedimientos seguros de entrega de credenciales.
=============================================================================
"""

from django.core.management.base import BaseCommand
from apps.usuarios.models import Usuario, Rol


class Command(BaseCommand):
    help = "Crea o restablece las cuentas de prueba para cada rol del sistema con fines de desarrollo."

    # Definición de credenciales de prueba por rol
    # NOTA: Estas cuentas son para desarrollo y pruebas del equipo.
    CUENTAS_PRUEBA = [
        {
            "username": "administrador",
            "password": "Admin123*",
            "email": "administrador@pradospets.com",
            "nombre_completo": "Administrador General",
            "rol": "administrador",
            "is_staff": True,
            "is_superuser": True,
            "telefono": "3001112233",
        },
        {
            "username": "veterinario",
            "password": "Vet123*",
            "email": "veterinario@pradospets.com",
            "nombre_completo": "Dr. Veterinario Pruebas",
            "rol": "veterinario",
            "is_staff": False,
            "is_superuser": False,
            "telefono": "3002223344",
        },
        {
            "username": "auxiliar",
            "password": "Auxiliar123*",
            "email": "auxiliar@pradospets.com",
            "nombre_completo": "Auxiliar Veterinario Pruebas",
            "rol": "auxiliar",
            "is_staff": False,
            "is_superuser": False,
            "telefono": "3003334455",
        },
        {
            "username": "groomer",
            "password": "Groomer123*",
            "email": "groomer@pradospets.com",
            "nombre_completo": "Groomer / Estilista Canino",
            "rol": "groomer",
            "is_staff": False,
            "is_superuser": False,
            "telefono": "3004445566",
        },
        {
            "username": "domiciliario",
            "password": "Domicilio123*",
            "email": "domiciliario@pradospets.com",
            "nombre_completo": "Repartidor / Domiciliario",
            "rol": "domiciliario",
            "is_staff": False,
            "is_superuser": False,
            "telefono": "3005556677",
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "\n[AVISO]: Creando / actualizando usuarios de prueba para desarrollo local."
        ))

        for datos in self.CUENTAS_PRUEBA:
            rol, _ = Rol.objects.get_or_create(
                nombre_rol=datos["rol"],
                defaults={"descripcion": f"Rol de {datos['rol']} del sistema"}
            )

            usuario, creado = Usuario.objects.get_or_create(
                username=datos["username"],
                defaults={
                    "email": datos["email"],
                    "nombre_completo": datos["nombre_completo"],
                    "id_rol": rol,
                    "is_staff": datos["is_staff"],
                    "is_superuser": datos["is_superuser"],
                    "estado": "activo",
                    "telefono": datos["telefono"],
                }
            )

            # Restablecer contraseña y asegurar rol y estado activo
            usuario.set_password(datos["password"])
            usuario.id_rol = rol
            usuario.nombre_completo = datos["nombre_completo"]
            usuario.estado = "activo"
            usuario.is_staff = datos["is_staff"]
            usuario.is_superuser = datos["is_superuser"]
            usuario.save()

            accion = "Creado" if creado else "Actualizado"
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ [{accion}] Rol: {rol.nombre_rol:<13} | Usuario: {usuario.username:<14} | Clave: {datos['password']}"
            ))

        self.stdout.write(self.style.SUCCESS(
            "\n✓ Todos los usuarios de prueba han sido sincronizados en la base de datos de Supabase.\n"
        ))
