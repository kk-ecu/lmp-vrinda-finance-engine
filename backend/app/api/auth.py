"""Authentication endpoints: login, current-user, revoke-all, change-password."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth as auth_svc
from app.config.settings import get_settings
from app.db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.auth_enabled:
        return {"token": auth_svc.create_token(settings.auth_username), "username": settings.auth_username}

    # Boot guard: never allow login against an empty/demo password.
    if not auth_svc.password_is_safe(db):
        raise HTTPException(
            status_code=503,
            detail="Admin password is not set to a secure value. Set AUTH_PASSWORD_HASH to a strong hash (make hash-password) and restart.",
        )

    if not auth_svc.authenticate(db, payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"token": auth_svc.create_token(payload.username), "username": payload.username}


@router.get("/me")
def me(username: str = Depends(auth_svc.require_auth)):
    return {"username": username}


@router.post("/revoke-all")
def revoke_all(username: str = Depends(auth_svc.require_auth), db: Session = Depends(get_db)):
    """Sign out everywhere: invalidate every token issued before now."""
    auth_svc.revoke_all(db)
    return {"revoked": True}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordIn,
    username: str = Depends(auth_svc.require_auth),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not auth_svc.verify_password(payload.current_password, auth_svc.current_password_hash(db)):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one")

    # Writes the new hash to the DB AND revokes all existing tokens.
    auth_svc.set_password(db, payload.new_password)
    # Issue a fresh token so the caller stays signed in with the new password.
    return {"changed": True, "token": auth_svc.create_token(settings.auth_username)}
