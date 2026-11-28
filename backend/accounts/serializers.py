"""Serializers for staff user accounts (Spec 002, User Stories 2 and 3).

The user-admin API is Admin-only except that a user may view their own
record. Passwords are write-only and never appear in any response or
audit metadata.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Role

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read (and limited update) representation of a staff user.

    ``staff_profile`` is the reverse of the staff↔account link (Spec 003
    US2 scenario 4, D-04): the link is visible on both records — the
    staff profile carries the account id, and the account carries the
    profile. Read-only; linking is done from the staff side.
    """

    staff_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
            "must_change_password",
            "staff_profile",
        )
        read_only_fields = ("id", "must_change_password", "staff_profile")

    def get_staff_profile(self, obj):
        # Reverse OneToOne accessor; raises RelatedObjectDoesNotExist
        # (an AttributeError subclass) when no profile is linked, so
        # getattr's default applies.
        profile = getattr(obj, "staff_profile", None)
        if profile is None:
            return None
        return {
            "id": profile.id,
            "staff_id": profile.staff_id,
            "full_name": profile.full_name,
        }


class UserCreateSerializer(serializers.ModelSerializer):
    """Create a staff account. The Admin-chosen role is assigned and the
    account is forced to change its password at first sign-in (D-14)."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "role", "password")

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        role = Role(validated_data.pop("role", Role.RECEPTIONIST))
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password, must_change_password=True, **validated_data
        )
        user.assign_role(role)
        return user
