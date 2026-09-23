import secrets
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.invitation import Invitation
from app.models.role import Role
from app.models.user import User
from app.services.mail_service import MailService

INVITATION_EXPIRY_DAYS = 7


class InvitationNotFoundError(Exception):
    pass


class DuplicateInvitationEmailError(Exception):
    pass


class InvitationService:

    def __init__(self, db: Session):
        self.db = db

    def list_invitations(self, organization_id: int) -> list[Invitation]:
        return (
            self.db.query(Invitation)
            .filter(Invitation.organization_id == organization_id)
            .order_by(Invitation.created_at.desc())
            .all()
        )

    def create(self, organization_id: int, email: str, role_ids: list[int], invited_by: User) -> tuple[Invitation, bool]:
        normalized_email = email.strip().lower()

        if self.db.query(User.id).filter(User.email == normalized_email).first():
            raise DuplicateInvitationEmailError("A user with this email address already exists")

        roles = (
            self.db.query(Role)
            .filter(Role.id.in_(set(role_ids)), Role.organization_id == organization_id)
            .all()
            if role_ids
            else []
        )
        if len(roles) != len(set(role_ids)):
            raise ValueError("One or more roles do not exist")

        invitation = (
            self.db.query(Invitation)
            .filter(
                Invitation.organization_id == organization_id,
                Invitation.email == normalized_email,
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
            )
            .first()
        )
        if invitation is None:
            invitation = Invitation(organization_id=organization_id, email=normalized_email)
            self.db.add(invitation)

        invitation.token = secrets.token_urlsafe(32)
        invitation.invited_by = invited_by
        invitation.roles = roles
        invitation.expires_at = datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS)

        self.db.commit()
        self.db.refresh(invitation)

        invite_link = f"{settings.FRONTEND_URL.rstrip('/')}/accept-invite/{invitation.token}"
        email_sent = MailService().send_invitation(
            to_email=invitation.email,
            organization_name=invited_by.organization.name,
            invited_by_email=invited_by.email,
            invite_link=invite_link,
            expiry_days=INVITATION_EXPIRY_DAYS,
        )

        return invitation, email_sent

    def revoke(self, invitation_id: int, organization_id: int) -> Invitation:
        invitation = self.db.query(Invitation).filter(
            Invitation.id == invitation_id,
            Invitation.organization_id == organization_id,
        ).first()
        if invitation is None:
            raise InvitationNotFoundError("Invitation not found")

        invitation.revoked_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(invitation)
        return invitation

    def get_valid_by_token(self, token: str) -> Invitation | None:
        invitation = self.db.query(Invitation).filter(Invitation.token == token).first()
        if invitation is None or invitation.status != "pending":
            return None
        return invitation

    def accept(self, token: str, first_name: str, last_name: str, password: str) -> User:
        invitation = self.get_valid_by_token(token)
        if invitation is None:
            raise InvitationNotFoundError("Invitation not found or no longer valid")

        if self.db.query(User.id).filter(User.email == invitation.email).first():
            raise DuplicateInvitationEmailError("A user with this email address already exists")

        user = User(
            email=invitation.email,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            password_hash=hash_password(password),
            organization_id=invitation.organization_id,
            is_active=True,
            # The invitation link was delivered to this address, which proves it.
            email_verified_at=datetime.utcnow(),
        )
        user.roles = invitation.roles
        self.db.add(user)

        invitation.accepted_at = datetime.utcnow()

        try:
            self.db.commit()
        except IntegrityError as exc:
            # A concurrent request (double-submit, retry) may have accepted
            # this invitation, or registered this email, between the checks
            # above and this commit. The unique constraint on users.email is
            # the real guard; translate the race into the same clean error.
            self.db.rollback()
            raise DuplicateInvitationEmailError("A user with this email address already exists") from exc

        self.db.refresh(user)
        return user
