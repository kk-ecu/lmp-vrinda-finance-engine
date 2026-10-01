"""Bridges ORM entities to the pure finance engine and builds the report model.

Keeps all currency as integer paise. Totals are always recomputed here from the
stored line items; extracted/claimed totals are never trusted (API rule).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain import finance
from app.models import Month, Payment, Receipt
from app.money import format_amount


def to_finance_input(month: Month) -> finance.FinanceInput:
    receipts = [
        finance.ReceiptLine(
            id=r.id,
            description=r.description,
            amount=r.amount,
            receipt_date=r.receipt_date,
            status=r.status,
        )
        for r in month.receipts
    ]
    payments = [
        finance.PaymentLine(
            id=p.id,
            description=p.description,
            amount=p.amount,
            payment_date=p.payment_date,
            voucher=p.voucher,
            status=p.status,
        )
        for p in month.payments
    ]
    return finance.FinanceInput(
        opening_balance=month.opening_balance,
        receipts=receipts,
        payments=payments,
    )


def compute_totals(month: Month) -> finance.FinanceTotals:
    return finance.compute_totals(to_finance_input(month))


def validate(month: Month) -> finance.ValidationReport:
    return finance.validate(to_finance_input(month))


# ---------------------------------------------------------------------------
# Report view model (consumed by the DOCX generator)
# ---------------------------------------------------------------------------
@dataclass
class ReportRow:
    sno: int
    date: str
    description: str
    voucher: str
    amount: str


@dataclass
class ReportNote:
    title: str
    body: str
    highlight: bool


@dataclass
class ReportModel:
    period_label: str  # e.g. "SEPTEMBER 2026"
    total_receipts_display: str
    total_payments_display: str
    closing_balance_display: str
    net_position_display: str
    opening_balance_display: str
    receipt_rows: list[ReportRow]
    payment_rows: list[ReportRow]
    notes: list[ReportNote]


_MONTHS = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]


def period_label(period: str) -> str:
    year, month = period.split("-")
    return f"{_MONTHS[int(month) - 1]} {year}"


def _fmt_date(d) -> str:
    return d.strftime("%d-%m-%Y") if d else "-"


def _ordered_approved(items):
    approved = [i for i in items if i.status == "APPROVED"]
    return sorted(approved, key=lambda i: (i.sort_order, i.id))


def build_report_model(month: Month) -> ReportModel:
    totals = compute_totals(month)

    receipt_rows: list[ReportRow] = []
    # Opening balance is presented as the first receipt line (per sample output).
    receipt_rows.append(
        ReportRow(
            sno=1,
            date=_fmt_date(_period_first_day(month.period)),
            description="Opening Balance\nBrought Forward (+)",
            voucher="-",
            amount=format_amount(month.opening_balance),
        )
    )
    for idx, r in enumerate(_ordered_approved(month.receipts), start=2):
        receipt_rows.append(
            ReportRow(
                sno=idx,
                date=_fmt_date(r.receipt_date),
                description=r.description,
                voucher="-",
                amount=format_amount(r.amount),
            )
        )

    payment_rows: list[ReportRow] = []
    for idx, p in enumerate(_ordered_approved(month.payments), start=1):
        payment_rows.append(
            ReportRow(
                sno=idx,
                date=_fmt_date(p.payment_date),
                description=p.description,
                voucher=p.voucher or "-",
                amount=format_amount(p.amount),
            )
        )

    notes = [
        ReportNote(title=n.title, body=n.body, highlight=n.highlight)
        for n in sorted(month.notes, key=lambda n: (n.sort_order, n.id))
    ]

    return ReportModel(
        period_label=period_label(month.period),
        total_receipts_display=format_amount(totals.total_receipts, with_suffix=True),
        total_payments_display=format_amount(totals.total_payments, with_suffix=True),
        closing_balance_display=format_amount(totals.closing_balance, with_suffix=True),
        net_position_display=format_amount(totals.net_position, with_suffix=True),
        opening_balance_display=format_amount(totals.opening_balance),
        receipt_rows=receipt_rows,
        payment_rows=payment_rows,
        notes=notes,
    )


def _period_first_day(period: str):
    from datetime import date

    year, month = period.split("-")
    return date(int(year), int(month), 1)
