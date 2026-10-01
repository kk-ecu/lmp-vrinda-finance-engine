import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import Badge from '../components/Badge';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
function periodLabel(period) {
  const [y, m] = period.split('-');
  return `${MONTH_NAMES[Number(m) - 1]} ${y}`;
}

export default function Admin({ onBack, onOpenMonth }) {
  const [months, setMonths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busyId, setBusyId] = useState('');

  async function load() {
    setLoading(true); setError('');
    try {
      const data = await api.adminListMonths();
      setMonths(data.months || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  async function remove(m) {
    if (!window.confirm(
      `Delete ${periodLabel(m.period)} (${m.status})?\n\nThis permanently removes its database rows and source/report files. This cannot be undone.`
    )) return;
    setBusyId(m.id); setError(''); setNotice('');
    try {
      await api.deleteMonth(m.id);
      setNotice(`Deleted ${periodLabel(m.period)}.`);
      await load();
    } catch (err) {
      setError(`Could not delete ${periodLabel(m.period)}: ${err.message}`);
    } finally {
      setBusyId('');
    }
  }

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <button className="link-btn" onClick={onBack}>← All months</button>
          <h1 style={{ marginTop: 6 }}>Admin — Manage Months</h1>
          <p>Review and delete months. Signed-off (FINAL/ARCHIVED) months are protected.</p>
        </div>
        <button className="ghost" onClick={load}>Refresh</button>
      </div>

      {error && <div className="panel err">{error}</div>}
      {notice && <div className="panel"><span className="ok">{notice}</span></div>}

      <div className="panel">
        {loading ? (
          <div className="empty">Loading…</div>
        ) : months.length === 0 ? (
          <div className="empty">No months in the database.</div>
        ) : (
          <table className="data">
            <thead>
              <tr>
                <th>Period</th><th>Status</th><th>Rev</th>
                <th>Sources</th><th>Receipts</th><th>Payments</th><th>Reports</th><th></th>
              </tr>
            </thead>
            <tbody>
              {months.map((m) => (
                <tr key={m.id}>
                  <td>
                    <button className="link-btn" onClick={() => onOpenMonth(m.id)}>{periodLabel(m.period)}</button>
                  </td>
                  <td><Badge status={m.status} /></td>
                  <td>{m.revision}</td>
                  <td>{m.sources}</td>
                  <td>{m.receipts}</td>
                  <td>{m.payments}</td>
                  <td>{m.reports}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    {m.deletable ? (
                      <button className="link-btn" style={{ color: 'var(--red)' }} disabled={busyId === m.id} onClick={() => remove(m)}>
                        {busyId === m.id ? 'deleting…' : 'delete'}
                      </button>
                    ) : (
                      <span className="muted" title="Signed-off months are protected. Reopen inside the month to make changes.">🔒 protected</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="muted" style={{ fontSize: 12 }}>
        FINAL and ARCHIVED months cannot be deleted here. To correct a signed-off month, open it and use Reopen (which creates a new revision).
      </p>
    </div>
  );
}
