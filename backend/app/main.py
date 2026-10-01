import os
from contextlib import asynccontextmanager
from pathlib import Path


def _load_repo_env() -> None:
    """Load the repo-root .env into os.environ (no override of existing vars).

    Makes the key/provider visible to BOTH the app settings and the extraction
    engine (which reads os.getenv). Dependency-free; existing env wins.
    """
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_repo_env()

import time

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth as auth_router
from app.api import extraction as extraction_router
from app.api import months as months_router
from app.api import reports as reports_router
from app.api import sources as sources_router
from app.auth import require_auth
from app.config.settings import get_settings
from app.db import init_db
from app.logging_config import get_logger, setup_logging

setup_logging()
log = get_logger("http")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log.info("Starting up — env=%s pdf_engine=%s auth=%s", settings.app_env, settings.pdf_engine, settings.auth_enabled)
    settings.ensure_directories()
    init_db()
    # Seed AppState (password hash from .env on first run) and warn loudly if the
    # active admin password is empty or a known demo value.
    if settings.auth_enabled:
        from app.auth import password_is_safe
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            if not password_is_safe(db):
                print(
                    "\n*** SECURITY WARNING: admin password is empty or a demo value. "
                    "Login is blocked until you set AUTH_PASSWORD_HASH to a strong hash "
                    "(run `make hash-password`) and restart. ***\n"
                )
        finally:
            db.close()
    yield


app = FastAPI(title="LMP Vrinda Finance Engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _access_log(request: Request, call_next):
    """Log every request: method, path, status, and duration — for diagnosis."""
    start = time.perf_counter()
    client = request.client.host if request.client else "?"
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        dur = (time.perf_counter() - start) * 1000
        log.exception("%s %s from %s FAILED after %.0fms: %s", request.method, request.url.path, client, dur, exc)
        raise
    dur = (time.perf_counter() - start) * 1000
    log.info("%s %s -> %s (%.0fms)", request.method, request.url.path, response.status_code, dur)
    return response


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "lmp-vrinda-finance-api", "version": "0.1.0"}


# Public: auth endpoints (login) and health are open.
app.include_router(auth_router.router)

# Protected business routers require a valid JWT.
_auth = [Depends(require_auth)]
app.include_router(months_router.router, dependencies=_auth)
app.include_router(sources_router.router, dependencies=_auth)
app.include_router(reports_router.router, dependencies=_auth)

# Extraction router: /api/config stays public (frontend reads it pre-login);
# the extraction/admin endpoints are protected individually within the router.
app.include_router(extraction_router.router)
