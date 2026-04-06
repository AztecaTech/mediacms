import os

FRONTEND_HOST = os.getenv('FRONTEND_HOST', 'http://localhost')
PORTAL_NAME = os.getenv('PORTAL_NAME', 'MediaCMS')
SECRET_KEY = os.getenv('SECRET_KEY', 'ma!s3^b-cw!f#7s6s0m3*jx77a@riw(7701**(r=ww%w!2+yk2')
REDIS_LOCATION = os.getenv('REDIS_LOCATION', 'redis://redis:6379/1')

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv('POSTGRES_NAME', 'mediacms'),
        "HOST": os.getenv('POSTGRES_HOST', 'db'),
        "PORT": os.getenv('POSTGRES_PORT', '5432'),
        "USER": os.getenv('POSTGRES_USER', 'mediacms'),
        "PASSWORD": os.getenv('POSTGRES_PASSWORD', 'mediacms'),
        "OPTIONS": {'pool': True},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_LOCATION,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# CELERY STUFF
BROKER_URL = REDIS_LOCATION
CELERY_RESULT_BACKEND = BROKER_URL

MP4HLS_COMMAND = "/home/mediacms.io/bento4/bin/mp4hls"

DEBUG = os.getenv('DEBUG', 'False') == 'True'

USE_RBAC = True
PORTAL_WORKFLOW = "private"

CAN_ADD_MEDIA = "advancedUser"
CAN_SEE_MEMBERS_PAGE = "admins"

# Use PNG logos (SVG files contain old MediaCMS logo)
PORTAL_LOGO_DARK_SVG = ""
PORTAL_LOGO_LIGHT_SVG = ""


def _env_bool(key, default="False"):
    return os.getenv(key, default).lower() in ("true", "1", "yes", "on")


# SMTP from environment (Dokploy, Railway, etc.). Until EMAIL_HOST is set, Django
# keeps placeholder values from cms/settings.py — panel env vars alone do nothing.
_email_host = (os.getenv("EMAIL_HOST") or os.getenv("SMTP_HOST") or "").strip()
if _email_host:
    EMAIL_HOST = _email_host
    _port = os.getenv("EMAIL_PORT") or os.getenv("SMTP_PORT") or "587"
    EMAIL_PORT = int(_port)
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER") or os.getenv("SMTP_USER") or ""
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD") or os.getenv("SMTP_PASSWORD") or ""
    EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", "True")
    EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", "False")
    DEFAULT_FROM_EMAIL = (
        os.getenv("DEFAULT_FROM_EMAIL")
        or os.getenv("MAIL_FROM")
        or EMAIL_HOST_USER
        or "noreply@localhost"
    )
    SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
    _admin_raw = os.getenv("ADMIN_EMAIL_LIST")
    if _admin_raw and _admin_raw.strip():
        ADMIN_EMAIL_LIST = [x.strip() for x in _admin_raw.split(",") if x.strip()]

_backend = os.getenv("EMAIL_BACKEND")
if _backend:
    EMAIL_BACKEND = _backend
