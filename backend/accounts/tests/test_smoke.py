"""Backend smoke tests: health check and deny-by-default auth.

Covers the scaffold contract only — no feature behaviour yet:
- the health-check endpoint answers without authentication
- unauthenticated access to a protected endpoint is denied
- a signed-in user can read their own session
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.mark.django_db
def test_health_check_ok():
    client = Client()
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_unauthenticated_session_denied():
    client = Client()
    response = client.get("/api/auth/session/")
    # DRF SessionAuthentication returns 403 for anonymous requests.
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_login_and_session_flow():
    user = User.objects.create_user(
        username="reception1", password="TempPass123!", role="receptionist"
    )
    client = Client()
    # Login via the session-auth endpoint (CSRF enforced by the view,
    # but the Django test client handles the cookie flow).
    response = client.post(
        "/api/auth/login/",
        {"username": "reception1", "password": "TempPass123!"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["username"] == "reception1"
    assert response.json()["role"] == "receptionist"

    response = client.get("/api/auth/session/")
    assert response.status_code == 200
    assert response.json()["username"] == "reception1"

    response = client.post("/api/auth/logout/")
    assert response.status_code == 200
    response = client.get("/api/auth/session/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_login_rejects_wrong_password():
    User.objects.create_user(
        username="reception1", password="TempPass123!", role="receptionist"
    )
    client = Client()
    response = client.post(
        "/api/auth/login/",
        {"username": "reception1", "password": "wrong-password"},
        content_type="application/json",
    )
    assert response.status_code == 400
