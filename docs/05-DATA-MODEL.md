# Data Model

## Entity relationship

```mermaid
erDiagram
    MONTH ||--o{ SOURCE : contains
    MONTH ||--o{ RECEIPT : contains
    MONTH ||--o{ PAYMENT : contains
    MONTH ||--o{ CORRECTION : contains
    MONTH ||--o{ VALIDATION : has
    MONTH ||--o{ REPORT : produces

    SOURCE ||--o{ RECEIPT : supports
    SOURCE ||--o{ PAYMENT : supports

    MONTH {
      uuid id PK
      string period
      string status
      decimal opening_balance
      int revision
      datetime created_at
      datetime updated_at
    }

    SOURCE {
      uuid id PK
      uuid month_id FK
      string filename
      string mime_type
      string sha256
      string path
      string status
      datetime uploaded_at
    }

    RECEIPT {
      uuid id PK
      uuid month_id FK
      uuid source_id FK
      date receipt_date
      string type
      string flat_no
      string depositor
      string description
      decimal amount
      string status
    }

    PAYMENT {
      uuid id PK
      uuid month_id FK
      uuid source_id FK
      date payment_date
      string category
      string description
      string payee
      decimal amount
      string voucher
      string status
    }

    CORRECTION {
      uuid id PK
      uuid month_id FK
      string entity_type
      string entity_id
      string field_name
      string old_value
      string new_value
      string reason
      datetime created_at
    }

    VALIDATION {
      uuid id PK
      uuid month_id FK
      string check_name
      string result
      string message
      datetime checked_at
    }

    REPORT {
      uuid id PK
      uuid month_id FK
      int revision
      string docx_path
      string pdf_path
      string qa_status
      string status
      datetime generated_at
    }
```

## Calculation model

```text
Opening Balance = explicit approved opening value

Receipts = SUM(approved receipt amounts)

Payments = SUM(approved payment amounts)

Closing Balance =
    Opening Balance
    + Receipts
    - Payments
```

## Data integrity

Use decimal/numeric database fields for currency rather than floating-point arithmetic.

Currency should be represented to two decimal places where required.

Amounts displayed in Indian Rupee format:

```text
₹59,498
₹51,207
₹8,291
```
