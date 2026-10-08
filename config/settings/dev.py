"""
Settings de desarrollo — PostgreSQL (Supabase).
Las credenciales se cargan desde las variables de entorno en el archivo .env.
Uso del equipo mientras trabajamos en E1.
"""

import os

from .base import *  # noqa: F401,F403

SECRET_KEY = "django-insecure-dev-key-cambiar-en-produccion"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Conexión a la base de datos PostgreSQL compartida (Supabase)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "postgres"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}
