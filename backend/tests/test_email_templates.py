from email import message_from_bytes, policy

from app.services import email_templates as t
from app.services.mail_service import MailService


def test_button_and_fallback_link_are_present_and_escaped():
    email = t.password_reset('https://x.example/reset#token=a"b<c>', 30)
    assert 'href="https://x.example/reset#token=a&quot;b&lt;c&gt;"' in email.html
    assert email.html.count("https://x.example/reset#token=a&quot;b&lt;c&gt;") >= 2  # button + copy-paste link
    assert "https://x.example/reset#token=a\"b<c>" in email.text


def test_user_controlled_values_cannot_inject_markup():
    email = t.invitation("<img src=x onerror=alert(1)>", '"><script>1</script>@evil', "https://x.example/i", 7)
    assert "<img src=x" not in email.html and "<script>" not in email.html
    assert "&lt;img" in email.html


def test_bold_markup_is_html_in_html_and_stripped_in_text():
    email = t.email_verification("https://x.example/v", 24)
    assert "<strong>24 hours</strong>" in email.html
    assert "**" not in email.text and "24 hours" in email.text


def test_every_email_has_branding_preheader_and_plain_text_part():
    emails = [
        t.invitation("Org", "a@example.com", "https://x.example", 7),
        t.email_verification("https://x.example", 24),
        t.password_reset("https://x.example", 30),
        t.password_changed(),
        t.existing_account_notice("https://x.example"),
        t.smtp_test(),
    ]
    for email in emails:
        assert "ScanHive" in email.html and "cid:scanhive-logo" in email.html
        assert "#7c3aed" in email.html          # brand primary
        assert email.text.strip() and "<" not in email.text.replace("<3", "")
        assert email.subject


def test_logo_is_attached_inline_so_it_renders_without_remote_images(monkeypatch):
    sent = []
    monkeypatch.setattr(MailService, "is_configured", property(lambda self: True))
    monkeypatch.setattr(MailService, "_deliver", staticmethod(lambda message: sent.append(message)))

    MailService().send_password_reset("to@example.com", "https://x.example/reset", 30)

    parsed = message_from_bytes(sent[0].as_bytes(), policy=policy.default)
    types = [part.get_content_type() for part in parsed.walk()]
    assert "text/plain" in types and "text/html" in types and "image/png" in types
    logo = next(p for p in parsed.walk() if p.get_content_type() == "image/png")
    assert logo["Content-ID"] == "<scanhive-logo>"
