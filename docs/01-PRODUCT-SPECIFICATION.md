# Product Specification

## 1. Product name

**LMP Vrinda Finance Engine**

## 2. Product objective

Provide a reliable and lightweight workflow for producing the monthly financial statement of LMP Vrinda Apartment Association without manually maintaining Word documents, calculating totals, or performing repeated visual QA.

## 3. Problem statement

The current process can become document-centric:

- information is extracted manually;
- amounts may be mistyped;
- calculations are repeated;
- Word formatting can break;
- amount columns can disappear or clip;
- source corrections can be difficult to trace;
- final PDF requires visual inspection.

The new product makes the structured financial dataset the source of truth.

## 4. Product outcome

For each month, the system produces:

- approved monthly financial dataset;
- reconciliation result;
- review status;
- DOCX statement;
- PDF statement;
- source-document references;
- exception/correction history.

## 5. Primary user

RWA financial administrator / association representative.

## 6. Primary use case

Create one monthly executive financial statement from source receipts, payment records, bank statements, notes, or images.

## 7. Design principles

### Simple
The UI should expose only what is necessary.

### Local-first
All financial documents remain on the local machine in V1.

### Data-first
DOCX/PDF are outputs, not the system of record.

### Explicit corrections
The system never silently changes extracted values.

### Deterministic calculations
Totals and balances are calculated by code.

### Review gates
A report cannot become FINAL unless financial validation passes and the user approves it.

### Lightweight
Prefer a modular monolith over distributed architecture.

## 8. Success criteria

A monthly report should normally require:

- upload;
- review exceptions;
- approve;
- generate.

The final PDF must have:

- correct values;
- visible amount columns;
- correct totals;
- correct closing balance;
- professional formatting;
- no clipping or overflow;
- intended page count;
- attention notes visibly highlighted.

## 9. Example September 2026 baseline

Known approved example:

- Opening balance: ₹998
- Maintenance collection: ₹58,500
- Total receipts: ₹59,498
- Total payments: ₹51,207
- Closing balance: ₹8,291
- Flat 301 depositor: Rahul Singh

The system must support explicit user corrections such as changing an extracted ₹7,998 to ₹998 rather than silently correcting it.
