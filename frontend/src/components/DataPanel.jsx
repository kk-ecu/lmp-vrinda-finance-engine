import React, { useState } from 'react';
import { api } from '../services/api';

function confidenceLabel(c) {
  if (c >= 0.8) return { text: `${Math.round(c * 100)}%`, cls: 'pass' };
  if (c >= 0.5) return { text: `${Math.round(c * 100)}%`, cls: 'review' };
  return { text: `${Math.round(c * 100)}%`, cls: 'fail' };
}

// An existing receipt/payment row with inline edit + accept + move (for review).
function EditableRow({ row, kind, onChange, readOnly }) {
  const [editing, setEditing] = useState(false);
  const [f, setF] = useState({
    date: kind === 'receipt' ? row.receipt_date || '' : row.payment_date || '',
    description: row.description || '',
    voucher: row.voucher || '',
    amount: String(row.amount ?? ''),
  });
  const flagged = row.needs_review;

  async function save(status) {
    const base = {
      description: f.description,
      amount: f.amount,
      status: status || row.status,
    };
    if (kind === 'receipt') {
      await api.updateReceipt(row.id, { ...base, receipt_date: f.date || null });
    } else {
      await api.updatePayment(row.id, { ...base, payment_date: f.date || null, voucher: f.voucher || null });
    }
    setEditing(false);
    await onChange();
  }

  async function remove() {
    if (kind === 'receipt') await api.deleteReceipt(row.id);
    else await api.deletePayment(row.id);
    await onChange();
  }

  async function move() {
    if (kind === 'receipt') await api.moveReceiptToPayment(row.id);
    else await api.movePaymentToReceipt(row.id);
    await onChange();
  }

  const conf = confidenceLabel(row.confidence ?? 1);
  const moveLabel = kind === 'receipt' ? '→ Payments' : '→ Receipts';

  if (editing) {
    return (
      <tr style={flagged ? { background: 'var(--amber-bg)' } : undefined}>
        <td><input type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} /></td>
        <td><input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} style={{ width: '100%' }} /></td>
        {kind === 'payment' && <td><input value={f.voucher} onChange={(e) => setF({ ...f, voucher: e.target.value })} style={{ width: 90 }} /></td>}
        <td className="amt"><input value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} style={{ textAlign: 'right', width: 100 }} /></td>
        <td><button className="primary" onClick={() => save('APPROVED')}>Save</button></td>
      </tr>
    );
  }

  if (readOnly) {
    return (
      <tr>
        <td className="muted">{(kind === 'receipt' ? row.receipt_date : row.payment_date) || '—'}</td>
        <td>{row.description}</td>
        {kind === 'payment' && <td className="muted">{row.voucher || '—'}</td>}
        <td className="amt">{row.amount_display}</td>
        <td />
      </tr>
    );
  }

  return (
    <tr
      draggable
      onDragStart={(e) => { e.dataTransfer.setData('text/plain', JSON.stringify({ id: row.id, kind })); e.dataTransfer.effectAllowed = 'move'; }}
      style={flagged ? { background: 'var(--amber-bg)', cursor: 'grab' } : { cursor: 'grab' }}
      title="Drag to the other section to reclassify"
    >
      <td className="muted">⋮⋮ {(kind === 'receipt' ? row.receipt_date : row.payment_date) || '—'}</td>
      <td>
        {row.description}
        {flagged && <span className="badge review" style={{ marginLeft: 8 }}>REVIEW</span>}
      </td>
      {kind === 'payment' && <td className="muted">{row.voucher || '—'}</td>}
      <td className="amt">{row.amount_display}</td>
      <td style={{ whiteSpace: 'nowrap' }}>
        <span className={`badge ${conf.cls}`} title="Extraction confidence">{conf.text}</span>
        <button className="link-btn" style={{ marginLeft: 8 }} onClick={() => setEditing(true)}>edit</button>
        {flagged && <button className="link-btn" style={{ marginLeft: 8 }} onClick={() => save('APPROVED')}>accept</button>}
        <button className="link-btn" style={{ marginLeft: 8 }} onClick={move} title={`Move this row to ${kind === 'receipt' ? 'Payments' : 'Receipts'}`}>{moveLabel}</button>
        <button className="link-btn" style={{ marginLeft: 8 }} onClick={remove}>remove</button>
      </td>
    </tr>
  );
}

function AddReceiptRow({ monthId, onAdded }) {
  const [f, setF] = useState({ receipt_date: '', description: '', amount: '' });
  async function add() {
    if (!f.description || !f.amount) return;
    await api.addReceipt(monthId, { ...f, receipt_date: f.receipt_date || null });
    setF({ receipt_date: '', description: '', amount: '' });
    await onAdded();
  }
  return (
    <tr>
      <td><input type="date" value={f.receipt_date} onChange={(e) => setF({ ...f, receipt_date: e.target.value })} /></td>
      <td><input placeholder="Add receipt…" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} style={{ width: '100%' }} /></td>
      <td className="amt"><input placeholder="Amount" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} style={{ textAlign: 'right', width: 100 }} /></td>
      <td><button onClick={add}>Add</button></td>
    </tr>
  );
}

