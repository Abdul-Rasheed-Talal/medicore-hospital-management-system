"""Auth & RBAC decision tests (Spec 002, decisions D-09 to D-19).

Written test-first for M1-T03: each test covers one approved decision.
Run with: backend/.venv/bin/python -m pytest accounts/tests/test_auth_decisions.py
"""

import time

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import Client
from django.utils import timezone

from accounts.models import LoginLockout, Role

User = get_user_model()

STRONG_PASSWORD = "Xy9!kLm2QwEr"
OTHER_PASSWORD = "Zz8!pLk3MnVb"


def make_user(username="staff1", password=STRONG_PASSWORD, role="receptionist", **kwargs):
    user = User.objects.create_user(username=username, password=password, role=role, **kwargs)
    # Role assignment syncs Django group membership (the permission
    # mechanism); creating the row alone does not.
    user.assign_role(role)
    return user


@pytest.fixture(autouse=True)
def _seed_role_groups():
    """Groups must exist before assign_role can sync membership."""
    call_command("seed_roles")


def login(client, identifier, password=STRONG_PASSWORD):
    """Log in through the API. ``identifier`` may be a username or an email."""
    return client.post(
        "/api/auth/login/",
        {"username": identifier, "password": password},
        content_type="application/json",
    )


# --- D-09: sign-in accepts username OR email -------------------------------


@pytest.mark.django_db
def test_login_with_username_still_works():
    make_user()
    assert login(Client(), "staff1").status_code == 200


@pytest.mark.django_db
def test_login_with_email_works():
    make_user(email="staff1@hospital.example")
    response = login(Client(), "staff1@hospital.example")
    assert response.status_code == 200
    assert response.json()["username"] == "staff1"


@pytest.mark.django_db
def test_login_with_email_is_case_insensitive():
    make_user(email="staff1@hospital.example")
    assert login(Client(), "STAFF1@Hospital.Example").status_code == 200


@pytest.mark.django_db
def test_login_with_unknown_email_fails_generically():
    make_user()
    response = login(Client(), "nobody@hospital.example", "whatever-password")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid username or password."


@pytest.mark.django_db
def test_login_with_unknown_username_fails_generically():
    response = login(Client(), "ghost", "whatever-password")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid username or password."


@pytest.mark.django_db
def test_disabled_account_sign_in_fails_with_the_same_generic_error():
    """Spec edge case: a disabled sign-in must not reveal the account is disabled."""
    user = make_user()
    user.is_active = False
    user.save()
    response = login(Client(), "staff1")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid username or password."


# --- D-10: 12-hour session + 30-minute idle timeout -------------------------


@pytest.mark.django_db
def test_session_cookie_age_is_twelve_hours():
    assert settings.SESSION_COOKIE_AGE == 12 * 60 * 60


@pytest.mark.django_db
def test_session_idle_timeout_setting_is_thirty_minutes():
    assert settings.SESSION_IDLE_TIMEOUT_SECONDS == 30 * 60


@pytest.mark.django_db
def test_session_survives_activity_inside_idle_window():
    make_user()
    client = Client()
    assert login(client, "staff1").status_code == 200
    assert client.get("/api/auth/session/").status_code == 200
    # Simulate 10 minutes of inactivity: still signed in.
    session = client.session
    session["last_activity"] = time.time() - 10 * 60
    session.save()
    assert client.get("/api/auth/session/").status_code == 200


@pytest.mark.django_db
def test_session_ends_after_thirty_minutes_idle():
    make_user()
    client = Client()
    assert login(client, "staff1").status_code == 200
    session = client.session
    session["last_activity"] = time.time() - 31 * 60
    session.save()
    assert client.get("/api/auth/session/").status_code in (401, 403)
    # The idle session is gone: signing in again is required.
    assert login(client, "staff1").status_code == 200


# --- D-11: brute-force protection -------------------------------------------


@pytest.mark.django_db
def test_five_failed_sign_ins_then_lockout():
    make_user()
    client = Client()
    for _ in range(5):
        response = login(client, "staff1", "wrong-password")
        assert response.status_code == 400
    # Even the correct password is refused while locked out.
    response = login(client, "staff1")
    assert response.status_code == 429
    assert "Too many" in response.json()["detail"]


