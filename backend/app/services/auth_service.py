from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)

from app.repositories.user_repository import UserRepository
from app.services.organization_service import create_organization_with_admin

# Verified against when the email is unknown, so a failed sign-in costs the
# same bcrypt work whether or not the account exists (no timing oracle).
_DUMMY_HASH = hash_password("scanhive-timing-equalizer")


class DisabledAccountError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class EmailNotVerifiedError(Exception):
    pass


class AuthService:

    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def register(self, email, first_name, last_name, password, organization_name):
        """Creates an org + first admin. Returns the new user, or raises
        DuplicateEmailError (the API answers both cases identically)."""

        if self.repo.get_by_email(email):
            raise DuplicateEmailError("Email address already exists")

        _organization, user = create_organization_with_admin(
            self.repo.db,
            organization_name=organization_name,
            admin_email=email,
            admin_first_name=first_name,
            admin_last_name=last_name,
            admin_password_hash=hash_password(password),
        )
        if not settings.EMAIL_VERIFICATION_REQUIRED:
            user.email_verified_at = datetime.utcnow()

        self.repo.db.commit()
        self.repo.db.refresh(user)

        return user

    def login(self, email, password):

        user = self.repo.get_by_email(email)

        # Always run one bcrypt verification, then decide.
        password_ok = verify_password(
            password,
            user.password_hash if user else _DUMMY_HASH,
        )

        if not user or not password_ok:
            return None

        # Account state is only revealed to someone who proved the password.
        if not user.is_active:
            raise DisabledAccountError("User account is disabled. Please reach out to your administrator.")

        if not user.organization.is_active:
            return None

        if settings.EMAIL_VERIFICATION_REQUIRED and user.email_verified_at is None:
            raise EmailNotVerifiedError("Please verify your email address before signing in.")

        return create_access_token(user.email)
