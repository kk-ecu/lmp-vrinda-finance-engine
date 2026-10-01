# LMP Vrinda Finance Engine

Lightweight, local-first monthly financial statement engine for LMP Vrinda Apartment Association.

## Product workflow

**Upload → Resolve Exceptions → Approve → Final Report**

Internally:

```text
Source Documents
      ↓
Extraction
      ↓
Structured Monthly Data
      ↓
Financial Validation
      ↓
User Approval
      ↓
DOCX Generation
      ↓
PDF Rendering
      ↓
Rendered QA
      ↓
FINAL
```

## V1 technology

- React
- FastAPI / Python
- SQLite
- Local filesystem
- DOCX generation
- PDF rendering
- Podman
- Apple Silicon Mac M2

No Kubernetes, Kafka, Redis, cloud database, or microservice fleet is required for V1.

## Workspace

```text
LMP-Vrinda-Finance-Engine/
├── README.md
├── Makefile
├── podman-compose.yml
├── .env.example
├── .gitignore
├── docs/                  # Complete product/specification pack
├── backend/               # FastAPI modular monolith
├── frontend/              # React application
├── data/                  # Persistent local data; not committed
└── scripts/               # Developer/operations scripts
```

## Start building

### Option A — editor-first

Open this directory in VS Code, Cursor, IntelliJ, PyCharm, or any editor.

### Option B — Podman

```bash
podman compose up --build
```

Frontend: `http://localhost:3000`
Backend: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

The V1 workspace is intentionally a small modular monolith. Keep the boundaries in the codebase, but do not split them into separate services unless a later requirement justifies it.

## Documentation starting point

Read `docs/INDEX.md`, then `docs/00-README.md` through `docs/17-V1-ARCHITECTURE-AT-A-GLANCE.md`.

## First implementation milestone

Build this vertical slice first:

```text
Create Month
 → Upload Source
 → Enter/Review Receipts & Payments
 → Validate
 → Approve
 → Generate DOCX/PDF
 → QA
 → Final
```
