"""Shared audit events (Master Plan §12, Spec 001 FR-012, data-model.md).

One row per significant action: who did what, when, to which record,
and whether it succeeded. Audit records MUST NOT contain passwords,
tokens, full clinical content, or sensitive identifiers such as a
patient's full CNIC / B-Form number — ``metadata`` holds limited,
non-sensitive context only.
"""

import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """A single auditable action. Append-only; never edited in place."""

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        help_text="Staff user who performed the action (null for system/anonymous).",
    )
    action = models.CharField(
        max_length=100,
        help_text="Dotted action name, e.g. patient.create, patient.correct, duplicate.review.",
    )
    target_type = models.CharField(
        max_length=100,
        help_text="Model name of the record acted on, e.g. Patient.",
    )
    target_id = models.CharField(
        max_length=100,
        help_text="Identifier of the target record (UUID or MRN — never a CNIC).",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    outcome = models.CharField(
        max_length=10, choices=Outcome.choices, default=Outcome.SUCCESS
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Limited non-sensitive context only. No passwords, tokens, "
        "clinical content, or national ID numbers.",
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.actor} {self.action} {self.target_type}:{self.target_id} ({self.outcome})"
