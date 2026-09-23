from tests.conftest import register_org


def test_register_creates_org_and_returns_token(client):
    token = register_org(client, email="owner@example.com")
    assert token

    response = client.get(
        "/api/v1/iam/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "owner@example.com"
    assert body["organization_name"] == "Acme Security"


def test_login_with_valid_credentials(client):
    register_org(client, email="login@example.com", password="Password123!")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_invalid_password_is_rejected(client):
    register_org(client, email="wrongpw@example.com", password="Password123!")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/api/v1/iam/profile")
    assert response.status_code in (401, 403)
