import React, { useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import NewMonthModal from '../components/NewMonthModal';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function periodLabel(period) {
  const [y, m] = period.split('-');
  return `${MONTH_NAMES[Number(m) - 1]} ${y}`;
}

export default function Dashboard({ onOpenMonth, testEnabled, authEnabled, onLogout }) {
  const [months, setMonths] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [notice, setNotice] = useState('');
  const uploadRef = useRef(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await api.dashboard();
      setMonths(data.months || []);
    } catch (err) {
      setError(`Could not reach the backend: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  // Scan-driven entry: upload a scan, detect the month from it, open that month.
  async function handleScan(fileList) {
    const files = Array.from(fileList || []);
    if (files.length === 0) return;
    setDetecting(true); setError(''); setNotice('');
    try {
      // Detect the month from the first page.
      const res = await api.uploadFirst(files[0]);
      if (!res.detected) {
        setError(`Could not read the month from the scan (${res.reason || 'low confidence'}). Use “New Month (manual)” to set it, then upload pages inside.`);
        return;
      }
      // Attach every uploaded page as an immutable source on that month.
      for (const f of files) {
        await api.uploadSource(res.month_id, f);
      }
      const label = periodLabel(res.period);
      const pages = files.length > 1 ? ` (${files.length} pages)` : '';
      if (res.period_needs_review) {
        setNotice(`Detected ${label}${pages} (low confidence) — please confirm it's correct inside the month.`);
      } else {
        setNotice(`Detected ${label}${pages}. Opening…`);
      }
      onOpenMonth(res.month_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setDetecting(false);
      if (uploadRef.current) uploadRef.current.value = '';
    }
  }

  async function remove(e, m) {
    e.stopPropagation();
    if (!window.confirm(`Delete ${periodLabel(m.period)}? This removes its data and files. (Final months are protected.)`)) return;
    try {
      await api.deleteMonth(m.id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function revokeAll() {
    if (!window.confirm('Sign out of ALL sessions everywhere? This immediately invalidates every token (including any that may have been stolen). You will need to log in again.')) return;
    try {
      await api.revokeAll();
    } catch { /* the call itself may 401 as our token dies; that's fine */ }
    if (onLogout) onLogout();
  }

  const isFinal = (s) => s === 'FINAL' || s === 'ARCHIVED';

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <div className="eyebrow">LMP VRINDA</div>
          <h1>Finance Engine</h1>
          <p>Monthly financial statements — local-first, controlled and simple.</p>
        </div>
      </div>

      <div className="action-row">
        <button
          className="action-card primary"
          disabled={detecting}
          onClick={() => uploadRef.current?.click()}
        >
          <span className="ac-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16V4" /><path d="M7 9l5-5 5 5" /><path d="M4 20h16" />
            </svg>
          </span>
          <span className="ac-title">{detecting ? 'Detecting…' : 'Upload Scan'}</span>
          <span className="ac-sub">Auto-detect the month</span>
        </button>

        <button className="action-card" onClick={() => setShowNew(true)}>
          <span className="ac-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18" /><path d="M8 2v4" /><path d="M16 2v4" /><path d="M12 13v4" /><path d="M10 15h4" />
            </svg>
          </span>
          <span className="ac-title">New Month</span>
          <span className="ac-sub">Create manually</span>
        </button>

        <a
          className={`action-card${testEnabled ? '' : ' is-disabled'}`}
          href={testEnabled ? '#/test-extraction' : undefined}
          aria-disabled={!testEnabled}
        >
          <span className="ac-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 3h6" /><path d="M10 3v6l-4.5 8a2 2 0 0 0 1.8 3h9.4a2 2 0 0 0 1.8-3L14 9V3" /><path d="M7 15h10" />
            </svg>
          </span>
          <span className="ac-title">Extraction Test</span>
          <span className="ac-sub">Try the OCR engine</span>
        </a>

        <a className="action-card" href="#/admin">
          <span className="ac-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </span>
          <span className="ac-title">Admin</span>
          <span className="ac-sub">Settings & tools</span>
        </a>

        {authEnabled && (
          <a className="action-card" href="#/change-password">
            <span className="ac-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </span>
            <span className="ac-title">Change Password</span>
            <span className="ac-sub">Update & revoke sessions</span>
          </a>
        )}

        {authEnabled && (
          <button className="action-card" onClick={revokeAll}>
            <span className="ac-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="9" /><path d="M15 9l-6 6" /><path d="M9 9l6 6" />
              </svg>
            </span>
            <span className="ac-title">Sign out everywhere</span>
            <span className="ac-sub">Revoke all tokens</span>
          </button>
        )}

        {authEnabled && (
          <button className="action-card" onClick={onLogout}>
            <span className="ac-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5" /><path d="M21 12H9" />
              </svg>
            </span>
            <span className="ac-title">Logout</span>
            <span className="ac-sub">Sign out</span>
          </button>
        )}

        <input
          ref={uploadRef}
          type="file"
          multiple
          accept=".png,.jpg,.jpeg,.webp,.pdf"
          style={{ display: 'none' }}
          onChange={(e) => handleScan(e.target.files)}
        />
      </div>

      {error && <div className="panel err">{error}</div>}
      {notice && <div className="panel"><span className="ok">{notice}</span></div>}

      {loading ? (
        <div className="panel empty">Loading…</div>
      ) : months.length === 0 ? (
        <div className="panel empty">
          No months yet. Upload a scan to auto-detect the month, or create one manually.
        </div>
      ) : (
        <div className="month-grid">
          {months.map((m) => (
            <div key={m.id} className="month-card" onClick={() => onOpenMonth(m.id)}>
              <div>
                <div className="period">{periodLabel(m.period)}</div>
                <div style={{ marginTop: 6 }}><Badge status={m.status} /></div>
              </div>
              <div className="figs">
                <div className="fig receipts"><small>RECEIPTS</small><strong>{m.total_receipts_display}</strong></div>
                <div className="fig payments"><small>PAYMENTS</small><strong>{m.total_payments_display}</strong></div>
                <div className="fig closing"><small>CLOSING</small><strong>{m.closing_balance_display}</strong></div>
                {!isFinal(m.status) && (
                  <button className="link-btn" title="Delete this month" onClick={(e) => remove(e, m)}>delete</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showNew && (
        <NewMonthModal
          onClose={() => setShowNew(false)}
          onCreated={(created) => { setShowNew(false); onOpenMonth(created.id); }}
        />
      )}
    </div>
  );
}
