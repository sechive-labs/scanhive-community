import time
from datetime import datetime, timedelta

import pytest

from app.models.password_reset_token import PasswordResetToken
from app.services.mail_service import MailService
from tests.conftest import auth_headers, register_org

GENERIC = "If an account exists for that email, a password reset link has been sent."


@pytest.fixture
def sent_links(monkeypatch):
    """Captures reset links instead of sending mail (SMTP isn't configured in tests)."""
    links: list[tuple[str, str]] = []
    monkeypatch.setattr(MailService, "is_configured", property(lambda self: True))
    monkeypatch.setattr(
        MailService, "send_password_reset",
        lambda self, to, link, minutes: links.append((to, link)) or True,
    )
    monkeypatch.setattr(MailService, "send_password_changed_notice", lambda self, to: True)
    return links


def token_from(link: str) -> str:
    assert "#token=" in link, "token must be in the URL fragment, never the query string"
    return link.split("#token=", 1)[1]


def forgot(client, email):
    return client.post("/api/v1/auth/forgot-password", json={"email": email})


def reset(client, token, password="NewPassword456!"):
    return client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": password})


def login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_full_reset_flow(client, sent_links):
    register_org(client, email="user@example.com", password="OldPassword123!")

    response = forgot(client, "user@example.com")
    assert response.status_code == 200
    assert response.json()["message"] == GENERIC
    assert response.headers["cache-control"] == "no-store"
    assert len(sent_links) == 1

    assert reset(client, token_from(sent_links[0][1])).status_code == 200
    assert login(client, "user@example.com", "OldPassword123!").status_code == 401
    assert login(client, "user@example.com", "NewPassword456!").status_code == 200


def test_unknown_email_gets_identical_response_and_sends_nothing(client, sent_links):
    register_org(client, email="user@example.com")
    known = forgot(client, "user@example.com")
    unknown = forgot(client, "nobody@example.com")

    assert (known.status_code, known.json()) == (unknown.status_code, unknown.json())
    assert len(sent_links) == 1


def test_token_is_single_use(client, sent_links):
    register_org(client, email="user@example.com")
    forgot(client, "user@example.com")
    token = token_from(sent_links[0][1])

    assert reset(client, token).status_code == 200
    assert reset(client, token, "AnotherPass789!").status_code == 400


def test_new_request_invalidates_previous_link(client, sent_links):
    register_org(client, email="user@example.com")
    forgot(client, "user@example.com")
    forgot(client, "user@example.com")
    first, second = (token_from(link) for _, link in sent_links)

    assert reset(client, first).status_code == 400
    assert reset(client, second).status_code == 200


def test_expired_token_is_rejected(client, sent_links, db):
    register_org(client, email="user@example.com")
    forgot(client, "user@example.com")
    record = db.query(PasswordResetToken).one()
    record.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    assert reset(client, token_from(sent_links[0][1])).status_code == 400


def test_garbage_token_is_rejected_with_same_error(client):
    response = reset(client, "x" * 43)
    assert response.status_code == 400
    assert response.json()["detail"] == "This password reset link is invalid or has expired."


def test_token_is_stored_hashed_only(client, sent_links, db):
    register_org(client, email="user@example.com")
    forgot(client, "user@example.com")
    token = token_from(sent_links[0][1])

    stored = db.query(PasswordResetToken).one()
    assert stored.token_hash != token
    assert len(stored.token_hash) == 64


def test_short_new_password_is_rejected_without_burning_the_token(client, sent_links):
    register_org(client, email="user@example.com")
    forgot(client, "user@example.com")
    token = token_from(sent_links[0][1])

    assert reset(client, token, "short").status_code == 422
    assert reset(client, token).status_code == 200


def test_reset_signs_out_existing_sessions(client, sent_links):
    old_session = register_org(client, email="user@example.com", password="OldPassword123!")
    assert client.get("/api/v1/iam/profile", headers=auth_headers(old_session)).status_code == 200

    forgot(client, "user@example.com")
    reset(client, token_from(sent_links[0][1]))

    assert client.get("/api/v1/iam/profile", headers=auth_headers(old_session)).status_code == 401

    time.sleep(1.1)  # session tokens carry second-resolution timestamps
    new_session = login(client, "user@example.com", "NewPassword456!").json()["access_token"]
    assert client.get("/api/v1/iam/profile", headers=auth_headers(new_session)).status_code == 200


def test_disabled_account_cannot_request_reset(client, sent_links, db):
    from app.models.user import User

    register_org(client, email="user@example.com")
    user = db.query(User).filter(User.email == "user@example.com").one()
    user.is_active = False
    db.commit()

    forgot(client, "user@example.com")
    assert sent_links == []


def test_disabling_account_after_request_blocks_reset(client, sent_links, db):
    from app.models.user import User

    register_org(client, email="user@example.com")
    forgot(client, "user@example.com")
    user = db.query(User).filter(User.email == "user@example.com").one()
    user.is_active = False
    db.commit()

    assert reset(client, token_from(sent_links[0][1])).status_code == 400


def test_per_account_hourly_quota_is_silent(client, sent_links):
    register_org(client, email="user@example.com")
    responses = [forgot(client, "user@example.com") for _ in range(5)]

    assert all(r.status_code == 200 and r.json()["message"] == GENERIC for r in responses)
    assert len(sent_links) == 3


def test_ip_rate_limit_on_forgot_password(client, sent_links):
    statuses = [forgot(client, f"u{i}@example.com").status_code for i in range(12)]
    assert statuses[:10] == [200] * 10
    assert statuses[10:] == [429, 429]


def test_ip_rate_limit_on_reset_attempts(client):
    statuses = [reset(client, "x" * 43).status_code for _ in range(12)]
    assert statuses[:10] == [400] * 10
    assert statuses[10:] == [429, 429]


def test_rate_limited_response_has_retry_after(client):
    for i in range(10):
        forgot(client, f"u{i}@example.com")
    limited = forgot(client, "u@example.com")
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) > 0
