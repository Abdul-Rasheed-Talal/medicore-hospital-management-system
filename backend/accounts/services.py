"""Account lifecycle rules (Spec 002).

These are the actor-aware guards the API and the Django admin share —
a plain model method cannot know *who* is acting, so the self-disable /
self-demotion refusals (FR-014) live here, next to the last-Admin rule
(D-15). The model-level guards (``User.assign_role`` /
``User.deactivate``) are the backstop for direct model use.
"""

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import LoginLockout, Role, is_last_admin

# --- D-15 / FR-014: account lifecycle guards --------------------------------


def disable_user(*, actor, target):
    """Disable ``target`` (is_active=False). Refuses disabling the last
    remaining Admin (D-15) and self-disable (FR-014). The last-Admin
    check comes first: it is the system invariant, and it also covers
    the case where the last Admin tries to disable themself."""
    if target.role == Role.ADMIN and is_last_admin(target):
        raise ValidationError("Cannot disable the last Admin account.")
    if actor.pk == target.pk:
        raise ValidationError("You cannot disable your own account.")
    target.deactivate()
    return target


def set_user_role(*, actor, target, role):
    """Assign ``role`` to ``target``. Refuses demoting the last remaining
    Admin (D-15) and self-demotion (FR-014); the last-Admin check comes
    first for the same reason as in ``disable_user``."""
    role = Role(role)
    if target.role == Role.ADMIN and role != Role.ADMIN and is_last_admin(target):
        raise ValidationError("Cannot remove the Admin role from the last Admin account.")
    if actor.pk == target.pk and target.role == Role.ADMIN and role != Role.ADMIN:
        raise ValidationError("You cannot remove your own Admin role.")
    target.assign_role(role)
    return target


# --- D-11: brute-force protection -------------------------------------------

LOCKOUT_MESSAGE = "Too many failed sign-in attempts. Try again later."


def _normalise(identifier):
    return (identifier or "").strip().lower()


def is_locked_out(identifier):
    """True while the identifier is inside its 15-minute lockout (D-11)."""
    try:
        record = LoginLockout.objects.get(identifier=_normalise(identifier))
    except LoginLockout.DoesNotExist:
        return False
    return record.is_locked()


def record_failed_sign_in(identifier):
    """Count a failed sign-in. Locks the identifier for 15 minutes on
    the 5th consecutive failure (D-11)."""
    identifier = _normalise(identifier)
    if not identifier:
        return
    record, _ = LoginLockout.objects.get_or_create(identifier=identifier)
    record.failed_attempts += 1
    if record.failed_attempts >= LoginLockout.MAX_FAILED_ATTEMPTS:
        record.locked_until = timezone.now() + timezone.timedelta(
            minutes=LoginLockout.LOCKOUT_MINUTES
        )
    record.save()


def clear_failed_sign_ins(identifier):
    """Forget failures for the identifier after a successful sign-in."""
    LoginLockout.objects.filter(identifier=_normalise(identifier)).delete()
