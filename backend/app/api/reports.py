"""Report generation, rendering, QA, and download endpoints (FR-013..FR-017)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_month_or_404
from app.config.settings import get_settings
from app.db import get_db
from app.models import MonthStatus, QaStatus, Report
from app.money import format_amount
from app.services import finance_service, weasyprint_renderer
from app.services.docx_generator import generate_docx
from app.services.pdf_renderer import RendererUnavailable, find_soffice, render_pdf
from app.services.qa import run_qa
from app.services.report_html import build_report_html

router = APIRouter(prefix="/api", tags=["reports"])
settings = get_settings()


def _report_out(report: Report) -> dict:
    return {
        "id": report.id,
        "revision": report.revision,
        "qa_status": report.qa_status,
        "status": report.status,
        "generated_at": report.generated_at,
        "has_docx": bool(report.docx_path and Path(report.docx_path).exists()),
        "has_pdf": bool(report.pdf_path and Path(report.pdf_path).exists()),
        "qa_detail": json.loads(report.qa_detail) if report.qa_detail else None,
    }


@router.post("/months/{month_id}/generate")
def generate_report(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)

    # Gate: financial validation must pass before generation (FR-017).
    report_check = finance_service.validate(month)
    if not report_check.passed:
        raise HTTPException(
            status_code=409,
            detail="Financial validation must pass before generating a report.",
        )

    model = finance_service.build_report_model(month)
    totals = finance_service.compute_totals(month)

    year, mon = month.period.split("-")
    revision_dir = (
        settings.reports_dir / year / mon / f"revision-{month.revision:02d}"
    )
    docx_path = revision_dir / "statement.docx"
    generate_docx(model, docx_path)

    # Render the PDF. WeasyPrint (HTML->PDF) is the default engine; LibreOffice
    # (DOCX->PDF) is the configurable fallback. Both derive from the same model.
    pdf_path: Path | None = None
    renderer_available = False
    pdf_target = revision_dir / "statement.pdf"

    if settings.pdf_engine == "weasyprint" and weasyprint_renderer.is_available():
        renderer_available = True
        try:
            pdf_path = weasyprint_renderer.render_pdf_from_html(
                build_report_html(model), pdf_target
            )
        except weasyprint_renderer.RendererUnavailable:
            renderer_available = False
    elif settings.pdf_engine == "libreoffice" and find_soffice() is not None:
        renderer_available = True
        try:
            pdf_path = render_pdf(docx_path, revision_dir)
        except RendererUnavailable:
            renderer_available = False
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=f"PDF rendering failed: {exc}")

    expected_amounts = [
        format_amount(totals.total_receipts),
        format_amount(totals.total_payments),
        format_amount(totals.closing_balance),
    ]
    qa = run_qa(docx_path, pdf_path, expected_amounts, renderer_available)

    # Persist the report row and QA result.
    report = Report(
        month_id=month_id,
        revision=month.revision,
        docx_path=str(docx_path),
        pdf_path=str(pdf_path) if pdf_path else None,
        qa_status=qa.status,
        qa_detail=json.dumps({"status": qa.status, "page_count": qa.page_count, "checks": qa.checks}),
        status="GENERATED",
    )
    db.add(report)

    if qa.status == QaStatus.PASS:
        month.status = MonthStatus.FINAL
        report.status = MonthStatus.FINAL
    else:
        month.status = MonthStatus.GENERATED

    db.commit()
    db.refresh(report)
    return _report_out(report)


@router.get("/months/{month_id}/reports")
def list_reports(month_id: str, db: Session = Depends(get_db)):
    month = get_month_or_404(db, month_id)
    reports = sorted(month.reports, key=lambda r: r.generated_at, reverse=True)
    return [_report_out(r) for r in reports]


@router.get("/reports/{report_id}/docx")
def download_docx(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None or not report.docx_path or not Path(report.docx_path).exists():
        raise HTTPException(status_code=404, detail="DOCX not found")
    return FileResponse(
        report.docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"statement-{report.revision:02d}.docx",
    )


@router.get("/reports/{report_id}/pdf")
def download_pdf(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None or not report.pdf_path or not Path(report.pdf_path).exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        report.pdf_path,
        media_type="application/pdf",
        filename=f"statement-{report.revision:02d}.pdf",
    )
