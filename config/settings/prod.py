from .base import *  # noqa: F403

DEBUG = False

# Allow hosts - include .vercel.app by default for Vercel preview/production deployments
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".vercel.app"])  # noqa: F405
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# In serverless reverse-proxy environments (like Vercel), tell Django to trust HTTPS headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Database support for PostgreSQL or DATABASE_URL
DATABASE_URL = env.str("DATABASE_URL", default="")  # noqa: F405
if DATABASE_URL:
    DATABASES = {"default": env.db_url("DATABASE_URL")}  # noqa: F405

# Static & Media files storage handling
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

DEFAULT_FILE_STORAGE = env.str(
    "DEFAULT_FILE_STORAGE",
    default="django.core.files.storage.FileSystemStorage",
)  # noqa: F405

# Custom WhiteNoise storage that tolerates optional missing vendor map files
from whitenoise.storage import CompressedManifestStaticFilesStorage


class NonStrictCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content=content, filename=filename)
        except ValueError:
            return name


STORAGES = {
    "default": {
        "BACKEND": DEFAULT_FILE_STORAGE,
    },
    "staticfiles": {
        "BACKEND": "config.settings.prod.NonStrictCompressedManifestStaticFilesStorage",
    },
}

# Production Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)  # noqa: F405
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)  # noqa: F405

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)  # noqa: F405
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
