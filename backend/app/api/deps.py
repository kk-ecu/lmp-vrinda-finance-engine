"""Shared API helpers."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Month, Payment, Receipt
from app.money import format_amount, paise_to_rupees


def get_month_or_404(db: Session, month_id: str) -> Month:
    month = db.get(Month, month_id)
    if month is None:
        raise HTTPException(status_code=404, detail="Month not found")
    return month


def receipt_out(r: Receipt) -> dict:
    return {
        "id": r.id,
        "receipt_date": r.receipt_date,
        "type": r.type,
        "flat_no": r.flat_no,
        "depositor": r.depositor,
        "description": r.description,
        "amount": paise_to_rupees(r.amount),
        "amount_display": format_amount(r.amount),
        "status": r.status,
        "confidence": r.confidence,
        "needs_review": r.status == "REVIEW_REQUIRED",
        "sort_order": r.sort_order,
    }


def payment_out(p: Payment) -> dict:
    return {
        "id": p.id,
        "payment_date": p.payment_date,
        "category": p.category,
        "description": p.description,
        "payee": p.payee,
        "amount": paise_to_rupees(p.amount),
        "amount_display": format_amount(p.amount),
        "voucher": p.voucher,
        "note": p.note,
        "status": p.status,
        "confidence": p.confidence,
        "needs_review": p.status == "REVIEW_REQUIRED",
        "sort_order": p.sort_order,
    }


def month_out(m: Month) -> dict:
    return {
        "id": m.id,
        "period": m.period,
        "status": m.status,
        "opening_balance": paise_to_rupees(m.opening_balance),
        "opening_balance_display": format_amount(m.opening_balance),
        "revision": m.revision,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }
