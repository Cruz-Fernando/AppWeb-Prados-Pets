import django.db.models.deletion
from django.db import migrations, models


def asignar_rol_a_usuarios_sin_rol(apps, schema_editor):
    """
    Antes de exigir id_rol como obligatorio, cualquier Usuario que se haya
    creado sin rol (por ejemplo el primer superusuario, creado con
    createsuperuser antes de que existiera esta restricción) recibe el rol
    'administrador' por defecto. Superusuarios ya tienen acceso total vía
    es_administrador, así que esto solo formaliza el dato.
    """
    Usuario = apps.get_model("usuarios", "Usuario")
    Rol = apps.get_model("usuarios", "Rol")

    sin_rol = Usuario.objects.filter(id_rol__isnull=True)
    if not sin_rol.exists():
        return

    rol_admin, _ = Rol.objects.get_or_create(
        nombre_rol="administrador",
        defaults={
            "descripcion": "Acceso total al sistema, incluida la gestión de usuarios y roles."
        },
    )
    sin_rol.update(id_rol=rol_admin)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0002_seed_roles"),
    ]

    operations = [
        migrations.RunPython(asignar_rol_a_usuarios_sin_rol, noop),
        migrations.AlterField(
            model_name="usuario",
            name="id_rol",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="usuarios",
                to="usuarios.rol",
            ),
        ),
    ]
