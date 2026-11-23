"""Authentication backends (Spec 002 D-09).

Sign-in accepts a username OR an email address. Django's default
backend only matches usernames, so this backend resolves an identifier
containing "@" against the (unique) email field first. An ambiguous or
unknown email fails exactly like an unknown username — the caller gets
the same generic error either way.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate with a username or an email address (D-09)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("identifier") or kwargs.get("email")
        if not identifier or not password:
            return None
        User = get_user_model()
        if "@" in identifier:
            try:
                user = User.objects.get(email__iexact=identifier.strip())
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None
        else:
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