function AddPaymentRow({ monthId, onAdded }) {
  const [f, setF] = useState({ payment_date: '', description: '', amount: '', voucher: '' });
  async function add() {
    if (!f.description || !f.amount) return;
    await api.addPayment(monthId, { ...f, payment_date: f.payment_date || null, voucher: f.voucher || null });
    setF({ payment_date: '', description: '', amount: '', voucher: '' });
    await onAdded();
  }
  return (
    <tr>
      <td><input type="date" value={f.payment_date} onChange={(e) => setF({ ...f, payment_date: e.target.value })} /></td>
      <td><input placeholder="Add payment…" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} style={{ width: '100%' }} /></td>
      <td><input placeholder="Voucher" value={f.voucher} onChange={(e) => setF({ ...f, voucher: e.target.value })} style={{ width: 90 }} /></td>
      <td className="amt"><input placeholder="Amount" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} style={{ textAlign: 'right', width: 100 }} /></td>
      <td><button onClick={add}>Add</button></td>
    </tr>
  );
}

export default function DataPanel({ month, receipts, payments, onChange, readOnly = false }) {
  const [editingOpening, setEditingOpening] = useState(false);
  const [newOpening, setNewOpening] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  const flaggedCount = [...receipts, ...payments].filter((r) => r.needs_review).length;

  const [dropHint, setDropHint] = useState(null); // 'receipts' | 'payments' | null

  async function correctOpening() {
    setError('');
    try {
      await api.applyCorrection(month.id, {
        entity_type: 'month', entity_id: month.id, field_name: 'opening_balance',
        new_value: newOpening, reason: reason || 'Manual correction',
      });
      setEditingOpening(false);
      setNewOpening('');
      setReason('');
      await onChange();
    } catch (err) {
      setError(err.message);
    }
  }

  // Drop a dragged row onto a section to reclassify it.
  async function handleDrop(targetSection, e) {
    e.preventDefault();
    setDropHint(null);
    let payload;
    try { payload = JSON.parse(e.dataTransfer.getData('text/plain')); } catch { return; }
    if (!payload?.id) return;
    // Only act if the row came from the OTHER section.
    if (targetSection === 'payments' && payload.kind === 'receipt') {
      await api.moveReceiptToPayment(payload.id);
      await onChange();
    } else if (targetSection === 'receipts' && payload.kind === 'payment') {
      await api.movePaymentToReceipt(payload.id);
      await onChange();
    }
  }

  const dropProps = (section) => (readOnly ? {} : {
    onDragOver: (e) => { e.preventDefault(); setDropHint(section); },
    onDragLeave: () => setDropHint((h) => (h === section ? null : h)),
    onDrop: (e) => handleDrop(section, e),
    style: dropHint === section ? { outline: '2px dashed var(--navy)', outlineOffset: 2 } : undefined,
  });

  return (
    <>
      {!readOnly && flaggedCount > 0 && (
        <div className="attention">
          <h4>ATTENTION — {flaggedCount} ROW(S) NEED REVIEW</h4>
          <span className="muted">Highlighted rows were read with low confidence. Compare against the scan, then <strong>edit</strong> or <strong>accept</strong> each one. Nothing is final until you approve.</span>
        </div>
      )}

      <div className="panel">
        <div className="row-between">
          <h3 style={{ margin: 0 }}>Opening Balance</h3>
          {!editingOpening && (
            <div className="inline-row">
              <strong style={{ fontSize: 18, color: 'var(--navy)' }}>{month.opening_balance_display}</strong>
              {!readOnly && (
                <button className="ghost" onClick={() => { setEditingOpening(true); setNewOpening(String(month.opening_balance)); }}>Correct</button>
              )}
            </div>
          )}
        </div>
        {editingOpening && (
          <div className="attention" style={{ marginTop: 12 }}>
            <h4>EXPLICIT CORRECTION</h4>
            <div className="inline-row">
              <div className="field" style={{ marginBottom: 0 }}>
                <label>New opening balance (₹)</label>
                <input value={newOpening} onChange={(e) => setNewOpening(e.target.value)} />
              </div>
              <div className="field" style={{ marginBottom: 0, flex: 1 }}>
                <label>Reason (recorded in audit trail)</label>
                <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Extraction misread; source shows 998" />
              </div>
              <button className="primary" onClick={correctOpening}>Save Correction</button>
              <button className="ghost" onClick={() => setEditingOpening(false)}>Cancel</button>
            </div>
            {error && <div className="err">{error}</div>}
          </div>
        )}
      </div>

      <div className="panel" {...dropProps('receipts')}>
        <div className="row-between">
          <h3 style={{ margin: 0 }}>Receipts</h3>
          {!readOnly && <span className="muted" style={{ fontSize: 12 }}>Drag a row here (or use “→ Receipts”) to move a payment in.</span>}
        </div>
        <div className="spacer" />
        <table className="data">
          <thead><tr><th>Date</th><th>Description</th><th className="amt">Amount</th><th></th></tr></thead>
          <tbody>
            {receipts.map((r) => <EditableRow key={r.id} row={r} kind="receipt" onChange={onChange} readOnly={readOnly} />)}
            {!readOnly && <AddReceiptRow monthId={month.id} onAdded={onChange} />}
          </tbody>
        </table>
      </div>

      <div className="panel" {...dropProps('payments')}>
        <div className="row-between">
          <h3 style={{ margin: 0 }}>Payments</h3>
          {!readOnly && <span className="muted" style={{ fontSize: 12 }}>Drag a row here (or use “→ Payments”) to move a receipt in.</span>}
        </div>
        <div className="spacer" />
        <table className="data">
          <thead><tr><th>Date</th><th>Description</th><th>Voucher</th><th className="amt">Amount</th><th></th></tr></thead>
          <tbody>
            {payments.map((p) => <EditableRow key={p.id} row={p} kind="payment" onChange={onChange} readOnly={readOnly} />)}
            {!readOnly && <AddPaymentRow monthId={month.id} onAdded={onChange} />}
          </tbody>
        </table>
      </div>
    </>
  );
}
