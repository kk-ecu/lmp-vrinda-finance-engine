import React, { useState } from 'react';
import { api, auth } from '../services/api';

export default function ChangePassword({ onBack }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(''); setOk('');
    if (next !== confirm) { setError('New passwords do not match.'); return; }
    if (next.length < 8) { setError('New password must be at least 8 characters.'); return; }
    setBusy(true);
    try {
      const res = await api.changePassword(current, next);
      // Server revoked old tokens and returned a fresh one — keep us signed in.
      if (res.token) auth.token = res.token;
      setOk('Password changed. All other sessions have been signed out.');
      setCurrent(''); setNext(''); setConfirm('');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <button className="link-btn" onClick={onBack}>← All months</button>
          <h1 style={{ marginTop: 6 }}>Change Password</h1>
          <p>Changing the password signs out every existing session (including stolen tokens).</p>
        </div>
      </div>

      <div className="panel" style={{ maxWidth: 420 }}>
        <form onSubmit={submit}>
          <div className="field">
            <label>Current password</label>
            <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoFocus />
          </div>
          <div className="field">
            <label>New password (min 8 chars)</label>
            <input type="password" value={next} onChange={(e) => setNext(e.target.value)} />
          </div>
          <div className="field">
            <label>Confirm new password</label>
            <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </div>
          {error && <div className="err">{error}</div>}
          {ok && <div className="ok">{ok}</div>}
          <div className="actions">
            <button type="button" className="ghost" onClick={onBack}>Done</button>
            <button type="submit" className="primary" disabled={busy}>{busy ? 'Changing…' : 'Change Password'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
