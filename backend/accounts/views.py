"""Session-auth endpoints for the staff web app (spec D-09 / ADR-001).

Django session authentication: secure HttpOnly cookie, CSRF protection,
server-side revocation. No JWT in v1.

- GET  /api/auth/csrf/              — sets the CSRF cookie the frontend must send back
- POST /api/auth/login/             — username OR email + password, creates a session
- POST /api/auth/logout/            — destroys the session
- GET  /api/auth/session/           — current user, or 403 when not signed in
- POST /api/auth/change-password/   — signed-in user changes own password

Decisions implemented here: D-09 (username or email sign-in), D-11
(5 failed sign-ins, then a 15-minute lockout), D-14 (forced password
change at first sign-in). Failed sign-ins always return the same
generic error — a disabled account fails exactly like a wrong password,
so the response never reveals whether an account exists or is disabled.
"""

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    LOCKOUT_MESSAGE,
    clear_failed_sign_ins,
    is_locked_out,
    record_failed_sign_in,
)

GENERIC_SIGN_IN_ERROR = "Invalid username or password."


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "must_change_password": user.must_change_password,
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Set the CSRF cookie. The frontend calls this before login."""

    permission_classes = [AllowAny]

    def get(self, request):
        get_token(request)  # ensures the cookie is set
        return Response({"detail": "CSRF cookie set."})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # D-09: the identifier may be a username or an email address.
        # ``username`` is kept for the existing frontend; ``identifier``
        # is the preferred field name going forward.
        identifier = (
            request.data.get("identifier") or request.data.get("username") or ""
        )
        password = request.data.get("password", "")
        if not identifier or not password:
            return Response(
                {"detail": GENERIC_SIGN_IN_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # D-11: locked-out identifiers are refused before any password check.
        if is_locked_out(identifier):
            return Response(
                {"detail": LOCKOUT_MESSAGE},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            record_failed_sign_in(identifier)
            return Response(
                {"detail": GENERIC_SIGN_IN_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )
        clear_failed_sign_ins(identifier)
        login(request, user)
        return Response(_user_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Signed out."})


class SessionView(APIView):
    """Who is signed in right now. 403 when anonymous (deny by default)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))


class ChangePasswordView(APIView):
    """Change the signed-in user's own password (D-14, FR-009).

    Requires the current password. The new password must satisfy the
    password policy (D-12: Django defaults + minimum length 10).
    A successful change clears ``must_change_password`` and keeps the
    current session alive.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password", "")
        new_password = request.data.get("new_password", "")
        if not user.check_password(current_password):
            return Response(
                {"detail": "Your current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        update_session_auth_hash(request, user)
        return Response(_user_payload(user))
