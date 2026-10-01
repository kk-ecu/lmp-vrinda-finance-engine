"""Extraction utility endpoints: app config flags and ad-hoc test extraction.

The ad-hoc endpoint powers the /test-extraction UI page: upload any image and
run any provider WITHOUT creating a month or persisting anything. Useful for
validating each engine's output before trusting it in the real workflow.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.config.settings import get_settings
from app.db import get_db
from app.models import Month, MonthStatus
from app.services import extraction_service

router = APIRouter(prefix="/api", tags=["extraction"])
settings = get_settings()


@router.get("/admin/months")
def admin_list_months(db: Session = Depends(get_db), _: str = Depends(require_auth)):
    """All months with status, revision, and row/source counts for admin management."""
    months = db.scalars(select(Month).order_by(Month.period.desc())).all()
    out = []
    for m in months:
        protected = m.status in (MonthStatus.FINAL, MonthStatus.ARCHIVED)
        out.append({
            "id": m.id,
            "period": m.period,
            "status": m.status,
            "revision": m.revision,
            "sources": len([s for s in m.sources if s.status != "IGNORED"]),
            "receipts": len(m.receipts),
            "payments": len(m.payments),
            "reports": len(m.reports),
            "deletable": not protected,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
        })
    return {"months": out}


@router.get("/config")
def app_config():
    """Public feature flags / config the frontend can read."""
    s = get_settings()
    status = extraction_service.engine_status()
    return {
        "app_env": s.app_env,
        "is_production": s.is_production,
        "auth_enabled": s.auth_enabled,
        "test_extraction_enabled": s.test_extraction_enabled,
        "pdf_engine": s.pdf_engine,
        # Providers the API will actually serve in THIS environment. The UI uses
        # this to show only permitted providers (openrouter-only in production).
        "allowed_providers": list(s.allowed_providers),
        "extraction": status,
    }


def _enforce_provider_policy(provider: str | None) -> None:
    """Reject extraction with a provider not permitted in this environment.

    `provider` is the effective provider for the call (the per-call override if
    given, else the configured default). In production only 'openrouter' is
    allowed; anything else is refused with 409 so the API never serves traffic
    through an unsupported provider.
    """
    s = get_settings()
    effective = provider
    if not effective:
        # No override — fall back to the configured default.
        if extraction_service.engine_available():
            effective = extraction_service.engine_status().get("provider")
    allowed = s.allowed_providers
    if effective and effective not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Provider '{effective}' is not permitted in {s.app_env}. "
                f"Allowed: {', '.join(allowed)}."
            ),
        )


@router.post("/upload-first")
async def upload_first(file: UploadFile, db: Session = Depends(get_db), _: str = Depends(require_auth)):
    """Detect the statement period from an uploaded scan and create/open that month.

    This is the scan-driven entry point: the period and opening balance come from
    the image, not a manual form. Returns the detected period (with confidence) and
    the month id so the UI can confirm, store the source, and run full extraction.
    """
    if not extraction_service.engine_available():
        raise HTTPException(status_code=503, detail="Extraction engine not available.")

    # Environment policy: block the configured provider if not permitted here.
    _enforce_provider_policy(None)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    suffix = Path(file.filename or "upload").suffix or ".jpg"
    tmp = Path(tempfile.gettempdir()) / f"upload-first-{os.getpid()}{suffix}"
    tmp.write_bytes(data)
    try:
        result, cfg = extraction_service.extract_file(tmp)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Extraction failed: {exc}")
    finally:
        tmp.unlink(missing_ok=True)

    period = result.period
    if not period or len(period) != 7 or period[4] != "-":
        # Could not read a usable period; let the UI fall back to manual entry.
        return {
            "detected": False,
            "reason": "Could not read the month from the scan.",
            "period": period,
            "period_confidence": result.period_confidence,
        }

    # Create the month if new, else reuse the existing one.
    month = db.scalar(select(Month).where(Month.period == period))
    created = False
    if month is None:
        month = Month(period=period, status=MonthStatus.DRAFT, opening_balance=0)
        db.add(month)
        db.commit()
        db.refresh(month)
        created = True

    return {
        "detected": True,
        "created": created,
        "month_id": month.id,
        "period": period,
        "period_confidence": result.period_confidence,
        "period_needs_review": result.period_confidence < cfg.low_confidence_threshold,
        "opening_balance": result.opening_balance,
        "status": month.status,
    }


@router.post("/test/extract")
async def test_extract(file: UploadFile, provider: str | None = Form(default=None), _: str = Depends(require_auth)):
    """Run extraction on an uploaded file ad-hoc (no persistence).

    Optional `provider` overrides the configured one for this call only, so the
    UI can compare openrouter / ollama / tesseract / stub side by side.
    """
    if not get_settings().test_extraction_enabled:
        raise HTTPException(status_code=404, detail="Test extraction is disabled.")
    if not extraction_service.engine_available():
        raise HTTPException(status_code=503, detail="Extraction engine not available.")

    # Environment policy: block providers not permitted here (prod = openrouter only).
    _enforce_provider_policy(provider)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    suffix = Path(file.filename or "upload").suffix or ".jpg"
    tmp = Path(tempfile.gettempdir()) / f"test-extract-{os.getpid()}{suffix}"
    tmp.write_bytes(data)

    # Temporarily override the provider for this call if requested.
    prev = os.environ.get("EXTRACTION_PROVIDER")
    if provider:
        os.environ["EXTRACTION_PROVIDER"] = provider
    try:
        result, cfg = extraction_service.extract_file(tmp)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    finally:
        if provider:
            if prev is None:
                os.environ.pop("EXTRACTION_PROVIDER", None)
            else:
                os.environ["EXTRACTION_PROVIDER"] = prev
        tmp.unlink(missing_ok=True)

    def row(r):
        return {
            "kind": r.kind,
            "description": r.description,
            "amount": r.amount,
            "date": r.date,
            "voucher": r.voucher,
            "flat_no": r.flat_no,
            "depositor": r.depositor,
            "confidence": r.confidence,
            "needs_review": r.confidence < cfg.low_confidence_threshold,
        }

    return {
        "provider": result.provider,
        "model": result.model,
        "low_confidence_threshold": cfg.low_confidence_threshold,
        "period": result.period,
        "period_confidence": result.period_confidence,
        "opening_balance": result.opening_balance,
        "opening_balance_confidence": result.opening_balance_confidence,
        "receipts": [row(r) for r in result.receipts],
        "payments": [row(r) for r in result.payments],
        "warnings": result.warnings,
        "raw_text": (result.raw_text or "")[:4000],
    }
