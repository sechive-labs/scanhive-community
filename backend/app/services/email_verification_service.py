import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_verification_token import EmailVerificationToken
from app.models.user import User
from app.services.password_reset_service import hash_token

logger = logging.getLogger(__name__)


class InvalidVerificationTokenError(Exception):
    pass


class EmailVerificationService:

    def __init__(self, db: Session):
        self.db = db

    def issue(self, user: User) -> str | None:
        """Creates a fresh verification token, or None when the account is
        already verified or over its hourly quota. Callers must respond
        identically either way."""
        if user.email_verified_at is not None:
            return None

        now = datetime.utcnow()
        recent = (
            self.db.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.user_id == user.id,
                EmailVerificationToken.created_at > now - timedelta(hours=1),
            )
            .count()
        )
        if recent >= settings.EMAIL_VERIFICATION_MAX_PER_HOUR:
            logger.warning("Email verification quota reached for user id=%s", user.id)
            return None

        # Only the newest link is ever valid.
        (
            self.db.query(EmailVerificationToken)
            .filter(EmailVerificationToken.user_id == user.id, EmailVerificationToken.used_at.is_(None))
            .update({EmailVerificationToken.used_at: now}, synchronize_session=False)
        )

        token = secrets.token_urlsafe(32)
        self.db.add(EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS),
        ))
        self.db.commit()
        return token

    def verify(self, token: str) -> User:
        now = datetime.utcnow()
        record = (
            self.db.query(EmailVerificationToken)
            .filter(EmailVerificationToken.token_hash == hash_token(token))
            .first()
        )
        if record is None or record.used_at is not None or record.expires_at <= now:
            raise InvalidVerificationTokenError()

        user = self.db.get(User, record.user_id)
        if user is None:
            raise InvalidVerificationTokenError()

        user.email_verified_at = user.email_verified_at or now
        record.used_at = now
        self.db.commit()
        return user
