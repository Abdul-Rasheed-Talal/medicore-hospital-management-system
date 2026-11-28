"""M2-T06 review tests (Spec 003): acceptance scenarios the M2-T03/T04/T05
suites left unasserted.

Written test-first for M2-T06. Each test covers one Spec 003 acceptance
scenario, decision, or success criterion that had no failing-or-passing
test before the review: D-14 (disabling an account leaves the linked
staff profile unchanged), US2 scenario 4 (the staff↔account link is
visible on both records), US2 scenario 5 (missing required staff field),
FR-003 (one-to-one link enforced on edit, not just create), FR-008 /
SC-005 (audit events for plain edits, category/visit-type creation and
deactivation, refused category deletion), FR-006 (unused service and
visit type delete), and US1 scenario 1 (created-by / created-at on the
created department).

Run with: backend/.venv/bin/python -m pytest organization/tests/test_m2_t06_review.py
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client

from audit.models import AuditEvent

User = get_user_model()

STRONG_PASSWORD = "CorrectHorseBatteryStaple1"  # noqa: S105 - test fixture only


def make_user(username="staff1", password=STRONG_PASSWORD, role="receptionist", **kwargs):
    user = User.objects.create_user(username=username, password=password, role=role, **kwargs)
    user.assign_role(role)
    return user


@pytest.fixture(autouse=True)
def _seed_role_groups():
    """Groups must exist before assign_role can sync membership."""
    call_command("seed_roles")


def signed_in_client(username, role="receptionist"):
    """A client signed in via the API login, so session/CSRF behave as in prod."""
    make_user(username=username, role=role)
    client = Client()
    resp = client.post(
        "/api/auth/login/",
        {"username": username, "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    assert resp.status_code == 200
    return client


def admin_client():
    return signed_in_client("admin1", role="admin")


def make_department(client, code="OPD", name="Outpatient"):
    resp = client.post(
        "/api/departments/",
        {"name": name, "code": code},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.content
    return resp.json()


def make_category(client, name="Consultation"):
    resp = client.post(
        "/api/service-categories/",
        {"name": name},
        content_type="application/json",
    )
    assert resp.status_code == 201, resp.content
    return resp.json()


def make_visit_type(client, name="First visit"):
    resp = client.post(
        "/api/visit-types/", {"name": name}, content_type="application/json"
    )
    assert resp.status_code == 201, resp.content
    return resp.json()


def make_service(client, category_id, code="CONS-GEN", name="General consultation", **overrides):
    payload = {"name": name, "code": code, "category": category_id}
    payload.update(overrides)
    resp = client.post("/api/services/", payload, content_type="application/json")
    assert resp.status_code == 201, resp.content
    return resp.json()


def make_staff(client, department_id, **overrides):
    payload = {
        "full_name": "Dr Ayesha Khan",
        "job_title": "Consultant Physician",
        "department": department_id,
        "role": "doctor",
    }
    payload.update(overrides)
    resp = client.post("/api/staff/", payload, content_type="application/json")
    assert resp.status_code == 201, resp.content
    return resp.json()


# --- D-14: disabling an account leaves the linked profile unchanged --------


@pytest.mark.django_db
def test_disabling_linked_account_leaves_staff_profile_unchanged():
    client = admin_client()
    dept = make_department(client, code="OPD")
    account = make_user(username="doctor1", role="doctor")
    profile = make_staff(client, dept["id"], user=account.pk)
    resp = client.patch(
        f"/api/users/{account.pk}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    # The profile itself is unchanged: still Active, still linked, still listed.
    after = client.get(f"/api/staff/{profile['id']}/").json()
    assert after["status"] == "active"
    assert after["user"] == account.pk
    assert after["department"] == dept["id"]
    listed = client.get("/api/staff/").json()["results"]
    assert [p["id"] for p in listed] == [profile["id"]]


# --- US2 scenario 4: the link is visible on both records -------------------


@pytest.mark.django_db
def test_user_record_shows_linked_staff_profile():
    client = admin_client()
    dept = make_department(client, code="OPD")
    account = make_user(username="doctor1", role="doctor")
    profile = make_staff(client, dept["id"], user=account.pk)
    detail = client.get(f"/api/users/{account.pk}/").json()
    assert detail["staff_profile"] == {
        "id": profile["id"],
        "staff_id": profile["staff_id"],
        "full_name": "Dr Ayesha Khan",
    }
    # The staff record shows the same link from the other side.
    assert client.get(f"/api/staff/{profile['id']}/").json()["user"] == account.pk


@pytest.mark.django_db
def test_user_record_without_profile_shows_no_staff_profile():
    client = admin_client()
    account = make_user(username="doctor1", role="doctor")
    detail = client.get(f"/api/users/{account.pk}/").json()
    assert detail["staff_profile"] is None


# --- US2 scenario 5: missing required staff field --------------------------


@pytest.mark.django_db
def test_staff_create_missing_full_name_returns_field_error():
    client = admin_client()
    dept = make_department(client, code="OPD")
    resp = client.post(
        "/api/staff/",
        {"job_title": "Doctor", "department": dept["id"], "role": "doctor"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "full_name" in resp.json()
    assert client.get("/api/staff/").json()["count"] == 0


# --- FR-003: one-to-one link enforced on edit as well as create ------------


@pytest.mark.django_db
def test_staff_relink_to_already_linked_account_is_refused():
    client = admin_client()
    dept = make_department(client, code="OPD")
    account = make_user(username="doctor1", role="doctor")
    make_staff(client, dept["id"], user=account.pk)
    second = make_staff(
        client, dept["id"], full_name="Dr Bilal Ahmed", job_title="Medical Officer"
    )
    resp = client.patch(
        f"/api/staff/{second['id']}/",
        {"user": account.pk},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert client.get(f"/api/staff/{second['id']}/").json()["user"] is None


# --- US1 scenario 1: created-by / created-at on the created record ---------


@pytest.mark.django_db
def test_created_department_response_carries_created_by_and_created_at():
    client = admin_client()
    resp = client.post(
        "/api/departments/",
        {"name": "Outpatient", "code": "OPD"},
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created_by"] == "admin1"
    assert data["created_at"]


# --- FR-008 / SC-005: audit events for edits, category/visit-type
#     creation and deactivation, and refused category deletion -------------


@pytest.mark.django_db
def test_plain_edits_record_update_audit_events_not_status_changes():
    client = admin_client()
    dept = make_department(client, code="OPD")
    profile = make_staff(client, dept["id"])
    resp = client.patch(
        f"/api/departments/{dept['id']}/",
        {"name": "Outpatient Clinic"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert AuditEvent.objects.filter(
        action="organization.department.update",
        target_type="Department",
        target_id=str(dept["id"]),
        actor__username="admin1",
    ).exists()
    resp = client.patch(
        f"/api/staff/{profile['id']}/",
        {"job_title": "Senior Consultant"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert AuditEvent.objects.filter(
        action="organization.staff.update",
        target_type="StaffProfile",
        target_id=str(profile["id"]),
    ).exists()
    # A plain edit is not a status change: no status_change event, no history.
    assert not AuditEvent.objects.filter(
        action="organization.staff.status_change",
        target_type="StaffProfile",
        target_id=str(profile["id"]),
    ).exists()
    history = client.get(f"/api/staff/{profile['id']}/status-history/").json()
    entries = history["results"] if "results" in history else history
    assert entries == []


@pytest.mark.django_db
def test_category_and_visit_type_creation_are_audited():
    client = admin_client()
    category = make_category(client, name="Consultation")
    visit_type = make_visit_type(client, name="First visit")
    assert AuditEvent.objects.filter(
        action="organization.service_category.create",
        target_type="ServiceCategory",
        target_id=str(category["id"]),
        actor__username="admin1",
    ).exists()
    assert AuditEvent.objects.filter(
        action="organization.visit_type.create",
        target_type="VisitType",
        target_id=str(visit_type["id"]),
        actor__username="admin1",
    ).exists()


@pytest.mark.django_db
def test_category_deactivation_and_reactivation_are_audited():
    client = admin_client()
    category = make_category(client, name="Consultation")
    client.patch(
        f"/api/service-categories/{category['id']}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert AuditEvent.objects.filter(
        action="organization.service_category.deactivate",
        target_type="ServiceCategory",
        target_id=str(category["id"]),
    ).exists()
    client.patch(
        f"/api/service-categories/{category['id']}/",
        {"is_active": True},
        content_type="application/json",
    )
    assert AuditEvent.objects.filter(
        action="organization.service_category.reactivate",
        target_type="ServiceCategory",
        target_id=str(category["id"]),
    ).exists()


@pytest.mark.django_db
def test_refused_category_deletion_records_failure_audit_event():
    client = admin_client()
    category = make_category(client, name="Consultation")
    make_service(client, category["id"])
    resp = client.delete(f"/api/service-categories/{category['id']}/")
    assert resp.status_code == 400
    assert AuditEvent.objects.filter(
        action="organization.service_category.delete_refused",
        target_type="ServiceCategory",
        target_id=str(category["id"]),
        outcome="failure",
        actor__username="admin1",
    ).exists()
    assert client.get(f"/api/service-categories/{category['id']}/").status_code == 200


# --- FR-006: an unused service and an unused visit type delete -------------


@pytest.mark.django_db
def test_unused_service_and_visit_type_delete():
    client = admin_client()
    category = make_category(client, name="Consultation")
    service = make_service(client, category["id"])
    resp = client.delete(f"/api/services/{service['id']}/")
    assert resp.status_code == 204
    assert client.get(f"/api/services/{service['id']}/").status_code == 404
    assert AuditEvent.objects.filter(
        action="organization.service.delete",
        target_type="Service",
        target_id=str(service["id"]),
    ).exists()
    visit_type = make_visit_type(client, name="First visit")
    assert client.delete(f"/api/visit-types/{visit_type['id']}/").status_code == 204
    assert client.get(f"/api/visit-types/{visit_type['id']}/").status_code == 404
