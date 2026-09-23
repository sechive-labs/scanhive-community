import hashlib
import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User

logger = logging.getLogger(__name__)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InvalidResetTokenError(Exception):
    pass


class PasswordResetService:

    def __init__(self, db: Session):
        self.db = db

    def request_reset(self, email: str, requested_ip: str | None) -> tuple[User, str] | None:
        """Creates a reset token for the account, or returns None.

        None is returned for unknown emails, disabled accounts/orgs, and
        accounts over their hourly quota. The caller must treat every case
        identically so responses never reveal whether an email is registered.
        """
        user = self.db.query(User).filter(User.email == email.strip().lower()).first()
        if user is None or not user.is_active or not user.organization.is_active:
            return None

        now = datetime.utcnow()
        recent = (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.created_at > now - timedelta(hours=1),
            )
            .count()
        )
        if recent >= settings.PASSWORD_RESET_MAX_PER_HOUR:
            logger.warning("Password reset quota reached for user id=%s", user.id)
            return None

        # Only the newest link is ever valid.
        self._invalidate_outstanding(user.id, now)

        token = secrets.token_urlsafe(32)
        self.db.add(PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
            requested_ip=requested_ip,
        ))
        self.db.commit()
        return user, token

    def reset_password(self, token: str, new_password: str) -> User:
        now = datetime.utcnow()
        record = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == hash_token(token))
            .first()
        )
        # One error for every failure mode: unknown, used, or expired.
        if record is None or record.used_at is not None or record.expires_at <= now:
            raise InvalidResetTokenError()

        user = self.db.get(User, record.user_id)
        if user is None or not user.is_active or not user.organization.is_active:
            raise InvalidResetTokenError()

        user.password_hash = hash_password(new_password)
        # Kills every session token issued before now.
        user.password_changed_at = now
        # Receiving the reset link proves control of the mailbox.
        user.email_verified_at = user.email_verified_at or now
        record.used_at = now
        self._invalidate_outstanding(user.id, now)
        self.db.commit()
        return user

    def _invalidate_outstanding(self, user_id: int, now: datetime) -> None:
        (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.user_id == user_id, PasswordResetToken.used_at.is_(None))
            .update({PasswordResetToken.used_at: now}, synchronize_session=False)
        )
