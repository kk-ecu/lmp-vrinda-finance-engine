"""Feature / acceptance tests for the LMP Vrinda Finance Engine.

These exercise product behavior end-to-end through the public API, mapped to the
functional requirements in docs/02-FUNCTIONAL-REQUIREMENTS.md. Each test names
the FR(s) it protects so regressions are traceable to a product promise.

The September 2026 baseline (docs/01 §9) is the canonical scenario:
    Opening 998 + Maintenance 58,500 = Total Receipts 59,498
    Total Payments 51,207  ->  Closing Balance 8,291
"""
import pytest

from tests.conftest import create_month, seed_september

from app.services import weasyprint_renderer


# ---------------------------------------------------------------------------
# FR-001 Monthly period management
# ---------------------------------------------------------------------------
class TestMonthlyPeriod:
    def test_create_and_list_month(self, client):
        mid = create_month(client, 2026, 9, "998")
        months = client.get("/api/months").json()
        assert any(m["id"] == mid and m["period"] == "2026-09" for m in months)

    def test_new_month_starts_in_draft(self, client):
        mid = create_month(client)
        assert client.get(f"/api/months/{mid}").json()["status"] == "DRAFT"

    def test_period_is_unique(self, client):
        create_month(client, 2026, 9)
        r = client.post("/api/months", json={"year": 2026, "month": 9, "opening_balance": "0"})
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# FR-002 / FR-003 Source upload and immutability
# ---------------------------------------------------------------------------
class TestSources:
    def test_upload_records_metadata_and_checksum(self, client):
        mid = create_month(client)
        r = client.post(
            f"/api/months/{mid}/sources",
            files={"file": ("statement.txt", b"opening balance 998", "text/plain")},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["filename"] == "statement.txt"
        assert len(body["sha256"]) == 64
        assert body["size_bytes"] == len(b"opening balance 998")

    def test_identical_content_has_identical_checksum(self, client):
        mid = create_month(client)
        content = b"same bytes"
        a = client.post(f"/api/months/{mid}/sources", files={"file": ("a.txt", content, "text/plain")}).json()
        b = client.post(f"/api/months/{mid}/sources", files={"file": ("b.txt", content, "text/plain")}).json()
        assert a["sha256"] == b["sha256"]

    def test_unsupported_file_type_rejected(self, client):
        mid = create_month(client)
        r = client.post(f"/api/months/{mid}/sources", files={"file": ("malware.exe", b"x", "application/octet-stream")})
        assert r.status_code == 400

    def test_empty_file_rejected(self, client):
        mid = create_month(client)
        r = client.post(f"/api/months/{mid}/sources", files={"file": ("empty.pdf", b"", "application/pdf")})
        assert r.status_code == 400

    def test_delete_is_logical_only(self, client):
        """FR-003: original evidence is preserved; delete flips status, not existence."""
        mid = create_month(client)
        s = client.post(f"/api/months/{mid}/sources", files={"file": ("a.txt", b"x", "text/plain")}).json()
        client.delete(f"/api/sources/{s['id']}")
        got = client.get(f"/api/sources/{s['id']}")
        assert got.status_code == 200
        assert got.json()["status"] == "IGNORED"


# ---------------------------------------------------------------------------
# FR-005/006/009/010 Transactions, calculation, reconciliation
# ---------------------------------------------------------------------------
class TestReconciliation:
    def test_september_reconciles_to_baseline(self, client, september):
        v = client.post(f"/api/months/{september}/validate").json()
        t = v["totals"]
        assert t["total_receipts_display"] == "₹59,498/-"
        assert t["total_payments_display"] == "₹51,207/-"
        assert t["closing_balance_display"] == "₹8,291/-"
        assert t["net_position_display"] == "₹8,291/-"

    def test_totals_are_server_computed_not_client_supplied(self, client):
        """FR-010: the system recalculates; a bogus posted amount can't fake a total."""
        mid = create_month(client, opening="998")
        client.post(f"/api/months/{mid}/receipts", json={"description": "A", "amount": "100"})
        client.post(f"/api/months/{mid}/receipts", json={"description": "B", "amount": "200"})
        t = client.post(f"/api/months/{mid}/validate").json()["totals"]
        # 998 + 100 + 200 = 1298
        assert t["total_receipts_display"] == "₹1,298/-"

    def test_rejected_lines_excluded(self, client):
        mid = create_month(client, opening="998")
        client.post(f"/api/months/{mid}/receipts", json={"description": "Keep", "amount": "58500", "receipt_date": "2026-09-05"})
        client.post(f"/api/months/{mid}/receipts", json={"description": "Drop", "amount": "58500", "status": "REJECTED"})
        t = client.post(f"/api/months/{mid}/validate").json()["totals"]
        assert t["total_receipts_display"] == "₹59,498/-"


# ---------------------------------------------------------------------------
# FR-008 Explicit corrections (ADR-006: never silent)
# ---------------------------------------------------------------------------
class TestCorrections:
    def test_correction_changes_value_and_is_audited(self, client):
        mid = seed_september(client, with_correction=False)
        before = client.post(f"/api/months/{mid}/validate").json()["totals"]
        assert before["closing_balance_display"] == "₹15,291/-"  # with the wrong 7,998

        client.post(
            f"/api/months/{mid}/corrections",
            json={"entity_type": "month", "entity_id": mid, "field_name": "opening_balance", "new_value": "998", "reason": "misread"},
        )
        after = client.post(f"/api/months/{mid}/validate").json()["totals"]
        assert after["closing_balance_display"] == "₹8,291/-"

        audit = client.get(f"/api/months/{mid}/corrections").json()
        assert len(audit) == 1
        assert audit[0]["old_value"] == "7998.00"
        assert audit[0]["new_value"] == "998"
        assert audit[0]["reason"] == "misread"
        assert audit[0]["created_at"]

    def test_receipt_amount_correction_audited(self, client):
        mid = create_month(client, opening="998")
        r = client.post(f"/api/months/{mid}/receipts", json={"description": "Maint", "amount": "50000"}).json()
        client.post(
            f"/api/months/{mid}/corrections",
            json={"entity_type": "receipt", "entity_id": r["id"], "field_name": "amount", "new_value": "58500", "reason": "typo"},
        )
        audit = client.get(f"/api/months/{mid}/corrections").json()
        assert audit[0]["old_value"] == "50000.00"
        updated = client.get(f"/api/months/{mid}/receipts").json()[0]
        assert updated["amount_display"] == "₹58,500"


# ---------------------------------------------------------------------------
# FR-011 Exception management (validation failures)
# ---------------------------------------------------------------------------
class TestExceptions:
    def test_missing_amount_flagged(self, client):
        mid = create_month(client, opening="998")
        client.post(f"/api/months/{mid}/receipts", json={"description": "Blank", "amount": "0"})
        v = client.post(f"/api/months/{mid}/validate").json()
        assert v["passed"] is False
        assert v["status"] == "REVIEW_REQUIRED"
        assert any(c["name"] == "amounts_present" and c["result"] == "FAIL" for c in v["checks"])

    def test_duplicate_transactions_flagged(self, client):
        mid = create_month(client, opening="998")
        for _ in range(2):
            client.post(f"/api/months/{mid}/payments", json={"payment_date": "2026-09-01", "description": "Garbage", "amount": "2500"})
        v = client.post(f"/api/months/{mid}/validate").json()
        assert any(c["name"] == "no_unintended_duplicates" and c["result"] == "FAIL" for c in v["checks"])


# ---------------------------------------------------------------------------
# FR-012 / FR-017 Approval and finalization gates
# ---------------------------------------------------------------------------
class TestApprovalAndFinalization:
    def test_cannot_approve_without_passing_validation(self, client):
        mid = create_month(client, opening="998")  # no transactions
        assert client.post(f"/api/months/{mid}/approve").status_code == 409

    def test_cannot_generate_before_validation_passes(self, client):
        mid = create_month(client, opening="998")
        assert client.post(f"/api/months/{mid}/generate").status_code == 409

    def test_approve_sets_status(self, client, september):
        client.post(f"/api/months/{september}/validate")
        r = client.post(f"/api/months/{september}/approve")
        assert r.status_code == 200
        assert r.json()["status"] == "FINANCIAL_APPROVED"


# ---------------------------------------------------------------------------
# FR-013/014/015 Document generation + FR-016 rendered QA
# ---------------------------------------------------------------------------
class TestDocumentAndQa:
    def test_docx_always_generated(self, client, september):
        client.post(f"/api/months/{september}/validate")
        client.post(f"/api/months/{september}/approve")
        g = client.post(f"/api/months/{september}/generate").json()
        assert g["has_docx"] is True
        assert client.get(f"/api/reports/{g['id']}/docx").status_code == 200

    def test_qa_detail_present(self, client, september):
        client.post(f"/api/months/{september}/validate")
        client.post(f"/api/months/{september}/approve")
        g = client.post(f"/api/months/{september}/generate").json()
        names = {c["name"] for c in g["qa_detail"]["checks"]}
        assert "docx_exists" in names

    @pytest.mark.skipif(not weasyprint_renderer.is_available(), reason="WeasyPrint/Pango unavailable")
    def test_full_pipeline_reaches_final_with_pdf(self, client, september):
        client.post(f"/api/months/{september}/validate")
        client.post(f"/api/months/{september}/approve")
        g = client.post(f"/api/months/{september}/generate").json()
        assert g["qa_status"] == "PASS", g["qa_detail"]
        assert g["status"] == "FINAL"
        assert g["has_pdf"] is True

        pdf = client.get(f"/api/reports/{g['id']}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert client.get(f"/api/months/{september}").json()["status"] == "FINAL"


# ---------------------------------------------------------------------------
# FR-018 Historical reports / dashboard
# ---------------------------------------------------------------------------
class TestDashboard:
    def test_dashboard_shows_month_totals(self, client, september):
        client.post(f"/api/months/{september}/validate")
        months = client.get("/api/dashboard").json()["months"]
        sep = next(m for m in months if m["period"] == "2026-09")
        assert sep["total_receipts_display"] == "₹59,498/-"
        assert sep["closing_balance_display"] == "₹8,291/-"


# ---------------------------------------------------------------------------
# FR-020 Reopen (new revision)
# ---------------------------------------------------------------------------
class TestReopen:
    def _finalize(self, client, mid):
        client.post(f"/api/months/{mid}/validate")
        client.post(f"/api/months/{mid}/approve")
        client.post(f"/api/months/{mid}/generate")

    @pytest.mark.skipif(not weasyprint_renderer.is_available(), reason="WeasyPrint/Pango unavailable")
    def test_reopen_with_reason_creates_new_revision(self, client, september):
        self._finalize(client, september)
        assert client.get(f"/api/months/{september}").json()["status"] == "FINAL"

        r = client.post(f"/api/months/{september}/reopen", json={"reason": "Correcting the water bill amount"})
        assert r.status_code == 200
        assert r.json()["revision"] == 2
        assert r.json()["status"] == "FINANCIAL_APPROVED"

    @pytest.mark.skipif(not weasyprint_renderer.is_available(), reason="WeasyPrint/Pango unavailable")
    def test_reopen_requires_a_reason(self, client, september):
        self._finalize(client, september)
        # Empty / too-short reason is rejected.
        assert client.post(f"/api/months/{september}/reopen", json={"reason": ""}).status_code == 400
        assert client.post(f"/api/months/{september}/reopen", json={"reason": "x"}).status_code == 400

    @pytest.mark.skipif(not weasyprint_renderer.is_available(), reason="WeasyPrint/Pango unavailable")
    def test_reopen_is_audited(self, client, september):
        self._finalize(client, september)
        client.post(f"/api/months/{september}/reopen", json={"reason": "Fix guard salary"})
        corrections = client.get(f"/api/months/{september}/corrections").json()
        audit = [c for c in corrections if c["field_name"] == "status"]
        assert len(audit) == 1
        assert audit[0]["reason"] == "Fix guard salary"
        assert "FINAL" in audit[0]["old_value"]
        assert "REOPENED" in audit[0]["new_value"]

    @pytest.mark.skipif(not weasyprint_renderer.is_available(), reason="WeasyPrint/Pango unavailable")
    def test_prior_revision_pdf_preserved_after_reopen_and_regenerate(self, client, september):
        self._finalize(client, september)
        rev1 = client.get(f"/api/months/{september}/reports").json()[0]
        assert rev1["revision"] == 1 and rev1["has_pdf"]

        client.post(f"/api/months/{september}/reopen", json={"reason": "Amend figures"})
        # Regenerate -> produces revision 2.
        client.post(f"/api/months/{september}/approve")
        client.post(f"/api/months/{september}/generate")

        reports = client.get(f"/api/months/{september}/reports").json()
        revisions = sorted(r["revision"] for r in reports)
        assert revisions == [1, 2], revisions
        # The ORIGINAL revision-1 PDF is still downloadable (not overwritten).
        assert client.get(f"/api/reports/{rev1['id']}/pdf").status_code == 200

    def test_cannot_reopen_non_final(self, client, september):
        assert client.post(f"/api/months/{september}/reopen", json={"reason": "whatever"}).status_code == 409
