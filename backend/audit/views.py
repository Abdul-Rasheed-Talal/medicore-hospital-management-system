"""Audit trail listing (Spec 002, User Story 5; FR-008).

GET /api/audit/events/ — Admin only, paginated, newest first.
Filters: ?actor=<username or id>&action=<dotted name>&date=<YYYY-MM-DD>.
Audit records are append-only and never edited in place.
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from accounts.models import Role
from accounts.permissions import HasRole

from .models import AuditEvent

User = get_user_model()


class AuditEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "actor",
            "action",
            "target_type",
            "target_id",
            "timestamp",
            "outcome",
            "metadata",
        )

    def get_actor(self, obj):
        return obj.actor.username if obj.actor_id else None


class AuditEventListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, HasRole.for_roles(Role.ADMIN)]
    serializer_class = AuditEventSerializer
    queryset = AuditEvent.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        actor = self.request.query_params.get("actor")
        if actor:
            if actor.isdigit():
                qs = qs.filter(actor__pk=actor)
            else:
                qs = qs.filter(actor__username=actor)
        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(timestamp__date=date)
        return qs
