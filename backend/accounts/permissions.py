"""DRF permission helpers for role-based access control.

Rules (Constitution Principle III, Master Plan §5):
- Authorization is enforced on the backend; frontend restrictions alone
  are insufficient.
- Checks read Django group membership, not the ``User.role`` field
  directly — groups are the permission mechanism, the field is a label.
- Deny by default: no role listed means no access.
"""

from rest_framework.permissions import BasePermission


def user_has_role(user, *roles):
    """True if the authenticated user belongs to any of the given role groups."""
    if not user or not user.is_authenticated:
        return False
    role_names = {role.value if hasattr(role, "value") else str(role) for role in roles}
    return user.groups.filter(name__in=role_names).exists()


class HasRole(BasePermission):
    """Allow only users in one of the listed role groups.

    Usage: ``permission_classes = [IsAuthenticated, HasRole.for_roles(Role.ADMIN)]``
    """

    roles = ()

    @classmethod
    def for_roles(cls, *roles):
        return type(f"HasRole_{'_'.join(r.value for r in roles)}", (cls,), {"roles": roles})

    def has_permission(self, request, view):
        return user_has_role(request.user, *self.roles)
