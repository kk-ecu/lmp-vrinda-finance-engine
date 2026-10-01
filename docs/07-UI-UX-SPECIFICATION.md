# UI / UX Specification

## UX objective

The user should never feel that they are operating an accounting system.

The application should feel like a monthly reporting assistant.

## Screen 1 — Dashboard

```text
LMP VRINDA FINANCE

[ New Month ]

September 2026     FINAL
Receipts            ₹59,498
Payments            ₹51,207
Closing Balance      ₹8,291

[ View ]

October 2026        DRAFT
[ Continue ]
```

## Screen 2 — Month Workspace

```text
September 2026

1  SOURCES        ✓
2  DATA           ✓
3  VALIDATION     ⚠
4  APPROVAL       -
5  REPORT         -
```

Main actions:

```text
[ Upload Documents ]
[ Review Data ]
[ Validate ]
[ Approve & Generate ]
```

## Screen 3 — Exception Review

Each exception should show:

```text
ATTENTION REQUIRED

Field: Opening Balance
Extracted: ₹7,998
Source: payment-statement.pdf

[ Use ₹998 ]
[ Keep ₹7,998 ]
[ Edit ]
```

## Screen 4 — Financial Review

```text
FINANCIAL VALIDATION

Opening Balance            ₹998       ✓
Receipts                ₹58,500       ✓
Total Receipts           ₹59,498       ✓
Payments                 ₹51,207       ✓
Closing Balance            ₹8,291      ✓

Arithmetic                 PASS        ✓
Duplicates                 PASS        ✓
Missing Amounts             PASS        ✓

[ APPROVE & GENERATE ]
```

## Screen 5 — Report

```text
REPORT READY

Financial Validation       PASS
DOCX Generation            PASS
PDF Generation             PASS
Visual QA                  PASS

[ Open PDF ]
[ Open DOCX ]
[ Download Package ]
```

## UX rules

- Avoid dashboards with excessive charts in V1.
- Avoid unnecessary navigation.
- Keep the current month prominent.
- Use clear status badges.
- Make errors actionable.
- Never hide a financial discrepancy.
- Always show the source when asking for a correction.