@pytest.mark.django_db
def test_failed_sign_ins_for_unknown_identifier_also_lock_out():
    client = Client()
    for _ in range(5):
        assert login(client, "ghost", "wrong-password").status_code == 400
    assert login(client, "ghost", "wrong-password").status_code == 429


@pytest.mark.django_db
def test_successful_sign_in_clears_failed_attempts():
    make_user()
    client = Client()
    for _ in range(4):
        login(client, "staff1", "wrong-password")
    assert login(client, "staff1").status_code == 200
    assert LoginLockout.objects.count() == 0
    # Four more failures after the reset must not lock the account yet.
    for _ in range(4):
        login(client, "staff1", "wrong-password")
    assert login(client, "staff1").status_code == 200


@pytest.mark.django_db
def test_lockout_expires_after_fifteen_minutes():
    make_user()
    client = Client()
    for _ in range(5):
        login(client, "staff1", "wrong-password")
    assert login(client, "staff1").status_code == 429
    record = LoginLockout.objects.get()
    record.locked_until = timezone.now() - timezone.timedelta(minutes=1)
    record.save()
    assert login(client, "staff1").status_code == 200


# --- D-12: password policy — Django defaults + minimum length 10 -----------


@pytest.mark.django_db
def test_password_shorter_than_ten_characters_is_rejected():
    user = make_user()
    with pytest.raises(ValidationError):
        validate_password("Short1!x", user=user)


@pytest.mark.django_db
def test_password_of_ten_characters_is_accepted():
    user = make_user()
    validate_password("Xy9!kLm2Qw", user=user)  # 10 chars, no error raised


# --- D-13: role changes take effect immediately ------------------------------


@pytest.mark.django_db
def test_role_change_is_visible_on_the_next_request():
    user = make_user(role="receptionist")
    client = Client()
    assert login(client, "staff1").status_code == 200
    assert client.get("/api/auth/session/").json()["role"] == "receptionist"
    # An Admin changes the role while the user is signed in.
    user.assign_role(Role.ADMIN)
    assert client.get("/api/auth/session/").json()["role"] == "admin"


@pytest.mark.django_db
def test_permission_checks_read_group_membership_from_the_database():
    from rest_framework.test import APIRequestFactory

    from accounts.permissions import HasRole

    user = make_user(role="receptionist")
    factory = APIRequestFactory()
    permission = HasRole.for_roles(Role.ADMIN)()
    request = factory.get("/")
    request.user = User.objects.get(pk=user.pk)
    assert permission.has_permission(request, None) is False
    user.assign_role(Role.ADMIN)
    request.user = User.objects.get(pk=user.pk)
    assert permission.has_permission(request, None) is True


# --- D-14: forced password change --------------------------------------------


@pytest.mark.django_db
def test_login_reports_must_change_password_flag():
    user = make_user()
    user.must_change_password = True
    user.save()
    client = Client()
    response = login(client, "staff1")
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


@pytest.mark.django_db
def test_forced_password_change_blocks_other_endpoints_until_changed():
    user = make_user()
    user.must_change_password = True
    user.save()
    client = Client()
    assert login(client, "staff1").status_code == 200
    # Any non-auth endpoint is refused while the flag is set.
    assert client.get("/api/users/").status_code == 403
    # The change-password endpoint itself stays reachable.
    assert client.get("/api/auth/session/").status_code == 200


