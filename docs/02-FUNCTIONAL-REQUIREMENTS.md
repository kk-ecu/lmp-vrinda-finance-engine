# Functional Requirements

## FR-001 Monthly period management

The system shall allow creation and selection of a financial month.

Fields:

- year
- month
- status
- created timestamp
- updated timestamp

Statuses:

```text
DRAFT
EXTRACTED
REVIEW_REQUIRED
FINANCIAL_APPROVED
GENERATED
FINAL
ARCHIVED
```

## FR-002 Source document upload

The user shall upload source files associated with a month.

V1 supported formats should be:

- PDF
- PNG
- JPG/JPEG
- DOCX
- XLSX
- TXT

The application shall store files locally and record metadata in SQLite.

Metadata:

- source ID
- month ID
- original filename
- MIME type
- file size
- SHA-256 checksum
- upload timestamp
- processing status

## FR-003 Source immutability

Original source files shall not be modified.

Any transformed copy shall be stored separately.

## FR-004 Data extraction

The system shall extract financial facts from supported source files.

V1 should support deterministic/manual-assisted extraction first.

OCR/AI extraction should be an extension point rather than a mandatory dependency.

## FR-005 Receipt management

The system shall support:

- receipt date
- receipt type
- flat number
- depositor name
- description
- amount
- source reference
- confidence/status

## FR-006 Payment management

The system shall support:

- payment date
- category
- description
- vendor/payee
- amount
- voucher/reference
- source reference
- notes

## FR-007 Opening balance

The user shall enter or confirm opening balance.

## FR-008 Explicit corrections

Every correction shall record:

- original value
- corrected value
- field
- reason
- timestamp
- user/action source

## FR-009 Financial calculation

The system shall calculate:

```text
Total Receipts =
Opening Balance + all receipt inflows

Closing Balance =
Opening Balance + Receipts - Payments
```

The application must distinguish between opening balance and current-period receipts in the UI even if the executive report groups them under the financial position.

## FR-010 Reconciliation

The system shall independently calculate totals rather than trusting extracted totals.

Checks:

- receipt total
- payment total
- closing balance
- arithmetic consistency
- duplicate transaction detection
- missing amount detection
- invalid date detection
- negative amount detection where not allowed

## FR-011 Exception management

Any uncertain or inconsistent record shall enter REVIEW_REQUIRED.

Examples:

- amount missing;
- ambiguous date;
- duplicate transaction;
- source conflict;
- arithmetic mismatch;
- unreadable source;
- inconsistent depositor name.

## FR-012 Approval

The user shall explicitly approve the financial dataset before generation.

## FR-013 Document generation

The system shall generate:

- DOCX
- PDF

from the approved structured dataset.

## FR-014 Executive statement

The statement should contain, as applicable:

1. Association title
2. Reporting month
3. Opening balance
4. Receipts
5. Payments
6. Closing balance
7. Transaction details
8. Notes
9. Review/approval status

## FR-015 Highlighted notes

Important notes shall support:

- larger text;
- bold text;
- attention color;
- visually distinct blocks.

## FR-016 Rendered QA

The application shall render the generated document to PDF and run automated checks where practical.

At minimum:

- PDF exists;
- PDF is readable;
- page count is captured;
- amount cells contain values;
- document is not empty.

A visual review screen may be added in V1 if lightweight implementation permits.

## FR-017 Finalization

A statement can become FINAL only when:

```text
Financial Validation = PASS
AND
User Approval = YES
AND
Document Generation = PASS
AND
Rendered QA = PASS
```

## FR-018 Historical reports

The user shall be able to browse prior months and retrieve their generated reports.

## FR-019 Export

The user shall be able to export/download:

- DOCX
- PDF
- monthly data JSON
- optional CSV transaction export

## FR-020 Reopen

A FINAL month should be read-only by default.

Reopening requires an explicit action and creates a new revision.
