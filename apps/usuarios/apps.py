from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.usuarios'

    def ready(self):
        # Después de cada migrate: RLS en public y sin permisos para la API de
        # Supabase (ver seguridad_bd.py). sender=self para que corra una sola vez.
        from django.db.models.signals import post_migrate

        from .seguridad_bd import asegurar_tras_migrar
        post_migrate.connect(asegurar_tras_migrar, sender=self)
