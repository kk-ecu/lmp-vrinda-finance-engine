"""Source document upload and retrieval (FR-002, FR-003).

Original files are stored immutably under data/sources/<yyyy>/<mm>/<source-id>/
with a sha256 checksum recorded in SQLite.
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_month_or_404
from app.config.settings import get_settings
from app.db import get_db
from app.models import Source

router = APIRouter(prefix="/api", tags=["sources"])
settings = get_settings()


def _source_out(s: Source) -> dict:
    return {
        "id": s.id,
        "filename": s.filename,
        "mime_type": s.mime_type,
        "size_bytes": s.size_bytes,
        "sha256": s.sha256,
        "status": s.status,
        "uploaded_at": s.uploaded_at,
    }


@router.get("/months/{month_id}/sources")
def list_sources(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    return [_source_out(s) for s in month.sources]


@router.post("/months/{month_id}/sources", status_code=201)
async def upload_source(month_id: str, file: UploadFile, db: Session = Depends(get_db)):
    import os

    month = get_month_or_404(db, month_id)

    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in settings.allowed_upload_suffixes:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix or 'unknown'}")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds maximum allowed size")

    sha256 = hashlib.sha256(data).hexdigest()

    source = Source(
        month_id=month_id,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        sha256=sha256,
        path="",  # set after we know the id
        status="STORED",
    )
    db.add(source)
    db.flush()  # assign source.id without committing yet

    year, mon = month.period.split("-")
    dest_dir = settings.sources_dir / year / mon / source.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    original = dest_dir / f"original{suffix}"
    original.write_bytes(data)

    # Store a small metadata sidecar alongside the immutable original.
    (dest_dir / "metadata.json").write_text(
        f'{{"filename": {file.filename!r}, "sha256": "{sha256}", "size_bytes": {len(data)}}}'
    )

    source.path = str(original)
    db.commit()
    db.refresh(source)
    return _source_out(source)


@router.get("/sources/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return _source_out(source)


@router.delete("/sources/{source_id}", status_code=200)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    """Logical deletion only — original evidence is preserved (FR-003)."""
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    source.status = "IGNORED"
    db.commit()
    return {"id": source.id, "status": source.status}
