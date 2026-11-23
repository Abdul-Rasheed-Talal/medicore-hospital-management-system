"""Staff user accounts and roles (M01 — authentication/RBAC foundation).

Roles are the seven staff roles from Master Plan §5 / Spec 001:
Admin, Doctor, Nurse, Receptionist, Lab Technician, Pharmacist, Billing.

A role is stored on the user as a ``role`` field AND as membership of a
Django ``Group`` of the same name (see ``assign_role``). Permission
checks must use Django permissions / group membership (see
``accounts/permissions.py``), never ``if user.role == ...`` in a view —
the field is a convenience label and a single source of truth for which
group a user belongs to; the group is what grants access.
"""

from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    DOCTOR = "doctor", "Doctor"
    NURSE = "nurse", "Nurse"
    RECEPTIONIST = "receptionist", "Receptionist"
    LAB_TECHNICIAN = "lab_technician", "Lab Technician"
    PHARMACIST = "pharmacist", "Pharmacist"
    BILLING = "billing", "Billing"


class User(AbstractUser):
    """Staff user. Distinct from Patient (a person receiving care)."""

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.RECEPTIONIST,
        help_text="Staff role. Mirrored to a Django group of the same name.",
    )

    def assign_role(self, role):
        """Set the user's role and sync their Django group membership.

        A user belongs to exactly one role group. Group membership is what
        permission checks read; this method keeps the field and the group
        in agreement. Call ``seed_roles`` first so the groups exist.
        """
        role = Role(role)
        self.role = role.value
        self.save(update_fields=["role"])
        self.groups.set(Group.objects.filter(name=role.value))
        return self

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
