import os
import shutil
import tempfile

# Must happen before any `app.*` module is imported: app.core.config.Settings
# reads these at import time, and app.db.session builds the SQLAlchemy engine
# from DATABASE_URL at import time too. An in-memory SQLite database is fast
# and dependency-free for tests -- see app/db/session.py for the SQLite/
# StaticPool handling that makes a single in-memory DB usable across
# connections in the same test run.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
# Never let a developer's backend/.env (real SMTP, log-link toggles, ...) leak
# into tests: env vars take precedence over the .env file.
for _name, _value in {
    "SMTP_HOST": "",
    "SMTP_FROM_EMAIL": "",
    "TRUST_PROXY_HEADERS": "false",
    "EMAIL_VERIFICATION_REQUIRED": "true",
    "EMAIL_VERIFICATION_LOG_LINK": "false",
    "PASSWORD_RESET_LOG_LINK": "false",
    "PASSWORD_RESET_MAX_PER_HOUR": "3",
    "EMAIL_VERIFICATION_MAX_PER_HOUR": "3",
}.items():
    os.environ[_name] = _value

# Scan uploads write real files to disk (see app/services/scan_service.py).
# Point that at a throwaway temp directory instead of the real
# app/uploads/, so running the suite never leaves test SARIF files behind
# in a directory the running application also uses.
_TEST_UPLOAD_DIR = tempfile.mkdtemp(prefix="scanhive-test-uploads-")
os.environ.setdefault("UPLOAD_DIR", _TEST_UPLOAD_DIR)

import atexit

atexit.register(shutil.rmtree, _TEST_UPLOAD_DIR, ignore_errors=True)

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    from app.core import rate_limit

    limiters = [v for v in vars(rate_limit).values() if isinstance(v, rate_limit.SlidingWindowLimiter)]
    for limiter in limiters:
        limiter.reset()
    yield


@pytest.fixture(autouse=True)
def _reset_database():
    """Fresh schema for every test -- full isolation, no cross-test leakage."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_org(
    client: TestClient,
    *,
    email: str = "admin@example.com",
    password: str = "Password123!",
    organization_name: str = "Acme Security",
    first_name: str = "Ada",
    last_name: str = "Admin",
) -> str:
    """Registers a new organization, verifies its first user's email (as the
    emailed link would), and returns a session token for them. The first user
    is seeded with the platform-admin role."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": organization_name,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
        },
    )
    assert response.status_code == 202, response.text
    mark_email_verified(email)
    login_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    return login_response.json()["access_token"]


def mark_email_verified(email: str) -> None:
    from datetime import datetime

    from app.models.user import User

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email.lower()).one()
        user.email_verified_at = datetime.utcnow()
        session.commit()
    finally:
        session.close()


def get_role_id(client: TestClient, admin_token: str, role_name: str) -> int:
    response = client.get("/api/v1/iam/roles", headers=auth_headers(admin_token))
    assert response.status_code == 200, response.text
    for role in response.json():
        if role["name"] == role_name:
            return role["id"]
    raise AssertionError(f"Role {role_name!r} not found among seeded roles")


def create_user_with_role(
    client: TestClient,
    admin_token: str,
    *,
    role_name: str | None,
    email: str,
    password: str = "Password123!",
    first_name: str = "Test",
    last_name: str = "User",
) -> str:
    """Invites and accepts an invitation for a new org member with a single
    named role (or no roles at all when role_name is None), returning their
    access token."""
    role_ids = [get_role_id(client, admin_token, role_name)] if role_name else []

    invite_response = client.post(
        "/api/v1/iam/invitations",
        json={"email": email, "role_ids": role_ids},
        headers=auth_headers(admin_token),
    )
    assert invite_response.status_code == 201, invite_response.text
    token = invite_response.json()["token"]

    accept_response = client.post(
        f"/api/v1/auth/invitations/{token}/accept",
        json={"first_name": first_name, "last_name": last_name, "password": password},
    )
    assert accept_response.status_code == 200, accept_response.text
    return accept_response.json()["access_token"]


def create_custom_role(
    client: TestClient,
    admin_token: str,
    *,
    name: str,
    permissions: list[str],
    description: str = "Custom role for tests",
) -> int:
    response = client.post(
        "/api/v1/iam/roles",
        json={"name": name, "description": description, "permissions": permissions},
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]
