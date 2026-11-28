"""Hospital setup backend (Spec 003, M2): departments, staff profiles,
service catalog, categories and visit types.

Written test-first for M2-T03: the organization API. Each test covers
one Spec 003 acceptance scenario (User Stories 1–5, FR-001–FR-013) and
must FAIL before implementation — the models and endpoints do not exist
yet and no audit events are recorded yet.

Run with: backend/.venv/bin/python -m pytest organization/tests/test_organization.py
"""

import re

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


# --- User Story 1: Admin creates and manages departments -------------------


@pytest.mark.django_db
def test_admin_creates_department_and_audit_event_recorded():
    client = admin_client()
    resp = client.post(
        "/api/departments/",
        {"name": "Outpatient", "code": "OPD", "description": "Walk-in clinic"},
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "OPD"
    assert data["is_active"] is True
    assert AuditEvent.objects.filter(
        action="organization.department.create",
        target_type="Department",
        target_id=str(data["id"]),
    ).exists()


@pytest.mark.django_db
def test_duplicate_department_code_returns_field_error():
    client = admin_client()
    make_department(client, code="OPD")
    resp = client.post(
        "/api/departments/",
        {"name": "Other Outpatient", "code": "opd"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "code" in resp.json()


@pytest.mark.django_db
def test_missing_department_name_returns_field_error():
    client = admin_client()
    resp = client.post(
        "/api/departments/", {"code": "LAB"}, content_type="application/json"
    )
    assert resp.status_code == 400
    assert "name" in resp.json()


@pytest.mark.django_db
def test_non_admin_cannot_create_department_and_unauthenticated_cannot_list():
    client = signed_in_client("recept1", role="receptionist")
    resp = client.post(
        "/api/departments/",
        {"name": "Outpatient", "code": "OPD"},
        content_type="application/json",
    )
    assert resp.status_code == 403
    assert Client().get("/api/departments/").status_code in (401, 403)


@pytest.mark.django_db
def test_staff_lists_active_departments_read_only():
    client = admin_client()
    make_department(client, code="OPD")
    make_department(client, code="LAB", name="Laboratory")
    staff = signed_in_client("recept1", role="receptionist")
    resp = staff.get("/api/departments/")
    assert resp.status_code == 200
    codes = [d["code"] for d in resp.json()["results"]]
    assert {"OPD", "LAB"} <= set(codes)


@pytest.mark.django_db
def test_deactivated_department_hidden_from_active_list_and_reactivatable():
    client = admin_client()
    dept = make_department(client, code="OPD")
    resp = client.patch(
        f"/api/departments/{dept['id']}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    active = client.get("/api/departments/?is_active=true")
    assert "OPD" not in [d["code"] for d in active.json()["results"]]
    resp = client.patch(
        f"/api/departments/{dept['id']}/",
        {"is_active": True},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True
    active = client.get("/api/departments/?is_active=true")
    assert "OPD" in [d["code"] for d in active.json()["results"]]


@pytest.mark.django_db
def test_deactivating_department_with_active_staff_allowed_with_warning():
    client = admin_client()
    dept = make_department(client, code="OPD")
    make_staff(client, dept["id"])
    resp = client.patch(
        f"/api/departments/{dept['id']}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert "warning" in resp.json()
    # Staff keep their department link (D-13).
    staff = client.get("/api/staff/").json()["results"][0]
    assert staff["department"] == dept["id"]


# --- User Story 4: reference data used by history cannot be deleted ---------


@pytest.mark.django_db
def test_delete_department_linked_to_staff_is_refused():
    client = admin_client()
    dept = make_department(client, code="OPD")
    make_staff(client, dept["id"])
    resp = client.delete(f"/api/departments/{dept['id']}/")
    assert resp.status_code == 400
    assert "detail" in resp.json()
    assert client.get(f"/api/departments/{dept['id']}/").status_code == 200
    assert AuditEvent.objects.filter(
        action="organization.department.delete_refused", outcome="failure"
    ).exists()


@pytest.mark.django_db
def test_delete_unused_department_succeeds():
    client = admin_client()
    dept = make_department(client, code="OPD")
    resp = client.delete(f"/api/departments/{dept['id']}/")
    assert resp.status_code == 204
    assert client.get(f"/api/departments/{dept['id']}/").status_code == 404


# --- User Story 3: service catalog, categories, visit types -----------------


@pytest.mark.django_db
def test_admin_creates_category_visit_type_and_service():
    client = admin_client()
    dept = make_department(client, code="OPD")
    category = client.post(
        "/api/service-categories/",
        {"name": "Consultation"},
        content_type="application/json",
    )
    assert category.status_code == 201
    visit_type = client.post(
        "/api/visit-types/", {"name": "First visit"}, content_type="application/json"
    )
    assert visit_type.status_code == 201
    service = client.post(
        "/api/services/",
        {
            "name": "General consultation",
            "code": "CONS-GEN",
            "category": category.json()["id"],
            "department": dept["id"],
        },
        content_type="application/json",
    )
    assert service.status_code == 201
    data = service.json()
    assert data["is_active"] is True
    assert "price" not in data  # D-10: no price field in v1
    assert AuditEvent.objects.filter(action="organization.service.create").exists()


@pytest.mark.django_db
def test_duplicate_service_code_returns_field_error():
    client = admin_client()
    category = client.post(
        "/api/service-categories/",
        {"name": "Consultation"},
        content_type="application/json",
    ).json()
    payload = {"name": "General consultation", "code": "CONS-GEN", "category": category["id"]}
    assert client.post("/api/services/", payload, content_type="application/json").status_code == 201
    resp = client.post("/api/services/", payload, content_type="application/json")
    assert resp.status_code == 400
    assert "code" in resp.json()


@pytest.mark.django_db
def test_non_admin_cannot_create_service_but_can_list_services():
    client = admin_client()
    category = client.post(
        "/api/service-categories/",
        {"name": "Consultation"},
        content_type="application/json",
    ).json()
    client.post(
        "/api/services/",
        {"name": "General consultation", "code": "CONS-GEN", "category": category["id"]},
        content_type="application/json",
    )
    staff = signed_in_client("doctor1", role="doctor")
    resp = staff.post(
        "/api/services/",
        {"name": "X-ray", "code": "XRAY", "category": category["id"]},
        content_type="application/json",
    )
    assert resp.status_code == 403
    listed = staff.get("/api/services/")
    assert listed.status_code == 200
    assert [s["code"] for s in listed.json()["results"]] == ["CONS-GEN"]


@pytest.mark.django_db
def test_delete_category_with_services_is_refused_unused_category_deletes():
    client = admin_client()
    used = client.post(
        "/api/service-categories/",
        {"name": "Consultation"},
        content_type="application/json",
    ).json()
    unused = client.post(
        "/api/service-categories/", {"name": "Imaging"}, content_type="application/json"
    ).json()
    client.post(
        "/api/services/",
        {"name": "General consultation", "code": "CONS-GEN", "category": used["id"]},
        content_type="application/json",
    )
    assert client.delete(f"/api/service-categories/{used['id']}/").status_code == 400
    assert client.get(f"/api/service-categories/{used['id']}/").status_code == 200
    assert client.delete(f"/api/service-categories/{unused['id']}/").status_code == 204


@pytest.mark.django_db
def test_deactivated_service_hidden_from_active_list():
    client = admin_client()
    category = client.post(
        "/api/service-categories/",
        {"name": "Consultation"},
        content_type="application/json",
    ).json()
    service = client.post(
        "/api/services/",
        {"name": "General consultation", "code": "CONS-GEN", "category": category["id"]},
        content_type="application/json",
    ).json()
    assert client.patch(
        f"/api/services/{service['id']}/",
        {"is_active": False},
        content_type="application/json",
    ).status_code == 200
    active = client.get("/api/services/?is_active=true")
    assert active.json()["results"] == []


# --- User Story 2: Admin creates a staff profile ----------------------------


@pytest.mark.django_db
def test_admin_creates_staff_profile_with_auto_staff_id_and_audit():
    client = admin_client()
    dept = make_department(client, code="OPD")
    staff = make_staff(client, dept["id"], blood_group="O+")
    assert re.fullmatch(r"STF-\d{4}-\d{4}", staff["staff_id"])
    assert staff["status"] == "active"
    assert staff["blood_group"] == "O+"
    assert AuditEvent.objects.filter(
        action="organization.staff.create",
        target_type="StaffProfile",
        target_id=str(staff["id"]),
    ).exists()
    second = make_staff(
        client, dept["id"], full_name="Dr Bilal Ahmed", job_title="Medical Officer"
    )
    assert second["staff_id"] != staff["staff_id"]


@pytest.mark.django_db
def test_staff_blood_group_optional_but_validated():
    client = admin_client()
    dept = make_department(client, code="OPD")
    without = make_staff(client, dept["id"])
    assert without["blood_group"] is None
    resp = client.post(
        "/api/staff/",
        {
            "full_name": "Bad Group",
            "job_title": "Nurse",
            "department": dept["id"],
            "role": "nurse",
            "blood_group": "X",
        },
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "blood_group" in resp.json()


@pytest.mark.django_db
def test_department_required_for_clinical_roles_optional_for_others():
    client = admin_client()
    resp = client.post(
        "/api/staff/",
        {"full_name": "Dr No Dept", "job_title": "Doctor", "role": "doctor"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "department" in resp.json()
    billing = client.post(
        "/api/staff/",
        {"full_name": "Billing Clerk", "job_title": "Billing Officer", "role": "billing"},
        content_type="application/json",
    )
    assert billing.status_code == 201
    assert billing.json()["department"] is None


@pytest.mark.django_db
def test_staff_profile_may_link_at_most_one_user_account():
    client = admin_client()
    dept = make_department(client, code="OPD")
    account = make_user(username="doctor1", role="doctor")
    linked = make_staff(client, dept["id"], user=account.pk)
    assert linked["user"] == account.pk
    resp = client.post(
        "/api/staff/",
        {
            "full_name": "Second Profile",
            "job_title": "Doctor",
            "department": dept["id"],
            "role": "doctor",
            "user": account.pk,
        },
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_non_admin_cannot_create_staff_profile():
    client = admin_client()
    dept = make_department(client, code="OPD")
    staff = signed_in_client("recept1", role="receptionist")
    resp = staff.post(
        "/api/staff/",
        {"full_name": "Dr X", "job_title": "Doctor", "department": dept["id"], "role": "doctor"},
        content_type="application/json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_staff_directory_hides_contact_details_from_other_roles():
    client = admin_client()
    dept = make_department(client, code="OPD")
    account = make_user(username="doctor1", role="doctor")
    make_staff(
        client, dept["id"], user=account.pk, phone="03001234567",
        email="ayesha@example.com",
    )
    other = signed_in_client("nurse1", role="nurse")
    listed = other.get("/api/staff/").json()["results"][0]
    assert listed["full_name"] == "Dr Ayesha Khan"
    assert "phone" not in listed and "email" not in listed and "blood_group" not in listed
    # Admin sees full detail.
    full = client.get("/api/staff/").json()["results"][0]
    assert full["phone"] == "03001234567"
    # The staff member themself sees their own contact details.
    own = Client()
    own.post(
        "/api/auth/login/",
        {"username": "doctor1", "password": STRONG_PASSWORD},
        content_type="application/json",
    )
    mine = own.get("/api/staff/").json()["results"][0]
    assert mine["phone"] == "03001234567"


# --- User Story 5: staff status changes are controlled and traceable --------


@pytest.mark.django_db
def test_staff_status_change_needs_reason_and_is_recorded_in_history():
    client = admin_client()
    dept = make_department(client, code="OPD")
    staff = make_staff(client, dept["id"])
    no_reason = client.patch(
        f"/api/staff/{staff['id']}/",
        {"status": "inactive"},
        content_type="application/json",
    )
    assert no_reason.status_code == 400
    changed = client.patch(
        f"/api/staff/{staff['id']}/",
        {"status": "inactive", "status_reason": "Left the hospital"},
        content_type="application/json",
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "inactive"
    history = client.get(f"/api/staff/{staff['id']}/status-history/")
    assert history.status_code == 200
    entries = history.json()["results"] if "results" in history.json() else history.json()
    assert len(entries) == 1
    assert entries[0]["reason"] == "Left the hospital"
    assert entries[0]["new_status"] == "inactive"
    assert entries[0]["actor"] == "admin1"
    assert AuditEvent.objects.filter(action="organization.staff.status_change").exists()


@pytest.mark.django_db
def test_inactive_staff_not_available_as_provider():
    client = admin_client()
    dept = make_department(client, code="OPD")
    staff = make_staff(client, dept["id"])
    client.patch(
        f"/api/staff/{staff['id']}/",
        {"status": "inactive", "status_reason": "Left the hospital"},
        content_type="application/json",
    )
    available = client.get("/api/staff/?available=true")
    assert available.json()["results"] == []
    # The profile itself is still in the directory, with its history.
    assert client.get(f"/api/staff/{staff['id']}/").status_code == 200


@pytest.mark.django_db
def test_staff_profile_is_never_hard_deleted():
    client = admin_client()
    dept = make_department(client, code="OPD")
    staff = make_staff(client, dept["id"])
    resp = client.delete(f"/api/staff/{staff['id']}/")
    assert resp.status_code == 400
    assert client.get(f"/api/staff/{staff['id']}/").status_code == 200
    assert AuditEvent.objects.filter(
        action="organization.staff.delete_refused", outcome="failure"
    ).exists()
