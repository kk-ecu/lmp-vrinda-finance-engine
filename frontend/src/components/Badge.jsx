import React from 'react';

const CLASS_BY_STATUS = {
  DRAFT: 'draft',
  EXTRACTED: 'draft',
  REVIEW_REQUIRED: 'review',
  FINANCIAL_APPROVED: 'approved',
  GENERATED: 'generated',
  FINAL: 'final',
  ARCHIVED: 'draft',
  PASS: 'pass',
  FAIL: 'fail',
  NOT_RUN: 'draft',
};

const LABEL = {
  REVIEW_REQUIRED: 'REVIEW',
  FINANCIAL_APPROVED: 'APPROVED',
};

export default function Badge({ status }) {
  const cls = CLASS_BY_STATUS[status] || 'draft';
  const label = LABEL[status] || status;
  return <span className={`badge ${cls}`}>{label}</span>;
}
