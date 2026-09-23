"""Send a test email with the configured SMTP settings and print any error.

    docker compose exec backend python -m app.scripts.send_test_email you@example.com
"""
import sys

from app.core.config import settings
from app.services import email_templates
from app.services.mail_service import MailService


def main() -> int:
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        print("usage: python -m app.scripts.send_test_email recipient@example.com")
        return 2

    mail = MailService()
    if not mail.is_configured:
        print("SMTP is not configured: set SMTP_HOST and SMTP_FROM_EMAIL in backend/.env")
        return 1

    print(f"Sending via {settings.SMTP_HOST}:{settings.SMTP_PORT} as {settings.SMTP_USERNAME or '(no login)'} ...")
    try:
        mail.send_rendered(sys.argv[1], email_templates.smtp_test(), raise_errors=True)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1

    print("OK: message accepted by the SMTP server. Check the inbox (and spam).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
