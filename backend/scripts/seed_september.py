"""Seed the September 2026 month end-to-end against a running API.

Usage:
    .venv/bin/python scripts/seed_september.py [BASE_URL]

Drives the real 5-button workflow: create month -> upload sources ->
enter receipts/payments -> correct opening balance -> validate -> approve ->
generate. Prints the reconciled totals and QA result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = REPO_ROOT / "output-validation" / "input"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=120) as c:
        assert c.get("/api/health").json()["status"] == "ok"

        # 1. Create month with the (mis-extracted) opening balance 7,998.
        r = c.post("/api/months", json={"year": 2026, "month": 9, "opening_balance": "7998"})
        if r.status_code == 409:
            # Already seeded; find it.
            months = c.get("/api/months").json()
            mid = next(m["id"] for m in months if m["period"] == "2026-09")
            print("Month 2026-09 already exists:", mid)
            return 0
        r.raise_for_status()
        mid = r.json()["id"]
        print("Created month", mid)

        # 2. Upload the real source scans as immutable evidence.
        for img in sorted(INPUT_DIR.glob("*.jpeg")):
            with img.open("rb") as fh:
                resp = c.post(
                    f"/api/months/{mid}/sources",
                    files={"file": (img.name, fh, "image/jpeg")},
                )
            resp.raise_for_status()
            print("Uploaded source", img.name, "sha256", resp.json()["sha256"][:12])

        # 3. Receipts (maintenance). Opening balance lives on the month.
        c.post(
            f"/api/months/{mid}/receipts",
            json={"receipt_date": "2026-09-05", "type": "maintenance", "description": "Maintenance Collection (13 Flats x 4,500)", "amount": "58500", "sort_order": 1},
        ).raise_for_status()

        # 4. Payments.
        payments = [
            ("2026-09-01", "Garbage Collection", "2500", "VC-SEP-01", None),
            ("2026-09-01", "Security Guard Salary", "11000", "VC-SEP-02", "Advance of 30,000 referenced; 11,000 paid as September salary."),
            ("2026-09-01", "Water Bill - Previous Supply Clearance", "26450", None, None),
            ("2026-09-05", "Broom, Phenyl & Other Housekeeping Items", "580", None, None),
            ("2026-09-07", "Electricity - BESCOM", "6177", None, None),
            ("2026-09-30", "Water Supply Vendor - Pooja (5 x 900)", "4500", None, None),
        ]
        for i, (d, desc, amt, vc, note) in enumerate(payments, start=1):
            c.post(
                f"/api/months/{mid}/payments",
                json={"payment_date": d, "description": desc, "amount": amt, "voucher": vc, "note": note, "sort_order": i},
            ).raise_for_status()

        # 5. Explicit correction: opening balance 7,998 -> 998.
        c.post(
            f"/api/months/{mid}/corrections",
            json={"entity_type": "month", "entity_id": mid, "field_name": "opening_balance", "new_value": "998", "reason": "Extraction misread; source shows (+)998"},
        ).raise_for_status()

        # 6. Notes.
        c.post(f"/api/months/{mid}/notes", json={"title": "Security Guard Advance", "body": "An advance of 30,000/- is referenced in the records. The September statement records 11,000/- as the month's salary.", "highlight": True, "sort_order": 1}).raise_for_status()
        c.post(f"/api/months/{mid}/notes", json={"title": "Maintenance Payment - Flat No. 301", "body": "Rahul Singh deposited 4,500/- directly into the Association bank account; included in September receipts.", "highlight": True, "sort_order": 2}).raise_for_status()

        # 7. Validate.
        v = c.post(f"/api/months/{mid}/validate").json()
        print("\nValidation:", v["status"], "passed=", v["passed"])
        t = v["totals"]
        print("  Total Receipts :", t["total_receipts_display"])
        print("  Total Payments :", t["total_payments_display"])
        print("  Closing Balance:", t["closing_balance_display"])

        assert t["total_receipts_display"] == "₹59,498/-", t
        assert t["total_payments_display"] == "₹51,207/-", t
        assert t["closing_balance_display"] == "₹8,291/-", t

        # 8. Approve + generate.
        c.post(f"/api/months/{mid}/approve").raise_for_status()
        g = c.post(f"/api/months/{mid}/generate").json()
        print("\nReport:", g["id"], "status=", g["status"], "qa=", g["qa_status"])
        print("  has_docx:", g["has_docx"], " has_pdf:", g["has_pdf"])
        for chk in g["qa_detail"]["checks"]:
            print(f"    [{chk['result']}] {chk['name']} {chk['message']}")

        print("\nReconciliation verified: 998 + 58,500 - 51,207 = 8,291 ✓")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
