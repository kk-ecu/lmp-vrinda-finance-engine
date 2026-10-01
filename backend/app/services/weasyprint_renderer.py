"""HTML -> PDF rendering via WeasyPrint.

WeasyPrint is pure-Python (BSD) but loads native Pango/cairo via cffi. If those
system libraries are missing it raises on import, so we import lazily and expose
availability so QA can report the gap cleanly instead of crashing.
"""
from __future__ import annotations

from pathlib import Path


class RendererUnavailable(RuntimeError):
    """Raised when WeasyPrint or its native dependencies are unavailable."""


def is_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except Exception:
        return False
    return True


def render_pdf_from_html(html: str, output_path: Path) -> Path:
    """Render an HTML string to a PDF at output_path."""
    try:
        from weasyprint import HTML
    except Exception as exc:  # ImportError or native-library load error
        raise RendererUnavailable(
            "WeasyPrint is unavailable. Ensure the package and the Pango/cairo "
            f"system libraries are installed. Underlying error: {exc}"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(output_path))
    return output_path
