"""Hospital setup API (Spec 003, M2).

- GET  /api/departments/ /api/staff/ /api/services/
     /api/service-categories/ /api/visit-types/ — any signed-in role
- POST / PATCH / DELETE on those — Admin only (FR-009), enforced here.
- ?is_active=true filters selection lists to active records; deactivated
  records stay linked from existing records (FR-005).
- ?available=true on /api/staff/ lists Active staff only — the provider
  list appointments use (FR-013).
- Deleting a referenced record is refused with an understandable error
  and audited as a failure (FR-005, FR-008); an unused record may be
  deleted (FR-006). Staff profiles are never hard-deleted (FR-011).
- Every mutation is audited with actor / action / target / outcome.
"""

from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.response import Response

from audit.models import AuditEvent
from audit.services import record_event

from .models import (
    Department,
    Service,
    ServiceCategory,
    StaffProfile,
    StaffStatusChange,
    VisitType,
)
from .permissions import IsAdminOrReadOnly
from .serializers import (
    DepartmentSerializer,
    ServiceCategorySerializer,
    ServiceSerializer,
    StaffProfileSerializer,
    StaffStatusChangeSerializer,
    VisitTypeSerializer,
)


class _OrganizationViewSet(viewsets.ModelViewSet):
    """Shared behaviour for Admin-managed reference data."""

    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = "organization.reference"  # overridden per viewset

    def get_queryset(self):
        qs = super().get_queryset()
        flag = self.request.query_params.get("is_active")
        if flag in ("true", "false"):
            qs = qs.filter(is_active=(flag == "true"))
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        record_event(
            actor=self.request.user,
            action=f"{self.audit_prefix}.create",
            target=obj,
        )

    def perform_update(self, serializer):
        was_active = serializer.instance.is_active
        obj = serializer.save()
        if was_active and not obj.is_active:
            action = f"{self.audit_prefix}.deactivate"
        elif not was_active and obj.is_active:
            action = f"{self.audit_prefix}.reactivate"
        else:
            action = f"{self.audit_prefix}.update"
        record_event(actor=self.request.user, action=action, target=obj)

    def referenced_by(self, obj):
        """Human-readable reason the record cannot be deleted, or None."""
        return None

    def perform_destroy(self, instance):
        reason = self.referenced_by(instance)
        if reason is not None:
            record_event(
                actor=self.request.user,
                action=f"{self.audit_prefix}.delete_refused",
                target=instance,
                outcome=AuditEvent.Outcome.FAILURE,
                metadata={"reason": reason},
            )
            raise DRFValidationError({"detail": reason})
        record_event(
            actor=self.request.user,
            action=f"{self.audit_prefix}.delete",
            target=instance,
        )
        try:
            instance.delete()
        except ProtectedError:
            # Backstop for a reference the view check missed.
            reason = (
                "This record is still used by other records. "
                "Deactivate it instead of deleting it."
            )
            record_event(
                actor=self.request.user,
                action=f"{self.audit_prefix}.delete_refused",
                target=instance,
                outcome=AuditEvent.Outcome.FAILURE,
                metadata={"reason": reason},
            )
            raise DRFValidationError({"detail": reason})


class DepartmentViewSet(_OrganizationViewSet):
    """Departments (User Story 1, FR-001)."""

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    audit_prefix = "organization.department"

    def referenced_by(self, obj):
        staff_count = StaffProfile.objects.filter(department=obj).count()
        service_count = Service.objects.filter(department=obj).count()
        if staff_count or service_count:
            parts = []
            if staff_count:
                parts.append(f"{staff_count} staff profile(s)")
            if service_count:
                parts.append(f"{service_count} service(s)")
            return (
                "Cannot delete this department: it is still linked to "
                + " and ".join(parts)
                + ". Deactivate it instead — existing records keep their link."
            )
        return None

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK and not response.data.get(
            "is_active", True
        ):
            dept = self.get_object()
            active_staff = StaffProfile.objects.filter(
                department=dept, status=StaffProfile.Status.ACTIVE
            ).count()
            if active_staff:
                # D-13: deactivation is allowed with a warning; staff keep
                # their department link.
                response.data["warning"] = (
                    f"This department still has {active_staff} active staff "
                    "member(s). They keep their department link; the "
                    "department is only hidden from new selections."
                )
        return response


class ServiceCategoryViewSet(_OrganizationViewSet):
    """Service categories (User Story 3, FR-004)."""

    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    audit_prefix = "organization.service_category"

    def referenced_by(self, obj):
        count = Service.objects.filter(category=obj).count()
        if count:
            return (
                f"Cannot delete this category: {count} service(s) still use it. "
                "Deactivate it instead — existing records keep their link."
            )
        return None


class VisitTypeViewSet(_OrganizationViewSet):
    """Visit types (User Story 3, FR-004). No records reference them yet —
    appointments (M4) will; the refusal hook stays for then."""

    queryset = VisitType.objects.all()
    serializer_class = VisitTypeSerializer
    audit_prefix = "organization.visit_type"


class ServiceViewSet(_OrganizationViewSet):
    """Service catalog (User Story 3, FR-004)."""

    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    audit_prefix = "organization.service"


class StaffViewSet(_OrganizationViewSet):
    """Staff profiles (User Stories 2 and 5, FR-002, FR-011, FR-013)."""

    queryset = StaffProfile.objects.select_related("department", "user").all()
    serializer_class = StaffProfileSerializer
    audit_prefix = "organization.staff"

    def get_queryset(self):
        qs = super().get_queryset()
        available = self.request.query_params.get("available")
        if available == "true":
            qs = qs.filter(status=StaffProfile.Status.ACTIVE)
        wanted = self.request.query_params.get("status")
        if wanted in (StaffProfile.Status.ACTIVE, StaffProfile.Status.INACTIVE):
            qs = qs.filter(status=wanted)
        return qs

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        reason = (self.request.data.get("status_reason") or "").strip()
        obj = serializer.save()
        if obj.status != old_status:
            StaffStatusChange.objects.create(
                staff=obj,
                previous_status=old_status,
                new_status=obj.status,
                reason=reason,
                actor=self.request.user,
            )
            record_event(
                actor=self.request.user,
                action="organization.staff.status_change",
                target=obj,
                metadata={"from": old_status, "to": obj.status},
            )
        else:
            record_event(
                actor=self.request.user,
                action="organization.staff.update",
                target=obj,
            )

    def perform_destroy(self, instance):
        # FR-011: staff profiles are never hard-deleted. The controlled
        # alternative is a status change to Inactive, with a reason.
        reason = (
            "Staff profiles are never deleted, so past work keeps its author. "
            "Change the status to Inactive with a reason instead."
        )
        record_event(
            actor=self.request.user,
            action="organization.staff.delete_refused",
            target=instance,
            outcome=AuditEvent.Outcome.FAILURE,
            metadata={"reason": reason},
        )
        raise DRFValidationError({"detail": reason})

    @action(detail=True, methods=["get"], url_path="status-history")
    def status_history(self, request, pk=None):
        """Chronological status history (User Story 5). Admin, or the
        staff member themself; nobody else."""
        staff = self.get_object()
        is_admin = request.user.groups.filter(name="admin").exists()
        if not is_admin and staff.user_id != request.user.pk:
            raise PermissionDenied("You may only view your own status history.")
        changes = staff.status_history.all()
        page = self.paginate_queryset(changes)
        serializer = StaffStatusChangeSerializer(page or changes, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
