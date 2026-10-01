# LMP Vrinda Finance Engine

Local-first monthly financial-statement engine for LMP Vrinda Apartment
Association. It turns scanned source documents into a validated, signed one-page
statement (DOCX + PDF).

**Workflow:** Upload scan → Extract → Review & correct → Approve → Generate → Final.

Internally: `Source → Extraction → Structured data → Validation → Approval →
DOCX → PDF → QA → FINAL` (amendable only via an audited Reopen → new revision).

## Stack
React (Vite) · FastAPI · SQLite · WeasyPrint (DOCX/PDF) · JWT auth · Caddy +
Docker · pluggable extraction engine. Single-admin, local-first; no cloud DB,
queue, or microservices.

## Extraction providers (two)
| Provider | When | Notes |
|---|---|---|
| **openrouter** (cloud, Gemini 2.5 Flash) | **PROD default & only allowed** | needs `OPENROUTER_API_KEY` |
| **ollama** (local, qwen2.5vl:7b) | **DEV default** | needs Ollama + the model + RAM |

(`stub` exists for offline tests only — not a product provider.) The default is
chosen from `APP_ENV` (dev→ollama, prod→openrouter) and enforced by the API.

## Run locally (development)
```bash
make install-backend          # creates backend/.venv and installs deps
make install-frontend         # npm install
cp .env.example .env          # then set AUTH_PASSWORD_HASH (make hash-password) etc.
make backend                  # FastAPI on :8000
make frontend                 # Vite on :5173   (3000 is used by Podman's gvproxy)
```
Open `http://localhost:5173`. API docs at `http://localhost:8000/docs`.

## Deploy to a VPS (production)
One script does everything (installs Docker, generates secrets, builds, HTTPS):
```bash
git clone <repo> && cd lmp-vrinda-finance-engine
./deploy.sh                   # answers: env, domain, admin password, OpenRouter key
```
See **`deploy/README.md`** for the full guide (DNS, HTTPS, updates, backups).

## Tests
```bash
make test                     # backend pytest suite
```

## Documentation (authoritative, kept current)
- **`docs/ARCHITECTURE.md`** — overall architecture, system design, feature
  catalog, use cases, full C4 model, data model, env policy. **Start here.**
- **`docs/DEBUGGING.md`** — layer-by-layer troubleshooting runbook.
- **`deploy/README.md`** — VPS deployment & operations.
- **`extraction-engine/README.md`** — extraction engine internals & config.

### Original specification pack (historical design intent)
`docs/00`–`docs/18` are the original V1 specification written *before*
implementation. They capture the intended design and requirements. For the
**current, as-built** system, rely on `ARCHITECTURE.md` above — where the two
differ, the implementation docs win.

## Data & backup
All state lives in `./data` (SQLite DB + source scans + generated reports).
Back up = copy that folder: `tar czf backup-$(date +%F).tar.gz data/`.
