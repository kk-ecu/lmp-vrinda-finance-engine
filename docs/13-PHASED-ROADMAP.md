# Phased Implementation Roadmap

## Phase 0 — Foundation

Goal: establish the repository and architecture.

Deliver:

- project structure;
- Podman setup;
- React shell;
- FastAPI shell;
- SQLite;
- local storage;
- health endpoint;
- basic configuration.

## Phase 1 — Core Monthly Workflow

Goal: complete the end-to-end workflow manually assisted.

Deliver:

- month management;
- source upload;
- receipt entry;
- payment entry;
- opening balance;
- deterministic calculations;
- validation;
- approval;
- DOCX generation;
- PDF generation;
- final report download.

This is the recommended V1.

## Phase 2 — Source Extraction

Goal: reduce manual data entry.

Add:

- PDF extraction;
- DOCX extraction;
- XLSX extraction;
- image OCR adapter;
- extraction confidence;
- exception review.

Important: AI/OCR output remains untrusted until reviewed.

## Phase 3 — Financial Intelligence

Add:

- duplicate detection;
- anomaly detection;
- month-over-month comparison;
- category trends;
- vendor trends;
- unusual payment warnings.

These are advisory signals, not automatic accounting decisions.

## Phase 4 — Historical Dashboard

Add:

- 12-month view;
- income/payment trend;
- closing balance trend;
- category breakdown;
- searchable transaction history.

Keep the dashboard lightweight.

## Phase 5 — Bank Reconciliation

Add optional:

- bank statement import;
- transaction matching;
- unmatched bank entries;
- unmatched ledger entries;
- reconciliation report.

## Phase 6 — Multi-user

Only if required:

- authentication;
- roles;
- reviewer/approver;
- concurrent users;
- audit trail.

## Phase 7 — Backup and Portability

Add:

- encrypted backup option;
- restore workflow;
- export package;
- migration tooling.

## Phase 8 — Optional Cloud

Only if there is a real need:

- remote access;
- managed database;
- object storage;
- hosted authentication.

The local-first architecture should remain supported.

## Phase 9 — AI Assistant

Potential capabilities:

- “Why did payments increase this month?”
- “Show all water-related payments.”
- “Find transactions without vouchers.”
- “Prepare the monthly report.”
- “Explain this reconciliation difference.”

AI must never directly alter financial records without explicit user confirmation.
