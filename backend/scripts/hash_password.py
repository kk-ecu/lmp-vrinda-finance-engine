"""Generate a bcrypt hash for AUTH_PASSWORD_HASH, without echoing the password.

Usage (from backend/, using the venv):
    .venv/bin/python scripts/hash_password.py
It prompts for the password (hidden), prints the hash to paste into .env.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import hash_password  # noqa: E402


def main() -> int:
    pw = getpass.getpass("New password: ")
    if not pw:
        print("Empty password; aborting.")
        return 1
    confirm = getpass.getpass("Confirm password: ")
    if pw != confirm:
        print("Passwords do not match; aborting.")
        return 1
    print("\nAdd this to your .env (single line):\n")
    print(f"AUTH_PASSWORD_HASH={hash_password(pw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
