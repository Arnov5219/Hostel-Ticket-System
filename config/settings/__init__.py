import os

# Default to dev settings if not explicitly specified
settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.dev")
if settings_module == "config.settings":
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"
    from .dev import *  # noqa: F403
