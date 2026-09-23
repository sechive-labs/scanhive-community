from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
import logging

from sqlalchemy.orm import Session

from app.db.session import get_db, translate_integrity_error

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    InvitationPreviewResponse,
    AcceptInvitationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app.core.config import settings
from app.core.rate_limit import (
    client_ip, enforce, enforce_blocked, forgot_password_limiter, reset_password_limiter,
    login_ip_limiter, login_failure_limiter, register_limiter, verify_email_limiter,
    resend_verification_limiter, existing_account_notice_limiter,
)
from app.services.mail_service import MailService
from app.services.password_reset_service import PasswordResetService, InvalidResetTokenError

from app.services.auth_service import AuthService, DisabledAccountError, DuplicateEmailError, EmailNotVerifiedError
from app.repositories.user_repository import UserRepository
from app.services.email_verification_service import EmailVerificationService, InvalidVerificationTokenError
from app.services.invitation_service import (
    InvitationService,
    InvitationNotFoundError,
    DuplicateInvitationEmailError,
)
from app.core.security import create_access_token

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

logger = logging.getLogger(__name__)


GENERIC_REGISTER_MESSAGE = (
    "Check your email to verify your address, then sign in. "
    "If you already have an account, you'll get an email about that instead."
)
GENERIC_RESEND_MESSAGE = (
    "If that account exists and isn't verified yet, a new verification link has been sent."
)


def _deliver_verification_link(email: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email#token={token}"
    mail = MailService()
    sent = mail.send_email_verification(
        email, link, settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
    ) if mail.is_configured else False
    if not sent:
        if settings.EMAIL_VERIFICATION_LOG_LINK:
            logger.warning("Email verification link for %s: %s", email, link)
        else:
            logger.warning("Could not email a verification link to %s (SMTP unavailable).", email)


def _deliver_existing_account_notice(email: str) -> None:
    if existing_account_notice_limiter.check(email.lower()) is not None:
        return
    MailService().send_existing_account_notice(email, f"{settings.FRONTEND_URL.rstrip('/')}/login")


@router.post("/register", response_model=MessageResponse, status_code=202)
def register(
    request: RegisterRequest,
    http_request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    response.headers["Cache-Control"] = "no-store"
    enforce(register_limiter, client_ip(http_request))

    service = AuthService(db)

    try:
        with translate_integrity_error(db, "Organization name already exists"):
            user = service.register(
                email=request.email,
                first_name=request.first_name,
                last_name=request.last_name,
                password=request.password,
                organization_name=request.organization_name,
            )
    except DuplicateEmailError:
        # Same response as a fresh sign-up so the form can't be used to probe
        # which emails have accounts; the real owner is told by email.
        background_tasks.add_task(_deliver_existing_account_notice, request.email)
        return {"message": GENERIC_REGISTER_MESSAGE}

    if user.email_verified_at is None:
        token = EmailVerificationService(db).issue(user)
        if token is not None:
            background_tasks.add_task(_deliver_verification_link, user.email, token)

    return {"message": GENERIC_REGISTER_MESSAGE}


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(
    request: VerifyEmailRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    enforce(verify_email_limiter, client_ip(http_request))

    try:
        EmailVerificationService(db).verify(request.token)
    except InvalidVerificationTokenError:
        raise HTTPException(400, "This verification link is invalid or has expired.")

    return {"message": "Your email address is verified. You can now sign in."}


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(
    request: ResendVerificationRequest,
    http_request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    enforce(resend_verification_limiter, client_ip(http_request))

    user = UserRepository(db).get_by_email(request.email)
    if user is not None and user.is_active and user.organization.is_active:
        token = EmailVerificationService(db).issue(user)
        if token is not None:
            background_tasks.add_task(_deliver_verification_link, user.email, token)

    return {"message": GENERIC_RESEND_MESSAGE}


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    response.headers["Cache-Control"] = "no-store"
    ip = client_ip(http_request)
    failure_key = f"{ip}|{request.email.lower()}"

    enforce_blocked(login_failure_limiter, failure_key)
    enforce(login_ip_limiter, ip)

    service = AuthService(db)

    try:
        token = service.login(
            request.email,
            request.password
        )
    except DisabledAccountError as exc:
        login_failure_limiter.clear(failure_key)
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EmailNotVerifiedError as exc:
        login_failure_limiter.clear(failure_key)
        raise HTTPException(
            status_code=403,
            detail={"code": "email_not_verified", "message": str(exc)},
        ) from exc

    if not token:
        login_failure_limiter.hit(failure_key)
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    login_failure_limiter.clear(failure_key)
    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/invitations/{token}", response_model=InvitationPreviewResponse)
def preview_invitation(token: str, db: Session = Depends(get_db)):
    invitation = InvitationService(db).get_valid_by_token(token)
    if invitation is None:
        raise HTTPException(404, "Invitation not found or no longer valid")
    return {
        "organization_name": invitation.organization.name,
        "email": invitation.email,
    }


@router.post("/invitations/{token}/accept", response_model=TokenResponse)
def accept_invitation(
    token: str,
    request: AcceptInvitationRequest,
    db: Session = Depends(get_db),
):
    service = InvitationService(db)

    try:
        user = service.accept(
            token=token,
            first_name=request.first_name,
            last_name=request.last_name,
            password=request.password,
        )
    except InvitationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateInvitationEmailError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "access_token": create_access_token(user.email),
        "token_type": "bearer",
    }


GENERIC_FORGOT_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)


def _deliver_reset_link(email: str, token: str) -> None:
    # Runs after the response is sent so SMTP latency can't reveal whether
    # the address belongs to an account. The link uses a URL fragment, which
    # browsers never send to servers or in Referer headers.
    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password#token={token}"
    mail = MailService()
    if mail.is_configured:
        mail.send_password_reset(email, link, settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    elif settings.PASSWORD_RESET_LOG_LINK:
        logger.warning("SMTP not configured; password reset link for %s: %s", email, link)
    else:
        logger.warning(
            "Password reset requested for %s but SMTP is not configured; no email was sent.", email
        )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    ip = client_ip(http_request)
    enforce(forgot_password_limiter, ip)

    issued = PasswordResetService(db).request_reset(request.email, ip)
    if issued is not None:
        user, token = issued
        background_tasks.add_task(_deliver_reset_link, user.email, token)

    # Identical response whether or not the account exists.
    return {"message": GENERIC_FORGOT_MESSAGE}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    enforce(reset_password_limiter, client_ip(http_request))

    try:
        user = PasswordResetService(db).reset_password(request.token, request.new_password)
    except InvalidResetTokenError:
        raise HTTPException(400, "This password reset link is invalid or has expired.")

    background_tasks.add_task(MailService().send_password_changed_notice, user.email)
    return {"message": "Your password has been reset. You can now sign in."}
