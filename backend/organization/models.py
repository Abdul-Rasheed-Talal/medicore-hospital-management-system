"""Hospital setup reference data (Spec 003, M2).

Departments, staff profiles, service catalog, service categories and
visit types — the controlled reference data appointments, encounters
and later modules link to. Business rules live here, not in views:

- Department / service codes are short uppercase codes chosen by the
  Admin, unique (D-15). Stored uppercased.
- Staff identifier is auto-generated STF-YYYY-NNNN (D-08), mirroring
  the MRN format from Spec 001.
- Department is required for clinical roles (Doctor, Nurse, Lab
  Technician) and optional for others (D-05).
- Staff profiles are never hard-deleted (FR-011); status changes carry
  a reason and are kept as history (User Story 5).
- Reference records used by other records cannot be deleted; they are
  deactivated instead (D-02, FR-005). Unused records may be deleted
  (FR-006). Deleting is refused in the view, which also audits it.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import Role


class BloodGroup(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"


CLINICAL_ROLES = {Role.DOCTOR, Role.NURSE, Role.LAB_TECHNICIAN}


class _ReferenceData(models.Model):
    """Shared fields for Admin-managed reference records."""

    is_active = models.BooleanField(
        default=True,
        help_text="Inactive records are hidden from selection lists for "
        "new records; existing links are preserved.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        help_text="Admin who created the record.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Department(_ReferenceData):
    """A hospital organisational unit (Spec 003 FR-001)."""

    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short uppercase code chosen by the Admin (D-15), e.g. OPD, LAB.",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        if self.code:
            self.code = self.code.strip().upper()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.name}"


class ServiceCategory(_ReferenceData):
    """A grouping for services, e.g. Consultation, Laboratory, Imaging."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "service categories"

    def __str__(self):
        return self.name


class VisitType(_ReferenceData):
    """A kind of appointment visit, e.g. first visit, follow-up."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Service(_ReferenceData):
    """An item in the service catalog (Spec 003 FR-004). No price in v1 (D-10)."""

    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short uppercase code chosen by the Admin, e.g. CONS-GEN.",
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="services",
        help_text="Deleting a category with services is refused (FR-005).",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="services",
        help_text="Optional link to the department that provides the service.",
    )

    class Meta:
        ordering = ["name"]

    def clean(self):
        if self.code:
            self.code = self.code.strip().upper()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.name}"


class StaffProfile(_ReferenceData):
    """A staff member's work identity (Spec 003 FR-002).

    Distinct from the user account (Spec 002): the profile is the work
    identity, the account is the sign-in identity; the two are linked at
    most one-to-one (D-04). A profile may exist with no linked account
    (D-12) — that person simply cannot sign in until one is linked.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    staff_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        help_text="Auto-generated STF-YYYY-NNNN (D-08).",
    )
    full_name = models.CharField(max_length=150)
    job_title = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="staff",
        help_text="Required for clinical roles (D-05); optional otherwise.",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        help_text="System role (one of the Spec 002 roles).",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profile",
        help_text="Linked sign-in account, if any (D-04, D-12).",
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroup.choices,
        blank=True,
        null=True,
        help_text="Optional for all staff (Spec 001 D-13).",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Active / Inactive only in v1 (D-09).",
    )

    class Meta:
        ordering = ["full_name"]

    def clean(self):
        if self.role in {r.value for r in CLINICAL_ROLES} and not self.department_id:
            raise ValidationError(
                {"department": "Department is required for clinical roles."}
            )

    def _next_staff_id(self):
        """Next free STF-YYYY-NNNN for the current year (D-08)."""
        year = timezone.now().year
        prefix = f"STF-{year}-"
        taken = StaffProfile.objects.filter(staff_id__startswith=prefix).values_list(
            "staff_id", flat=True
        )
        highest = 0
        for value in taken:
            try:
                highest = max(highest, int(value.rsplit("-", 1)[1]))
            except (IndexError, ValueError):
                continue
        return f"{prefix}{highest + 1:04d}"

    def save(self, *args, **kwargs):
        if not self.staff_id:
            self.staff_id = self._next_staff_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff_id} — {self.full_name}"


class StaffStatusChange(models.Model):
    """One staff status change, with reason and actor (Spec 003 FR-011).

    Staff history survives departure: the profile is never deleted, and
    every status change is kept in chronological order (User Story 5).
    """

    staff = models.ForeignKey(
        StaffProfile, on_delete=models.CASCADE, related_name="status_history"
    )
    previous_status = models.CharField(max_length=10, choices=StaffProfile.Status.choices)
    new_status = models.CharField(max_length=10, choices=StaffProfile.Status.choices)
    reason = models.TextField(help_text="Why the status changed (required).")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_status_changes",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return (
            f"{self.staff} {self.previous_status} → {self.new_status} "
            f"({self.timestamp:%Y-%m-%d})"
        )
