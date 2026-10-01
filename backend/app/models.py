"""SQLAlchemy ORM models for the LMP Vrinda Finance Engine.

Design notes:
- Currency is stored as integer paise (minor units) to avoid floating point
  error, consistent with docs/06-API-SPECIFICATION.md.
- The structured dataset is the authoritative source of truth (ADR-004).
- Original source files are immutable evidence (ADR-005); only metadata lives here.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Status vocabularies (FR-001)
# ---------------------------------------------------------------------------
class MonthStatus:
    DRAFT = "DRAFT"
    EXTRACTED = "EXTRACTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FINANCIAL_APPROVED = "FINANCIAL_APPROVED"
    GENERATED = "GENERATED"
    FINAL = "FINAL"
    ARCHIVED = "ARCHIVED"


class TxnStatus:
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class QaStatus:
    NOT_RUN = "NOT_RUN"
    PASS = "PASS"
    FAIL = "FAIL"


class Month(Base):
    __tablename__ = "months"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Canonical period key, e.g. "2026-09".
    period: Mapped[str] = mapped_column(String(7), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=MonthStatus.DRAFT)
    # Opening balance in paise.
    opening_balance: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    sources: Mapped[list["Source"]] = relationship(
        back_populates="month", cascade="all, delete-orphan"
    )
    receipts: Mapped[list["Receipt"]] = relationship(
        back_populates="month", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="month", cascade="all, delete-orphan"
    )
    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="month", cascade="all, delete-orphan"
    )
    validations: Mapped[list["Validation"]] = relationship(
        back_populates="month", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="month", cascade="all, delete-orphan"
    )
    notes: Mapped[list["Note"]] = relationship(
        back_populates="month", cascade="all, delete-orphan"
    )


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    month_id: Mapped[str] = mapped_column(ForeignKey("months.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="STORED")
    uploaded_at: Mapped[datetime] = mapped_column(default=_now)

    month: Mapped["Month"] = relationship(back_populates="sources")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    month_id: Mapped[str] = mapped_column(ForeignKey("months.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    receipt_date: Mapped[date | None] = mapped_column(nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    flat_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    depositor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(String(512), default="")
    # Amount in paise.
    amount: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default=TxnStatus.APPROVED)
    # Extraction confidence 0.0–1.0 (1.0 for manually entered rows).
    confidence: Mapped[float] = mapped_column(default=1.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    month: Mapped["Month"] = relationship(back_populates="receipts")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    month_id: Mapped[str] = mapped_column(ForeignKey("months.id"), index=True)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    payment_date: Mapped[date | None] = mapped_column(nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(String(512), default="")
    payee: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Amount in paise.
    amount: Mapped[int] = mapped_column(Integer, default=0)
    voucher: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TxnStatus.APPROVED)
    # Extraction confidence 0.0–1.0 (1.0 for manually entered rows).
    confidence: Mapped[float] = mapped_column(default=1.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    month: Mapped["Month"] = relationship(back_populates="payments")


class Correction(Base):
    """Immutable audit record of an explicit user correction (FR-008, ADR-006)."""

    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    month_id: Mapped[str] = mapped_column(ForeignKey("months.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(36))
    field_name: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reason: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(default=_now)

    month: Mapped["Month"] = relationship(back_populates="corrections")


class Validation(Base):
    __tablename__ = "validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    month_id: Mapped[str] = mapped_column(ForeignKey("months.id"), index=True)
    check_name: Mapped[str] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(16))  # PASS / FAIL
    message: Mapped[str] = mapped_column(String(512), default="")
    checked_at: Mapped[datetime] = mapped_column(default=_now)

    month: Mapped["Month"] = relationship(back_populates="validations")


class Note(Base):
    """Attention/highlight note shown in the report NOTES block (FR-015)."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    month_id: Mapped[str] = mapped_column(ForeignKey("months.id"), index=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    highlight: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    month: Mapped["Month"] = relationship(back_populates="notes")


class AppState(Base):
    """Single-row table holding mutable application/auth state.

    - password_hash: the CURRENT admin password hash (DB is source of truth after
      first-run seeding from AUTH_PASSWORD_HASH). Lets the password be changed from
      the UI without editing .env.
    - token_valid_after: tokens issued (iat) before this instant are rejected.
      'Sign out everywhere' / change-password set this to now to kill old tokens.
    """

    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    token_valid_after: Mapped[datetime] = mapped_column(
        default=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    month_id: Mapped[str] = mapped_column(ForeignKey("months.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    docx_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    qa_status: Mapped[str] = mapped_column(String(16), default=QaStatus.NOT_RUN)
    qa_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="GENERATED")
    generated_at: Mapped[datetime] = mapped_column(default=_now)

    month: Mapped["Month"] = relationship(back_populates="reports")
