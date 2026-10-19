from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    "http://10.0.2.2:4000",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
    "capacitor://localhost",
    "https://localhost",
]

# In development, use console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

