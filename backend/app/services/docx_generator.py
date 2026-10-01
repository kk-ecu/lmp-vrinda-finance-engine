"""DOCX generation for the one-page executive monthly financial statement.

Style-driven (ADR-008): the template defines typography, spacing, tables, and
colours; transaction rows expand dynamically from the report model. The layout
mirrors the approved sample output (output-validation/output/*.pdf).
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from app.services.finance_service import ReportModel

# Palette
_NAVY = RGBColor(0x1F, 0x30, 0x5E)
_GREEN = RGBColor(0x1E, 0x7A, 0x3C)
_GREY = RGBColor(0x55, 0x55, 0x55)
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_HIGHLIGHT = RGBColor(0xB1, 0x00, 0x00)
_HEADER_FILL = "1F305E"
_NOTE_FILL = "FFF3CD"
_BAND_FILL = "F2F4F8"


def _set_cell_bg(cell, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.makeelement(qn("w:shd"), {qn("w:val"): "clear", qn("w:fill"): hex_fill})
    tc_pr.append(shd)


def _no_space(paragraph) -> None:
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)


def _run(paragraph, text, size=10, bold=False, color=None, italic=False):
    r = paragraph.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r


def _heading_band(doc, text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.rows[0].cells[0]
    _set_cell_bg(cell, _HEADER_FILL)
    p = cell.paragraphs[0]
    _no_space(p)
    _run(p, text, size=10, bold=True, color=_WHITE)


def _transaction_table(doc, rows, with_voucher: bool) -> None:
    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Fixed layout so amount columns never clip (document QA requirement).
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.makeelement(qn("w:tblLayout"), {qn("w:type"): "fixed"})
    tbl_pr.append(layout)

    headers = ["S.No.", "Date", "Particulars / Details", "Voucher Ref", "Amount"]
    hdr = table.rows[0].cells
    for i, text in enumerate(headers):
        _set_cell_bg(hdr[i], _BAND_FILL)
        p = hdr[i].paragraphs[0]
        _no_space(p)
        if i == 4:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        _run(p, text, size=9, bold=True, color=_NAVY)

    for row in rows:
        cells = table.add_row().cells
        _write_cell(cells[0], str(row.sno), align="center")
        _write_cell(cells[1], row.date, align="center")
        _write_cell(cells[2], row.description)
        _write_cell(cells[3], row.voucher if with_voucher else "-", align="center")
        _write_cell(cells[4], row.amount, align="right", bold=True)


def _write_cell(cell, text, align="left", bold=False) -> None:
    # Support multi-line descriptions (e.g. "Opening Balance\nBrought Forward (+)").
    lines = text.split("\n")
    p = cell.paragraphs[0]
    _no_space(p)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _run(p, lines[0], size=9, bold=bold)
    for extra in lines[1:]:
        np = cell.add_paragraph()
        _no_space(np)
        _run(np, extra, size=8, color=_GREY)


def _headline_numbers(doc, model: ReportModel) -> None:
    table = doc.add_table(rows=2, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    values = [
        (model.total_receipts_display, "TOTAL RECEIPTS", _GREEN),
        (model.total_payments_display, "TOTAL PAYMENTS", _HIGHLIGHT),
        (model.closing_balance_display, "CLOSING BALANCE", _NAVY),
    ]
    for i, (amount, label, color) in enumerate(values):
        amount_cell = table.rows[0].cells[i]
        p = amount_cell.paragraphs[0]
        _no_space(p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p, amount, size=16, bold=True, color=color)

        label_cell = table.rows[1].cells[i]
        lp = label_cell.paragraphs[0]
        _no_space(lp)
        lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(lp, label, size=8, bold=True, color=_GREY)


def _summary_table(doc, model: ReportModel) -> None:
    rows = [
        ("Total Receipts", model.total_receipts_display),
        ("Total Payments", model.total_payments_display),
        ("Net Position", f"{model.net_position_display} (Surplus)"),
        ("Closing Balance", f"{model.closing_balance_display} (Surplus)"),
    ]
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    _set_cell_bg(hdr[0], _BAND_FILL)
    _set_cell_bg(hdr[1], _BAND_FILL)
    _run(hdr[0].paragraphs[0], "Particular", size=9, bold=True, color=_NAVY)
    rp = hdr[1].paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _run(rp, "Amount", size=9, bold=True, color=_NAVY)
    for label, amount in rows:
        cells = table.add_row().cells
        _write_cell(cells[0], label, bold=label.startswith("Closing"))
        _write_cell(cells[1], amount, align="right", bold=True)


def _notes_block(doc, model: ReportModel) -> None:
    _heading_band(doc, f"NOTES • {model.period_label}")
    if not model.notes:
        return
    table = doc.add_table(rows=len(model.notes), cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, note in enumerate(model.notes):
        cell = table.rows[i].cells[0]
        if note.highlight:
            _set_cell_bg(cell, _NOTE_FILL)
        p = cell.paragraphs[0]
        _no_space(p)
        title = note.title.strip()
        if title:
            _run(p, f"{i + 1}. {title}: ", size=9, bold=True, color=_HIGHLIGHT if note.highlight else _NAVY)
            _run(p, note.body.strip(), size=9)
        else:
            _run(p, f"{i + 1}. {note.body.strip()}", size=9)


def _signature_row(doc, model: ReportModel) -> None:
    doc.add_paragraph()
    table = doc.add_table(rows=2, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, role in enumerate(["Treasurer", "Secretary", "President"]):
        line_cell = table.rows[0].cells[i]
        lp = line_cell.paragraphs[0]
        _no_space(lp)
        lp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(lp, "________________", size=9, color=_GREY)
        role_cell = table.rows[1].cells[i]
        rp = role_cell.paragraphs[0]
        _no_space(rp)
        rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(rp, role, size=9, bold=True)

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(
        footer,
        f"LMP Vrinda Apartment Association • {model.period_label.title()} • Page 1 of 1",
        size=8,
        color=_GREY,
        italic=True,
    )


def generate_docx(model: ReportModel, output_path: Path) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Pt(28)
    section.bottom_margin = Pt(28)
    section.left_margin = Pt(36)
    section.right_margin = Pt(36)

    # Title block
    conf = doc.add_paragraph()
    conf.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _run(conf, "CONFIDENTIAL", size=8, bold=True, color=_GREY)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _no_space(title)
    _run(title, "LMP VRINDA APARTMENT ASSOCIATION", size=15, bold=True, color=_NAVY)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _no_space(subtitle)
    _run(subtitle, "EXECUTIVE MONTHLY FINANCIAL STATEMENT", size=10, bold=True, color=_GREY)

    period = doc.add_paragraph()
    period.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _no_space(period)
    _run(period, model.period_label, size=11, bold=True, color=_NAVY)

    doc.add_paragraph()
    _headline_numbers(doc, model)
    doc.add_paragraph()

    _heading_band(doc, f"RECEIPT STATEMENT • CASH INFLOW • {model.period_label}")
    _transaction_table(doc, model.receipt_rows, with_voucher=False)

    _heading_band(doc, f"PAYMENT STATEMENT • CASH OUTFLOW • {model.period_label}")
    _transaction_table(doc, model.payment_rows, with_voucher=True)

    total_p = doc.add_paragraph()
    total_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _run(total_p, "TOTAL PAYMENTS   ", size=10, bold=True, color=_NAVY)
    _run(total_p, model.total_payments_display, size=10, bold=True, color=_HIGHLIGHT)

    doc.add_paragraph()
    _heading_band(doc, f"FINANCIAL POSITION SUMMARY • {model.period_label}")
    _summary_table(doc, model)

    doc.add_paragraph()
    _notes_block(doc, model)
    _signature_row(doc, model)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
