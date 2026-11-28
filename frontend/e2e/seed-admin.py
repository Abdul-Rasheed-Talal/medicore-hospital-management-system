"""Seed the E2E admin account.

Test-only: runs against the local dev / CI throwaway SQLite database via
``python manage.py shell`` from e2e/global-setup.ts. Idempotent — the
account is created only if it is missing, and its password is always
reset to the E2E password below. The account is an Admin with no forced
password change, so the E2E journey signs straight in.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command

call_command("seed_roles")

User = get_user_model()
username = os.environ.get("E2E_ADMIN_USERNAME", "e2e-admin")
password = os.environ.get("E2E_ADMIN_PASSWORD", "E2EAdminPass123")
user, created = User.objects.get_or_create(
    username=username, defaults={"role": "admin"}
)
user.role = "admin"
user.set_password(password)
user.must_change_password = False
user.is_active = True
user.save()
user.assign_role("admin")
print(f"E2E admin ready: {username} (created={created})")
