"""Permissions for hospital setup (Spec 003 FR-009).

Admin manages setup; every other signed-in role is read-only.
Enforced on the backend — frontend hiding alone is insufficient.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.models import Role
from accounts.permissions import user_has_role


class IsAdminOrReadOnly(BasePermission):
    """Safe methods for any signed-in user; mutations for Admin only."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return user_has_role(request.user, Role.ADMIN)
