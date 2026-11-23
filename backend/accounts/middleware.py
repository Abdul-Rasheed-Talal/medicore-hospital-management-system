"""Session middleware for Spec 002 decisions D-10 and D-14.

- ``IdleTimeoutMiddleware`` (D-10): a session ends after 30 minutes
  without a request, even though the session cookie itself lives for
  12 hours (``SESSION_COOKIE_AGE``). Shared ward machines must not
  stay signed in unattended.
- ``ForcePasswordChangeMiddleware`` (D-14): while
  ``user.must_change_password`` is set, only the endpoints needed to
  change the password (or sign out) answer; every other API request
  is refused until the password is changed.
"""

import time

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse

# Paths that stay usable while a password change is forced (D-14).
_PASSWORD_CHANGE_ALLOWLIST = (
    "/api/auth/change-password/",
    "/api/auth/logout/",
    "/api/auth/session/",
    "/api/auth/csrf/",
    "/api/health/",
    "/admin/",
)


class IdleTimeoutMiddleware:
    """End the session after SESSION_IDLE_TIMEOUT_SECONDS of inactivity."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = time.time()
            last_activity = request.session.get("last_activity")
            idle_limit = settings.SESSION_IDLE_TIMEOUT_SECONDS
            if last_activity is not None and now - last_activity > idle_limit:
                logout(request)
            else:
                request.session["last_activity"] = now
        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """Refuse all but the allowlisted endpoints while a password change
    is forced (D-14). Runs after AuthenticationMiddleware, so
    ``request.user`` is the session user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (
            user.is_authenticated
            and getattr(user, "must_change_password", False)
            and not request.path.startswith(_PASSWORD_CHANGE_ALLOWLIST)
        ):
            return JsonResponse(
                {
                    "detail": "You must change your password before continuing.",
                    "code": "password_change_required",
                },
                status=403,
            )
        return self.get_response(request)
