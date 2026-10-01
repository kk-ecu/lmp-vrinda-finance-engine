# Document Generation Specification

## Objective

Generate a professional one-page executive monthly financial statement.

## Template philosophy

The template defines:

- typography;
- spacing;
- table style;
- headings;
- notes;
- colors;
- margins;
- page structure.

The transaction data remains dynamic.

Do not hardcode a fixed number of transaction rows.

## Report structure

```text
------------------------------------------------
LMP VRINDA APARTMENT ASSOCIATION
Monthly Financial Statement
September 2026
------------------------------------------------

Opening Balance                         ₹998

RECEIPTS
Maintenance Collection              ₹58,500
Total Receipts                      ₹59,498

PAYMENTS
Date | Description | Amount | Voucher
...

TOTAL PAYMENTS                      ₹51,207

CLOSING BALANCE                      ₹8,291

NOTES
[Important attention notes]

------------------------------------------------
Prepared from approved monthly records
------------------------------------------------
```

## Document requirements

- One-page target for normal months.
- Automatic row expansion.
- Explicit amount column.
- Fixed-width table grids.
- Fixed table layout.
- No clipped headings.
- No hidden cells.
- Indian currency formatting.
- Consistent alignment.
- Attention notes visually distinct.

## Rendering pipeline

```text
Structured Dataset
       |
       v
Report View Model
       |
       v
DOCX Template
       |
       v
DOCX
       |
       v
PDF Renderer
       |
       v
PDF
       |
       v
QA
```

## Failure handling

If a report exceeds the intended page count:

1. identify cause;
2. reduce spacing/padding where safe;
3. adjust table layout;
4. regenerate;
5. rerun QA.

Do not silently remove financial information to force one page.
