from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# In development, use console email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
