"""Pydantic request/response schemas.

Amounts cross the API boundary as whole/decimal rupee strings or numbers for
human friendliness, but are stored internally as integer paise. Each response
also exposes a pre-formatted display string so the UI never formats currency.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Months
# ---------------------------------------------------------------------------
class MonthCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    opening_balance: Decimal = Field(default=Decimal("0"))


class ReopenIn(BaseModel):
    reason: str = ""


class MonthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    period: str
    status: str
    opening_balance: Decimal
    opening_balance_display: str
    revision: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: str
    uploaded_at: datetime


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------
class ReceiptIn(BaseModel):
    receipt_date: date | None = None
    type: str | None = None
    flat_no: str | None = None
    depositor: str | None = None
    description: str = ""
    amount: Decimal = Decimal("0")
    voucher: str | None = None
    source_id: str | None = None
    status: str = "APPROVED"
    sort_order: int = 0


class ReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    receipt_date: date | None
    type: str | None
    flat_no: str | None
    depositor: str | None
    description: str
    amount: Decimal
    amount_display: str
    status: str
    sort_order: int


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
class PaymentIn(BaseModel):
    payment_date: date | None = None
    category: str | None = None
    description: str = ""
    payee: str | None = None
    amount: Decimal = Decimal("0")
    voucher: str | None = None
    note: str | None = None
    source_id: str | None = None
    status: str = "APPROVED"
    sort_order: int = 0


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_date: date | None
    category: str | None
    description: str
    payee: str | None
    amount: Decimal
    amount_display: str
    voucher: str | None
    note: str | None
    status: str
    sort_order: int


# ---------------------------------------------------------------------------
# Corrections
# ---------------------------------------------------------------------------
class CorrectionIn(BaseModel):
    entity_type: str  # "receipt" | "payment" | "month"
    entity_id: str
    field_name: str
    new_value: str
    reason: str = ""


class CorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str
    entity_id: str
    field_name: str
    old_value: str | None
    new_value: str | None
    reason: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
class NoteIn(BaseModel):
    title: str = ""
    body: str = ""
    highlight: bool = True
    sort_order: int = 0


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    body: str
    highlight: bool
    sort_order: int


# ---------------------------------------------------------------------------
# Validation & totals
# ---------------------------------------------------------------------------
class CheckOut(BaseModel):
    name: str
    result: str
    message: str


class TotalsOut(BaseModel):
    opening_balance: Decimal
    receipts_subtotal: Decimal
    total_receipts: Decimal
    total_payments: Decimal
    closing_balance: Decimal
    net_position: Decimal
    # Display strings
    opening_balance_display: str
    total_receipts_display: str
    total_payments_display: str
    closing_balance_display: str
    net_position_display: str


class ValidationOut(BaseModel):
    status: str
    passed: bool
    checks: list[CheckOut]
    totals: TotalsOut


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    revision: int
    qa_status: str
    status: str
    generated_at: datetime
    has_docx: bool = False
    has_pdf: bool = False
