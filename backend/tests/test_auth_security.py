import time

import pytest

from app.core.security import verify_password
from app.services import auth_service
from app.services.mail_service import MailService
from tests.conftest import auth_headers, create_user_with_role, register_org


def login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def signup(client, **overrides):
    body = {
        "organization_name": "Sec Org", "email": "sec@example.com",
        "first_name": "S", "last_name": "E", "password": "Str0ngPassw0rd!",
    }
    body.update(overrides)
    return client.post("/api/v1/auth/register", json=body)


# ---- password policy -------------------------------------------------------

@pytest.mark.parametrize("password,reason", [
    ("short", "too short"),
    ("password123", "common"),
    ("PASSWORD", "common, case-insensitive"),
    ("        ", "blank"),
    ("a" * 73, "longer than bcrypt's 72 bytes"),
    ("é" * 40, "72+ bytes once UTF-8 encoded"),
    ("sec@example.com", "the email itself"),
])
def test_weak_or_unhashable_passwords_are_rejected_at_signup(client, password, reason):
    assert signup(client, password=password).status_code == 422, reason


def test_password_containing_the_email_local_part_is_rejected(client):
    assert signup(client, email="johnsmith@example.com", password="xxJohnSmithxx-99").status_code == 422


def test_72_byte_password_is_accepted_and_fully_significant(client):
    password = "aB3$" * 18  # exactly 72 bytes
    assert signup(client, password=password).status_code == 202


def test_password_policy_also_applies_to_invitation_acceptance(client):
    admin = register_org(client)
    invite = client.post(
        "/api/v1/iam/invitations", json={"email": "invitee@example.com", "role_ids": []},
        headers=auth_headers(admin),
    ).json()
    response = client.post(
        f"/api/v1/auth/invitations/{invite['token']}/accept",
        json={"first_name": "I", "last_name": "N", "password": "password123"},
    )
    assert response.status_code == 422


def test_invited_users_are_verified_by_the_invitation_itself(client):
    admin = register_org(client)
    token = create_user_with_role(client, admin, role_name=None, email="invitee@example.com")
    assert client.get("/api/v1/iam/profile", headers=auth_headers(token)).status_code == 200
    assert login(client, "invitee@example.com", "Password123!").status_code == 200


# ---- input hardening -------------------------------------------------------

@pytest.mark.parametrize("field", ["organization_name", "first_name", "last_name"])
def test_markup_in_names_is_rejected(client, field):
    assert signup(client, **{field: "<script>alert(1)</script>"}).status_code == 422


def test_invitation_email_html_escapes_user_controlled_values(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        MailService, "send",
        lambda self, to, subject, text, html_body, **kw: captured.update(html=html_body) or True,
    )
    MailService().send_invitation(
        "to@example.com", '<img src=x onerror=alert(1)>', 'a"><b>@evil.com',
        'https://x/"><script>1</script>', 7,
    )
    # (the template's own logo <img> is expected; the injected one is not)
    assert "<img src=x" not in captured["html"]
    assert "onerror=" not in captured["html"].replace("&lt;img src=x onerror=", "")
    assert "<script>" not in captured["html"]
    assert "&lt;img" in captured["html"]


def test_malformed_email_is_rejected(client):
    assert login(client, "not-an-email", "whatever").status_code == 422
    assert signup(client, email="a@b").status_code == 422


# ---- sign-in: enumeration & timing ----------------------------------------

def test_unknown_email_and_wrong_password_are_indistinguishable(client):
    register_org(client, email="real@example.com", password="Str0ngPassw0rd!")

    wrong_pw = login(client, "real@example.com", "WrongPassword1!")
    unknown = login(client, "ghost@example.com", "WrongPassword1!")

    assert (wrong_pw.status_code, wrong_pw.json()) == (unknown.status_code, unknown.json()) == (
        401, {"detail": "Invalid credentials"},
    )


def test_bcrypt_verification_runs_even_when_the_email_is_unknown(client, monkeypatch):
    calls = []
    real = auth_service.verify_password
    monkeypatch.setattr(auth_service, "verify_password", lambda p, h: calls.append(h) or real(p, h))

    login(client, "ghost@example.com", "WrongPassword1!")
    assert len(calls) == 1, "unknown accounts must cost the same bcrypt work as known ones"


