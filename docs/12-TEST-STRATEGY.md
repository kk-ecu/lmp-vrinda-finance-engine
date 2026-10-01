# Test Strategy

## Unit tests

### Financial calculation

Test:

- zero receipts;
- zero payments;
- normal month;
- multiple receipts;
- multiple payments;
- decimal amounts;
- negative/invalid values;
- reconciliation mismatch.

## Extraction tests

For each supported source type:

- valid document;
- missing amount;
- malformed date;
- duplicate record;
- ambiguous text.

## API tests

Test every V1 endpoint for:

- valid request;
- invalid request;
- missing entity;
- invalid state transition.

## Document tests

Generate representative reports:

- few transactions;
- normal transactions;
- many transactions;
- long descriptions;
- multiple notes;
- no payments;
- no receipts.

## PDF QA tests

Verify:

- PDF opens;
- page count;
- expected headings;
- expected amounts;
- closing balance;
- no blank amount cells.

## Golden report test

Maintain a known approved monthly dataset and expected report characteristics.

```text
Input Dataset
     |
     v
Generate
     |
     v
Expected Financial Values
     |
     v
Expected PDF checks
```

## Regression principle

A change to document styling must not alter financial values.

A change to financial logic must not silently alter the document structure.
