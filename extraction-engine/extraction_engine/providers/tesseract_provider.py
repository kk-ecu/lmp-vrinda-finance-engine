"""Local Tesseract OCR provider (printed documents; weak on handwriting).

Tesseract returns raw text, not structured rows, so this provider does a
best-effort line parse and assigns LOW confidence throughout — the review UI is
expected to carry most of the work here. Kept for printed PDFs/invoices and as a
fully-local, zero-cost fallback. Lazy imports keep it optional/deletable.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from extraction_engine.providers.base import (
    ExtractionError,
    ExtractionProvider,
    ProviderUnavailable,
)
from extraction_engine.schema import ExtractedRow, ExtractionResult

_AMOUNT_RE = re.compile(r"(\d[\d,]{1,})")


class TesseractProvider(ExtractionProvider):
    name = "tesseract"

    def is_available(self) -> bool:
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401
        except Exception:
            return False
        cmd = self.options.get("cmd") or shutil.which("tesseract")
        return bool(cmd)

    def extract(self, file_path: Path) -> ExtractionResult:
        try:
            import pytesseract
            from PIL import Image
        except Exception as exc:
            raise ProviderUnavailable(f"pytesseract/Pillow not installed: {exc}") from exc

        cmd = self.options.get("cmd")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd

        try:
            text = pytesseract.image_to_string(
                Image.open(file_path), lang=self.options.get("lang", "eng")
            )
        except Exception as exc:
            raise ExtractionError(f"Tesseract OCR failed: {exc}") from exc

        payments: list[ExtractedRow] = []
        for line in (ln.strip() for ln in text.splitlines()):
            if not line:
                continue
            m = _AMOUNT_RE.search(line)
            if not m:
                continue
            amount = m.group(1).replace(",", "")
            description = line[: m.start()].strip(" -:.") or line
            payments.append(
                ExtractedRow(
                    kind="payment",
                    description=description,
                    amount=amount,
                    confidence=0.4,  # OCR text is unstructured; always review.
                )
            )

        return ExtractionResult(
            provider=self.name,
            model="tesseract",
            receipts=[],
            payments=payments,
            raw_text=text,
            warnings=["Tesseract output is unstructured OCR; review every row."],
        )
