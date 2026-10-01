"""Integration layer between the backend and the self-contained extraction-engine.

The extraction-engine lives outside backend/ and is entirely optional: if the
folder is removed or its import fails, the backend still runs and extraction
endpoints report a clean 'unavailable' instead of crashing the app.
"""
from __future__ import annotations

import sys
from pathlib import Path

# extraction-engine/ sits next to backend/ at the repo root. In containers the
# path can be overridden via EXTRACTION_ENGINE_PATH.
import os

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENGINE_PATH = Path(os.getenv("EXTRACTION_ENGINE_PATH", _REPO_ROOT / "extraction-engine"))

_ENGINE_IMPORT_ERROR: str | None = None

if _ENGINE_PATH.exists() and str(_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(_ENGINE_PATH))

try:
    import extraction_engine as _ee  # type: ignore
except Exception as exc:  # noqa: BLE001 — engine is optional
    _ee = None
    _ENGINE_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def engine_available() -> bool:
    return _ee is not None


def engine_status() -> dict:
    if _ee is None:
        return {"available": False, "error": _ENGINE_IMPORT_ERROR}
    cfg = _ee.load_config()
    return {
        "available": True,
        "provider": cfg.provider,
        "low_confidence_threshold": cfg.low_confidence_threshold,
        "providers_loaded": _ee.available_provider_names(),
        "load_errors": _ee.load_errors,
    }


def extract_file(file_path: Path):
    """Run the configured provider. Returns (result, config).

    Raises RuntimeError with a readable message if the engine or provider is
    unavailable, so the API can translate it to a 4xx/5xx cleanly.
    """
    if _ee is None:
        raise RuntimeError(f"Extraction engine not available: {_ENGINE_IMPORT_ERROR}")
    cfg = _ee.load_config()
    try:
        result = _ee.extract_from_file(file_path, cfg)
    except _ee.ProviderUnavailable as exc:
        raise RuntimeError(str(exc)) from exc
    except _ee.ExtractionError as exc:
        raise RuntimeError(str(exc)) from exc
    return result, cfg
