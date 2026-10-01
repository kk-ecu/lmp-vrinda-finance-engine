"""HTML master template for the executive monthly financial statement.

The same ReportModel feeds both the DOCX generator and this HTML, which is
rendered to PDF by WeasyPrint. CSS targets a single A4 page with fixed table
layouts so amount columns never clip (document QA requirement).
"""
from __future__ import annotations

from html import escape

from app.services.finance_service import ReportModel

_CSS = """
@page {
    size: A4;
    margin: 12mm 10mm;
    @bottom-center {
        content: "LMP Vrinda Apartment Association \\2022 " string(period) " \\2022 Page " counter(page) " of " counter(pages);
        font-size: 7.5pt;
        color: #555;
        font-style: italic;
    }
}
* { box-sizing: border-box; }
body {
    font-family: "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a;
    font-size: 9pt;
    margin: 0;
}
.confidential { text-align: right; font-size: 7.5pt; font-weight: 700; color: #555; letter-spacing: 1px; }
h1 { text-align: center; color: #1F305E; font-size: 15pt; margin: 2px 0 0; letter-spacing: .5px; }
.subtitle { text-align: center; color: #555; font-size: 9.5pt; font-weight: 700; margin: 2px 0 0; }
.period { text-align: center; color: #1F305E; font-size: 11pt; font-weight: 700; margin: 2px 0 8px; string-set: period content(); }

.headline { width: 100%; border-collapse: collapse; margin: 6px 0 10px; }
.headline td { text-align: center; width: 33.33%; padding: 4px; }
.headline .amount { font-size: 16pt; font-weight: 700; }
.headline .label { font-size: 8pt; font-weight: 700; color: #555; letter-spacing: .5px; }
.amount.receipts { color: #1E7A3C; }
.amount.payments { color: #B10000; }
.amount.closing  { color: #1F305E; }

.band {
    background: #1F305E; color: #fff; font-weight: 700; font-size: 9pt;
    padding: 4px 8px; margin: 10px 0 0; border-radius: 2px;
}
table.txn { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 2px; }
table.txn th, table.txn td { border: 1px solid #c9ced8; padding: 3px 6px; font-size: 8.5pt; vertical-align: top; }
table.txn th { background: #F2F4F8; color: #1F305E; font-size: 8.5pt; text-align: left; }
col.sno { width: 7%; } col.date { width: 14%; } col.desc { width: 50%; }
col.vref { width: 15%; } col.amt { width: 14%; }
.c { text-align: center; } .r { text-align: right; } .b { font-weight: 700; }
.sub { color: #555; font-size: 7.5pt; }

.note-line { text-align: right; margin: 4px 0 0; font-size: 9.5pt; }
.note-line .lbl { color: #1F305E; font-weight: 700; }
.note-line .val { color: #B10000; font-weight: 700; }

table.summary { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 2px; }
table.summary th, table.summary td { border: 1px solid #c9ced8; padding: 3px 6px; font-size: 8.5pt; }
table.summary th { background: #F2F4F8; color: #1F305E; }

.notes { margin-top: 2px; }
.note { padding: 4px 8px; margin-top: 3px; border-radius: 2px; font-size: 8.5pt; }
.note.hl { background: #FFF3CD; border: 1px solid #FFE08A; }
.note .title { font-weight: 700; color: #B10000; }

.signatures { width: 100%; margin-top: 22px; border-collapse: collapse; }
.signatures td { text-align: center; width: 33.33%; }
.signatures .line { color: #555; }
.signatures .role { font-weight: 700; font-size: 9pt; }
"""


def _txn_rows(rows, with_voucher: bool) -> str:
    out = []
    for r in rows:
        desc_lines = escape(r.description).split("\n")
        desc_html = desc_lines[0] + "".join(
            f'<div class="sub">{line}</div>' for line in desc_lines[1:]
        )
        voucher = escape(r.voucher) if with_voucher else "-"
        out.append(
            f"<tr><td class='c'>{r.sno}</td><td class='c'>{escape(r.date)}</td>"
            f"<td>{desc_html}</td><td class='c'>{voucher}</td>"
            f"<td class='r b'>{escape(r.amount)}</td></tr>"
        )
    return "".join(out)


