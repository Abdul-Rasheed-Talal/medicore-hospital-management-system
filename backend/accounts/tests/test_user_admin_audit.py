"""User-admin API + auth audit events (Spec 002, FR-004/005/008/009/014).

Written test-first for the next M1 task after M1-T03: the user-admin API
(create users, assign roles, Admin password reset) plus recording the
auth audit events. Each test covers one Spec 002 acceptance scenario
(spec.md User Stories 2, 3, 5; plan.md API table) and must FAIL before
implementation — the endpoints do not exist yet and no audit events are
recorded yet.

Run with: backend/.venv/bin/python -m pytest accounts/tests/test_user_admin_audit.py
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client

from accounts.models import Role
from audit.models import AuditEvent

User = get_user_model()

STRONG_PASSWORD = "CorrectHorseBatteryStaple1"  # noqa: S105 - test fixture only
OTHER_PASSWORD = "Tr0ub4dorAndHorseBattery"  # noqa: S105 - test fixture only


def make_user(username="staff1", password=STRONG_PASSWORD, role="receptionist", **kwargs):
    user = User.objects.create_user(username=username, password=password, role=role, **kwargs)
    user.assign_role(role)
    return user


@pytest.fixture(autouse=True)
def _seed_role_groups():
    """Groups must exist before assign_role can sync membership."""
    call_command("seed_roles")


def admin_client():
    """A signed-in Admin client (via the API login, so session/CSRF behave as in prod)."""
    admin = make_user(username="admin1", role="admin")
    client = Client()
    resp = client.post(
        "/api/auth/login/",
        {"username": "admin1", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert resp.status_code == 200
    return client, admin


def audit_actions(action=None):
    qs = AuditEvent.objects.all()
    if action:
        qs = qs.filter(action=action)
    return list(qs.values_list("action", "actor__username", "target_type", "outcome"))


# --- User Story 2: Admin creates an account and assigns a role -------------


@pytest.mark.django_db
def test_admin_creates_account_with_role_and_audit_event():
    client, _admin = admin_client()
    resp = client.post(
        "/api/users/",
        {
            "username": "nurse1",
            "first_name": "Nadia",
            "last_name": "Nurse",
            "password": STRONG_PASSWORD,
            "role": "nurse",
        },
        content_type="application/json",
    )
    assert resp.status_code == 201
    user = User.objects.get(username="nurse1")
    assert user.role == Role.NURSE
    assert user.is_active is True
    assert user.must_change_password is True
    assert AuditEvent.objects.filter(
        action="accounts.create", target_type="User", target_id=str(user.pk)
    ).exists()


@pytest.mark.django_db
def test_create_duplicate_username_returns_field_error():
    client, _admin = admin_client()
    make_user(username="dup1")
    resp = client.post(
        "/api/users/",
        {"username": "dup1", "password": STRONG_PASSWORD, "role": "nurse"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "username" in resp.json()


@pytest.mark.django_db
def test_non_admin_cannot_create_account():
    client = Client()
    make_user(username="recept1", role="receptionist")
    client.post(
        "/api/auth/login/",
        {"username": "recept1", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    resp = client.post(
        "/api/users/",
        {"username": "new1", "password": STRONG_PASSWORD, "role": "nurse"},
        content_type="application/json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_cannot_list_users():
    resp = Client().get("/api/users/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_admin_lists_users_and_user_can_view_own_detail():
    client, admin = admin_client()
    other = make_user(username="doctor1", role="doctor")
    resp = client.get("/api/users/")
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()["results"]]
    assert {"admin1", "doctor1"} <= set(usernames)

    own = Client()
    own.post(
        "/api/auth/login/",
        {"username": "doctor1", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert own.get(f"/api/users/{other.pk}/").status_code == 200
    # ... but not another user's detail
    assert own.get(f"/api/users/{admin.pk}/").status_code == 403


# --- User Story 3: Admin disables / re-activates / resets a password -------


@pytest.mark.django_db
def test_admin_disables_account_and_it_cannot_sign_in():
    client, _admin = admin_client()
    target = make_user(username="to_disable", role="nurse")
    resp = client.patch(
        f"/api/users/{target.pk}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.is_active is False
    assert AuditEvent.objects.filter(action="accounts.disable").exists()
    login = Client().post(
        "/api/auth/login/",
        {"username": "to_disable", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert login.status_code == 400  # generic sign-in error, same as wrong password


@pytest.mark.django_db
def test_admin_reactivates_disabled_account():
    client, _admin = admin_client()
    target = make_user(username="to_reactivate", role="nurse")
    target.is_active = False
    target.save(update_fields=["is_active"])
    resp = client.patch(
        f"/api/users/{target.pk}/",
        {"is_active": True},
        content_type="application/json",
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.is_active is True
    login = Client().post(
        "/api/auth/login/",
        {"username": "to_reactivate", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert login.status_code == 200


@pytest.mark.django_db
def test_admin_changes_role_and_audit_event_recorded():
    client, _admin = admin_client()
    target = make_user(username="role_change", role="nurse")
    resp = client.patch(
        f"/api/users/{target.pk}/",
        {"role": "doctor"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.role == Role.DOCTOR
    assert target.groups.filter(name="doctor").exists()
    assert AuditEvent.objects.filter(action="accounts.role_change").exists()


@pytest.mark.django_db
def test_admin_cannot_disable_or_demote_self_or_last_admin():
    client, admin = admin_client()
    resp = client.patch(
        f"/api/users/{admin.pk}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert resp.status_code == 400
    resp = client.patch(
        f"/api/users/{admin.pk}/",
        {"role": "nurse"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    admin.refresh_from_db()
    assert admin.is_active is True and admin.role == Role.ADMIN


@pytest.mark.django_db
def test_admin_resets_password_old_stops_new_works_and_no_secret_in_audit():
    client, _admin = admin_client()
    target = make_user(username="reset_me", role="nurse")
    resp = client.post(
        f"/api/users/{target.pk}/reset-password/",
        {"password": OTHER_PASSWORD},
        content_type="application/json",
    )
    assert resp.status_code == 200
    target.refresh_from_db()
    assert target.must_change_password is True
    old_login = Client().post(
        "/api/auth/login/",
        {"username": "reset_me", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert old_login.status_code == 400
    new_login = Client().post(
        "/api/auth/login/",
        {"username": "reset_me", "password": OTHER_PASSWORD},
        content_type="application/json",
    )
    assert new_login.status_code == 200
    events = AuditEvent.objects.filter(action="accounts.password_reset")
    assert events.exists()
    for event in events:
        assert STRONG_PASSWORD not in str(event.metadata)
        assert OTHER_PASSWORD not in str(event.metadata)


# --- FR-008 / SC-005: audit events for auth actions --------------------------


@pytest.mark.django_db
def test_successful_and_failed_sign_ins_record_audit_events():
    client = Client()
    make_user(username="audited", role="nurse")
    assert client.post(
        "/api/auth/login/",
        {"username": "audited", "password": STRONG_PASSWORD},
        content_type="application/json",
    ).status_code == 200
    assert AuditEvent.objects.filter(action="auth.sign_in", outcome="success").exists()
    assert client.post(
        "/api/auth/login/",
        {"username": "audited", "password": "WrongPassword123"},
        content_type="application/json",
    ).status_code == 400
    assert AuditEvent.objects.filter(action="auth.sign_in", outcome="failure").exists()


@pytest.mark.django_db
def test_sign_out_and_password_change_record_audit_events():
    client = Client()
    make_user(username="audited2", role="nurse")
    client.post(
        "/api/auth/login/",
        {"username": "audited2", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert client.post(
        "/api/auth/change-password/",
        {"current_password": STRONG_PASSWORD, "new_password": OTHER_PASSWORD},
        content_type="application/json",
    ).status_code == 200
    assert AuditEvent.objects.filter(action="auth.password_change").exists()
    assert client.post("/api/auth/logout/").status_code == 200
    assert AuditEvent.objects.filter(action="auth.sign_out").exists()


# --- User Story 5: Admin reviews the security audit trail ------------------


@pytest.mark.django_db
def test_admin_lists_audit_events_non_admin_denied():
    client, _admin = admin_client()
    make_user(username="audited3", role="nurse")
    Client().post(
        "/api/auth/login/",
        {"username": "audited3", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    resp = client.get("/api/audit/events/")
    assert resp.status_code == 200
    events = resp.json()["results"]
    assert events, "expected at least one audit event"
    first = events[0]
    assert {"actor", "action", "target_type", "target_id", "timestamp", "outcome"} <= set(first)
    assert STRONG_PASSWORD not in str(resp.json())

    non_admin = Client()
    non_admin.post(
        "/api/auth/login/",
        {"username": "audited3", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert non_admin.get("/api/audit/events/").status_code == 403
