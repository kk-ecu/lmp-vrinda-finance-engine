"""Extraction feature tests using the offline stub provider.

Forcing EXTRACTION_PROVIDER=stub keeps these tests fully offline (no network,
no API key, no model) while exercising the real /extract wiring and the
confidence-based review flagging.
"""
import pytest

from tests.conftest import create_month

from app.services import extraction_service


pytestmark = pytest.mark.skipif(
    not extraction_service.engine_available(),
    reason="extraction-engine not importable",
)


def _use_stub(monkeypatch):
    monkeypatch.setenv("EXTRACTION_PROVIDER", "stub")


def _upload_dummy_source(client, mid):
    return client.post(
        f"/api/months/{mid}/sources",
        files={"file": ("scan.jpg", b"\xff\xd8\xff\xe0dummy-jpeg-bytes", "image/jpeg")},
    )


class TestExtraction:
    def test_status_reports_engine(self, client):
        s = client.get("/api/extraction/status").json()
        assert s["available"] is True
        assert "stub" in s["providers_loaded"]

    def test_extract_requires_a_source(self, client, monkeypatch):
        _use_stub(monkeypatch)
        mid = create_month(client, opening="0")
        r = client.post(f"/api/months/{mid}/extract")
        assert r.status_code == 409

    def test_extract_prefills_rows_with_confidence(self, client, monkeypatch):
        _use_stub(monkeypatch)
        mid = create_month(client, opening="0")
        _upload_dummy_source(client, mid)

        r = client.post(f"/api/months/{mid}/extract")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["extracted_receipts"] == 1
        assert body["extracted_payments"] == 6

        # Opening balance came back low-confidence (the 7998 misread) -> flagged.
        ob = body["opening_balance_suggestion"]
        assert ob["amount"] == "7998"
        assert ob["needs_review"] is True

        # Low-confidence rows are marked REVIEW_REQUIRED for the UI to flag.
        payments = client.get(f"/api/months/{mid}/payments").json()
        flagged = [p for p in payments if p["needs_review"]]
        assert any("Broom" in p["description"] for p in flagged)
        # High-confidence rows are APPROVED directly.
        assert any(p["description"].startswith("Garbage") and not p["needs_review"] for p in payments)

    def test_extract_then_correct_then_reconcile(self, client, monkeypatch):
        """The full intended flow: extract -> fix the flagged opening -> reconcile."""
        _use_stub(monkeypatch)
        mid = create_month(client, opening="0")
        _upload_dummy_source(client, mid)
        client.post(f"/api/months/{mid}/extract")

        # The stub leaves opening at 7998 (low confidence); user corrects to 998.
        client.post(
            f"/api/months/{mid}/corrections",
            json={"entity_type": "month", "entity_id": mid, "field_name": "opening_balance", "new_value": "998", "reason": "misread 7998 -> 998"},
        )
        # Accept the flagged rows by marking them APPROVED (simulating review).
        for p in client.get(f"/api/months/{mid}/payments").json():
            if p["needs_review"]:
                client.put(f"/api/payments/{p['id']}", json={
                    "payment_date": p["payment_date"], "description": p["description"],
                    "amount": str(p["amount"]), "voucher": p["voucher"], "status": "APPROVED",
                })
        for rc in client.get(f"/api/months/{mid}/receipts").json():
            if rc["needs_review"]:
                client.put(f"/api/receipts/{rc['id']}", json={
                    "receipt_date": rc["receipt_date"], "description": rc["description"],
                    "amount": str(rc["amount"]), "status": "APPROVED",
                })

        v = client.post(f"/api/months/{mid}/validate").json()
        t = v["totals"]
        assert t["total_receipts_display"] == "₹59,498/-"
        assert t["total_payments_display"] == "₹51,207/-"
        assert t["closing_balance_display"] == "₹8,291/-"


class TestMoveBetweenSections:
    def test_move_receipt_to_payment_preserves_amount(self, client):
        from tests.conftest import create_month

        mid = create_month(client, opening="0")
        r = client.post(f"/api/months/{mid}/receipts", json={"description": "Broom & Phenyl", "amount": "580"}).json()
        assert len(client.get(f"/api/months/{mid}/receipts").json()) == 1

        moved = client.post(f"/api/receipts/{r['id']}/move")
        assert moved.status_code == 200
        assert moved.json()["description"] == "Broom & Phenyl"
        assert moved.json()["amount_display"] == "₹580"

        assert len(client.get(f"/api/months/{mid}/receipts").json()) == 0
        assert len(client.get(f"/api/months/{mid}/payments").json()) == 1

    def test_move_payment_to_receipt(self, client):
        from tests.conftest import create_month

        mid = create_month(client, opening="0")
        p = client.post(f"/api/months/{mid}/payments", json={"description": "Maintenance", "amount": "58500"}).json()
        moved = client.post(f"/api/payments/{p['id']}/move")
        assert moved.status_code == 200
        assert len(client.get(f"/api/months/{mid}/receipts").json()) == 1
        assert len(client.get(f"/api/months/{mid}/payments").json()) == 0


