"""Create the first Admin account (Spec 002 D-18).

The deployer runs this once, at deploy time::

    python manage.py create_first_admin --username admin --email admin@hospital.example

The password is prompted securely (never passed on the command line in
normal use) and must satisfy the password policy (D-12: Django defaults
+ minimum length 10). The new Admin must change their password at first
sign-in (D-14). There is no hardcoded or default password anywhere.

Refuses to run when an Admin account already exists — the first Admin
is created exactly once; later Admins are created by an existing Admin.
"""

import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Role


class Command(BaseCommand):
    help = "Create the first Admin account (once, at deploy time)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Admin username.")
        parser.add_argument("--email", default="", help="Admin email (optional).")
        parser.add_argument(
            "--password",
            default=None,
            help="Admin password. Prefer omitting this and typing the "
            "password at the secure prompt instead.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(role=Role.ADMIN).exists():
            raise CommandError(
                "An Admin account already exists. Create further Admins "
                "from an existing Admin account instead."
            )
        username = options["username"]
        email = options["email"] or None
        password = options["password"]
        if password is None:
            password = getpass.getpass("Admin password: ")
            confirm = getpass.getpass("Admin password (again): ")
            if password != confirm:
                raise CommandError("Passwords do not match.")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(
                "Password does not satisfy the password policy: "
                + "; ".join(exc.messages)
            )
        call_command("seed_roles")
        admin = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=Role.ADMIN,
            is_staff=True,
            is_superuser=False,
            must_change_password=True,
        )
        admin.assign_role(Role.ADMIN)
        self.stdout.write(
            self.style.SUCCESS(
                f"Created first Admin '{admin.username}'. They must change "
                "their password at first sign-in."
            )
        )