def test_disabled_account_state_is_only_revealed_after_the_correct_password(client, db):
    from app.models.user import User

    register_org(client, email="off@example.com", password="Str0ngPassw0rd!")
    db.query(User).filter(User.email == "off@example.com").one().is_active = False
    db.commit()

    assert login(client, "off@example.com", "WrongPassword1!").status_code == 401
    disabled = login(client, "off@example.com", "Str0ngPassw0rd!")
    assert disabled.status_code == 403


def test_email_is_case_insensitive_for_signin(client):
    register_org(client, email="Mixed@Example.com", password="Str0ngPassw0rd!")
    assert login(client, "mixed@example.COM", "Str0ngPassw0rd!").status_code == 200


# ---- sign-in: brute force --------------------------------------------------

def test_repeated_failures_lock_that_ip_email_pair(client):
    register_org(client, email="victim@example.com", password="Str0ngPassw0rd!")

    statuses = [login(client, "victim@example.com", f"Guess{i}Password!").status_code for i in range(7)]
    assert statuses[:5] == [401] * 5
    assert statuses[5:] == [429, 429]

    # ...and the lock also blocks the *correct* password, so guessing can't win.
    blocked = login(client, "victim@example.com", "Str0ngPassw0rd!")
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_lockout_is_per_email_so_one_target_does_not_lock_others(client):
    register_org(client, email="a@example.com", password="Str0ngPassw0rd!", organization_name="Org A")
    register_org(client, email="b@example.com", password="Str0ngPassw0rd!", organization_name="Org B")

    for i in range(5):
        login(client, "a@example.com", f"Guess{i}Password!")

    assert login(client, "a@example.com", "Str0ngPassw0rd!").status_code == 429
    assert login(client, "b@example.com", "Str0ngPassw0rd!").status_code == 200


def test_successful_login_resets_the_failure_counter(client):
    register_org(client, email="user@example.com", password="Str0ngPassw0rd!")
    for i in range(4):
        login(client, "user@example.com", f"Guess{i}Password!")
    assert login(client, "user@example.com", "Str0ngPassw0rd!").status_code == 200
    for i in range(4):
        assert login(client, "user@example.com", f"Again{i}Password!").status_code == 401


def test_per_ip_login_ceiling_stops_password_spraying(client):
    statuses = [login(client, f"user{i}@example.com", "Str0ngPassw0rd!").status_code for i in range(32)]
    assert statuses[:30] == [401] * 30
    assert statuses[30:] == [429, 429]


def test_auth_responses_are_never_cacheable_even_on_errors(client):
    response = login(client, "ghost@example.com", "x" * 10)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def test_api_responses_carry_baseline_security_headers(client):
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


# ---- tokens ---------------------------------------------------------------

def test_tampered_or_foreign_tokens_are_rejected(client):
    token = register_org(client)
    header, payload, signature = token.split(".")

    assert client.get("/api/v1/iam/profile", headers=auth_headers(f"{header}.{payload}.{signature[:-2]}xx")).status_code == 401
    assert client.get("/api/v1/iam/profile", headers=auth_headers("not.a.jwt")).status_code == 401


def test_alg_none_token_is_rejected(client):
    import base64
    import json

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    forged = f'{b64({"alg": "none", "typ": "JWT"})}.{b64({"sub": "admin@example.com", "exp": 9999999999})}.'
    register_org(client, email="admin@example.com")
    assert client.get("/api/v1/iam/profile", headers=auth_headers(forged)).status_code == 401


def test_token_signed_with_another_secret_is_rejected(client):
    from jose import jwt

    register_org(client, email="admin@example.com")
    forged = jwt.encode({"sub": "admin@example.com", "exp": 9999999999}, "attacker-secret", algorithm="HS256")
    assert client.get("/api/v1/iam/profile", headers=auth_headers(forged)).status_code == 401


