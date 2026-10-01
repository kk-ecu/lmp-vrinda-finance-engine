"""Pytest fixtures: isolated in-memory-style SQLite DB per test session."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Point the app at a temporary database before importing it.
    db_file = tmp_path / "test_finance.db"
    monkeypatch.setenv("APP_ENV", "test")
    # Disable auth for the main app tests; auth itself is tested separately with
    # a dedicated client fixture that turns it on.
    monkeypatch.setenv("AUTH_ENABLED", "false")

    import app.db as db_module
    from app.config.settings import get_settings
    from app.db import Base

    get_settings.cache_clear()  # pick up the test env (AUTH_ENABLED, etc.)

    test_engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, future=True
    )
    TestingSessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )

    # Rebind the module-level engine/session used by get_db().
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(db_module, "SessionLocal", TestingSessionLocal)

    import app.models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=test_engine)

    from app.db import get_db
    from app.main import app

    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared helpers for feature/acceptance tests
# ---------------------------------------------------------------------------
SEPTEMBER_PAYMENTS = [
    ("2026-09-01", "Garbage Collection", "2500", "VC-SEP-01", None),
    ("2026-09-01", "Security Guard Salary", "11000", "VC-SEP-02", "Advance 30,000 referenced; 11,000 paid as salary."),
    ("2026-09-01", "Water Bill - Previous Supply Clearance", "26450", None, None),
    ("2026-09-05", "Broom, Phenyl & Other Housekeeping Items", "580", None, None),
    ("2026-09-07", "Electricity - BESCOM", "6177", None, None),
    ("2026-09-30", "Water Supply Vendor - Pooja (5 x 900)", "4500", None, None),
]


def create_month(client, year=2026, month=9, opening="7998"):
    r = client.post("/api/months", json={"year": year, "month": month, "opening_balance": opening})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def seed_september(client, with_correction=True):
    """Build the full September 2026 dataset. Returns the month id.

    Starts from the mis-extracted opening balance of 7,998 and (by default)
    applies the explicit correction to 998.
    """
    mid = create_month(client, opening="7998")
    client.post(
        f"/api/months/{mid}/receipts",
        json={"receipt_date": "2026-09-05", "description": "Maintenance Collection (13 Flats x 4,500)", "amount": "58500", "sort_order": 1},
    )
    for i, (d, desc, amt, vc, note) in enumerate(SEPTEMBER_PAYMENTS, start=1):
        client.post(
            f"/api/months/{mid}/payments",
            json={"payment_date": d, "description": desc, "amount": amt, "voucher": vc, "note": note, "sort_order": i},
        )
    if with_correction:
        client.post(
            f"/api/months/{mid}/corrections",
            json={"entity_type": "month", "entity_id": mid, "field_name": "opening_balance", "new_value": "998", "reason": "Extraction misread; source shows (+)998"},
        )
    return mid


@pytest.fixture()
def september(client):
    """A fully-seeded, corrected September 2026 month id."""
    return seed_september(client, with_correction=True)
