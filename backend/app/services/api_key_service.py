from datetime import datetime, timedelta
import hashlib
import secrets

from sqlalchemy.orm import Session

from sqlalchemy import func

from app.models.api_key import ApiKey


class DuplicateApiKeyNameError(Exception):
    pass


class ApiKeyService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def create(self, user_id: int, name: str) -> tuple[ApiKey, str]:
        name = name.strip()

        existing = (
            self.db.query(ApiKey)
            .filter(
                ApiKey.user_id == user_id,
                func.lower(ApiKey.name) == name.lower(),
            )
            .first()
        )
        if existing is not None:
            raise DuplicateApiKeyNameError("An API key with this name already exists")

        prefix = secrets.token_hex(4)
        plaintext = f"osk_{prefix}.{secrets.token_urlsafe(32)}"
        api_key = ApiKey(
            name=name,
            prefix=prefix,
            key_hash=self.hash_key(plaintext),
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(days=365),
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key, plaintext

    def list_for_user(self, user_id: int) -> list[ApiKey]:
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.user_id == user_id, ApiKey.revoked_at.is_(None))
            .order_by(ApiKey.created_at.desc())
            .all()
        )

    def regenerate(self, user_id: int, key_id: int) -> tuple[ApiKey, str] | None:
        api_key = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .first()
        )
        if api_key is None:
            return None
        prefix = secrets.token_hex(4)
        plaintext = f"osk_{prefix}.{secrets.token_urlsafe(32)}"
        now = datetime.utcnow()
        api_key.prefix = prefix
        api_key.key_hash = self.hash_key(plaintext)
        api_key.created_at = now
        api_key.expires_at = now + timedelta(days=365)
        api_key.last_used_at = None
        api_key.revoked_at = None
        self.db.commit()
        self.db.refresh(api_key)
        return api_key, plaintext

    def delete(self, user_id: int, key_id: int) -> bool:
        api_key = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .first()
        )
        if api_key is None:
            return False
        self.db.delete(api_key)
        self.db.commit()
        return True

    def authenticate(self, plaintext: str):
        if not plaintext.startswith("osk_") or "." not in plaintext:
            return None
        prefix = plaintext[4:].split(".", 1)[0]
        api_key = (
            self.db.query(ApiKey)
            .filter(
                ApiKey.prefix == prefix,
                ApiKey.revoked_at.is_(None),
                ApiKey.expires_at > datetime.utcnow(),
            )
            .first()
        )
        if api_key is None or not secrets.compare_digest(
            api_key.key_hash,
            self.hash_key(plaintext),
        ):
            return None
        if not api_key.user.is_active or not api_key.user.organization.is_active:
            return None
        api_key.last_used_at = datetime.utcnow()
        self.db.commit()
        return api_key.user
