"""Rendered-document QA (Gate B, docs/09).

Checks the actual artifacts: DOCX exists & has content, PDF exists & is a valid
PDF, page count, and that the key financial amounts are present in the rendered
text. Degrades gracefully when the PDF or a PDF text tool is unavailable.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class QaResult:
    status: str  # PASS | FAIL | NOT_RUN
    checks: list[dict] = field(default_factory=list)
    page_count: int | None = None

    def add(self, name: str, ok: bool, message: str = "") -> None:
        self.checks.append({"name": name, "result": "PASS" if ok else "FAIL", "message": message})


def _pdf_text(pdf_path: Path) -> str | None:
    tool = shutil.which("pdftotext")
    if not tool:
        return None
    result = subprocess.run(
        [tool, "-layout", str(pdf_path), "-"], capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


def _pdf_page_count(pdf_path: Path) -> int | None:
    tool = shutil.which("pdfinfo")
    if not tool:
        return None
    result = subprocess.run([tool, str(pdf_path)], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.lower().startswith("pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def run_qa(
    docx_path: Path | None,
    pdf_path: Path | None,
    expected_amounts: list[str],
    renderer_available: bool,
) -> QaResult:
    result = QaResult(status="NOT_RUN")

    # DOCX checks
    docx_ok = bool(docx_path and docx_path.exists() and docx_path.stat().st_size > 0)
    result.add("docx_exists", docx_ok, "" if docx_ok else "DOCX missing or empty")

    if not renderer_available:
        result.add(
            "pdf_renderer_available",
            False,
            "PDF renderer unavailable; PDF not rendered. DOCX produced successfully.",
        )
        # Without a renderer we cannot complete Gate B.
        result.status = "FAIL"
        return result

    result.add("pdf_renderer_available", True)

    pdf_ok = bool(pdf_path and pdf_path.exists() and pdf_path.stat().st_size > 0)
    result.add("pdf_exists", pdf_ok, "" if pdf_ok else "PDF missing or empty")
    if not pdf_ok:
        result.status = "FAIL"
        return result

    pages = _pdf_page_count(pdf_path)
    result.page_count = pages
    if pages is not None:
        result.add("page_count", pages >= 1, f"{pages} page(s)")
        result.add("single_page_target", pages == 1, f"{pages} page(s); target is 1")

    text = _pdf_text(pdf_path)
    if text is None:
        result.add("text_extractable", False, "pdftotext unavailable; skipped amount checks")
    else:
        result.add("not_empty", bool(text.strip()), "")
        missing = [a for a in expected_amounts if a not in text]
        result.add(
            "amounts_present",
            not missing,
            "" if not missing else f"Missing from PDF: {', '.join(missing)}",
        )

    result.status = "PASS" if all(c["result"] == "PASS" for c in result.checks) else "FAIL"
    return result
