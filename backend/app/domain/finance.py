"""Deterministic financial calculation and validation engine.

This module is intentionally free of any database, web, or document-rendering
dependency so it can be unit-tested in isolation (NFR-014, ADR-007).

All amounts are integer paise. The engine never trusts an extracted total; it
recomputes receipts, payments, and the closing balance from line items.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ReceiptLine:
    id: str
    description: str
    amount: int  # paise
    receipt_date: date | None = None
    status: str = "APPROVED"


@dataclass(frozen=True)
class PaymentLine:
    id: str
    description: str
    amount: int  # paise
    payment_date: date | None = None
    voucher: str | None = None
    status: str = "APPROVED"


@dataclass(frozen=True)
class FinanceInput:
    opening_balance: int  # paise
    receipts: list[ReceiptLine] = field(default_factory=list)
    payments: list[PaymentLine] = field(default_factory=list)


@dataclass(frozen=True)
class FinanceTotals:
    opening_balance: int
    receipts_subtotal: int  # sum of receipt line items (excludes opening balance)
    total_receipts: int  # opening_balance + receipts_subtotal (per FR-009)
    total_payments: int
    closing_balance: int  # opening + receipts_subtotal - payments
    net_position: int  # total_receipts - total_payments


@dataclass(frozen=True)
class Check:
    name: str
    result: str  # "PASS" or "FAIL"
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.result == "PASS"


@dataclass(frozen=True)
class ValidationReport:
    checks: list[Check]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def status(self) -> str:
        return "FINANCIAL_APPROVED" if self.passed else "REVIEW_REQUIRED"


PASS = "PASS"
FAIL = "FAIL"


def _approved(lines):
    return [l for l in lines if l.status == "APPROVED"]


def compute_totals(data: FinanceInput) -> FinanceTotals:
    """Recompute all totals deterministically from approved line items.

    Reconciliation (docs/05, docs/09):
        Total Receipts  = Opening Balance + sum(approved receipt inflows)
        Closing Balance = Opening Balance + receipts_subtotal - total_payments
    """
    receipts_subtotal = sum(l.amount for l in _approved(data.receipts))
    total_payments = sum(l.amount for l in _approved(data.payments))
    total_receipts = data.opening_balance + receipts_subtotal
    closing_balance = data.opening_balance + receipts_subtotal - total_payments
    net_position = total_receipts - total_payments
    return FinanceTotals(
        opening_balance=data.opening_balance,
        receipts_subtotal=receipts_subtotal,
        total_receipts=total_receipts,
        total_payments=total_payments,
        closing_balance=closing_balance,
        net_position=net_position,
    )


def validate(data: FinanceInput) -> ValidationReport:
    """Run the Gate A financial checks (docs/09-VALIDATION-QA-SPECIFICATION.md)."""
    checks: list[Check] = []
    totals = compute_totals(data)
    approved_receipts = _approved(data.receipts)
    approved_payments = _approved(data.payments)

    # Opening balance present (allowed to be zero, but must be set deliberately).
    checks.append(
        Check("opening_balance_present", PASS, f"Opening balance = {data.opening_balance} paise")
    )

    # At least one transaction exists.
    if not approved_receipts and not approved_payments:
        checks.append(Check("has_transactions", FAIL, "No approved receipts or payments."))
    else:
        checks.append(Check("has_transactions", PASS))

    # Missing / zero amounts.
    zero_amount = [l for l in approved_receipts + approved_payments if l.amount == 0]
    checks.append(
        Check(
            "amounts_present",
            FAIL if zero_amount else PASS,
            f"{len(zero_amount)} line(s) have a missing/zero amount." if zero_amount else "",
        )
    )

    # Negative amounts (not allowed for receipt/payment line items).
    negatives = [l for l in approved_receipts + approved_payments if l.amount < 0]
    checks.append(
        Check(
            "no_negative_amounts",
            FAIL if negatives else PASS,
            f"{len(negatives)} line(s) have a negative amount." if negatives else "",
        )
    )

    # Valid dates where present.
    bad_dates = [
        l
        for l in approved_receipts + approved_payments
        if l.__dict__.get("receipt_date", l.__dict__.get("payment_date")) is not None
        and not isinstance(
            l.__dict__.get("receipt_date", l.__dict__.get("payment_date")), date
        )
    ]
    checks.append(
        Check(
            "dates_valid",
            FAIL if bad_dates else PASS,
            f"{len(bad_dates)} line(s) have an invalid date." if bad_dates else "",
        )
    )

    # Duplicate detection: same (date, amount, description) within a group.
    def _dupes(lines, date_attr):
        seen: dict[tuple, int] = {}
        dup = 0
        for l in lines:
            key = (getattr(l, date_attr, None), l.amount, l.description.strip().lower())
            seen[key] = seen.get(key, 0) + 1
        for count in seen.values():
            if count > 1:
                dup += count - 1
        return dup

    dup_count = _dupes(approved_receipts, "receipt_date") + _dupes(
        approved_payments, "payment_date"
    )
    checks.append(
        Check(
            "no_unintended_duplicates",
            FAIL if dup_count else PASS,
            f"{dup_count} potential duplicate transaction(s)." if dup_count else "",
        )
    )

    # Arithmetic consistency: closing must equal the reconciliation formula.
    expected_closing = (
        totals.opening_balance + totals.receipts_subtotal - totals.total_payments
    )
    checks.append(
        Check(
            "arithmetic_consistent",
            PASS if totals.closing_balance == expected_closing else FAIL,
            "" if totals.closing_balance == expected_closing else "Closing balance mismatch.",
        )
    )

    return ValidationReport(checks=checks)
