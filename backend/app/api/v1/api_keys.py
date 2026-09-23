from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from app.services.api_key_service import ApiKeyService, DuplicateApiKeyNameError

router = APIRouter(prefix="/api/v1/api-keys", tags=["API Keys"])


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ApiKeyService(db).list_for_user(current_user.id)


@router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    request: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        api_key, plaintext = ApiKeyService(db).create(current_user.id, request.name)
    except DuplicateApiKeyNameError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.prefix,
        "created_at": api_key.created_at,
        "expires_at": api_key.expires_at,
        "last_used_at": api_key.last_used_at,
        "revoked_at": api_key.revoked_at,
        "key": plaintext,
    }


@router.post("/{key_id}/regenerate", response_model=ApiKeyCreatedResponse)
def regenerate_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ApiKeyService(db).regenerate(current_user.id, key_id)
    if result is None:
        raise HTTPException(404, "API key not found")
    api_key, plaintext = result
    return {
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.prefix,
        "created_at": api_key.created_at,
        "expires_at": api_key.expires_at,
        "last_used_at": api_key.last_used_at,
        "revoked_at": api_key.revoked_at,
        "key": plaintext,
    }


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not ApiKeyService(db).delete(current_user.id, key_id):
        raise HTTPException(404, "API key not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
