"""Application configuration.

Local-first V1 settings. Values can be overridden via environment variables
or a .env file (see .env.example at the repository root).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config/settings.py -> repo root is three parents up from app/
_APP_DIR = Path(__file__).resolve().parents[1]
_BACKEND_DIR = _APP_DIR.parent
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    # Root for all persistent local data (database, sources, reports, exports).
    data_root: Path = _REPO_ROOT / "data"

    @field_validator("data_root", mode="before")
    @classmethod
    def _resolve_data_root(cls, v):
        """Resolve a relative data_root against the repo root, not the CWD.

        Keeps data in a stable location (repo-root ./data) regardless of where
        uvicorn is launched from. Absolute paths (e.g. /app/data in containers)
        are used as-is.
        """
        if v is None:
            return _REPO_ROOT / "data"
        p = Path(v)
        return p if p.is_absolute() else (_REPO_ROOT / p)

    # PDF rendering engine: "weasyprint" (default) or "libreoffice".
    pdf_engine: str = "weasyprint"

    # Feature flags. Set TEST_EXTRACTION_ENABLED=false to hide the /test-extraction page.
    test_extraction_enabled: bool = True

    # Authentication (JWT). auth_enabled=false leaves the app open (local dev only).
    auth_enabled: bool = True
    auth_username: str = "admin"
    auth_password_hash: str = ""   # bcrypt hash; generate with `make hash-password`
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_hours: int = 3

    # Upload constraints (NFR-011).
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB
    allowed_upload_suffixes: tuple[str, ...] = (
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".docx",
        ".xlsx",
        ".txt",
    )

    @property
    def database_dir(self) -> Path:
        return self.data_root / "database"

    @property
    def database_path(self) -> Path:
        return self.database_dir / "finance.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    @property
    def sources_dir(self) -> Path:
        return self.data_root / "sources"

    @property
    def reports_dir(self) -> Path:
        return self.data_root / "reports"

    @property
    def exports_dir(self) -> Path:
        return self.data_root / "exports"

    def ensure_directories(self) -> None:
        for path in (
            self.database_dir,
            self.sources_dir,
            self.reports_dir,
            self.exports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
