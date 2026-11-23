"""Session-auth endpoints for the staff web app (spec D-09 / ADR-001).

Django session authentication: secure HttpOnly cookie, CSRF protection,
server-side revocation. No JWT in v1.

- GET  /api/auth/csrf/     — sets the CSRF cookie the frontend must send back
- POST /api/auth/login/    — username + password, creates a session
- POST /api/auth/logout/   — destroys the session
- GET  /api/auth/session/  — current user, or 403 when not signed in
"""

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
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
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_active:
            return Response(
                {"detail": "This account is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
