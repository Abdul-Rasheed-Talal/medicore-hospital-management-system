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
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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

    # Email is unique (Spec 002 D-09: sign-in accepts username OR email,
    # so an email must identify exactly one account) and nullable so
    # accounts without an email do not collide on an empty value.
    email = models.EmailField(blank=True, null=True, unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.RECEPTIONIST,
        help_text="Staff role. Mirrored to a Django group of the same name.",
    )

    must_change_password = models.BooleanField(
        default=False,
        help_text="Spec 002 D-14: set when an Admin creates or resets the "
        "account. The user must change their password at first sign-in; "
        "other endpoints are refused until then.",
    )

    def save(self, *args, **kwargs):
        # Normalise an empty email to NULL so the unique constraint only
        # applies to real addresses.
        if not self.email:
            self.email = None
        super().save(*args, **kwargs)

    def assign_role(self, role):
        """Set the user's role and sync their Django group membership.

        A user belongs to exactly one role group. Group membership is what
        permission checks read; this method keeps the field and the group
        in agreement. Call ``seed_roles`` first so the groups exist.

        Raises ValidationError when demoting the last remaining Admin
        (Spec 002 D-15) — the hospital must never be left with no Admin.
        """
        role = Role(role)
        if (
            self.role == Role.ADMIN
            and role != Role.ADMIN
            and self.pk is not None
            and is_last_admin(self)
        ):
            raise ValidationError(
                "Cannot remove the Admin role from the last Admin account."
            )
        self.role = role.value
        self.save(update_fields=["role"])
        self.groups.set(Group.objects.filter(name=role.value))
        return self

    def deactivate(self):
        """Disable the account (never hard-delete, Spec 002 D-15).

        Raises ValidationError when this is the last remaining Admin.
        Callers that know the acting Admin should use
        ``accounts.services.disable_user`` instead — it also enforces the
        self-disable refusal (FR-014).
        """
        if self.role == Role.ADMIN and is_last_admin(self):
            raise ValidationError("Cannot disable the last Admin account.")
        self.is_active = False
        self.save(update_fields=["is_active"])
        return self

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


def is_last_admin(user):
    """True when ``user`` is the only active Admin account (Spec 002 D-15)."""
    if user.role != Role.ADMIN:
        return False
    return (
        User.objects.filter(role=Role.ADMIN, is_active=True)
        .exclude(pk=user.pk)
        .count()
        == 0
    )


class LoginLockout(models.Model):
    """Brute-force protection state for one sign-in identifier (D-11).

    ``identifier`` is the username or email as typed (lowercased).
    After 5 failed sign-ins the identifier is locked for 15 minutes;
    a successful sign-in deletes the record. The lockout applies to
    unknown identifiers too, so failures never reveal whether an
    account exists.
    """

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15

    identifier = models.CharField(max_length=254, unique=True)
    failed_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_locked(self):
        return self.locked_until is not None and self.locked_until > timezone.now()

    def __str__(self):
        return f"{self.identifier} ({self.failed_attempts} failed)"
