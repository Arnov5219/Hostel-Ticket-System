import os

default_target = "config.settings.prod" if os.environ.get("VERCEL") else "config.settings.dev"
settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", default_target)
if settings_module in ("config.settings", "config.settings.dev") and os.environ.get("VERCEL"):
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
    from .prod import *  # noqa: F403
elif settings_module == "config.settings":
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"
    from .dev import *  # noqa: F403
