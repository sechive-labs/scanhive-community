import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_URL: str = "http://localhost:5173"
    UPLOAD_DIR: str = "app/uploads"

    # Email verification for new accounts. Turn off only if the install has no
    # way to send mail and you trust everyone who can reach the sign-up page.
    EMAIL_VERIFICATION_REQUIRED: bool = True
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    EMAIL_VERIFICATION_MAX_PER_HOUR: int = 3
    # Like PASSWORD_RESET_LOG_LINK: write the verification link to the server
    # log when mail can't be delivered. Off by default.
    EMAIL_VERIFICATION_LOG_LINK: bool = False

    # Password reset. Tokens are single-use, stored hashed, and short-lived.
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    # Max reset emails issued per account per hour (extra requests are
    # silently ignored so an attacker can't mail-bomb a victim).
    PASSWORD_RESET_MAX_PER_HOUR: int = 3
    # Self-hosted installs without SMTP can't email the link; when true the
    # link is written to the server log instead. Off by default because
    # anyone who can read the logs could then take over any account.
    PASSWORD_RESET_LOG_LINK: bool = False
    # Only enable when the API sits behind a proxy that overwrites
    # X-Forwarded-For / X-Real-IP (the bundled nginx does); otherwise clients
    # could spoof their IP to dodge per-IP rate limits.
    TRUST_PROXY_HEADERS: bool = False

    # Comma-separated list of extra origins allowed to call the API (e.g. a
    # public domain or IP the dashboard is served from). localhost, 127.0.0.1
    # and private LAN ranges are already allowed and don't need to be listed.
    EXTRA_CORS_ORIGINS: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "ScanHive"
    SMTP_USE_TLS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


def _load_or_generate_secret_key() -> str:
    """Persist a random JWT signing key across restarts so no manual setup is required."""
    key_path = Path("/data/secret_key")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_text().strip()
    generated = secrets.token_hex(32)
    key_path.write_text(generated)
    return generated


settings = Settings()
if not settings.SECRET_KEY:
    settings.SECRET_KEY = _load_or_generate_secret_key()
