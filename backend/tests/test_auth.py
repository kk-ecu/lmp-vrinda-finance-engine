"""Auth tests: with authentication ENABLED (the production posture).

Uses a self-contained client fixture that turns auth on with a known password,
so we verify login succeeds/fails and protected routes require a valid token.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def auth_client(tmp_path, monkeypatch):
    db_file = tmp_path / "auth_test.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-at-least-32-chars-long-xx")
    monkeypatch.setenv("JWT_EXPIRY_HOURS", "3")

    import app.auth as auth_module
    import app.db as db_module
    from app.config.settings import get_settings
    from app.db import Base

    get_settings.cache_clear()
    # Set a known password hash for 'correct-horse'.
    monkeypatch.setenv("AUTH_PASSWORD_HASH", auth_module.hash_password("correct-horse"))
    get_settings.cache_clear()

    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, future=True)
    TS = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", TS)

    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    from app.db import get_db
    from app.main import app

    def _override():
        s = TS()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_health_is_public(auth_client):
    assert auth_client.get("/api/health").status_code == 200


def test_config_is_public(auth_client):
    r = auth_client.get("/api/config")
    assert r.status_code == 200
    assert r.json()["auth_enabled"] is True


def test_protected_route_requires_token(auth_client):
    # No Authorization header -> 401.
    assert auth_client.get("/api/months").status_code == 401


def test_login_rejects_bad_credentials(auth_client):
    r = auth_client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_and_access_protected_route(auth_client):
    r = auth_client.post("/api/auth/login", json={"username": "admin", "password": "correct-horse"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]

    # With the token, protected routes work.
    headers = {"Authorization": f"Bearer {token}"}
    assert auth_client.get("/api/months", headers=headers).status_code == 200
    assert auth_client.get("/api/auth/me", headers=headers).json()["username"] == "admin"


def test_invalid_token_rejected(auth_client):
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert auth_client.get("/api/months", headers=headers).status_code == 401


def _login(client, password="correct-horse"):
    r = client.post("/api/auth/login", json={"username": "admin", "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_revoke_all_kills_existing_token(auth_client):
    import time

    token = _login(auth_client)
    h = {"Authorization": f"Bearer {token}"}
    assert auth_client.get("/api/months", headers=h).status_code == 200

    time.sleep(1)  # ensure the revoke line is strictly after the token's iat (1s resolution)
    assert auth_client.post("/api/auth/revoke-all", headers=h).status_code == 200

    # The SAME token is now rejected — this is the stolen-token kill.
    assert auth_client.get("/api/months", headers=h).status_code == 401

    # Logging in again yields a fresh token that works.
    token2 = _login(auth_client)
    assert auth_client.get("/api/months", headers={"Authorization": f"Bearer {token2}"}).status_code == 200


def test_change_password_flow(auth_client):
    import time

    token = _login(auth_client, "correct-horse")
    h = {"Authorization": f"Bearer {token}"}
    time.sleep(1)
    r = auth_client.post("/api/auth/change-password", headers=h,
                         json={"current_password": "correct-horse", "new_password": "brand-new-pass-9"})
    assert r.status_code == 200, r.text

    # Old password no longer works.
    assert auth_client.post("/api/auth/login", json={"username": "admin", "password": "correct-horse"}).status_code == 401
    # New password works.
    assert auth_client.post("/api/auth/login", json={"username": "admin", "password": "brand-new-pass-9"}).status_code == 200
    # The old token was revoked by the change.
    assert auth_client.get("/api/months", headers=h).status_code == 401


def test_change_password_rejects_wrong_current(auth_client):
    token = _login(auth_client)
    h = {"Authorization": f"Bearer {token}"}
    r = auth_client.post("/api/auth/change-password", headers=h,
                         json={"current_password": "nope", "new_password": "brand-new-pass-9"})
    assert r.status_code == 401


def test_token_expiry_is_three_hours(auth_client):
    import jwt as pyjwt

    token = _login(auth_client)
    # Decode without verifying exp to read the claims.
    claims = pyjwt.decode(token, options={"verify_signature": False})
    window = claims["exp"] - claims["iat"]
    assert 2.9 * 3600 <= window <= 3.1 * 3600  # ~3 hours


def test_boot_guard_blocks_demo_password(tmp_path, monkeypatch):
    """With auth on and a DEMO password hash, login is refused (503)."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_file = tmp_path / "guard.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-at-least-32-chars-long-xx")
    # The known demo hash from auth._DEMO_HASHES:
    monkeypatch.setenv("AUTH_PASSWORD_HASH", "$2b$12$kvMCLvay3CL2AZmXFdzjm.Zt94SRPbet1GxlsVRiE2KhZLrVLujPi")

    import app.db as db_module
    from app.config.settings import get_settings
    from app.db import Base
    get_settings.cache_clear()

    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, future=True)
    TS = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", TS)
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    from app.db import get_db
    from app.main import app

    def _o():
        s = TS()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _o
    with TestClient(app) as c:
        # Even with the "correct" demo password, login is blocked.
        r = c.post("/api/auth/login", json={"username": "admin", "password": "vrinda2026"})
        assert r.status_code == 503
    app.dependency_overrides.clear()
    get_settings.cache_clear()
