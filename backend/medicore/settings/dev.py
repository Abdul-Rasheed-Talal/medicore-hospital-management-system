"""Development settings. Never use these in a hosted/demo environment."""

from .base import *  # noqa: F401,F403

DEBUG = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
