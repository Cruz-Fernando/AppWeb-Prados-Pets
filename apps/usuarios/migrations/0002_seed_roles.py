from django.db import migrations

ROLES = [
    ("administrador", "Acceso total al sistema, incluida la gestión de usuarios y roles."),
    ("veterinario", "Atiende consultas médicas y hospitalizaciones."),
    ("auxiliar", "Apoya en la atención al cliente y el registro de hospitalización."),
    ("groomer", "Presta el servicio de peluquería y estética."),
    ("domiciliario", "Realiza las recogidas y entregas a domicilio."),
]


def seed_roles(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    for nombre, descripcion in ROLES:
        Rol.objects.get_or_create(nombre_rol=nombre, defaults={"descripcion": descripcion})


def unseed_roles(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    Rol.objects.filter(nombre_rol__in=[nombre for nombre, _ in ROLES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
