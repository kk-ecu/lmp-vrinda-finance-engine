import React, { useRef, useState } from 'react';
import { api } from '../services/api';

export default function UploadPanel({ monthId, sources, onChange, onExtracted }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  async function handleFiles(fileList) {
    setBusy(true);
    setError('');
    try {
      for (const file of Array.from(fileList)) {
        await api.uploadSource(monthId, file);
      }
      await onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  async function runExtract() {
    setExtracting(true);
    setError('');
    setInfo('');
    try {
      const res = await api.extract(monthId);
      const n = (res.extracted_receipts || 0) + (res.extracted_payments || 0);
      setInfo(`Extracted ${n} row(s). Review the highlighted ones in step 2.`);
      await onChange();
      if (onExtracted) onExtracted();
    } catch (err) {
      setError(`Extraction failed: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  }

  return (
    <div className="panel">
      <div className="row-between">
        <h3 style={{ margin: 0 }}>Source Documents</h3>
        <button className="primary" disabled={busy} onClick={() => inputRef.current?.click()}>
          {busy ? 'Uploading…' : 'Upload Files'}
        </button>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.txt"
        style={{ display: 'none' }}
        onChange={(e) => handleFiles(e.target.files)}
      />
      {error && <div className="err">{error}</div>}
      {info && <div className="ok">{info}</div>}
      <div className="spacer" />
      {sources.length === 0 ? (
        <div className="muted">No sources uploaded yet. Scans, PDFs, DOCX, XLSX and TXT are accepted. Originals are stored immutably.</div>
      ) : (
        <>
          <table className="data">
            <thead><tr><th>File</th><th>Type</th><th>Checksum</th><th>Status</th></tr></thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.id}>
                  <td>{s.filename}</td>
                  <td className="muted">{s.mime_type}</td>
                  <td className="muted" title={s.sha256}>{s.sha256.slice(0, 12)}…</td>
                  <td>{s.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="spacer" />
          <div className="row-between">
            <span className="muted">Auto-read the uploaded scans into receipts &amp; payments. Low-confidence rows are flagged for your review.</span>
            <button className="primary" disabled={extracting} onClick={runExtract}>
              {extracting ? 'Extracting…' : '✨ Extract Data from Sources'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
