"""Render every transactional email to HTML files you can open in a browser.

    python -m app.scripts.preview_emails [output_dir]      (default: ./email-previews)
"""
import base64
import sys
from pathlib import Path

from app.services import email_templates as t
from app.services.mail_service import LOGO_PATH

SAMPLES = {
    "invitation": t.invitation("Example Corp", "alex@example.com", "https://scanhive.example.com/accept-invite/abc123", 7),
    "email-verification": t.email_verification("https://scanhive.example.com/verify-email#token=abc123", 24),
    "password-reset": t.password_reset("https://scanhive.example.com/reset-password#token=abc123", 30),
    "password-changed": t.password_changed(),
    "existing-account": t.existing_account_notice("https://scanhive.example.com/login"),
    "smtp-test": t.smtp_test(),
}


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "email-previews")
    out.mkdir(parents=True, exist_ok=True)
    logo = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()
    for name, email in SAMPLES.items():
        # Browsers can't resolve cid: images, so inline the logo for previewing only.
        (out / f"{name}.html").write_text(email.html.replace(f"cid:{t.LOGO_CID}", logo), encoding="utf-8")
        (out / f"{name}.txt").write_text(email.text, encoding="utf-8")
    print(f"Wrote {len(SAMPLES)} previews to {out.resolve()}")


if __name__ == "__main__":
    main()
