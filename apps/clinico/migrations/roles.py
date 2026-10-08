from django.db import migrations
 
 
ROLES = [
    ("administrador", "Acceso total al sistema"),
    ("veterinario", "Consulta, hospitalizacion e historia clinica"),
    ("auxiliar", "Apoyo en consulta y hospitalizacion"),
    ("groomer", "Servicio de peluqueria"),
    ("domiciliario", "Entregas y servicios a domicilio"),
]
 
 
def crear_roles(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    for nombre, descripcion in ROLES:
        Rol.objects.get_or_create(
            nombre_rol=nombre,
            defaults={"descripcion": descripcion},
        )
 
 
def eliminar_roles(apps, schema_editor):
    Rol = apps.get_model("usuarios", "Rol")
    nombres = [nombre for nombre, _ in ROLES]
    Rol.objects.filter(nombre_rol__in=nombres).delete()
 
 
class Migration(migrations.Migration):
 
    dependencies = [
        ("usuarios", "0001_initial"),
    ]
 
    operations = [
        migrations.RunPython(crear_roles, eliminar_roles),
    ]