import React, { useEffect, useRef, useState } from 'react';
import { api } from '../services/api';

const DEFAULT_OPTION = '(configured default)';

function confBadge(c) {
  const pct = Math.round((c ?? 1) * 100);
  const cls = c >= 0.8 ? 'pass' : c >= 0.5 ? 'review' : 'fail';
  return <span className={`badge ${cls}`}>{pct}%</span>;
}

export default function TestExtraction({ onBack }) {
  const inputRef = useRef(null);
  const [provider, setProvider] = useState(DEFAULT_OPTION);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState(null);
  const [elapsed, setElapsed] = useState(null);

  useEffect(() => {
    api.appConfig().then(setStatus).catch(() => {});
  }, []);

  // Only providers the backend will actually serve in this environment
  // (openrouter-only in production). Falls back to a safe default pre-load.
  const allowed = status?.allowed_providers || ['openrouter'];
  const providerOptions = [DEFAULT_OPTION, ...allowed];

  async function run() {
    if (!file) { setError('Choose a file first.'); return; }
    setBusy(true); setError(''); setResult(null); setElapsed(null);
    const started = performance.now();
    try {
      const prov = provider === DEFAULT_OPTION ? undefined : provider;
      const res = await api.testExtract(file, prov);
      setResult(res);
      setElapsed(((performance.now() - started) / 1000).toFixed(1));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const rows = result ? [...result.receipts.map((r) => ({ ...r, kind: 'receipt' })), ...result.payments.map((p) => ({ ...p, kind: 'payment' }))] : [];

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <button className="link-btn" onClick={onBack}>← All months</button>
          <h1 style={{ marginTop: 6 }}>Extraction Test Bench</h1>
          <p>Upload a scan and validate any provider's output. Nothing is saved.</p>
        </div>
      </div>

      {status?.extraction && (
        <div className="panel">
          <div className="row-between">
            <h3 style={{ margin: 0 }}>Engine</h3>
            <span className="muted">
              env: <strong>{status.app_env}</strong> · default: <strong>{status.extraction.provider}</strong> ·
              threshold {status.extraction.low_confidence_threshold} ·
              allowed: {(status.allowed_providers || []).join(', ')}
              {status.is_production ? ' (production: openrouter only)' : ''}
            </span>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="form-grid">
          <div className="field">
            <label>Provider</label>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              {providerOptions.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Source file (image or PDF)</label>
            <input ref={inputRef} type="file" accept=".png,.jpg,.jpeg,.webp,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <span className="muted" style={{ fontSize: 11 }}>Vision providers (openrouter/ollama) read images best; PDFs may need conversion.</span>
          </div>
        </div>
        <div className="inline-row">
          <button className="primary" disabled={busy} onClick={run}>{busy ? 'Extracting…' : 'Run Extraction'}</button>
          {file && <span className="muted">{file.name}</span>}
        </div>
        {error && <div className="err">{error}</div>}
      </div>

      {result && (
        <>
          <div className="panel">
            <div className="row-between">
              <h3 style={{ margin: 0 }}>Result</h3>
              <span className="muted">{result.provider} · {result.model} · {elapsed}s</span>
            </div>
            <div className="spacer" />
            <div className="muted">
              Opening balance: <strong>{result.opening_balance || '—'}</strong> {confBadge(result.opening_balance_confidence)}
            </div>
            {result.warnings?.length > 0 && <div className="err">{result.warnings.join(' ')}</div>}
            <div className="spacer" />
            <table className="data">
              <thead><tr><th>Section</th><th>Date</th><th>Description</th><th>Voucher</th><th className="amt">Amount</th><th>Conf.</th></tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td><span className={`badge ${r.kind === 'receipt' ? 'generated' : 'approved'}`}>{r.kind}</span></td>
                    <td className="muted">{r.date || '—'}</td>
                    <td>{r.description}</td>
                    <td className="muted">{r.voucher || '—'}</td>
                    <td className="amt">{r.amount}</td>
                    <td>{confBadge(r.confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <h3>Raw model output</h3>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: 'var(--muted)', margin: 0 }}>{result.raw_text || '(none)'}</pre>
          </div>
        </>
      )}
    </div>
  );
}
