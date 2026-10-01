"""Unit tests for the deterministic finance engine.

These tests use the real September 2026 baseline from the source scans and must
reconcile to the approved figures: 998 / 59,498 / 51,207 / 8,291.
They have no DB or rendering dependency (NFR-014).
"""
from datetime import date

from app.domain.finance import (
    FinanceInput,
    PaymentLine,
    ReceiptLine,
    compute_totals,
    validate,
)
from app.money import rupees_to_paise as p


def september_2026() -> FinanceInput:
    return FinanceInput(
        opening_balance=p(998),
        receipts=[
            ReceiptLine("r2", "Maintenance Collection (13 Flats x 4,500)", p(58500), date(2026, 9, 5)),
        ],
        payments=[
            PaymentLine("y1", "Garbage Collection", p(2500), date(2026, 9, 1), "VC-SEP-01"),
            PaymentLine("y2", "Security Guard Salary", p(11000), date(2026, 9, 1), "VC-SEP-02"),
            PaymentLine("y3", "Water Bill - Previous Supply Clearance", p(26450), date(2026, 9, 1)),
            PaymentLine("y4", "Broom, Phenyl & Other Housekeeping", p(580), date(2026, 9, 5)),
            PaymentLine("y5", "Electricity - BESCOM", p(6177), date(2026, 9, 7)),
            PaymentLine("y6", "Water Supply Vendor - Pooja (5 x 900)", p(4500), date(2026, 9, 30)),
        ],
    )


def test_september_reconciles_to_baseline():
    totals = compute_totals(september_2026())
    assert totals.opening_balance == p(998)
    assert totals.receipts_subtotal == p(58500)
    assert totals.total_receipts == p(59498)
    assert totals.total_payments == p(51207)
    assert totals.closing_balance == p(8291)
    assert totals.net_position == p(8291)


def test_september_validation_passes():
    report = validate(september_2026())
    assert report.passed, [c for c in report.checks if not c.passed]
    assert report.status == "FINANCIAL_APPROVED"


def test_correction_from_7998_to_998_changes_result():
    # Before correction: an extraction misread of 7,998 inflates everything.
    wrong = september_2026()
    wrong = FinanceInput(
        opening_balance=p(7998),
        receipts=wrong.receipts,
        payments=wrong.payments,
    )
    assert compute_totals(wrong).closing_balance == p(15291)

    # After the explicit correction to 998 the baseline closing is restored.
    corrected = september_2026()
    assert compute_totals(corrected).closing_balance == p(8291)


def test_zero_amount_fails_validation():
    data = FinanceInput(
        opening_balance=p(998),
        receipts=[ReceiptLine("r1", "Empty", 0)],
        payments=[],
    )
    report = validate(data)
    assert not report.passed
    names = {c.name for c in report.checks if not c.passed}
    assert "amounts_present" in names


def test_negative_amount_fails_validation():
    data = FinanceInput(
        opening_balance=p(998),
        receipts=[ReceiptLine("r1", "Bad", -p(100))],
        payments=[],
    )
    report = validate(data)
    assert not report.passed
    assert "no_negative_amounts" in {c.name for c in report.checks if not c.passed}


def test_duplicate_payments_flagged():
    data = FinanceInput(
        opening_balance=p(998),
        receipts=[ReceiptLine("r1", "Maint", p(58500), date(2026, 9, 5))],
        payments=[
            PaymentLine("y1", "Garbage Collection", p(2500), date(2026, 9, 1)),
            PaymentLine("y2", "Garbage Collection", p(2500), date(2026, 9, 1)),
        ],
    )
    report = validate(data)
    assert "no_unintended_duplicates" in {c.name for c in report.checks if not c.passed}


def test_rejected_lines_excluded_from_totals():
    data = FinanceInput(
        opening_balance=p(998),
        receipts=[
            ReceiptLine("r1", "Maint", p(58500), date(2026, 9, 5)),
            ReceiptLine("r2", "Rejected dupe", p(58500), date(2026, 9, 5), status="REJECTED"),
        ],
        payments=[],
    )
    totals = compute_totals(data)
    assert totals.total_receipts == p(59498)
