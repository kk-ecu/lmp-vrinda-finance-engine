# API Specification — V1

The API is intentionally small.

## Health

```http
GET /api/health
```

## Months

```http
GET    /api/months
POST   /api/months
GET    /api/months/{month_id}
POST   /api/months/{month_id}/reopen
```

## Sources

```http
GET    /api/months/{month_id}/sources
POST   /api/months/{month_id}/sources
GET    /api/sources/{source_id}
DELETE /api/sources/{source_id}
```

DELETE should be logical deletion only where appropriate; original evidence should normally remain preserved.

## Extraction

```http
POST /api/months/{month_id}/extract
GET  /api/months/{month_id}/extraction-status
```

## Receipts

```http
GET    /api/months/{month_id}/receipts
POST   /api/months/{month_id}/receipts
PUT    /api/receipts/{receipt_id}
DELETE /api/receipts/{receipt_id}
```

## Payments

```http
GET    /api/months/{month_id}/payments
POST   /api/months/{month_id}/payments
PUT    /api/payments/{payment_id}
DELETE /api/payments/{payment_id}
```

## Validation

```http
POST /api/months/{month_id}/validate
GET  /api/months/{month_id}/validation
```

## Approval

```http
POST /api/months/{month_id}/approve
```

## Reports

```http
POST /api/months/{month_id}/generate
GET  /api/months/{month_id}/reports
GET  /api/reports/{report_id}/docx
GET  /api/reports/{report_id}/pdf
```

## Dashboard

```http
GET /api/dashboard
```

## API rules

- Validate all request payloads.
- Never trust client-side totals.
- Recalculate totals server-side.
- Return clear validation errors.
- Use consistent ISO dates in APIs.
- Use integer minor units or Decimal semantics for currency.
- Do not expose filesystem paths unnecessarily.
