"""Branded transactional email templates.

Emails can't use the app's CSS, so everything is table-based with inline
styles (the only thing that renders consistently across Gmail, Outlook and
Apple Mail). Colours and type follow the ScanHive UI: violet primary, zinc
neutrals, and the dark hex mark on a dark header band.

All caller-supplied text is HTML-escaped here; templates never interpolate raw
values into markup.
"""
import html
import re
from dataclasses import dataclass

PRIMARY = "#7c3aed"
PRIMARY_DARK = "#6d28d9"
HEADER_BG = "#0d0b14"
TEXT = "#18181b"
TEXT_BODY = "#3f3f46"
MUTED = "#71717a"
BORDER = "#e4e4e7"
PAGE_BG = "#f4f4f5"
NOTE_BG = "#f5f3ff"
NOTE_BORDER = "#ddd6fe"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

LOGO_CID = "scanhive-logo"
_BOLD = re.compile(r"\*\*(.+?)\*\*")


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


def _inline(value: str) -> str:
    """Escape, then turn **bold** into <strong>."""
    return _BOLD.sub(r"<strong>\1</strong>", html.escape(value, quote=True))


def _plain(value: str) -> str:
    return _BOLD.sub(r"\1", value)


def render_email(
    *,
    subject: str,
    preheader: str,
    heading: str,
    paragraphs: list[str],
    button_label: str | None = None,
    button_url: str | None = None,
    note: str | None = None,
    footer: str = "If you didn't expect this email, you can safely ignore it.",
) -> RenderedEmail:
    body_html = "".join(
        f'<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:{TEXT_BODY};">{_inline(p)}</p>'
        for p in paragraphs
    )

    button_html = ""
    link_html = ""
    if button_label and button_url:
        safe_url = html.escape(button_url, quote=True)
        button_html = (
            '<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 24px;">'
            f'<tr><td align="center" bgcolor="{PRIMARY}" style="border-radius:8px;">'
            f'<a href="{safe_url}" target="_blank" '
            f'style="display:inline-block;padding:13px 28px;font-family:{FONT};font-size:15px;'
            f'font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;background:{PRIMARY};">'
            f"{html.escape(button_label)}</a></td></tr></table>"
        )
        link_html = (
            f'<p style="margin:0 0 20px;font-size:12px;line-height:1.6;color:{MUTED};">'
            "Button not working? Copy and paste this link into your browser:<br>"
            f'<a href="{safe_url}" target="_blank" style="color:{PRIMARY};word-break:break-all;">'
            f"{safe_url}</a></p>"
        )

    note_html = ""
    if note:
        note_html = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:0 0 8px;"><tr><td style="background:{NOTE_BG};border:1px solid {NOTE_BORDER};'
            f'border-radius:8px;padding:12px 14px;font-size:13px;line-height:1.55;color:{TEXT_BODY};">'
            f"{_inline(note)}</td></tr></table>"
        )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{html.escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background:{PAGE_BG};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{PAGE_BG};">{html.escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAGE_BG};">
<tr><td align="center" style="padding:32px 16px;">
  <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:560px;">
    <tr><td style="background:{HEADER_BG};border-radius:12px 12px 0 0;padding:20px 28px;border-bottom:3px solid {PRIMARY};">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        <td style="vertical-align:middle;"><img src="cid:{LOGO_CID}" width="36" height="36" alt="" style="display:block;border:0;border-radius:8px;"></td>
        <td style="vertical-align:middle;padding-left:12px;font-family:{FONT};font-size:20px;font-weight:700;letter-spacing:-0.2px;color:#ffffff;">ScanHive</td>
      </tr></table>
    </td></tr>
    <tr><td style="background:#ffffff;border:1px solid {BORDER};border-top:0;border-radius:0 0 12px 12px;padding:32px 28px 28px;font-family:{FONT};">
      <h1 style="margin:0 0 16px;font-size:22px;line-height:1.3;font-weight:700;color:{TEXT};">{html.escape(heading)}</h1>
      {body_html}
      {button_html}
      {link_html}
      {note_html}
    </td></tr>
    <tr><td style="padding:20px 8px 0;text-align:center;font-family:{FONT};font-size:12px;line-height:1.6;color:{MUTED};">
      {html.escape(footer)}<br>
      Sent by ScanHive &middot; Please don't reply to this automated message.
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>"""

    text_parts = [heading, ""]
    text_parts += [f"{_plain(p)}\n" for p in paragraphs]
    if button_label and button_url:
        text_parts.append(f"{button_label}:\n{button_url}\n")
    if note:
        text_parts.append(f"{_plain(note)}\n")
    text_parts += ["--", footer, "Sent by ScanHive. Please don't reply to this automated message."]

    return RenderedEmail(subject=subject, text="\n".join(text_parts), html=page)


# ---- the individual emails -------------------------------------------------

def invitation(organization_name: str, invited_by_email: str, invite_link: str, expiry_days: int) -> RenderedEmail:
    return render_email(
        subject=f"You're invited to join {organization_name} on ScanHive",
        preheader=f"{invited_by_email} invited you to {organization_name}.",
        heading="You're invited to ScanHive",
        paragraphs=[
            f"{invited_by_email} invited you to join **{organization_name}** on ScanHive, "
            "where your team consolidates and triages security scan results.",
            "Accept the invitation to set your name and password and get started.",
        ],
        button_label="Accept invitation",
        button_url=invite_link,
        note=f"This invitation expires in **{expiry_days} days** and can only be used once.",
    )


def email_verification(verify_link: str, expiry_hours: int) -> RenderedEmail:
    return render_email(
        subject="Verify your email address for ScanHive",
        preheader="Confirm your email to finish creating your ScanHive account.",
        heading="Verify your email address",
        paragraphs=[
            "Welcome to ScanHive! Confirm that this is your email address to finish creating your account.",
        ],
        button_label="Verify my email",
        button_url=verify_link,
        note=f"This link expires in **{expiry_hours} hours** and can only be used once.",
        footer="If you didn't create a ScanHive account, you can safely ignore this email.",
    )


def password_reset(reset_link: str, expiry_minutes: int) -> RenderedEmail:
    return render_email(
        subject="Reset your ScanHive password",
        preheader="Use this link to choose a new ScanHive password.",
        heading="Reset your password",
        paragraphs=[
            "We received a request to reset the password for your ScanHive account. "
            "Click the button below to choose a new one.",
        ],
        button_label="Choose a new password",
        button_url=reset_link,
        note=(
            f"This link expires in **{expiry_minutes} minutes** and works once. "
            "Using it will sign you out of every device."
        ),
        footer="If you didn't request this, ignore this email — your password won't change.",
    )


def password_changed() -> RenderedEmail:
    return render_email(
        subject="Your ScanHive password was changed",
        preheader="Your password was just changed and all sessions were signed out.",
        heading="Your password was changed",
        paragraphs=[
            "The password for your ScanHive account was just changed, and every existing session was signed out.",
            "If this was you, no further action is needed.",
        ],
        note="**Wasn't you?** Reset your password again straight away and let your administrator know.",
        footer="You're receiving this security notice because of a change to your account.",
    )


def existing_account_notice(sign_in_link: str) -> RenderedEmail:
    return render_email(
        subject="Someone tried to create a ScanHive account with your email",
        preheader="This email already has a ScanHive account.",
        heading="You already have an account",
        paragraphs=[
            "Someone just tried to sign up for ScanHive with this email address, but it already has an account.",
            "If that was you, sign in instead. If you've forgotten your password, use "
            "“Forgot password?” on the sign-in page.",
        ],
        button_label="Go to sign in",
        button_url=sign_in_link,
        footer="If this wasn't you, you can safely ignore this email — your account was not changed.",
    )


def smtp_test() -> RenderedEmail:
    return render_email(
        subject="ScanHive SMTP test",
        preheader="Your ScanHive email settings work.",
        heading="Email is working",
        paragraphs=["If you can read this, ScanHive can send email with your current SMTP settings."],
        footer="This was a manual test message.",
    )
