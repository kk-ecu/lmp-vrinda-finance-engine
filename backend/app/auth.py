"""Authentication: bcrypt + JWT, with DB-owned password and token revocation.

Design (single-admin, V1):
- Username is config-driven (AUTH_USERNAME in .env).
- Password hash is DB-owned: seeded once from AUTH_PASSWORD_HASH on first run,
  then changeable from the UI (DB wins thereafter). This means your real password
  travels with the data/ folder, not .env.
- Tokens are stateless JWTs (PyJWT). Revocation is done with a single
  `token_valid_after` timestamp: any token whose iat predates it is rejected.
  'Sign out everywhere' and change-password move that line to now.
- Boot guard: with auth enabled, the app refuses to operate on an empty/demo
  password so a fresh deployment can never come up wide open.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config.settings import get_settings

_ALGO = "HS256"
_bearer = HTTPBearer(auto_error=False)

# Known demo/placeholder values a real deployment must not run with.
_DEMO_HASHES = {
    # bcrypt hash of "vrinda2026" used during local validation
    "$2b$12$kvMCLvay3CL2AZmXFdzjm.Zt94SRPbet1GxlsVRiE2KhZLrVLujPi",
}


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# AppState (DB-owned password hash + revocation line)
# ---------------------------------------------------------------------------
def _epoch() -> datetime:
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def get_app_state(db: Session):
    """Return the single AppState row, creating + seeding it on first run."""
    from app.models import AppState

    state = db.get(AppState, 1)
    if state is None:
        settings = get_settings()
        state = AppState(
            id=1,
            password_hash=settings.auth_password_hash or "",
            token_valid_after=_epoch(),
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def current_password_hash(db: Session) -> str:
    return get_app_state(db).password_hash or ""


def set_password(db: Session, new_plain: str) -> None:
    state = get_app_state(db)
    state.password_hash = hash_password(new_plain)
    # Changing the password kills every existing token.
    state.token_valid_after = _now()
    db.commit()


def revoke_all(db: Session) -> None:
    state = get_app_state(db)
    state.token_valid_after = _now()
    db.commit()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def authenticate(db: Session, username: str, password: str) -> bool:
    settings = get_settings()
    if username != settings.auth_username:
        return False
    return verify_password(password, current_password_hash(db))


def password_is_safe(db: Session) -> bool:
    """False if the active password is empty or a known demo value."""
    h = current_password_hash(db)
    return bool(h) and h not in _DEMO_HASHES


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_token(username: str) -> str:
    settings = get_settings()
    now = _now()
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def _decode(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])


# ---------------------------------------------------------------------------
# FastAPI guard
# ---------------------------------------------------------------------------
def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Validate the Bearer JWT (signature, expiry, and revocation line)."""
    from app.db import SessionLocal

    settings = get_settings()
    if not settings.auth_enabled:
        return settings.auth_username

    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = _decode(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Revocation check: reject tokens issued before the valid-after line.
    iat = payload.get("iat")
    if iat is not None:
        issued = datetime.fromtimestamp(int(iat), tz=timezone.utc)
        db = SessionLocal()
        try:
            cutoff = _aware(get_app_state(db).token_valid_after)
        finally:
            db.close()
        # JWT iat has 1-second resolution, so a token minted in the same second
        # the revoke line was set must still count as "after". Floor the cutoff
        # to whole seconds before comparing.
        cutoff_floored = cutoff.replace(microsecond=0)
        if issued < cutoff_floored:
            raise HTTPException(status_code=401, detail="Token revoked")

    return payload.get("sub", "")
