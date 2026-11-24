"""Helpers for recording audit events (Spec 002 FR-008 / D-05).

Every event carries actor / action / target / timestamp / outcome, and
``metadata`` holds limited non-sensitive context only — never passwords,
tokens, or national ID numbers.
"""

from .models import AuditEvent


def record_event(*, actor, action, target=None, outcome=AuditEvent.Outcome.SUCCESS,
                 metadata=None, target_type="User", target_id=""):
    """Create one append-only audit event.

    ``target`` may be a model instance (its class name and pk become
    target_type/target_id); otherwise pass ``target_type``/``target_id``
    explicitly — e.g. a failed sign-in, where no account was identified.
    """
    if target is not None:
        target_type = type(target).__name__
        target_id = str(target.pk)
    return AuditEvent.objects.create(
        actor=actor if actor is not None and getattr(actor, "is_authenticated", False) else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        metadata=metadata or {},
    )
