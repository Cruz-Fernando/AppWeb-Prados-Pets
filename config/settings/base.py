"""
Settings comunes para AppWeb Prados Pets.
Django 6.1 — no incluir aquí nada específico de un solo entorno
(eso va en dev.py o prod.py).
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # BASE_DIR apunta a la raíz del repo (dos niveles arriba de este archivo:
    # config/settings/base.py -> config/ -> raíz)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps propias del proyecto (una por módulo del alcance de E1)
    "apps.directorio",
    "apps.usuarios",
    "apps.agendamiento",
    "apps.clinico",
    "apps.inventario",
    "apps.peluqueria",
    "apps.facturacion",
    "apps.reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # sirve estáticos en producción
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # Exige login en todas las rutas (excepto login, estáticos y admin).
    # Debe ir DESPUÉS de AuthenticationMiddleware.
    "config.middleware.LoginRequeridoMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

from config.db import comprobar_conexion  # noqa: E402

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'postgres'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', '5432'),
        # Rendimiento: las conexiones se reutilizan (ver config/db.py).
        # Con pool, CONN_MAX_AGE debe quedar en 0 (lo exige Django).
        'CONN_MAX_AGE': 0,
        # Los cursores del servidor (que Django usa en .iterator() y en los
        # <select> de formularios) cuestan varias idas y vueltas al pooler;
        # con el volumen de datos de la clínica no aportan nada.
        'DISABLE_SERVER_SIDE_CURSORS': True,
        'OPTIONS': {
            'pool': {
                'min_size': 1,
                # Pocas por proceso: el pooler de Supabase limita las conexiones
                # totales y todo el equipo comparte la misma base.
                'max_size': int(os.environ.get('DB_POOL_MAX', '4')),
                'timeout': 15,          # espera máxima por una conexión libre
                'max_idle': 300,        # cierra las sobrantes tras 5 min sin uso
                'max_lifetime': 1800,   # renueva cada conexión a los 30 min
                'check': comprobar_conexion,
            },
        },
    }
}

# Carga el rol junto con el usuario (una consulta menos en cada página: el menú
# lateral y los permisos siempre consultan el rol).
AUTHENTICATION_BACKENDS = ["apps.usuarios.backends.UsuarioConRolBackend"]

STATIC_URL = 'static/'

# Dónde busca Django los estáticos durante el desarrollo (logos, imágenes, CSS)
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Dónde recojo/copia Django TODOS los estáticos para PRODUCCIÓN cuando ejecutas collectstatic:
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Archivos subidos por los usuarios (consentimientos, exámenes, adjuntos clínicos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "usuarios.Usuario"

LOGIN_URL = "usuarios:login"
LOGIN_REDIRECT_URL = "usuarios:dashboard"
LOGOUT_REDIRECT_URL = "usuarios:login"
