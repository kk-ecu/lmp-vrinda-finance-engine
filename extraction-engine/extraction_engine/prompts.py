"""Shared prompt + JSON schema for vision-LLM providers (openrouter, ollama)."""
from __future__ import annotations

EXTRACTION_SYSTEM = (
    "You are a careful financial data extractor for an apartment association's "
    "monthly ledger. You read scanned/handwritten receipt and payment statements "
    "and return STRICT JSON only. Never invent values. If a value is unclear, "
    "still return your best reading but lower its confidence."
)

EXTRACTION_INSTRUCTIONS = """\
Extract the month's financial lines from the image(s).

Return ONLY a JSON object with this exact shape (no markdown, no commentary):
{
  "period": {"value": "<YYYY-MM or empty>", "confidence": 0.0-1.0},
  "opening_balance": {"amount": "<rupees or empty>", "confidence": 0.0-1.0},
  "receipts": [
    {"date": "YYYY-MM-DD or null", "description": "...", "amount": "<rupees>",
     "flat_no": "... or null", "depositor": "... or null", "confidence": 0.0-1.0}
  ],
  "payments": [
    {"date": "YYYY-MM-DD or null", "description": "...", "amount": "<rupees>",
     "voucher": "... or null", "note": "... or null", "confidence": 0.0-1.0}
  ]
}

Rules:
- period is the statement month as YYYY-MM read from the header (e.g. a header
  "Sep-2026" or "September 2026" -> "2026-09"). Lower confidence if unclear.
- amount is digits only in rupees, no symbols or separators (e.g. "58500", "2500").
- Resolve arithmetic hints like "13 x 4500" to the product (58500) and keep the
  hint in the description.
- Opening balance is a receipt-side figure; put it in opening_balance, not receipts.
- confidence reflects how sure you are of each field; handwriting you had to guess
  should be below 0.8.
- Output must be valid JSON and nothing else.
"""
