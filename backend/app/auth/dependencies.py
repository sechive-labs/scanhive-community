import calendar

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active or not user.organization.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    if settings.EMAIL_VERIFICATION_REQUIRED and user.email_verified_at is None:
        raise HTTPException(status_code=401, detail="Email address not verified")

    # A password reset invalidates every session issued before it.
    if user.password_changed_at is not None:
        issued_at = payload.get("iat")
        changed_at = calendar.timegm(user.password_changed_at.utctimetuple())
        if not isinstance(issued_at, (int, float)) or issued_at <= changed_at:
            raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    return get_user_from_token(credentials.credentials, db)


def get_scan_uploader(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    if api_key:
        from app.services.api_key_service import ApiKeyService

        user = ApiKeyService(db).authenticate(api_key)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return user
    if credentials:
        return get_user_from_token(credentials.credentials, db)
    raise HTTPException(status_code=401, detail="Authentication required")
