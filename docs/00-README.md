# LMP Vrinda Finance Engine — Specification Pack

## Purpose

A lightweight, local-first monthly financial statement application for LMP Vrinda Apartment Association.

The application converts monthly source documents into a validated structured financial dataset and then generates a professional one-page executive financial statement in DOCX and PDF.

## Core principle

```text
Source Documents
      |
      v
Extraction
      |
      v
Structured Monthly Data
      |
      v
Financial Validation
      |
      v
User Approval
      |
      v
DOCX Generation
      |
      v
PDF Rendering
      |
      v
Visual QA
      |
      v
Final Statement
```

The user should experience only three meaningful actions:

1. Upload source documents.
2. Resolve exceptions.
3. Approve and generate.

## V1 technology boundary

V1 is intentionally small:

- Frontend: React
- Backend: FastAPI
- Database: SQLite
- File storage: local filesystem
- Document generation: DOCX
- PDF generation/rendering: local tooling
- Runtime: Podman
- Target machine: Apple Silicon Mac M2
- Deployment: local, single-user/small-user installation
- No Kubernetes
- No cloud dependency
- No Kafka
- No microservice fleet
- No external database

## Later phases

Later phases may add:

- OCR/AI-assisted extraction
- Bank statement ingestion
- Historical analytics
- Automated anomaly detection
- Multi-user access
- Role-based access
- Backup/export
- Optional cloud deployment
- Optional notifications
- Audit enhancements
- Configurable association templates

V1 must not be architected in a way that blocks these extensions.