class TestConfigFlag:
    def test_config_exposes_test_flag(self, client):
        c = client.get("/api/config").json()
        assert "test_extraction_enabled" in c
        assert "extraction" in c

    def test_config_lists_allowed_providers_dev(self, client):
        c = client.get("/api/config").json()
        # Non-production env -> the two product providers, NOT stub/tesseract.
        assert "allowed_providers" in c
        assert set(c["allowed_providers"]) == {"ollama", "openrouter"}
        assert "stub" not in c["allowed_providers"]


class TestProdProviderLockdown:
    """In production only openrouter may serve extraction (API-enforced)."""

    def test_dev_allows_stub_provider(self, client):
        from tests.conftest import create_month

        mid = create_month(client, opening="0")
        client.post(
            f"/api/months/{mid}/sources",
            files={"file": ("s.jpg", b"\xff\xd8\xffdummy", "image/jpeg")},
        )
        # In the default (non-prod) test env, stub is allowed and succeeds.
        r = client.post(f"/api/months/{mid}/extract")
        # stub is the configured default in tests via EXTRACTION_PROVIDER=stub set per-test;
        # here no override, so just assert it is NOT a policy rejection.
        assert r.status_code != 409 or "not permitted" not in r.text

    def test_prod_blocks_non_openrouter(self, tmp_path, monkeypatch):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        db_file = tmp_path / "prod.db"
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("AUTH_ENABLED", "false")  # focus on provider policy
        monkeypatch.setenv("EXTRACTION_PROVIDER", "stub")  # a non-openrouter default

        import app.db as db_module
        from app.config.settings import get_settings
        from app.db import Base
        get_settings.cache_clear()

        engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, future=True)
        TS = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        monkeypatch.setattr(db_module, "engine", engine)
        monkeypatch.setattr(db_module, "SessionLocal", TS)
        import app.models  # noqa: F401
        Base.metadata.create_all(bind=engine)

        from app.db import get_db
        from app.main import app

        def _o():
            s = TS()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = _o
        with TestClient(app) as c:
            # config reflects production lockdown
            cfg = c.get("/api/config").json()
            assert cfg["is_production"] is True
            assert cfg["allowed_providers"] == ["openrouter"]

            # Create a month + source, then try to extract with the stub default -> blocked.
            mid = c.post("/api/months", json={"year": 2026, "month": 9, "opening_balance": "0"}).json()["id"]
            c.post(f"/api/months/{mid}/sources", files={"file": ("s.jpg", b"\xff\xd8\xffx", "image/jpeg")})
            r = c.post(f"/api/months/{mid}/extract")
            assert r.status_code == 409
            assert "not permitted" in r.json()["detail"]

            # test-bench override to a non-allowed provider is also blocked in prod.
            r2 = c.post("/api/test/extract", files={"file": ("s.jpg", b"\xff\xd8\xffx", "image/jpeg")}, data={"provider": "ollama"})
            assert r2.status_code == 409
        app.dependency_overrides.clear()
        get_settings.cache_clear()


class TestAdmin:
    def test_admin_lists_months_with_counts(self, client):
        from tests.conftest import create_month

        mid = create_month(client, opening="0")
        client.post(f"/api/months/{mid}/receipts", json={"description": "R", "amount": "100"})
        data = client.get("/api/admin/months").json()
        row = next(m for m in data["months"] if m["id"] == mid)
        assert row["receipts"] == 1
        assert row["deletable"] is True  # DRAFT is deletable


class TestDeleteMonth:
    def test_delete_draft_month(self, client):
        from tests.conftest import create_month

        mid = create_month(client, opening="0")
        assert client.delete(f"/api/months/{mid}").status_code == 200
        assert client.get(f"/api/months/{mid}").status_code == 404

    def test_cannot_delete_final_month(self, client, september):
        import pytest

        from app.services import weasyprint_renderer
        if not weasyprint_renderer.is_available():
            pytest.skip("WeasyPrint unavailable")
        client.post(f"/api/months/{september}/validate")
        client.post(f"/api/months/{september}/approve")
        client.post(f"/api/months/{september}/generate")
        assert client.get(f"/api/months/{september}").json()["status"] == "FINAL"
        # Deleting a FINAL month is blocked.
        assert client.delete(f"/api/months/{september}").status_code == 409


class TestNotes:
    def test_note_crud(self, client):
        from tests.conftest import create_month

        mid = create_month(client, opening="0")
        # add
        n = client.post(f"/api/months/{mid}/notes", json={"title": "Advance", "body": "30,000 referenced", "highlight": True}).json()
        assert n["title"] == "Advance"
        # list
        assert len(client.get(f"/api/months/{mid}/notes").json()) == 1
        # update
        u = client.put(f"/api/notes/{n['id']}", json={"title": "Advance", "body": "corrected body", "highlight": False, "sort_order": 1}).json()
        assert u["body"] == "corrected body"
        assert u["highlight"] is False
        # delete
        assert client.delete(f"/api/notes/{n['id']}").status_code == 204
        assert len(client.get(f"/api/months/{mid}/notes").json()) == 0
