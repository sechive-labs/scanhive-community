from datetime import datetime, timedelta

import pytest

from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.mail_service import MailService
from tests.conftest import register_org

REGISTER_MESSAGE = (
    "Check your email to verify your address, then sign in. "
    "If you already have an account, you'll get an email about that instead."
)
RESEND_MESSAGE = "If that account exists and isn't verified yet, a new verification link has been sent."


@pytest.fixture
def mailbox(monkeypatch):
    box = {"verify": [], "notice": []}
    monkeypatch.setattr(MailService, "is_configured", property(lambda self: True))
    monkeypatch.setattr(
        MailService, "send_email_verification",
        lambda self, to, link, hours: box["verify"].append((to, link)) or True,
    )
    monkeypatch.setattr(
        MailService, "send_existing_account_notice",
        lambda self, to, link: box["notice"].append(to) or True,
    )
    return box


def signup(client, email="new@example.com", org="New Org", password="Str0ngPassw0rd!"):
    return client.post("/api/v1/auth/register", json={
        "organization_name": org, "email": email, "first_name": "N", "last_name": "U", "password": password,
    })


def login(client, email="new@example.com", password="Str0ngPassw0rd!"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def token_from(link: str) -> str:
    assert "#token=" in link
    return link.split("#token=", 1)[1]


def verify(client, token):
    return client.post("/api/v1/auth/verify-email", json={"token": token})


def test_register_returns_no_session_and_sends_verification_email(client, mailbox):
    response = signup(client)

    assert response.status_code == 202
    assert response.json() == {"message": REGISTER_MESSAGE}
    assert "access_token" not in response.text
    assert len(mailbox["verify"]) == 1
    assert mailbox["verify"][0][0] == "new@example.com"


def test_cannot_sign_in_until_email_is_verified(client, mailbox):
    signup(client)

    blocked = login(client)
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "email_not_verified"

    assert verify(client, token_from(mailbox["verify"][0][1])).status_code == 200
    assert login(client).status_code == 200


def test_wrong_password_on_unverified_account_does_not_reveal_it_is_unverified(client, mailbox):
    signup(client)
    response = login(client, password="WrongPassword1!")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_verification_token_is_single_use(client, mailbox):
    signup(client)
    token = token_from(mailbox["verify"][0][1])

    assert verify(client, token).status_code == 200
    assert verify(client, token).status_code == 400


def test_expired_verification_token_is_rejected(client, mailbox, db):
    signup(client)
    record = db.query(EmailVerificationToken).one()
    record.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.commit()

    assert verify(client, token_from(mailbox["verify"][0][1])).status_code == 400
    assert login(client).status_code == 403


def test_garbage_verification_token_is_rejected(client):
    response = verify(client, "x" * 43)
    assert response.status_code == 400
    assert response.json()["detail"] == "This verification link is invalid or has expired."


def test_verification_token_is_stored_hashed(client, mailbox, db):
    signup(client)
    token = token_from(mailbox["verify"][0][1])
    stored = db.query(EmailVerificationToken).one()
    assert stored.token_hash != token and len(stored.token_hash) == 64


def test_resend_invalidates_the_previous_link(client, mailbox):
    signup(client)
    client.post("/api/v1/auth/resend-verification", json={"email": "new@example.com"})
    first, second = (token_from(link) for _, link in mailbox["verify"])

    assert verify(client, first).status_code == 400
    assert verify(client, second).status_code == 200


def test_resend_response_is_identical_for_unknown_and_verified_accounts(client, mailbox):
    signup(client)
    register_org(client, email="verified@example.com", organization_name="Verified Org")
    sent_before = len(mailbox["verify"])

    responses = [
        client.post("/api/v1/auth/resend-verification", json={"email": e})
        for e in ("new@example.com", "ghost@example.com", "verified@example.com")
    ]

    assert {(r.status_code, r.json()["message"]) for r in responses} == {(200, RESEND_MESSAGE)}
    assert len(mailbox["verify"]) == sent_before + 1  # only the genuinely unverified account


def test_resend_is_capped_per_account_per_hour(client, mailbox):
    signup(client)
    for _ in range(6):
        client.post("/api/v1/auth/resend-verification", json={"email": "new@example.com"})
    assert len(mailbox["verify"]) == 3


def test_duplicate_signup_looks_identical_and_notifies_the_real_owner(client, mailbox):
    register_org(client, email="owner@example.com", organization_name="Owner Org")

    fresh = signup(client, email="fresh@example.com", org="Fresh Org")
    duplicate = signup(client, email="owner@example.com", org="Different Org")
    fresh_recipients = [to for to, _ in mailbox["verify"] if to != "owner@example.com"]

    assert (fresh.status_code, fresh.json()) == (duplicate.status_code, duplicate.json())
    assert mailbox["notice"] == ["owner@example.com"]
    assert fresh_recipients == ["fresh@example.com"]


def test_existing_account_notices_are_rate_limited_per_address(client, mailbox):
    register_org(client, email="owner@example.com", organization_name="Owner Org")
    for i in range(3):
        signup(client, email="owner@example.com", org=f"Spam {i}")
    assert mailbox["notice"] == ["owner@example.com"]


def test_signing_up_with_someone_elses_email_does_not_grant_access(client, mailbox, db):
    signup(client, email="victim@example.com", password="AttackerChosen1!")
    # The attacker can't verify (link goes to the victim), so cannot sign in.
    assert login(client, "victim@example.com", "AttackerChosen1!").status_code == 403
    assert db.query(User).filter(User.email == "victim@example.com").one().email_verified_at is None


def test_completing_a_password_reset_also_verifies_the_email(client, mailbox, monkeypatch):
    signup(client, email="user@example.com")
    links = []
    monkeypatch.setattr(
        MailService, "send_password_reset", lambda self, to, link, minutes: links.append(link) or True
    )
    monkeypatch.setattr(MailService, "send_password_changed_notice", lambda self, to: True)

    client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    client.post("/api/v1/auth/reset-password", json={
        "token": token_from(links[0]), "new_password": "BrandNewPassw0rd!",
    })

    assert login(client, "user@example.com", "BrandNewPassw0rd!").status_code == 200


def test_verify_endpoint_is_rate_limited(client):
    statuses = [verify(client, "x" * 43).status_code for _ in range(12)]
    assert statuses[:10] == [400] * 10 and statuses[10:] == [429, 429]


def test_register_is_rate_limited_per_ip(client, mailbox):
    statuses = [signup(client, email=f"u{i}@example.com", org=f"Org {i}").status_code for i in range(7)]
    assert statuses[:5] == [202] * 5 and statuses[5:] == [429, 429]
