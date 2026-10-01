"""DOCX -> PDF rendering via LibreOffice headless.

LibreOffice is the dependable converter inside a Linux/Podman container on
Apple Silicon. We resolve the binary across common locations and fail with a
clear, catchable error if it is not installed (so QA can report MISSING rather
than crash). This is the real presentation artifact per ADR-009.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_CANDIDATES = (
    "soffice",
    "libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice",
    "/opt/homebrew/bin/soffice",
)


class RendererUnavailable(RuntimeError):
    """Raised when no LibreOffice binary can be located."""


def find_soffice() -> str | None:
    for candidate in _CANDIDATES:
        resolved = shutil.which(candidate) if "/" not in candidate else (
            candidate if Path(candidate).exists() else None
        )
        if resolved:
            return resolved
    return None


def render_pdf(docx_path: Path, output_dir: Path, timeout: int = 120) -> Path:
    """Convert a DOCX to PDF in output_dir and return the PDF path.

    Raises RendererUnavailable if LibreOffice is not installed, or
    RuntimeError if conversion fails or produces no file.
    """
    soffice = find_soffice()
    if soffice is None:
        raise RendererUnavailable(
            "LibreOffice (soffice) was not found. Install LibreOffice to enable "
            "PDF rendering (bundled in the Podman image for deployment)."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(docx_path),
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    produced = output_dir / (docx_path.stem + ".pdf")
    if result.returncode != 0 or not produced.exists():
        raise RuntimeError(
            f"PDF conversion failed (code {result.returncode}): {result.stderr.strip()}"
        )
    return produced
