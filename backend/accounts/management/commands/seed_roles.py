"""Create one Django group per staff role (idempotent).

Roles are realised as groups so permission checks read group
membership (see accounts/permissions.py). Run after migrations::

    python manage.py seed_roles

Per-app model permissions (e.g. patients add/change/view) are granted
by each feature's own migration/command once that app has models —
this command only guarantees the groups exist.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.models import Role


class Command(BaseCommand):
    help = "Create one Django group per staff role (idempotent)."

    def handle(self, *args, **options):
        for role in Role:
            group, created = Group.objects.get_or_create(name=role.value)
            self.stdout.write(
                self.style.SUCCESS(f"{'Created' if created else 'Exists'}: {group.name}")
            )
