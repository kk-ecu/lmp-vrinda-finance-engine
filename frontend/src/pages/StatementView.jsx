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

// Read-only view of a signed-off (FINAL) month: the exact stored PDF, embedded.
export default function StatementView({ month, latestReport, onBack, onReopened }) {
  const [pdfUrl, setPdfUrl] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let revoked = false;
    let url = '';
    if (latestReport && latestReport.has_pdf) {
      api.pdfObjectUrl(latestReport.id)
        .then((u) => { if (!revoked) { url = u; setPdfUrl(u); } })
        .catch((e) => setError(e.message));
    }
    return () => { revoked = true; if (url) URL.revokeObjectURL(url); };
  }, [latestReport]);

  async function downloadDocx() {
    try {
      const url = await api.docxObjectUrl(latestReport.id);
      const a = document.createElement('a');
      a.href = url; a.download = `statement-${String(latestReport.revision).padStart(2, '0')}.docx`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (e) { setError(e.message); }
  }

  async function openPdfTab() {
    if (pdfUrl) window.open(pdfUrl, '_blank', 'noopener');
  }

  async function reopen() {
    const reason = window.prompt(
      'Reopen this signed-off statement for rectification?\n\n' +
      'This creates a NEW revision and unlocks editing. The current signed PDF is kept on record.\n\n' +
      'Enter the reason (required, recorded in the audit trail):'
    );
    if (reason === null) return; // cancelled
    if (reason.trim().length < 3) { setError('A reason of at least 3 characters is required.'); return; }
    setBusy(true); setError('');
    try {
      await api.reopenMonth(month.id, reason.trim());
      onReopened();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <button className="link-btn" onClick={onBack}>← All months</button>
          <h1 style={{ marginTop: 6 }}>
            {periodLabel(month.period)}{month.revision > 1 ? ` · revision ${month.revision}` : ''}
          </h1>
          <div style={{ marginTop: 4 }}><Badge status={month.status} /></div>
        </div>
      </div>

      <div className="panel" style={{ borderLeft: '4px solid var(--green)' }}>
        <div className="row-between">
          <div>
            <strong style={{ color: 'var(--green)' }}>🔒 Signed off &amp; locked.</strong>{' '}
            <span className="muted">
              This is the final statement for {periodLabel(month.period)}
              {latestReport ? ` · QA ` : ''}
            </span>
            {latestReport && <Badge status={latestReport.qa_status} />}
          </div>
          <div className="inline-row">
            {latestReport?.has_pdf && <button className="ghost" onClick={openPdfTab}>Open PDF</button>}
            {latestReport?.has_docx && <button className="ghost" onClick={downloadDocx}>Download Word</button>}
            <button className="primary" disabled={busy} onClick={reopen}>
              {busy ? 'Reopening…' : '🔓 Reopen for Rectification'}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="panel err">{error}</div>}

      <div className="panel" style={{ padding: 0, overflow: 'hidden' }}>
        {!latestReport ? (
          <div className="empty">No generated statement found for this month.</div>
        ) : !latestReport.has_pdf ? (
          <div className="empty">The PDF for this statement is not available (renderer may have been offline). Use Download Word.</div>
        ) : !pdfUrl ? (
          <div className="empty">Loading statement…</div>
        ) : (
          <iframe
            title="Final Statement"
            src={pdfUrl}
            style={{ width: '100%', height: '80vh', border: 'none', display: 'block' }}
          />
        )}
      </div>
    </div>
  );
}
