"""
Settings de desarrollo — PostgreSQL (Supabase).
Las credenciales se cargan desde las variables de entorno en el archivo .env
(la conexión, con su pool, se define en base.py).
Uso del equipo mientras trabajamos en E1.
"""

from .base import *  # noqa: F401,F403

SECRET_KEY = "django-insecure-dev-key-cambiar-en-produccion"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Sesiones en caché con respaldo en la base: ahorra una consulta (~170 ms a
# Supabase) en cada petición. Solo en desarrollo: runserver es UN proceso.
# En producción Gunicorn corre varios procesos y cada uno tendría su propia
# caché en memoria (un logout en uno no se vería en otro). Para usarlo allí
# haría falta una caché compartida, como Redis.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
