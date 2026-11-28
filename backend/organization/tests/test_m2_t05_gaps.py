"""M2-T05 gap tests (Spec 003): permission deny beyond create, audit on
deactivation/reactivation, FR-010 pagination/filter/sort, and
unauthenticated access across all organisation endpoints.

Written test-first for M2-T05. Each test covers one Spec 003 acceptance
scenario (SC-004, SC-005, FR-008, FR-010) or test-strategy §2 (allow/deny
for 100% of protected endpoints) that M2-T03/T04 left uncovered.

Run with: backend/.venv/bin/python -m pytest organization/tests/test_m2_t05_gaps.py
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


# --- Gap 2a: SC-004 — a non-Admin attempting ANY setup mutation is denied ---


@pytest.mark.django_db
def test_non_admin_cannot_patch_or_delete_department():
    client = admin_client()
    dept = make_department(client, code="OPD")
    staff = signed_in_client("recept1", role="receptionist")
    patch = staff.patch(
        f"/api/departments/{dept['id']}/",
        {"name": "Renamed"},
        content_type="application/json",
    )
    assert patch.status_code == 403
    assert staff.delete(f"/api/departments/{dept['id']}/").status_code == 403
    # Nothing changed, nothing deleted.
    assert client.get(f"/api/departments/{dept['id']}/").json()["name"] == "Outpatient"


@pytest.mark.django_db
def test_non_admin_cannot_patch_or_delete_staff():
    client = admin_client()
    dept = make_department(client, code="OPD")
    profile = make_staff(client, dept["id"])
    staff = signed_in_client("nurse1", role="nurse")
    assert staff.patch(
        f"/api/staff/{profile['id']}/",
        {"job_title": "Renamed"},
        content_type="application/json",
    ).status_code == 403
    assert staff.patch(
        f"/api/staff/{profile['id']}/",
        {"status": "inactive", "status_reason": "Trying"},
        content_type="application/json",
    ).status_code == 403
    assert staff.delete(f"/api/staff/{profile['id']}/").status_code == 403
    assert client.get(f"/api/staff/{profile['id']}/").status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_patch_or_delete_service():
    client = admin_client()
    category = make_category(client)
    service = make_service(client, category["id"])
    staff = signed_in_client("doctor1", role="doctor")
    assert staff.patch(
        f"/api/services/{service['id']}/",
        {"name": "Renamed"},
        content_type="application/json",
    ).status_code == 403
    assert staff.delete(f"/api/services/{service['id']}/").status_code == 403
    assert client.get(f"/api/services/{service['id']}/").status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_mutate_service_category_or_visit_type():
    client = admin_client()
    category = make_category(client)
    visit_type = make_visit_type(client)
    staff = signed_in_client("recept1", role="receptionist")
    # Create deny (neither was tested before M2-T05).
    assert staff.post(
        "/api/service-categories/", {"name": "Imaging"}, content_type="application/json"
    ).status_code == 403
    assert staff.post(
        "/api/visit-types/", {"name": "Follow-up"}, content_type="application/json"
    ).status_code == 403
    # Edit + delete deny.
    assert staff.patch(
        f"/api/service-categories/{category['id']}/",
        {"name": "Renamed"},
        content_type="application/json",
    ).status_code == 403
    assert staff.patch(
        f"/api/visit-types/{visit_type['id']}/",
        {"name": "Renamed"},
        content_type="application/json",
    ).status_code == 403
    assert staff.delete(f"/api/service-categories/{category['id']}/").status_code == 403
    assert staff.delete(f"/api/visit-types/{visit_type['id']}/").status_code == 403


# --- Gap 2b: SC-005 / FR-008 — deactivation/reactivation are audited --------


@pytest.mark.django_db
def test_department_deactivation_and_reactivation_are_audited():
    client = admin_client()
    dept = make_department(client, code="OPD")
    client.patch(
        f"/api/departments/{dept['id']}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert AuditEvent.objects.filter(
        action="organization.department.deactivate",
        target_type="Department",
        target_id=str(dept["id"]),
        actor__username="admin1",
    ).exists()
    client.patch(
        f"/api/departments/{dept['id']}/",
        {"is_active": True},
        content_type="application/json",
    )
    assert AuditEvent.objects.filter(
        action="organization.department.reactivate",
        target_type="Department",
        target_id=str(dept["id"]),
        actor__username="admin1",
    ).exists()


@pytest.mark.django_db
def test_service_deactivation_and_reactivation_are_audited():
    client = admin_client()
    category = make_category(client)
    service = make_service(client, category["id"])
    client.patch(
        f"/api/services/{service['id']}/",
        {"is_active": False},
        content_type="application/json",
    )
    assert AuditEvent.objects.filter(
        action="organization.service.deactivate",
        target_type="Service",
        target_id=str(service["id"]),
    ).exists()
    client.patch(
        f"/api/services/{service['id']}/",
        {"is_active": True},
        content_type="application/json",
    )
    assert AuditEvent.objects.filter(
        action="organization.service.reactivate",
        target_type="Service",
        target_id=str(service["id"]),
    ).exists()


@pytest.mark.django_db
def test_staff_reactivation_is_audited_and_recorded_in_history():
    client = admin_client()
    dept = make_department(client, code="OPD")
    profile = make_staff(client, dept["id"])
    client.patch(
        f"/api/staff/{profile['id']}/",
        {"status": "inactive", "status_reason": "Left the hospital"},
        content_type="application/json",
    )
    client.patch(
        f"/api/staff/{profile['id']}/",
        {"status": "active", "status_reason": "Returned to work"},
        content_type="application/json",
    )
    events = AuditEvent.objects.filter(
        action="organization.staff.status_change",
        target_type="StaffProfile",
        target_id=str(profile["id"]),
    ).order_by("timestamp")
    assert events.count() == 2
    assert events[1].metadata == {"from": "inactive", "to": "active"}
    history = client.get(f"/api/staff/{profile['id']}/status-history/")
    assert history.status_code == 200
    entries = history.json()["results"] if "results" in history.json() else history.json()
    assert [e["new_status"] for e in entries] == ["inactive", "active"]
    assert entries[1]["reason"] == "Returned to work"


# --- Gap 2c: FR-010 — paginate, filter, and sort list views ------------------


@pytest.mark.django_db
def test_department_list_paginates_at_20():
    client = admin_client()
    for i in range(25):
        make_department(client, code=f"D{i:02d}", name=f"Department {i:02d}")
    page1 = client.get("/api/departments/")
    assert page1.status_code == 200
    body = page1.json()
    assert body["count"] == 25
    assert len(body["results"]) == 20
    assert body["next"] is not None
    page2 = client.get("/api/departments/?page=2")
    assert len(page2.json()["results"]) == 5
    assert page2.json()["next"] is None


@pytest.mark.django_db
def test_department_list_orders_by_name_ascending_and_descending():
    client = admin_client()
    make_department(client, code="ZUL", name="Zulu")
    make_department(client, code="ALP", name="Alpha")
    make_department(client, code="MIK", name="Mike")
    asc = client.get("/api/departments/?ordering=name").json()["results"]
    assert [d["name"] for d in asc] == ["Alpha", "Mike", "Zulu"]
    desc = client.get("/api/departments/?ordering=-name").json()["results"]
    assert [d["name"] for d in desc] == ["Zulu", "Mike", "Alpha"]


@pytest.mark.django_db
def test_department_list_searches_name_and_code():
    client = admin_client()
    make_department(client, code="OPD", name="Outpatient")
    make_department(client, code="LAB", name="Laboratory")
    by_name = client.get("/api/departments/?search=outpat").json()["results"]
    assert [d["code"] for d in by_name] == ["OPD"]
    by_code = client.get("/api/departments/?search=LAB").json()["results"]
    assert [d["code"] for d in by_code] == ["LAB"]


@pytest.mark.django_db
def test_service_list_orders_and_searches():
    client = admin_client()
    category = make_category(client)
    make_service(client, category["id"], code="XRAY", name="X-ray")
    make_service(client, category["id"], code="CONS-GEN", name="General consultation")
    asc = client.get("/api/services/?ordering=name").json()["results"]
    assert [s["code"] for s in asc] == ["CONS-GEN", "XRAY"]
    found = client.get("/api/services/?search=xray").json()["results"]
    assert [s["code"] for s in found] == ["XRAY"]


@pytest.mark.django_db
def test_staff_list_orders_searches_and_filters_by_status():
    client = admin_client()
    dept = make_department(client, code="OPD")
    first = make_staff(client, dept["id"])
    make_staff(
        client,
        dept["id"],
        full_name="Dr Bilal Ahmed",
        job_title="Medical Officer",
    )
    client.patch(
        f"/api/staff/{first['id']}/",
        {"status": "inactive", "status_reason": "Left the hospital"},
        content_type="application/json",
    )
    inactive = client.get("/api/staff/?status=inactive").json()["results"]
    assert [s["full_name"] for s in inactive] == ["Dr Ayesha Khan"]
    found = client.get("/api/staff/?search=bilal").json()["results"]
    assert [s["full_name"] for s in found] == ["Dr Bilal Ahmed"]
    desc = client.get("/api/staff/?ordering=-full_name").json()["results"]
    assert [s["full_name"] for s in desc] == ["Dr Bilal Ahmed", "Dr Ayesha Khan"]


# --- Gap 2d: unauthenticated (401) coverage across org endpoints -------------


@pytest.mark.django_db
def test_unauthenticated_access_denied_on_all_organization_endpoints():
    client = admin_client()
    dept = make_department(client, code="OPD")
    category = make_category(client)
    visit_type = make_visit_type(client)
    service = make_service(client, category["id"])
    profile = make_staff(client, dept["id"])
    anon = Client()
    # Lists and details.
    for path in (
        "/api/departments/",
        f"/api/departments/{dept['id']}/",
        "/api/staff/",
        f"/api/staff/{profile['id']}/",
        f"/api/staff/{profile['id']}/status-history/",
        "/api/services/",
        f"/api/services/{service['id']}/",
        "/api/service-categories/",
        f"/api/service-categories/{category['id']}/",
        "/api/visit-types/",
        f"/api/visit-types/{visit_type['id']}/",
    ):
        assert anon.get(path).status_code in (401, 403), path
    # Mutations.
    for method, path, payload in (
        ("post", "/api/departments/", {"name": "X", "code": "XXX"}),
        ("patch", f"/api/departments/{dept['id']}/", {"name": "X"}),
        ("delete", f"/api/departments/{dept['id']}/", None),
        ("post", "/api/staff/", {"full_name": "X", "job_title": "Y", "role": "nurse"}),
        ("patch", f"/api/staff/{profile['id']}/", {"job_title": "X"}),
        ("delete", f"/api/staff/{profile['id']}/", None),
        ("post", "/api/services/", {"name": "X", "code": "XXX", "category": category["id"]}),
        ("patch", f"/api/services/{service['id']}/", {"name": "X"}),
        ("delete", f"/api/services/{service['id']}/", None),
        ("post", "/api/service-categories/", {"name": "X"}),
        ("delete", f"/api/service-categories/{category['id']}/", None),
        ("post", "/api/visit-types/", {"name": "X"}),
        ("delete", f"/api/visit-types/{visit_type['id']}/", None),
    ):
        kwargs = {"content_type": "application/json"} if payload is not None else {}
        resp = getattr(anon, method)(path, payload, **kwargs)
        assert resp.status_code in (401, 403), (method, path)
