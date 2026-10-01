"""Provider-neutral data structures returned by every extraction provider.

These are plain dataclasses with no dependency on the web app or the database,
so the extraction engine stays self-contained and independently testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractedRow:
    """One extracted receipt or payment line.

    amount is a string in rupees exactly as read (e.g. "58500", "2,500"); the
    application normalizes/validates it. confidence is 0.0–1.0.
    """
    kind: str  # "receipt" | "payment"
    description: str = ""
    amount: str = ""
    date: str | None = None            # ISO yyyy-mm-dd if the model could parse it
    voucher: str | None = None
    flat_no: str | None = None
    depositor: str | None = None
    note: str | None = None
    confidence: float = 1.0

    def needs_review(self, threshold: float) -> bool:
        return self.confidence < threshold


@dataclass
class ExtractionResult:
    provider: str
    model: str
    receipts: list[ExtractedRow] = field(default_factory=list)
    payments: list[ExtractedRow] = field(default_factory=list)
    period: str | None = None               # YYYY-MM read from the statement header
    period_confidence: float = 1.0
    opening_balance: str | None = None
    opening_balance_confidence: float = 1.0
    raw_text: str | None = None        # provider's raw output, for debugging
    warnings: list[str] = field(default_factory=list)

    @property
    def rows(self) -> list[ExtractedRow]:
        return [*self.receipts, *self.payments]
