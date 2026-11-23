"""Production settings. Requires real env values (see .env.example)."""

from .base import *  # noqa: F401,F403

DEBUG = False
# SECRET_KEY must come from the environment in production; the base
# default is a dev-only placeholder and must never be used here.
if SECRET_KEY.startswith("django-insecure-"):  # noqa: F405
    raise RuntimeError(
        "SECRET_KEY must be set to a real random value in production."
    )

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"