def test_expired_token_is_rejected(client):
    from datetime import datetime, timedelta, UTC
    from jose import jwt

    from app.core.config import settings

    register_org(client, email="admin@example.com")
    expired = jwt.encode(
        {"sub": "admin@example.com", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )
    assert client.get("/api/v1/iam/profile", headers=auth_headers(expired)).status_code == 401


def test_missing_authorization_header_is_rejected(client):
    assert client.get("/api/v1/iam/profile").status_code in (401, 403)


def test_token_of_a_user_who_is_later_disabled_stops_working(client, db):
    from app.models.user import User

    token = register_org(client, email="admin@example.com")
    db.query(User).filter(User.email == "admin@example.com").one().is_active = False
    db.commit()
    assert client.get("/api/v1/iam/profile", headers=auth_headers(token)).status_code == 401


def test_password_hashes_are_salted_bcrypt_and_never_returned(client, db):
    from app.models.user import User

    token = register_org(client, email="a@example.com", password="Str0ngPassw0rd!", organization_name="Org A")
    register_org(client, email="b@example.com", password="Str0ngPassw0rd!", organization_name="Org B")

    a, b = (db.query(User).filter(User.email == e).one().password_hash for e in ("a@example.com", "b@example.com"))
    assert a.startswith("$2") and a != b and "Str0ngPassw0rd!" not in a
    assert verify_password("Str0ngPassw0rd!", a)

    profile = client.get("/api/v1/iam/profile", headers=auth_headers(token)).text
    assert "password" not in profile.lower()


def test_sql_injection_in_email_field_is_inert(client):
    register_org(client, email="real@example.com")
    response = login(client, "x'@example.com", "' OR '1'='1")
    assert response.status_code in (401, 422)


def test_weak_password_error_names_the_password_field_with_a_helpful_message(client):
    common = signup(client, password="password123").json()["detail"][0]
    assert common["loc"] == ["body", "password"]
    assert "too common" in common["msg"] and "passphrase" in common["msg"]

    contains_email = signup(client, email="johnsmith@example.com", password="xxJohnSmithxx-99").json()["detail"][0]
    assert contains_email["loc"] == ["body", "password"]
    assert "email" in contains_email["msg"]


# ---- SMTP transport --------------------------------------------------------

class _FakeSMTP:
    instances: list = []

    def __init__(self, host, port, timeout=None, context=None):
        self.kind = type(self).__name__
        self.context, self.calls = context, []
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append(("starttls", context))

    def login(self, user, password):
        self.calls.append(("login", user))

    def send_message(self, message):
        self.calls.append(("send", message["To"]))


class _FakeSMTPSSL(_FakeSMTP):
    pass


@pytest.fixture
def smtp(monkeypatch):
    import ssl

    from app.core.config import settings

    _FakeSMTP.instances = []
    monkeypatch.setattr("smtplib.SMTP", _FakeSMTP)
    monkeypatch.setattr("smtplib.SMTP_SSL", _FakeSMTPSSL)
    for name, value in {"SMTP_HOST": "smtp.example.com", "SMTP_FROM_EMAIL": "noreply@example.com",
                        "SMTP_USERNAME": "noreply@example.com", "SMTP_PASSWORD": "pw"}.items():
        monkeypatch.setattr(settings, name, value)
    return settings, ssl


def test_starttls_verifies_the_server_certificate(smtp, monkeypatch):
    settings, ssl = smtp
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)

    assert MailService().send("to@example.com", "s", "t", "<p>h</p>") is True

    client = _FakeSMTP.instances[0]
    (_, context), = [c for c in client.calls if c[0] == "starttls"]
    assert client.kind == "_FakeSMTP"
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True


def test_port_465_uses_implicit_tls_with_certificate_verification(smtp, monkeypatch):
    settings, ssl = smtp
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)

    assert MailService().send("to@example.com", "s", "t", "<p>h</p>") is True

    client = _FakeSMTP.instances[0]
    assert client.kind == "_FakeSMTPSSL"
    assert not [c for c in client.calls if c[0] == "starttls"]
    assert client.context.verify_mode == ssl.CERT_REQUIRED and client.context.check_hostname is True
    assert ("login", "noreply@example.com") in client.calls


def test_send_errors_can_be_surfaced_for_diagnostics(smtp, monkeypatch):
    settings, _ = smtp
    monkeypatch.setattr(settings, "SMTP_PORT", 587)

    def boom(self, message):
        raise ConnectionError("nope")

    monkeypatch.setattr(_FakeSMTP, "send_message", boom)
    assert MailService().send("to@example.com", "s", "t", "h") is False
    with pytest.raises(ConnectionError):
        MailService().send("to@example.com", "s", "t", "h", raise_errors=True)
