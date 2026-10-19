from .base import *  # noqa: F403

DEBUG = False

# Hosts and CSRF trusted origins for Vercel
# Read from env if supplied; always ensure .vercel.app is included in production
_env_allowed_hosts = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".vercel.app"])  # noqa: F405
ALLOWED_HOSTS = list(dict.fromkeys(_env_allowed_hosts + [".vercel.app", "127.0.0.1", "localhost"]))

_env_csrf = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_env_csrf + ["https://*.vercel.app"]))

# In serverless reverse-proxy environments (like Vercel), tell Django to trust HTTPS headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Production Database (Supabase PostgreSQL / DATABASE_URL)
DATABASE_URL = env.str("DATABASE_URL", default="").strip()  # noqa: F405
if not DATABASE_URL:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "DATABASE_URL environment variable is required in production (config.settings.prod). "
        "SQLite is not permitted in production serverless environments. "
        "Please configure your Supabase PostgreSQL DATABASE_URL in the Vercel dashboard."
    )

try:
    _parsed_db = env.db_url_config(DATABASE_URL)
except Exception as exc:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        f"Unable to parse DATABASE_URL into a valid Django database configuration: {exc}"
    ) from exc

if not _parsed_db.get("ENGINE"):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "settings.DATABASES is improperly configured. Please supply the ENGINE value. "
        "Ensure DATABASE_URL starts with 'postgresql://' or 'postgres://'."
    )

DATABASES = {"default": _parsed_db}

# Ensure secure SSL connection by default for remote PostgreSQL
db_options = DATABASES["default"].setdefault("OPTIONS", {})
if "sslmode" not in db_options and "postgres" in DATABASES["default"].get("ENGINE", ""):
    db_options["sslmode"] = "require"

# Disable persistent connections in serverless functions unless explicitly configured
# In Vercel serverless functions with Supabase Transaction Pooler (port 6543), CONN_MAX_AGE must be 0
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=0)  # noqa: F405

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
