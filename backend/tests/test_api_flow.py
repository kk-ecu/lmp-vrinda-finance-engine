"""End-to-end API flow for the September 2026 month.

Covers: create month -> add receipts/payments -> explicit correction ->
validate -> approve, reconciling to the baseline figures.
"""


def _september(client):
    r = client.post("/api/months", json={"year": 2026, "month": 9, "opening_balance": "7998"})
    assert r.status_code == 201, r.text
    month = r.json()
    mid = month["id"]

    # Receipt line (maintenance). Opening balance lives on the month itself.
    client.post(
        f"/api/months/{mid}/receipts",
        json={"receipt_date": "2026-09-05", "description": "Maintenance Collection", "amount": "58500", "sort_order": 1},
    )

    payments = [
        ("2026-09-01", "Garbage Collection", "2500", "VC-SEP-01"),
        ("2026-09-01", "Security Guard Salary", "11000", "VC-SEP-02"),
        ("2026-09-01", "Water Bill - Previous Supply Clearance", "26450", None),
        ("2026-09-05", "Broom, Phenyl & Other Housekeeping", "580", None),
        ("2026-09-07", "Electricity - BESCOM", "6177", None),
        ("2026-09-30", "Water Supply Vendor - Pooja", "4500", None),
    ]
    for i, (d, desc, amt, vc) in enumerate(payments, start=1):
        client.post(
            f"/api/months/{mid}/payments",
            json={"payment_date": d, "description": desc, "amount": amt, "voucher": vc, "sort_order": i},
        )
    return mid


def test_full_flow_reconciles_after_correction(client):
    mid = _september(client)

    # Explicit correction of the opening balance 7,998 -> 998 (the hero case).
    r = client.post(
        f"/api/months/{mid}/corrections",
        json={
            "entity_type": "month",
            "entity_id": mid,
            "field_name": "opening_balance",
            "new_value": "998",
            "reason": "Extraction misread; source shows (+)998",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["old_value"] == "7998.00"
    assert r.json()["new_value"] == "998"

    # Validate.
    r = client.post(f"/api/months/{mid}/validate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["passed"] is True, body["checks"]
    assert body["status"] == "FINANCIAL_APPROVED"

    totals = body["totals"]
    assert totals["total_receipts_display"] == "₹59,498/-"
    assert totals["total_payments_display"] == "₹51,207/-"
    assert totals["closing_balance_display"] == "₹8,291/-"

    # Approve.
    r = client.post(f"/api/months/{mid}/approve")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "FINANCIAL_APPROVED"


def test_correction_is_audited(client):
    mid = _september(client)
    client.post(
        f"/api/months/{mid}/corrections",
        json={"entity_type": "month", "entity_id": mid, "field_name": "opening_balance", "new_value": "998", "reason": "fix"},
    )
    r = client.get(f"/api/months/{mid}/corrections")
    assert r.status_code == 200
    corrections = r.json()
    assert len(corrections) == 1
    assert corrections[0]["old_value"] == "7998.00"
    assert corrections[0]["reason"] == "fix"


def test_approve_blocked_when_validation_fails(client):
    r = client.post("/api/months", json={"year": 2026, "month": 10, "opening_balance": "100"})
    mid = r.json()["id"]
    # No transactions -> has_transactions fails.
    r = client.post(f"/api/months/{mid}/approve")
    assert r.status_code == 409


def test_duplicate_month_rejected(client):
    client.post("/api/months", json={"year": 2026, "month": 9, "opening_balance": "0"})
    r = client.post("/api/months", json={"year": 2026, "month": 9, "opening_balance": "0"})
    assert r.status_code == 409


def test_generate_produces_docx_and_runs_qa(client):
    from pathlib import Path

    mid = _september(client)
    client.post(
        f"/api/months/{mid}/corrections",
        json={"entity_type": "month", "entity_id": mid, "field_name": "opening_balance", "new_value": "998", "reason": "fix"},
    )
    client.post(f"/api/months/{mid}/validate")

    client.post(
        f"/api/months/{mid}/notes",
        json={"title": "Security Guard Advance", "body": "Advance of 30,000 referenced; 11,000 recorded as salary.", "highlight": True, "sort_order": 1},
    )

    r = client.post(f"/api/months/{mid}/generate")
    assert r.status_code == 200, r.text
    body = r.json()

    # DOCX is always produced (system-of-record output).
    assert body["has_docx"] is True
    docx_report = client.get(f"/api/reports/{body['id']}/docx")
    assert docx_report.status_code == 200

    # QA detail is attached.
    assert body["qa_detail"] is not None
    check_names = {c["name"]: c["result"] for c in body["qa_detail"]["checks"]}
    assert check_names["docx_exists"] == "PASS"
    # On a machine without LibreOffice the renderer check reports the gap.
    assert "pdf_renderer_available" in check_names


def test_generate_blocked_before_validation_passes(client):
    r = client.post("/api/months", json={"year": 2026, "month": 11, "opening_balance": "0"})
    mid = r.json()["id"]
    r = client.post(f"/api/months/{mid}/generate")
    assert r.status_code == 409


def test_weasyprint_generates_pdf_and_reaches_final(client):
    import pytest

    from app.services import weasyprint_renderer

    if not weasyprint_renderer.is_available():
        pytest.skip("WeasyPrint/Pango not available in this environment")

    mid = _september(client)
    client.post(
        f"/api/months/{mid}/corrections",
        json={"entity_type": "month", "entity_id": mid, "field_name": "opening_balance", "new_value": "998", "reason": "fix"},
    )
    client.post(f"/api/months/{mid}/validate")
    client.post(f"/api/months/{mid}/approve")

    r = client.post(f"/api/months/{mid}/generate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_pdf"] is True
    assert body["qa_status"] == "PASS", body["qa_detail"]
    assert body["status"] == "FINAL"

    # PDF is downloadable and the key amounts are present in the rendered text.
    pdf = client.get(f"/api/reports/{body['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"

    # Month reflects FINAL.
    assert client.get(f"/api/months/{mid}").json()["status"] == "FINAL"
