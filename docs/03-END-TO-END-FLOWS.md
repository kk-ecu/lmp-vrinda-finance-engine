# End-to-End Flows

## Flow 1 — Create monthly statement

```mermaid
flowchart TD
    A[Select Month] --> B[Upload Source Documents]
    B --> C[Store Immutable Sources]
    C --> D[Extract Financial Facts]
    D --> E[Build Structured Dataset]
    E --> F[Run Financial Validation]
    F -->|Issues| G[Review Exceptions]
    G --> H[Correct or Confirm]
    H --> F
    F -->|PASS| I[User Financial Approval]
    I --> J[Generate DOCX]
    J --> K[Render PDF]
    K --> L[Rendered QA]
    L -->|FAIL| M[Regenerate / Fix Template]
    M --> J
    L -->|PASS| N[Mark FINAL]
```

## Flow 2 — Upload

```mermaid
sequenceDiagram
    actor User
    participant UI
    participant API
    participant Storage
    participant DB

    User->>UI: Select files
    UI->>API: POST /sources
    API->>Storage: Save original file
    API->>DB: Save source metadata + checksum
    API-->>UI: Source registered
```

## Flow 3 — Extraction

```mermaid
flowchart LR
    A[Source] --> B{File Type}
    B -->|PDF| C[PDF Parser]
    B -->|Image| D[Image/OCR Adapter]
    B -->|DOCX| E[DOCX Parser]
    B -->|XLSX| F[Spreadsheet Parser]
    B -->|TXT| G[Text Parser]
    C --> H[Normalized Facts]
    D --> H
    E --> H
    F --> H
    G --> H
    H --> I[Structured Dataset]
```

## Flow 4 — Exception handling

```mermaid
flowchart TD
    A[Extracted Record] --> B{Validation}
    B -->|PASS| C[Approved Candidate]
    B -->|FAIL| D[Exception]
    D --> E[Show Source + Extracted Value]
    E --> F{User Decision}
    F -->|Accept| C
    F -->|Correct| G[Record Correction]
    G --> C
    F -->|Reject| H[Remove/Ignore with Reason]
```

## Flow 5 — Financial validation

```mermaid
flowchart TD
    A[Approved Candidate Data] --> B[Calculate Receipts]
    A --> C[Calculate Payments]
    A --> D[Calculate Closing]
    B --> E[Cross Checks]
    C --> E
    D --> E
    E --> F{All Checks Pass?}
    F -->|No| G[REVIEW_REQUIRED]
    F -->|Yes| H[FINANCIAL_APPROVED]
```

## Flow 6 — Document generation

```mermaid
flowchart LR
    A[Approved Dataset] --> B[Statement Model]
    B --> C[DOCX Template]
    C --> D[DOCX]
    D --> E[PDF Renderer]
    E --> F[PDF]
```

## Flow 7 — Final QA

```mermaid
flowchart TD
    A[Generated PDF] --> B[Page Count]
    A --> C[Text Extraction]
    A --> D[Amount Presence]
    A --> E[Overflow/Clipping Checks]
    A --> F[Visual Preview]
    B --> G[QA Result]
    C --> G
    D --> G
    E --> G
    F --> G
    G --> H{PASS?}
    H -->|YES| I[FINAL]
    H -->|NO| J[REGENERATE]
```

## Flow 8 — Reopen final month

```mermaid
flowchart TD
    A[FINAL Month] --> B[Request Reopen]
    B --> C[Create Revision]
    C --> D[Edit Dataset]
    D --> E[Revalidate]
    E --> F[Regenerate]
    F --> G[New FINAL Revision]
```
