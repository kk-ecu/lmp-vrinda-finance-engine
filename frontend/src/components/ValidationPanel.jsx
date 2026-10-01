import React from 'react';
import Badge from './Badge';

const PRETTY = {
  opening_balance_present: 'Opening balance present',
  has_transactions: 'Has transactions',
  amounts_present: 'All amounts present',
  no_negative_amounts: 'No negative amounts',
  dates_valid: 'Dates valid',
  no_unintended_duplicates: 'No duplicate transactions',
  arithmetic_consistent: 'Arithmetic consistent',
};

export default function ValidationPanel({ validation }) {
  if (!validation) return null;
  const t = validation.totals;
  return (
    <div className="panel">
      <div className="row-between">
        <h3 style={{ margin: 0 }}>Financial Validation</h3>
        <Badge status={validation.status} />
      </div>

      <div className="totals" style={{ marginTop: 16 }}>
        <div className="t-card receipts"><div className="v">{t.total_receipts_display}</div><div className="k">Total Receipts</div></div>
        <div className="t-card payments"><div className="v">{t.total_payments_display}</div><div className="k">Total Payments</div></div>
        <div className="t-card closing"><div className="v">{t.closing_balance_display}</div><div className="k">Closing Balance</div></div>
      </div>

      <div style={{ marginTop: 10 }}>
        {validation.checks.map((c) => (
          <div className="check" key={c.name}>
            <div>
              <div className="name">{PRETTY[c.name] || c.name}</div>
              {c.message && <div className="msg">{c.message}</div>}
            </div>
            <Badge status={c.result} />
          </div>
        ))}
      </div>
    </div>
  );
}
