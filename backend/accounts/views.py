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

from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditEvent
from audit.services import record_event

from .models import Role
from .permissions import HasRole
from .serializers import UserCreateSerializer, UserSerializer
from .services import (
    LOCKOUT_MESSAGE,
    clear_failed_sign_ins,
    disable_user,
    is_locked_out,
    record_failed_sign_in,
    set_user_role,
)

User = get_user_model()

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
            record_event(
                actor=None, action="auth.sign_in", target_id=identifier,
                outcome=AuditEvent.Outcome.FAILURE,
            )
            return Response(
                {"detail": GENERIC_SIGN_IN_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # D-11: locked-out identifiers are refused before any password check.
        if is_locked_out(identifier):
            record_event(
                actor=None, action="auth.sign_in", target_id=identifier,
                outcome=AuditEvent.Outcome.FAILURE,
            )
            return Response(
                {"detail": LOCKOUT_MESSAGE},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            record_failed_sign_in(identifier)
            record_event(
                actor=None, action="auth.sign_in", target_id=identifier,
                outcome=AuditEvent.Outcome.FAILURE,
            )
            return Response(
                {"detail": GENERIC_SIGN_IN_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )
        clear_failed_sign_ins(identifier)
        login(request, user)
        record_event(actor=user, action="auth.sign_in", target=user)
        return Response(_user_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        logout(request)
        record_event(actor=user, action="auth.sign_out", target=user)
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
        record_event(actor=user, action="auth.password_change", target=user)
        return Response(_user_payload(user))


# --- User-admin API (Spec 002, User Stories 2, 3, 5; FR-004/005/014) --------


class UserListCreateView(generics.ListCreateAPIView):
    """GET /api/users/ — Admin only, paginated. POST /api/users/ — Admin
    creates an account with a role (D-14: must change password at first
    sign-in). Creation is audited (accounts.create)."""

    permission_classes = [IsAuthenticated, HasRole.for_roles(Role.ADMIN)]
    queryset = User.objects.all().order_by("username")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        record_event(
            actor=self.request.user, action="accounts.create", target=user
        )


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET /api/users/{id}/ — Admin, or the user themself.
    PATCH /api/users/{id}/ — Admin only: activate/disable and assign a
    role. Lifecycle guards live in accounts.services (D-15 last-Admin,
    FR-014 self-disable/self-demotion); violations return 400."""

    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_object(self):
        target = super().get_object()
        is_admin = target is not None and self.request.user.groups.filter(
            name=Role.ADMIN.value
        ).exists()
        if self.request.method == "GET":
            if not is_admin and target.pk != self.request.user.pk:
                raise PermissionDenied("You may only view your own record.")
        elif not is_admin:
            raise PermissionDenied("Only an Admin may change accounts.")
        return target

    def partial_update(self, request, *args, **kwargs):
        target = self.get_object()
        try:
            if "role" in request.data:
                set_user_role(
                    actor=request.user, target=target, role=request.data["role"]
                )
                record_event(
                    actor=request.user, action="accounts.role_change", target=target,
                    metadata={"role": target.role},
                )
            if "is_active" in request.data:
                if request.data["is_active"]:
                    target.is_active = True
                    target.save(update_fields=["is_active"])
                else:
                    disable_user(actor=request.user, target=target)
                    record_event(
                        actor=request.user, action="accounts.disable", target=target
                    )
        except DjangoValidationError as exc:
            return Response(
                {"detail": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Remaining fields (name, email) go through the serializer.
        rest = {
            k: v
            for k, v in request.data.items()
            if k in ("first_name", "last_name", "email")
        }
        if rest:
            serializer = self.get_serializer(target, data=rest, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        target.refresh_from_db()
        return Response(UserSerializer(target).data)


class ResetPasswordView(APIView):
    """POST /api/users/{id}/reset-password/ — Admin only. Sets a new
    password and forces a change at first sign-in (D-14). The new
    password is never written to any audit record."""

    permission_classes = [IsAuthenticated, HasRole.for_roles(Role.ADMIN)]

    def post(self, request, pk):
        try:
            target = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        password = request.data.get("password", "")
        try:
            validate_password(password, user=target)
        except DjangoValidationError as exc:
            return Response(
                {"password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target.set_password(password)
        target.must_change_password = True
        target.save(update_fields=["password", "must_change_password"])
        record_event(
            actor=request.user, action="accounts.password_reset", target=target
        )
        return Response(UserSerializer(target).data)