@pytest.mark.django_db
def test_change_password_requires_current_password():
    make_user()
    client = Client()
    assert login(client, "staff1").status_code == 200
    response = client.post(
        "/api/auth/change-password/",
        {"current_password": "not-the-password", "new_password": OTHER_PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_change_password_rejects_short_new_password():
    make_user()
    client = Client()
    assert login(client, "staff1").status_code == 200
    response = client.post(
        "/api/auth/change-password/",
        {"current_password": STRONG_PASSWORD, "new_password": "Short1!x"},
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_change_password_clears_the_flag_and_the_new_password_works():
    user = make_user()
    user.must_change_password = True
    user.save()
    client = Client()
    assert login(client, "staff1").status_code == 200
    response = client.post(
        "/api/auth/change-password/",
        {"current_password": STRONG_PASSWORD, "new_password": OTHER_PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
    user.refresh_from_db()
    assert user.must_change_password is False
    # Old password no longer works; new password does.
    assert login(Client(), "staff1", STRONG_PASSWORD).status_code == 400
    assert login(Client(), "staff1", OTHER_PASSWORD).status_code == 200


@pytest.mark.django_db
def test_change_password_requires_authentication():
    response = Client().post(
        "/api/auth/change-password/",
        {"current_password": STRONG_PASSWORD, "new_password": OTHER_PASSWORD},
        content_type="application/json",
    )
    assert response.status_code in (401, 403)


# --- D-15: last-Admin rule ----------------------------------------------------


@pytest.mark.django_db
def test_cannot_disable_the_last_admin():
    from accounts.services import disable_user

    admin = make_user(username="admin1", role="admin")
    with pytest.raises(ValidationError, match="last Admin"):
        disable_user(actor=admin, target=admin)


@pytest.mark.django_db
def test_cannot_demote_the_last_admin():
    from accounts.services import set_user_role

    admin = make_user(username="admin1", role="admin")
    with pytest.raises(ValidationError, match="last Admin"):
        set_user_role(actor=admin, target=admin, role=Role.RECEPTIONIST)


@pytest.mark.django_db
def test_assign_role_refuses_demoting_the_last_admin():
    admin = make_user(username="admin1", role="admin")
    with pytest.raises(ValidationError, match="last Admin"):
        admin.assign_role(Role.DOCTOR)


@pytest.mark.django_db
def test_disabling_one_admin_is_allowed_when_another_remains():
    from accounts.services import disable_user

    admin1 = make_user(username="admin1", role="admin")
    admin2 = make_user(username="admin2", role="admin")
    disable_user(actor=admin1, target=admin2)
    admin2.refresh_from_db()
    assert admin2.is_active is False


@pytest.mark.django_db
def test_self_disable_is_refused_even_with_another_admin_present():
    from accounts.services import disable_user

    admin1 = make_user(username="admin1", role="admin")
    make_user(username="admin2", role="admin")
    with pytest.raises(ValidationError, match="own account"):
        disable_user(actor=admin1, target=admin1)


@pytest.mark.django_db
def test_self_demotion_is_refused_even_with_another_admin_present():
    from accounts.services import set_user_role

    admin1 = make_user(username="admin1", role="admin")
    make_user(username="admin2", role="admin")
    with pytest.raises(ValidationError, match="own Admin role"):
        set_user_role(actor=admin1, target=admin1, role=Role.NURSE)


# --- D-17: one role per user ---------------------------------------------------


@pytest.mark.django_db
def test_assigning_a_new_role_replaces_the_old_group():
    user = make_user(role="receptionist")
    assert Group.objects.filter(name="receptionist", user=user).exists()
    user.assign_role(Role.ADMIN)
    assert user.groups.count() == 1
    assert user.groups.filter(name="admin").exists()
    assert user.role == "admin"


# --- D-18: first-Admin bootstrap command --------------------------------------


@pytest.mark.django_db
def test_create_first_admin_command():
    call_command(
        "create_first_admin",
        username="firstadmin",
        email="admin@hospital.example",
        password=STRONG_PASSWORD,
    )
    admin = User.objects.get(username="firstadmin")
    assert admin.role == "admin"
    assert admin.is_staff is True
    assert admin.is_superuser is False
    assert admin.must_change_password is True
    assert admin.groups.filter(name="admin").exists()
    assert admin.check_password(STRONG_PASSWORD)


@pytest.mark.django_db
def test_create_first_admin_refuses_when_an_admin_already_exists():
    make_user(username="admin1", role="admin")
    with pytest.raises(CommandError, match="already exists"):
        call_command(
            "create_first_admin",
            username="second",
            password=STRONG_PASSWORD,
        )


@pytest.mark.django_db
def test_create_first_admin_rejects_a_short_password():
    with pytest.raises(CommandError):
        call_command(
            "create_first_admin",
            username="firstadmin",
            password="Short1!x",
        )
    assert not User.objects.filter(username="firstadmin").exists()


# --- D-19: concurrent sessions allowed -----------------------------------------


@pytest.mark.django_db
def test_same_user_can_be_signed_in_from_two_clients_at_once():
    make_user()
    first = Client()
    second = Client()
    assert login(first, "staff1").status_code == 200
    assert login(second, "staff1").status_code == 200
    assert first.get("/api/auth/session/").status_code == 200
    assert second.get("/api/auth/session/").status_code == 200
