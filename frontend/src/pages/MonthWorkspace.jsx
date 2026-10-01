import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import Badge from '../components/Badge';
import UploadPanel from '../components/UploadPanel';
import DataPanel from '../components/DataPanel';
import NotesPanel from '../components/NotesPanel';
import ValidationPanel from '../components/ValidationPanel';
import StatementView from './StatementView';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
function periodLabel(period) {
  const [y, m] = period.split('-');
  return `${MONTH_NAMES[Number(m) - 1]} ${y}`;
}

// The five monthly buttons.
const BUTTONS = [
  { key: 'upload', glyph: '📤', n: '①', t: 'Upload Documents' },
  { key: 'review', glyph: '📝', n: '②', t: 'Review Extracted Data' },
  { key: 'approve', glyph: '✅', n: '③', t: 'Approve Financials' },
  { key: 'generate', glyph: '📄', n: '④', t: 'Generate Statement' },
  { key: 'download', glyph: '⬇️', n: '⑤', t: 'Download PDF / Word' },
];

export default function MonthWorkspace({ monthId, onBack }) {
  const [month, setMonth] = useState(null);
  const [sources, setSources] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [payments, setPayments] = useState([]);
  const [validation, setValidation] = useState(null);
  const [reports, setReports] = useState([]);
  const [view, setView] = useState('upload');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');

  const refresh = useCallback(async () => {
    const [m, s, r, p, reps] = await Promise.all([
      api.getMonth(monthId),
      api.listSources(monthId),
      api.listReceipts(monthId),
      api.listPayments(monthId),
      api.listReports(monthId),
    ]);
    setMonth(m);
    setSources(s);
    setReceipts(r);
    setPayments(p);
    setReports(reps);
    try {
      setValidation(await api.getValidation(monthId));
    } catch { /* no validation yet */ }
  }, [monthId]);

  useEffect(() => { refresh().catch((e) => setError(e.message)); }, [refresh]);

  const latestReport = reports[0];
  const approved = month && ['FINANCIAL_APPROVED', 'GENERATED', 'FINAL'].includes(month.status);
  const generated = Boolean(latestReport);
  const canDownload = latestReport && (latestReport.has_pdf || latestReport.has_docx);
  const readOnly = month && ['FINAL', 'ARCHIVED'].includes(month.status);

  async function runValidate() {
    setBusy('validate'); setError('');
    try {
      const v = await api.validate(monthId);
      setValidation(v);
      await refresh();
      setView('approve');
    } catch (e) { setError(e.message); } finally { setBusy(''); }
  }

  async function runApprove() {
    setBusy('approve'); setError('');
    try {
      // Validate first so the gate is explicit for the user.
      const v = await api.validate(monthId);
      setValidation(v);
      if (!v.passed) { setView('approve'); setError('Validation must pass before approval. Resolve the failing checks.'); return; }
      await api.approve(monthId);
      await refresh();
      setView('generate');
    } catch (e) { setError(e.message); } finally { setBusy(''); }
  }

  async function runGenerate() {
    setBusy('generate'); setError('');
    try {
      await api.generate(monthId);
      await refresh();
      setView('download');
    } catch (e) { setError(e.message); } finally { setBusy(''); }
  }

  if (!month) {
    return <div className="shell"><div className="panel empty">{error || 'Loading…'}</div></div>;
  }

  // Signed-off months show the read-only Statement View (embedded signed PDF).
  // Reopen there creates a new revision and returns to the editable workflow.
  if (readOnly) {
    return (
      <StatementView
        month={month}
        latestReport={latestReport}
        onBack={onBack}
        onReopened={async () => { await refresh(); setView('review'); }}
      />
    );
  }

  const stepState = (key) => {
    if (key === 'upload') return sources.length > 0 ? 'done' : (view === 'upload' ? 'active' : '');
    if (key === 'review') return (receipts.length + payments.length) > 0 ? 'done' : (view === 'review' ? 'active' : '');
    if (key === 'approve') return approved ? 'done' : (view === 'approve' ? 'active' : '');
    if (key === 'generate') return generated ? 'done' : (view === 'generate' ? 'active' : '');
    if (key === 'download') return month.status === 'FINAL' ? 'done' : (view === 'download' ? 'active' : '');
    return '';
  };

  const disabledFor = (key) => {
    if (key === 'review') return sources.length === 0 && receipts.length === 0 && payments.length === 0 ? false : false;
    if (key === 'approve') return (receipts.length + payments.length) === 0;
    if (key === 'generate') return !approved;
    if (key === 'download') return !canDownload;
    return false;
  };

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <button className="link-btn" onClick={onBack}>← All months</button>
          <h1 style={{ marginTop: 6 }}>{periodLabel(month.period)}{month.revision > 1 ? ` · rev ${month.revision}` : ''}</h1>
          <div style={{ marginTop: 4 }}><Badge status={month.status} /></div>
        </div>
      </div>

      {/* Five-button workflow */}
      <div className="button-row" style={{ marginBottom: 18 }}>
        {BUTTONS.map((b) => (
          <button
            key={b.key}
            className={`action ${stepState(b.key) === 'active' ? '' : ''}`}
            disabled={disabledFor(b.key) || (readOnly && b.key !== 'download')}
            onClick={() => {
              if (b.key === 'upload' || b.key === 'review') setView(b.key);
              else if (b.key === 'approve') runApprove();
              else if (b.key === 'generate') runGenerate();
              else if (b.key === 'download') setView('download');
            }}
            style={stepState(b.key) === 'done' ? { borderColor: 'var(--green)' } : undefined}
          >
            <span className="glyph">{b.glyph}</span>
            <span className="n">{b.n}</span>
            <span className="t">{busy === b.key ? 'Working…' : b.t}</span>
          </button>
        ))}
      </div>

      {error && <div className="panel err">{error}</div>}

      {view === 'upload' && (
        <>
          <UploadPanel monthId={monthId} sources={sources} onChange={refresh} onExtracted={() => setView('review')} />
          <div className="row-between">
            <span className="muted">Step 1 of 5 — upload scans, then Extract to auto-fill, or go straight to Review to type manually.</span>
            <button className="primary" onClick={() => setView('review')}>Continue to Review →</button>
          </div>
        </>
      )}

      {view === 'review' && (
        <>
          <DataPanel month={month} receipts={receipts} payments={payments} onChange={refresh} readOnly={readOnly} />
          <NotesPanel monthId={monthId} readOnly={readOnly} />
          {!readOnly && (
            <div className="row-between">
              <button className="ghost" onClick={() => setView('upload')}>← Sources</button>
              <button className="primary" disabled={busy === 'validate'} onClick={runValidate}>Run Validation →</button>
            </div>
          )}
        </>
      )}

      {view === 'approve' && (
        <>
          <ValidationPanel validation={validation} />
          <div className="row-between">
            <button className="ghost" onClick={() => setView('review')}>← Review Data</button>
            <button className="primary" disabled={busy === 'approve' || !validation?.passed} onClick={runApprove}>
              Approve &amp; Continue →
            </button>
          </div>
          {validation && !validation.passed && (
            <p className="muted" style={{ marginTop: 10 }}>Resolve the failing checks in Review Data, then run validation again.</p>
          )}
        </>
      )}

      {view === 'generate' && (
        <div className="panel">
          <h3>Generate Statement</h3>
          <p className="muted">The approved dataset will be rendered to a DOCX and a PDF, then checked by the QA gate. The month becomes FINAL only when QA passes.</p>
          <button className="primary" disabled={busy === 'generate'} onClick={runGenerate}>
            {busy === 'generate' ? 'Generating…' : 'Generate DOCX + PDF'}
          </button>
        </div>
      )}

      {view === 'download' && (
        <div className="panel">
          <div className="row-between">
            <h3 style={{ margin: 0 }}>Report</h3>
            {latestReport && <Badge status={latestReport.qa_status} />}
          </div>
          {!latestReport ? (
            <p className="muted">No report generated yet.</p>
          ) : (
            <>
              <div style={{ margin: '14px 0' }}>
                {(latestReport.qa_detail?.checks || []).map((c) => (
                  <div className="check" key={c.name}>
                    <span className="name">{c.name}{c.message ? ` — ${c.message}` : ''}</span>
                    <Badge status={c.result} />
                  </div>
                ))}
              </div>
              <div className="inline-row">
                {latestReport.has_pdf && (
                  <a className="btn primary" href={api.pdfUrl(latestReport.id)} target="_blank" rel="noreferrer">Open PDF</a>
                )}
                {latestReport.has_docx && (
                  <a className="btn" href={api.docxUrl(latestReport.id)}>Download Word</a>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
