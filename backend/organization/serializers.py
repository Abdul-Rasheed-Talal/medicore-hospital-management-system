"""Serializers for hospital setup (Spec 003, M2).

Backend validation is authoritative (FR-007): required fields, unique
codes (case-insensitive — codes are stored uppercase), blood group from
the fixed list, department required for clinical roles, and a reason
required whenever a staff status changes.

Staff directory privacy (Spec 003 Permissions table): contact details
(phone, email) and blood group are visible to Admins and to the staff
member themself; other roles see only name, department, job title and
system role. That is enforced in ``StaffProfileSerializer`` — the
representation drops the restricted fields for anyone else.
"""

from rest_framework import serializers

from .models import (
    CLINICAL_ROLES,
    Department,
    Service,
    ServiceCategory,
    StaffProfile,
    StaffStatusChange,
    VisitType,
)


def _created_by_username(obj):
    return obj.created_by.username if obj.created_by_id else None


class DepartmentSerializer(serializers.ModelSerializer):
    """Department (FR-001). Code is normalised to uppercase."""

    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = (
            "id",
            "name",
            "code",
            "description",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_created_by(self, obj):
        return _created_by_username(obj)

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        code = attrs.get("code")
        if code:
            qs = Department.objects.filter(code__iexact=code)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": "A department with this code already exists."}
                )
        return attrs


class ServiceCategorySerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = ("id", "name", "is_active", "created_by", "created_at", "updated_at")
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_created_by(self, obj):
        return _created_by_username(obj)


class VisitTypeSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = VisitType
        fields = ("id", "name", "is_active", "created_by", "created_at", "updated_at")
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_created_by(self, obj):
        return _created_by_username(obj)


class ServiceSerializer(serializers.ModelSerializer):
    """Service catalog entry (FR-004). No price field in v1 (D-10)."""

    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = (
            "id",
            "name",
            "code",
            "category",
            "department",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def get_created_by(self, obj):
        return _created_by_username(obj)

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        code = attrs.get("code")
        if code:
            qs = Service.objects.filter(code__iexact=code)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": "A service with this code already exists."}
                )
        return attrs


class StaffStatusChangeSerializer(serializers.ModelSerializer):
    """One entry of a staff member's status history (FR-011)."""

    actor = serializers.SerializerMethodField()

    class Meta:
        model = StaffStatusChange
        fields = (
            "id",
            "previous_status",
            "new_status",
            "reason",
            "actor",
            "timestamp",
        )

    def get_actor(self, obj):
        return obj.actor.username if obj.actor_id else None


class StaffProfileSerializer(serializers.ModelSerializer):
    """Staff profile (FR-002). ``status_reason`` is write-only and is
    required whenever the status actually changes (User Story 5)."""

    created_by = serializers.SerializerMethodField()
    status_reason = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = StaffProfile
        fields = (
            "id",
            "staff_id",
            "full_name",
            "job_title",
            "department",
            "role",
            "user",
            "phone",
            "email",
            "blood_group",
            "status",
            "status_reason",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "staff_id", "created_by", "created_at", "updated_at")

    def create(self, validated_data):
        # Write-only helper for status changes; not a model field.
        validated_data.pop("status_reason", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("status_reason", None)
        return super().update(instance, validated_data)

    def get_created_by(self, obj):
        return _created_by_username(obj)

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", None))
        department = attrs.get(
            "department", getattr(self.instance, "department", None)
        )
        if role in {r.value for r in CLINICAL_ROLES} and not department:
            raise serializers.ValidationError(
                {"department": "Department is required for clinical roles."}
            )
        new_status = attrs.get("status")
        if new_status is not None:
            old_status = getattr(self.instance, "status", StaffProfile.Status.ACTIVE)
            if new_status != old_status and not (attrs.get("status_reason") or "").strip():
                raise serializers.ValidationError(
                    {"status_reason": "A reason is required when changing staff status."}
                )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_admin = bool(
            user
            and user.is_authenticated
            and user.groups.filter(name="admin").exists()
        )
        is_self = bool(
            user and user.is_authenticated and instance.user_id == user.pk
        )
        if not (is_admin or is_self):
            # Least privilege: other roles see directory fields only.
            for field in ("phone", "email", "blood_group"):
                data.pop(field, None)
        return data
