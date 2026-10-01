# Non-Functional Requirements

## NFR-001 Lightweight

V1 must run comfortably on an Apple Silicon M2 without requiring cloud infrastructure.

## NFR-002 Startup

Target application startup should be measured in seconds, not minutes.

## NFR-003 Resource efficiency

Avoid always-running heavyweight services.

Recommended V1 stack:

```text
React static frontend
FastAPI backend
SQLite
Local filesystem
DOCX/PDF tools
```

## NFR-004 Reliability

A failed document generation operation must not corrupt the approved dataset.

## NFR-005 Data integrity

Transactions must be stored transactionally.

## NFR-006 Local privacy

Financial source documents should remain on the local machine in V1.

## NFR-007 Backup

The application shall support a simple backup/export package containing:

```text
database
sources
reports
configuration
```

## NFR-008 Recoverability

The application shall be restartable without losing approved data.

## NFR-009 Determinism

Financial calculations must be deterministic and independently reproducible.

## NFR-010 Observability

V1 should provide:

- application log;
- processing log;
- report-generation log;
- validation result;
- QA result.

No external observability platform is required.

## NFR-011 Security

V1 local deployment should:

- bind only to localhost by default;
- avoid exposing the service publicly;
- restrict file access to application directories;
- validate uploaded file types;
- enforce reasonable file size limits.

## NFR-012 Authentication

V1 may remain single-user/local.

Authentication becomes a later-phase feature when remote/multi-user access is introduced.

## NFR-013 Maintainability

Use clear module boundaries and typed request/response models.

## NFR-014 Testability

Financial calculations and validation rules must have unit tests independent of DOCX/PDF rendering.
