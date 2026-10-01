"""Housekeeping: purge abandoned / empty 'garbage' months.

Safe by default (dry-run). FINAL and ARCHIVED months are NEVER touched — they
are signed-off records. Deletes a month's DB rows and its on-disk source/report
files.

Usage (from backend/, using the venv):
    .venv/bin/python scripts/cleanup_months.py                 # dry-run, show candidates
    .venv/bin/python scripts/cleanup_months.py --apply         # delete empty non-final months
    .venv/bin/python scripts/cleanup_months.py --apply --all-non-final  # delete ALL non-final months
    .venv/bin/python scripts/cleanup_months.py --apply --period 2026-09 # delete one non-final period
    .venv/bin/python scripts/cleanup_months.py --apply --force-period 2026-09  # delete a specific month EVEN IF FINAL

A month is 'garbage' (default rule) when it is NOT final/archived AND has zero
receipts and zero payments.

--force-period is a deliberate override to remove ONE named period regardless of
status (use for test leftovers or a wrongly-created signed month). It never does
bulk deletion — you must name the exact period.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Make the app importable when run from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.settings import get_settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Month, MonthStatus  # noqa: E402

PROTECTED = {MonthStatus.FINAL, MonthStatus.ARCHIVED}


def _remove_files(settings, period: str) -> None:
    year, mon = period.split("-")
    for base in (settings.sources_dir, settings.reports_dir):
        target = base / year / mon
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge abandoned/empty months.")
    parser.add_argument("--apply", action="store_true", help="Actually delete (default is dry-run).")
    parser.add_argument("--all-non-final", action="store_true", help="Delete ALL non-final months, even with data.")
    parser.add_argument("--period", help="Only consider this period (YYYY-MM).")
    parser.add_argument("--force-period", help="Delete this ONE period regardless of status (even FINAL).")
    args = parser.parse_args()

    init_db()
    settings = get_settings()
    db = SessionLocal()
    try:
        months = db.query(Month).all()

        # Deliberate single-period override — can remove a FINAL month.
        if args.force_period:
            candidates = [m for m in months if m.period == args.force_period]
            if not candidates:
                print(f"No month found for period {args.force_period}.")
                return 0
            print(f"{'DELETING' if args.apply else 'DRY-RUN — would delete'} (FORCED) {len(candidates)} month(s):")
            for m in candidates:
                print(f"  - {m.period}  status={m.status}  id={m.id}")
            if not args.apply:
                print("\nRe-run with --apply to force-delete this period.")
                return 0
            for m in candidates:
                period = m.period
                db.delete(m)
                db.commit()
                _remove_files(settings, period)
            print(f"\nForce-deleted {len(candidates)} month(s).")
            return 0

        candidates = []
        for m in months:
            if m.status in PROTECTED:
                continue
            if args.period and m.period != args.period:
                continue
            is_empty = len(m.receipts) == 0 and len(m.payments) == 0
            if args.all_non_final or is_empty:
                candidates.append(m)

        if not candidates:
            print("No garbage months found. Nothing to clean.")
            return 0

        print(f"{'DELETING' if args.apply else 'DRY-RUN — would delete'} {len(candidates)} month(s):")
        for m in candidates:
            print(f"  - {m.period}  status={m.status}  receipts={len(m.receipts)} payments={len(m.payments)}  id={m.id}")

        if not args.apply:
            print("\nRe-run with --apply to delete. FINAL/ARCHIVED months are always protected.")
            return 0

        for m in candidates:
            period = m.period
            db.delete(m)
            db.commit()
            _remove_files(settings, period)
        print(f"\nDeleted {len(candidates)} month(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
