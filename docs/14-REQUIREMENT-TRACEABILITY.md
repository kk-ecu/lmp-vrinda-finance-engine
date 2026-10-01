# Requirement Traceability

| Area | Requirement | V1 | Later |
|---|---|---:|---:|
| Month management | FR-001 | ✓ | |
| Source upload | FR-002 | ✓ | |
| Source immutability | FR-003 | ✓ | |
| Basic extraction | FR-004 | ✓ | Enhanced |
| OCR/AI extraction | FR-004 | | ✓ |
| Receipts | FR-005 | ✓ | |
| Payments | FR-006 | ✓ | |
| Opening balance | FR-007 | ✓ | |
| Corrections | FR-008 | ✓ | |
| Deterministic calculation | FR-009 | ✓ | |
| Reconciliation | FR-010 | ✓ | Enhanced |
| Exceptions | FR-011 | ✓ | |
| Approval | FR-012 | ✓ | |
| DOCX | FR-013 | ✓ | |
| PDF | FR-013 | ✓ | |
| Executive statement | FR-014 | ✓ | |
| Highlighted notes | FR-015 | ✓ | |
| Rendered QA | FR-016 | ✓ | Enhanced |
| Finalization | FR-017 | ✓ | |
| History | FR-018 | ✓ | |
| Export | FR-019 | ✓ | |
| Reopen/revision | FR-020 | ✓ | |
| Analytics | | | ✓ |
| Bank reconciliation | | | ✓ |
| Multi-user | | | ✓ |
| Cloud | | | Optional |
| AI assistant | | | Optional |

## V1 definition of done

A V1 release is complete when a user can:

```text
Create month
   ↓
Upload sources
   ↓
Enter/review financial data
   ↓
Validate
   ↓
Approve
   ↓
Generate DOCX
   ↓
Generate PDF
   ↓
Run QA
   ↓
Retrieve FINAL report
```

without requiring any external cloud service.
