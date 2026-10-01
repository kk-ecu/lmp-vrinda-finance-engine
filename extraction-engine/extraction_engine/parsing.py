"""Helpers to turn a vision-LLM JSON string into an ExtractionResult."""
from __future__ import annotations

import json
import re

from extraction_engine.schema import ExtractedRow, ExtractionResult


def _coerce_json(text: str) -> dict:
    """Extract the first JSON object from a model response, tolerant of fences."""
    text = text.strip()
    # Strip ```json ... ``` fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        brace = text.find("{")
        if brace > 0:
            text = text[brace:]
    return json.loads(text)


def result_from_json(text: str, provider: str, model: str) -> ExtractionResult:
    data = _coerce_json(text)

    def row(kind: str, d: dict) -> ExtractedRow:
        return ExtractedRow(
            kind=kind,
            description=str(d.get("description", "") or ""),
            amount=str(d.get("amount", "") or ""),
            date=d.get("date") or None,
            voucher=d.get("voucher") or None,
            flat_no=d.get("flat_no") or None,
            depositor=d.get("depositor") or None,
            note=d.get("note") or None,
            confidence=float(d.get("confidence", 1.0) or 1.0),
        )

    receipts = [row("receipt", r) for r in data.get("receipts", []) or []]
    payments = [row("payment", p) for p in data.get("payments", []) or []]

    ob = data.get("opening_balance") or {}
    period = data.get("period") or {}
    return ExtractionResult(
        provider=provider,
        model=model,
        receipts=receipts,
        payments=payments,
        period=str(period.get("value")) if period.get("value") else None,
        period_confidence=float(period.get("confidence", 1.0) or 1.0),
        opening_balance=str(ob.get("amount")) if ob.get("amount") else None,
        opening_balance_confidence=float(ob.get("confidence", 1.0) or 1.0),
        raw_text=text,
    )
