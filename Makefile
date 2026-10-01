.PHONY: up down logs test backend frontend venv install-backend install-frontend

# --- Podman (containerized) ---
up:
	podman compose up --build

down:
	podman compose down

logs:
	podman compose logs -f

# --- Local development (no containers) ---
venv:
	cd backend && python3 -m venv .venv

install-backend: venv
	cd backend && .venv/bin/pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# Run the FastAPI backend from the venv.
backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run the Vite dev server on 5173 (3000 is used by Podman's gvproxy locally).
frontend:
	cd frontend && npm run dev

# --- Housekeeping ---
# Show garbage months (empty, non-final) without deleting.
clean-months-dryrun:
	cd backend && .venv/bin/python scripts/cleanup_months.py

# Delete empty, non-final months (FINAL/ARCHIVED are always protected).
clean-months:
	cd backend && .venv/bin/python scripts/cleanup_months.py --apply

# Force-delete ONE named period even if FINAL (test leftovers / mistakes).
# Usage: make clean-period PERIOD=2026-09
clean-period:
	cd backend && .venv/bin/python scripts/cleanup_months.py --apply --force-period $(PERIOD)

# Nuclear reset: wipe the entire dev database (re-seeds empty on next start).
reset-db:
	rm -f data/database/finance.db && echo "dev database reset"

# --- Auth ---
# Generate a bcrypt hash to paste into .env as AUTH_PASSWORD_HASH (password hidden).
hash-password:
	cd backend && .venv/bin/python scripts/hash_password.py

# --- Tests ---
test:
	cd backend && .venv/bin/python -m pytest -q
