from django.contrib.auth.hashers import make_password
from django.db import migrations

#CONTRASEÑAS DE EJEMPLO,
# SUGERIR LAS PROPIAS COLOCARLAS EN UN TEXTO PLANO NO VISIBLE PARA PRE ELABORACION
USUARIOS_GLOBALES = [
    ("administrador", "administrador@pradospets.com", "Admin123*", "Administrador General", "administrador", True, True),
    ("veterinario", "veterinario@pradospets.com", "Vet123*", "Veterinario General", "veterinario", False, False),
    ("auxiliar", "auxiliar@pradospets.com", "Auxiliar123*", "Auxiliar General", "auxiliar", False, False),
    ("groomer", "groomer@pradospets.com", "Groomer123*", "Groomer General", "groomer", False, False),
    ("domiciliario", "domiciliario@pradospets.com", "Domicilio123*", "Domiciliario General", "domiciliario", False, False),
]


def seed_usuarios(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    Rol = apps.get_model("usuarios", "Rol")

    for username, email, password, nombre_completo, rol_nombre, is_staff, is_superuser in USUARIOS_GLOBALES:
        rol = Rol.objects.filter(nombre_rol=rol_nombre).first()
        Usuario.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "password": make_password(password),
                "nombre_completo": nombre_completo,
                "id_rol": rol,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
            },
        )


def unseed_usuarios(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    usernames = [u[0] for u in USUARIOS_GLOBALES]
    Usuario.objects.filter(username__in=usernames).delete()


class Migration(migrations.Migration):

    dependencies = [
        # Renumerada de 0003 a 0004: coincidía con nuestra propia
        # 0003_usuario_rol_obligatorio (mismo número, mismo padre
        # 0002_seed_roles), lo que generaba dos nodos hoja en el grafo de
        # migraciones de la app usuarios y hacía fallar `migrate` con
        # "Conflicting migrations detected; multiple leaf nodes".
        # Contenido de la migración sin tocar — solo se corrigió el número
        # y la dependencia para que quede después de la nuestra.
        ("usuarios", "0003_usuario_rol_obligatorio"),
    ]

    operations = [
        migrations.RunPython(seed_usuarios, unseed_usuarios),
    ]
