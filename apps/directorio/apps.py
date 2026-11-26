from django.apps import AppConfig


class DirectorioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.directorio'

    def ready(self):
        # PB-18: el contador de visitas se actualiza al cambiar una cita
        from . import signals  # noqa: F401
