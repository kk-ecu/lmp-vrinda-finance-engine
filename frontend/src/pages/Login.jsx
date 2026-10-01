import React, { useState } from 'react';
import { api, auth } from '../services/api';

export default function Login({ onLoggedIn }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const res = await api.login(username, password);
      auth.token = res.token;
      onLoggedIn(res.username);
    } catch (err) {
      setError(err.message || 'Login failed');
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" style={{ background: 'var(--bg)' }}>
      <div className="modal" style={{ maxWidth: 360 }}>
        <div className="eyebrow" style={{ color: 'var(--muted)', fontWeight: 700, letterSpacing: 2, fontSize: 11 }}>LMP VRINDA</div>
        <h3 style={{ marginTop: 4 }}>Finance Engine — Sign in</h3>
        <form onSubmit={submit}>
          <div className="field">
            <label>Username</label>
            <input autoFocus value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <div className="err">{error}</div>}
          <div className="actions">
            <button type="submit" className="primary" disabled={busy} style={{ width: '100%' }}>
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
