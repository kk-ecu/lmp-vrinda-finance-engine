import React, { useState } from 'react';
import { api } from '../services/api';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export default function NewMonthModal({ onClose, onCreated }) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      // Opening balance is read from the scan during extraction (and editable
      // in Review), so it is not asked for here. Start at 0.
      const created = await api.createMonth({ year: Number(year), month: Number(month), openingBalance: '0' });
      onCreated(created);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>New Month</h3>
        <form onSubmit={submit}>
          <div className="form-grid">
            <div className="field">
              <label>Month</label>
              <select value={month} onChange={(e) => setMonth(e.target.value)}>
                {MONTHS.map((m, i) => (
                  <option key={m} value={i + 1}>{m}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Year</label>
              <input type="number" value={year} min="2000" max="2100" onChange={(e) => setYear(e.target.value)} />
            </div>
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Opening balance and transactions are read from the uploaded scan in the next steps.
          </p>
          {error && <div className="err">{error}</div>}
          <div className="actions">
            <button type="button" className="ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary" disabled={busy}>{busy ? 'Creating…' : 'Create Month'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
