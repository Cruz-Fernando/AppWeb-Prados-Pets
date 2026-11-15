from django.apps import AppConfig


class PeluqueriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.peluqueria'

    def ready(self):
        # PB-17: al cancelar una cita, sus insumos vuelven al inventario
        from . import signals  # noqa: F401