def _txn_table(rows, with_voucher: bool) -> str:
    header = (
        "<colgroup><col class='sno'><col class='date'><col class='desc'>"
        "<col class='vref'><col class='amt'></colgroup>"
        "<tr><th>S.No.</th><th>Date</th><th>Particulars / Details</th>"
        "<th>Voucher Ref</th><th class='r'>Amount</th></tr>"
    )
    return f"<table class='txn'>{header}{_txn_rows(rows, with_voucher)}</table>"


def _notes(model: ReportModel) -> str:
    if not model.notes:
        return ""
    items = []
    for i, n in enumerate(model.notes, start=1):
        cls = "note hl" if n.highlight else "note"
        title = escape(n.title.strip())
        body = escape(n.body.strip())
        if title:
            inner = f"<span class='title'>{i}. {title}:</span> {body}"
        else:
            inner = f"{i}. {body}"
        items.append(f"<div class='{cls}'>{inner}</div>")
    return f"<div class='notes'>{''.join(items)}</div>"


def build_report_html(model: ReportModel) -> str:
    receipts = _txn_table(model.receipt_rows, with_voucher=False)
    payments = _txn_table(model.payment_rows, with_voucher=True)
    period = escape(model.period_label)
    summary = (
        "<table class='summary'>"
        "<tr><th>Particular</th><th class='r'>Amount</th></tr>"
        f"<tr><td>Total Receipts</td><td class='r b'>{escape(model.total_receipts_display)}</td></tr>"
        f"<tr><td>Total Payments</td><td class='r b'>{escape(model.total_payments_display)}</td></tr>"
        f"<tr><td>Net Position</td><td class='r b'>{escape(model.net_position_display)} (Surplus)</td></tr>"
        f"<tr><td class='b'>Closing Balance</td><td class='r b'>{escape(model.closing_balance_display)} (Surplus)</td></tr>"
        "</table>"
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
  <div class="confidential">CONFIDENTIAL</div>
  <h1>LMP VRINDA APARTMENT ASSOCIATION</h1>
  <div class="subtitle">EXECUTIVE MONTHLY FINANCIAL STATEMENT</div>
  <div class="period">{period}</div>

  <table class="headline">
    <tr>
      <td><div class="amount receipts">{escape(model.total_receipts_display)}</div></td>
      <td><div class="amount payments">{escape(model.total_payments_display)}</div></td>
      <td><div class="amount closing">{escape(model.closing_balance_display)}</div></td>
    </tr>
    <tr>
      <td><div class="label">TOTAL RECEIPTS</div></td>
      <td><div class="label">TOTAL PAYMENTS</div></td>
      <td><div class="label">CLOSING BALANCE</div></td>
    </tr>
  </table>

  <div class="band">RECEIPT STATEMENT &bull; CASH INFLOW &bull; {period}</div>
  {receipts}

  <div class="band">PAYMENT STATEMENT &bull; CASH OUTFLOW &bull; {period}</div>
  {payments}
  <div class="note-line"><span class="lbl">TOTAL PAYMENTS</span> &nbsp; <span class="val">{escape(model.total_payments_display)}</span></div>

  <div class="band">FINANCIAL POSITION SUMMARY &bull; {period}</div>
  {summary}

  <div class="band">NOTES &bull; {period}</div>
  {_notes(model)}

  <table class="signatures">
    <tr><td class="line">________________</td><td class="line">________________</td><td class="line">________________</td></tr>
    <tr><td class="role">Treasurer</td><td class="role">Secretary</td><td class="role">President</td></tr>
  </table>
</body></html>"""
