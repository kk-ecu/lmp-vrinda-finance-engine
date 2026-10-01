"""Deterministic, dependency-free provider.

Returns the September 2026 baseline so tests and offline demos work without any
network, API key, model, or binary. It mimics realistic extraction by giving the
tricky opening balance a LOW confidence (the 7998-vs-998 misread case) so the
review UI has something to flag.
"""
from __future__ import annotations

from pathlib import Path

from extraction_engine.providers.base import ExtractionProvider
from extraction_engine.schema import ExtractedRow, ExtractionResult


class StubProvider(ExtractionProvider):
    name = "stub"

    def is_available(self) -> bool:
        return True

    def extract(self, file_path: Path) -> ExtractionResult:
        receipts = [
            ExtractedRow(
                kind="receipt",
                date="2026-09-05",
                description="Maintenance Collection (13 Flats x 4,500)",
                amount="58500",
                confidence=0.93,
            ),
        ]
        payments = [
            ExtractedRow("payment", date="2026-09-01", description="Garbage Collection", amount="2500", voucher="VC-SEP-01", confidence=0.95),
            ExtractedRow("payment", date="2026-09-01", description="Security Guard Salary", amount="11000", voucher="VC-SEP-02", note="Advance 30,000 referenced; 11,000 paid as salary.", confidence=0.9),
            ExtractedRow("payment", date="2026-09-01", description="Water Bill - Previous Supply Clearance", amount="26450", confidence=0.82),
            ExtractedRow("payment", date="2026-09-05", description="Broom, Phenyl & Other Housekeeping Items", amount="580", confidence=0.6),
            ExtractedRow("payment", date="2026-09-07", description="Electricity - BESCOM", amount="6177", confidence=0.88),
            ExtractedRow("payment", date="2026-09-30", description="Water Supply Vendor - Pooja (5 x 900)", amount="4500", confidence=0.84),
        ]
        return ExtractionResult(
            provider=self.name,
            model="stub-september-2026",
            receipts=receipts,
            payments=payments,
            period="2026-09",
            period_confidence=0.95,
            # The classic misread: low confidence so the UI flags it for review.
            opening_balance="7998",
            opening_balance_confidence=0.45,
        )
