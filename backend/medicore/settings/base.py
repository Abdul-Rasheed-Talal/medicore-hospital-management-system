"""Base Django settings for MediCore.

Environment-driven: secrets and deployment values come from the
environment (see .env.example at the repository root). Never hard-code
a real SECRET_KEY or database password here.

Settings are split: base.py (shared) + dev.py / prod.py (per
environment). Select with DJANGO_SETTINGS_MODULE, e.g.
``medicore.settings.dev`` (the default in manage.py).
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


# --- Core -----------------------------------------------------------------

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-only-change-me-in-production"
)
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Hospital display timezone (ADR-001 decided): Asia/Karachi.
# Timestamps are stored in UTC and displayed in this timezone.
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Karachi")
USE_TZ = True
LANGUAGE_CODE = "en-us"
USE_I18N = True

# --- Applications ----------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "medicore",
    "accounts",
    "organization",
    "patients",
    "audit",
    "reporting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "medicore.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "medicore.wsgi.application"
ASGI_APPLICATION = "medicore.asgi.application"

# --- Database --------------------------------------------------------------
# PostgreSQL via DATABASE_URL (Constitution Principle IV requires
# PostgreSQL as the primary database). SQLite is the local-dev fallback
# only, so the scaffold runs without a Postgres server.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# --- Auth ------------------------------------------------------------------
# Custom user with a role field. Roles are realised as Django groups
# (see accounts app / `seed_roles` command); permission checks use
# Django permissions and group membership, never hard-coded role checks
# in views. See accounts/permissions.py.
AUTH_USER_MODEL = "accounts.User"

# Django session auth (spec D-09 / ADR-001): secure HttpOnly cookie,
# CSRF protection, server-side revocation. No JWT in v1.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False  # overridden to True in prod.py
SESSION_COOKIE_AGE = 8 * 60 * 60  # 8 hours — one staff shift
CSRF_COOKIE_HTTPONLY = False  # the JS client must read it to send X-CSRFToken
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = False  # overridden to True in prod.py
CSRF_TRUSTED_ORIGINS = _env_list(
    "CSRF_TRUSTED_ORIGINS", os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
)

# --- Password validation ----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# --- Static files ------------------------------------------------------------
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---------------------------------------------------
# Deny by default: every API endpoint requires an authenticated session
# unless its view explicitly overrides the permission class.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
