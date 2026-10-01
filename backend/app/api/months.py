"""Month, transaction, correction, note, validation, and approval endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_month_or_404, month_out, payment_out, receipt_out
from app.db import get_db
from app.models import (
    Correction,
    Month,
    MonthStatus,
    Note,
    Payment,
    Receipt,
    Validation,
)
from app.money import format_amount, paise_to_rupees, rupees_to_paise
from app.schemas.models import (
    CorrectionIn,
    MonthCreate,
    NoteIn,
    PaymentIn,
    ReceiptIn,
    ReopenIn,
)
from app.services import extraction_service, finance_service

router = APIRouter(prefix="/api", tags=["months"])


# ---------------------------------------------------------------------------
# Months
# ---------------------------------------------------------------------------
@router.get("/months")
def list_months(db: Session = Depends(get_db)):
    months = db.scalars(select(Month).order_by(Month.period.desc())).all()
    return [month_out(m) for m in months]


@router.post("/months", status_code=201)
def create_month(payload: MonthCreate, db: Session = Depends(get_db)):
    period = f"{payload.year:04d}-{payload.month:02d}"
    existing = db.scalar(select(Month).where(Month.period == period))
    if existing:
        raise HTTPException(status_code=409, detail=f"Month {period} already exists")
    month = Month(
        period=period,
        opening_balance=rupees_to_paise(payload.opening_balance),
        status=MonthStatus.DRAFT,
    )
    db.add(month)
    db.commit()
    db.refresh(month)
    return month_out(month)


@router.get("/months/{month_id}")
def get_month(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    return month_out(month)


@router.post("/months/{month_id}/reopen")
def reopen_month(month_id: str, payload: ReopenIn, db: Session = Depends(get_db)):
    """Reopen a signed-off month for rectification (FR-020).

    Requires an explicit reason, which is recorded as an audit Correction. Creates
    a new revision; the prior revision's generated report files are preserved on
    disk (each revision writes to its own revision-NN directory).
    """
    month = get_month_or_404(db, month_id)
    if month.status != MonthStatus.FINAL:
        raise HTTPException(status_code=409, detail="Only FINAL months can be reopened")

    reason = (payload.reason or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="A reason is required to reopen a signed-off statement.")

    old_revision = month.revision
    month.revision += 1
    month.status = MonthStatus.FINANCIAL_APPROVED

    db.add(Correction(
        month_id=month_id,
        entity_type="month",
        entity_id=month_id,
        field_name="status",
        old_value=f"FINAL (revision {old_revision})",
        new_value=f"REOPENED (revision {month.revision})",
        reason=reason,
    ))
    db.commit()
    db.refresh(month)
    return month_out(month)


@router.delete("/months/{month_id}", status_code=200)
def delete_month(month_id: str, db: Session = Depends(get_db)):
    """Hard-delete a month and its DB rows, plus its source/report files on disk.

    Guarded: FINAL/ARCHIVED months cannot be deleted (they are signed-off records);
    reopen first if a correction is genuinely needed. Intended for clearing
    DRAFT/abandoned months.
    """
    import shutil

    from app.config.settings import get_settings

    month = get_month_or_404(db, month_id)
    if month.status in (MonthStatus.FINAL, MonthStatus.ARCHIVED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete a {month.status} month. Reopen it first if a change is needed.",
        )

    period = month.period
    db.delete(month)  # cascades to sources/receipts/payments/notes/validations/reports
    db.commit()

    # Remove on-disk source and report files for this period.
    settings = get_settings()
    year, mon = period.split("-")
    for base in (settings.sources_dir, settings.reports_dir):
        target = base / year / mon
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)

    return {"deleted": True, "period": period}


# ---------------------------------------------------------------------------
# Extraction (FR-004) — pre-fill rows from uploaded sources via the engine
# ---------------------------------------------------------------------------
@router.get("/extraction/status")
def extraction_status():
    """Report whether the extraction engine is available and which provider is active."""
    return extraction_service.engine_status()


def _amount_to_paise(amount: str) -> int:
    cleaned = (amount or "").replace(",", "").replace("₹", "").strip()
    try:
        return rupees_to_paise(cleaned) if cleaned else 0
    except Exception:
        return 0


@router.post("/months/{month_id}/extract")
def extract_month(month_id: str, replace: bool = True, db: Session = Depends(get_db)):
    """Run extraction over the month's uploaded sources and pre-fill rows.

    Rows below the confidence threshold are stored as REVIEW_REQUIRED so the UI
    flags them. The opening balance is applied only if confident; otherwise it is
    surfaced for the user to confirm/correct explicitly (ADR-006).
    """
    from pathlib import Path

    month = get_month_or_404(db, month_id)
    if not extraction_service.engine_available():
        raise HTTPException(status_code=503, detail="Extraction engine is not available.")

    active_sources = [s for s in month.sources if s.status != "IGNORED" and s.path]
    if not active_sources:
        raise HTTPException(status_code=409, detail="Upload at least one source document first.")

    # Optionally clear previously extracted rows (keep manually added ones).
    if replace:
        for r in list(month.receipts):
            db.delete(r)
        for p in list(month.payments):
            db.delete(p)
        db.flush()

    threshold = None
    created_receipts = 0
    created_payments = 0
    opening_suggestion = None
    order = 1

    for src in active_sources:
        path = Path(src.path)
        if not path.exists():
            continue
        try:
            result, cfg = extraction_service.extract_file(path)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=f"Extraction failed: {exc}")
        threshold = cfg.low_confidence_threshold

        for row in result.receipts:
            status = "APPROVED" if row.confidence >= threshold else "REVIEW_REQUIRED"
            db.add(Receipt(
                month_id=month_id, source_id=src.id,
                receipt_date=_parse_date(row.date), description=row.description,
                flat_no=row.flat_no, depositor=row.depositor,
                amount=_amount_to_paise(row.amount), status=status,
                confidence=row.confidence, sort_order=order,
            ))
            created_receipts += 1
            order += 1

        for row in result.payments:
            status = "APPROVED" if row.confidence >= threshold else "REVIEW_REQUIRED"
            db.add(Payment(
                month_id=month_id, source_id=src.id,
                payment_date=_parse_date(row.date), description=row.description,
                voucher=row.voucher, note=row.note,
                amount=_amount_to_paise(row.amount), status=status,
                confidence=row.confidence, sort_order=order,
            ))
            created_payments += 1
            order += 1

        # Capture an opening-balance suggestion from the first source that has one.
        if opening_suggestion is None and result.opening_balance:
            opening_suggestion = {
                "amount": result.opening_balance,
                "confidence": result.opening_balance_confidence,
                "needs_review": result.opening_balance_confidence < threshold,
            }
            # Apply only when confident; otherwise leave for explicit confirmation.
            if result.opening_balance_confidence >= threshold:
                month.opening_balance = _amount_to_paise(result.opening_balance)

    month.status = MonthStatus.EXTRACTED
    db.commit()

    return {
        "extracted_receipts": created_receipts,
        "extracted_payments": created_payments,
        "low_confidence_threshold": threshold,
        "opening_balance_suggestion": opening_suggestion,
    }


def _parse_date(value):
    from datetime import date

    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------
@router.get("/months/{month_id}/receipts")
def list_receipts(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    rows = sorted(month.receipts, key=lambda r: (r.sort_order, r.id))
    return [receipt_out(r) for r in rows]


@router.post("/months/{month_id}/receipts", status_code=201)
def add_receipt(month_id: str, payload: ReceiptIn, db: Session = Depends(get_db)):
    get_month_or_404(db, month_id)
    receipt = Receipt(
        month_id=month_id,
        source_id=payload.source_id,
        receipt_date=payload.receipt_date,
        type=payload.type,
        flat_no=payload.flat_no,
        depositor=payload.depositor,
        description=payload.description,
        amount=rupees_to_paise(payload.amount),
        status=payload.status,
        sort_order=payload.sort_order,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt_out(receipt)


@router.put("/receipts/{receipt_id}")
def update_receipt(receipt_id: str, payload: ReceiptIn, db: Session = Depends(get_db)):
    receipt = db.get(Receipt, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    receipt.receipt_date = payload.receipt_date
    receipt.type = payload.type
    receipt.flat_no = payload.flat_no
    receipt.depositor = payload.depositor
    receipt.description = payload.description
    receipt.amount = rupees_to_paise(payload.amount)
    receipt.status = payload.status
    receipt.sort_order = payload.sort_order
    db.commit()
    db.refresh(receipt)
    return receipt_out(receipt)


@router.delete("/receipts/{receipt_id}", status_code=204)
def delete_receipt(receipt_id: str, db: Session = Depends(get_db)):
    receipt = db.get(Receipt, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    db.delete(receipt)
    db.commit()


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
@router.get("/months/{month_id}/payments")
def list_payments(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    rows = sorted(month.payments, key=lambda p: (p.sort_order, p.id))
    return [payment_out(p) for p in rows]


@router.post("/months/{month_id}/payments", status_code=201)
def add_payment(month_id: str, payload: PaymentIn, db: Session = Depends(get_db)):
    get_month_or_404(db, month_id)
    payment = Payment(
        month_id=month_id,
        source_id=payload.source_id,
        payment_date=payload.payment_date,
        category=payload.category,
        description=payload.description,
        payee=payload.payee,
        amount=rupees_to_paise(payload.amount),
        voucher=payload.voucher,
        note=payload.note,
        status=payload.status,
        sort_order=payload.sort_order,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment_out(payment)


@router.put("/payments/{payment_id}")
def update_payment(payment_id: str, payload: PaymentIn, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment.payment_date = payload.payment_date
    payment.category = payload.category
    payment.description = payload.description
    payment.payee = payload.payee
    payment.amount = rupees_to_paise(payload.amount)
    payment.voucher = payload.voucher
    payment.note = payload.note
    payment.status = payload.status
    payment.sort_order = payload.sort_order
    db.commit()
    db.refresh(payment)
    return payment_out(payment)


@router.delete("/payments/{payment_id}", status_code=204)
def delete_payment(payment_id: str, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    db.delete(payment)
    db.commit()


# ---------------------------------------------------------------------------
# Move a row between sections (receipt <-> payment)
# ---------------------------------------------------------------------------
@router.post("/receipts/{receipt_id}/move")
def move_receipt_to_payment(receipt_id: str, db: Session = Depends(get_db)):
    """Reclassify a misfiled receipt as a payment, preserving its data."""
    r = db.get(Receipt, receipt_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    payment = Payment(
        month_id=r.month_id,
        source_id=r.source_id,
        payment_date=r.receipt_date,
        description=r.description,
        amount=r.amount,
        status=r.status,
        confidence=r.confidence,
        sort_order=r.sort_order,
    )
    db.add(payment)
    db.delete(r)
    db.commit()
    db.refresh(payment)
    return payment_out(payment)


@router.post("/payments/{payment_id}/move")
def move_payment_to_receipt(payment_id: str, db: Session = Depends(get_db)):
    """Reclassify a misfiled payment as a receipt, preserving its data."""
    p = db.get(Payment, payment_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    receipt = Receipt(
        month_id=p.month_id,
        source_id=p.source_id,
        receipt_date=p.payment_date,
        description=p.description,
        amount=p.amount,
        status=p.status,
        confidence=p.confidence,
        sort_order=p.sort_order,
    )
    db.add(receipt)
    db.delete(p)
    db.commit()
    db.refresh(receipt)
    return receipt_out(receipt)


# ---------------------------------------------------------------------------
# Corrections (FR-008, ADR-006 — explicit, audited, never silent)
# ---------------------------------------------------------------------------
@router.get("/months/{month_id}/corrections")
def list_corrections(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    return [
        {
            "id": c.id,
            "entity_type": c.entity_type,
            "entity_id": c.entity_id,
            "field_name": c.field_name,
            "old_value": c.old_value,
            "new_value": c.new_value,
            "reason": c.reason,
            "created_at": c.created_at,
        }
        for c in sorted(month.corrections, key=lambda c: c.created_at)
    ]


@router.post("/months/{month_id}/corrections", status_code=201)
def apply_correction(month_id: str, payload: CorrectionIn, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    old_value = _apply_field_change(db, month, payload)

    correction = Correction(
        month_id=month_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        field_name=payload.field_name,
        old_value=old_value,
        new_value=payload.new_value,
        reason=payload.reason,
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return {
        "id": correction.id,
        "entity_type": correction.entity_type,
        "entity_id": correction.entity_id,
        "field_name": correction.field_name,
        "old_value": correction.old_value,
        "new_value": correction.new_value,
        "reason": correction.reason,
        "created_at": correction.created_at,
    }


def _apply_field_change(db: Session, month: Month, payload: CorrectionIn) -> str | None:
    """Apply the correction to the target entity and return the previous value."""
    etype = payload.entity_type.lower()
    field = payload.field_name

    if etype == "month":
        if field != "opening_balance":
            raise HTTPException(status_code=400, detail="Only opening_balance is correctable on a month")
        old = str(paise_to_rupees(month.opening_balance))
        month.opening_balance = rupees_to_paise(payload.new_value)
        return old

    if etype == "receipt":
        obj = db.get(Receipt, payload.entity_id)
    elif etype == "payment":
        obj = db.get(Payment, payload.entity_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown entity_type {payload.entity_type}")

    if obj is None or obj.month_id != month.id:
        raise HTTPException(status_code=404, detail="Target entity not found in this month")
    if not hasattr(obj, field):
        raise HTTPException(status_code=400, detail=f"Unknown field {field}")

    old_raw = getattr(obj, field)
    if field == "amount":
        old = str(paise_to_rupees(old_raw))
        setattr(obj, field, rupees_to_paise(payload.new_value))
    else:
        old = None if old_raw is None else str(old_raw)
        setattr(obj, field, payload.new_value)
    return old


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
@router.get("/months/{month_id}/notes")
def list_notes(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "highlight": n.highlight,
            "sort_order": n.sort_order,
        }
        for n in sorted(month.notes, key=lambda n: (n.sort_order, n.id))
    ]


@router.post("/months/{month_id}/notes", status_code=201)
def add_note(month_id: str, payload: NoteIn, db: Session = Depends(get_db)):
    get_month_or_404(db, month_id)
    note = Note(
        month_id=month_id,
        title=payload.title,
        body=payload.body,
        highlight=payload.highlight,
        sort_order=payload.sort_order,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_out(note)


@router.put("/notes/{note_id}")
def update_note(note_id: str, payload: NoteIn, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    note.title = payload.title
    note.body = payload.body
    note.highlight = payload.highlight
    note.sort_order = payload.sort_order
    db.commit()
    db.refresh(note)
    return _note_out(note)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: str, db: Session = Depends(get_db)):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()


def _note_out(note: Note) -> dict:
    return {
        "id": note.id,
        "title": note.title,
        "body": note.body,
        "highlight": note.highlight,
        "sort_order": note.sort_order,
    }


# ---------------------------------------------------------------------------
# Validation & approval
# ---------------------------------------------------------------------------
def _totals_payload(month: Month) -> dict:
    totals = finance_service.compute_totals(month)
    return {
        "opening_balance": paise_to_rupees(totals.opening_balance),
        "receipts_subtotal": paise_to_rupees(totals.receipts_subtotal),
        "total_receipts": paise_to_rupees(totals.total_receipts),
        "total_payments": paise_to_rupees(totals.total_payments),
        "closing_balance": paise_to_rupees(totals.closing_balance),
        "net_position": paise_to_rupees(totals.net_position),
        "opening_balance_display": format_amount(totals.opening_balance),
        "total_receipts_display": format_amount(totals.total_receipts, with_suffix=True),
        "total_payments_display": format_amount(totals.total_payments, with_suffix=True),
        "closing_balance_display": format_amount(totals.closing_balance, with_suffix=True),
        "net_position_display": format_amount(totals.net_position, with_suffix=True),
    }


@router.post("/months/{month_id}/validate")
def run_validation(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    report = finance_service.validate(month)

    # Persist validation results (replace prior run).
    for old in list(month.validations):
        db.delete(old)
    for c in report.checks:
        db.add(Validation(month_id=month_id, check_name=c.name, result=c.result, message=c.message))

    month.status = report.status
    db.commit()

    return {
        "status": report.status,
        "passed": report.passed,
        "checks": [{"name": c.name, "result": c.result, "message": c.message} for c in report.checks],
        "totals": _totals_payload(month),
    }


@router.get("/months/{month_id}/validation")
def get_validation(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    checks = [
        {"name": v.check_name, "result": v.result, "message": v.message}
        for v in sorted(month.validations, key=lambda v: v.check_name)
    ]
    passed = bool(checks) and all(c["result"] == "PASS" for c in checks)
    return {
        "status": month.status,
        "passed": passed,
        "checks": checks,
        "totals": _totals_payload(month),
    }


@router.post("/months/{month_id}/approve")
def approve_month(month_id: str, db: Session = Depends(get_db)):
    from datetime import datetime, timezone

    month = get_month_or_404(db, month_id)
    report = finance_service.validate(month)
    if not report.passed:
        raise HTTPException(
            status_code=409,
            detail="Financial validation must pass before approval.",
        )
    month.status = MonthStatus.FINANCIAL_APPROVED
    month.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(month)
    return month_out(month)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    months = db.scalars(select(Month).order_by(Month.period.desc())).all()
    out = []
    for m in months:
        totals = finance_service.compute_totals(m)
        out.append(
            {
                "id": m.id,
                "period": m.period,
                "status": m.status,
                "total_receipts_display": format_amount(totals.total_receipts, with_suffix=True),
                "total_payments_display": format_amount(totals.total_payments, with_suffix=True),
                "closing_balance_display": format_amount(totals.closing_balance, with_suffix=True),
            }
        )
    return {"months": out}
