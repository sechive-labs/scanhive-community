import logging
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from app.core.config import settings
from app.services import email_templates
from app.services.email_templates import LOGO_CID, RenderedEmail

logger = logging.getLogger(__name__)

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "email" / "logo.png"


class MailService:

    @property
    def is_configured(self) -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)

    def send(
        self, to_email: str, subject: str, text_body: str, html_body: str, *, raise_errors: bool = False,
    ) -> bool:
        if not self.is_configured:
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = (
            f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            if settings.SMTP_FROM_NAME
            else settings.SMTP_FROM_EMAIL
        )
        message["To"] = to_email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        # Embed the logo as an inline attachment referenced by cid: -- works
        # without hosting the image anywhere or relying on remote-image loading.
        if f"cid:{LOGO_CID}" in html_body and LOGO_PATH.exists():
            message.get_payload()[1].add_related(
                LOGO_PATH.read_bytes(), maintype="image", subtype="png", cid=f"<{LOGO_CID}>",
                filename="scanhive-logo.png", disposition="inline",
            )

        try:
            self._deliver(message)
            return True
        except Exception:
            if raise_errors:
                raise
            logger.exception("Failed to send email to %s", to_email)
            return False

    def send_rendered(self, to_email: str, email: RenderedEmail, *, raise_errors: bool = False) -> bool:
        return self.send(to_email, email.subject, email.text, email.html, raise_errors=raise_errors)

    @staticmethod
    def _deliver(message: EmailMessage) -> None:
        # Always verify the server certificate: the default smtplib context
        # doesn't, which would let a network attacker read or alter mail
        # (including reset/verification links) and capture the SMTP password.
        context = ssl.create_default_context()

        if settings.SMTP_PORT == 465:
            # Implicit TLS (the usual port-465 setup).
            client = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10, context=context)
        else:
            client = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)

        with client:
            if settings.SMTP_PORT != 465 and settings.SMTP_USE_TLS:
                client.starttls(context=context)
            if settings.SMTP_USERNAME:
                client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            client.send_message(message)

    def send_invitation(
        self,
        to_email: str,
        organization_name: str,
        invited_by_email: str,
        invite_link: str,
        expiry_days: int,
    ) -> bool:
        return self.send_rendered(
            to_email, email_templates.invitation(organization_name, invited_by_email, invite_link, expiry_days),
        )

    def send_password_reset(self, to_email: str, reset_link: str, expiry_minutes: int) -> bool:
        return self.send_rendered(to_email, email_templates.password_reset(reset_link, expiry_minutes))

    def send_password_changed_notice(self, to_email: str) -> bool:
        return self.send_rendered(to_email, email_templates.password_changed())

    def send_email_verification(self, to_email: str, verify_link: str, expiry_hours: int) -> bool:
        return self.send_rendered(to_email, email_templates.email_verification(verify_link, expiry_hours))

    def send_existing_account_notice(self, to_email: str, sign_in_link: str) -> bool:
        return self.send_rendered(to_email, email_templates.existing_account_notice(sign_in_link))
