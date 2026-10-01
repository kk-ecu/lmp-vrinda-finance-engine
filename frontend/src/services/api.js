// Thin API client for the LMP Vrinda Finance Engine backend.
// All currency crosses the wire as strings/numbers in rupees; the backend
// returns pre-formatted *_display strings so the UI never formats currency.

const BASE = '/api';
const TOKEN_KEY = 'lmp_token';

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY) || ''; },
  set token(v) { v ? localStorage.setItem(TOKEN_KEY, v) : localStorage.removeItem(TOKEN_KEY); },
  logout() { localStorage.removeItem(TOKEN_KEY); },
};

// Called when any request gets a 401 so the app can show the login gate.
let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) { onUnauthorized = fn; }

async function request(path, { method = 'GET', body, isForm = false } = {}) {
  const opts = { method, headers: {} };
  const token = auth.token;
  if (token) opts.headers['Authorization'] = `Bearer ${token}`;
  if (body !== undefined) {
    if (isForm) {
      opts.body = body; // FormData; let the browser set the boundary
    } else {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
  }
  const res = await fetch(`${BASE}${path}`, opts);
  if (res.status === 401) {
    auth.logout();
    onUnauthorized();
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data && data.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

export const api = {
  health: () => request('/health'),

  // Auth
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password } }),
  me: () => request('/auth/me'),
  revokeAll: () => request('/auth/revoke-all', { method: 'POST' }),
  changePassword: (current_password, new_password) =>
    request('/auth/change-password', { method: 'POST', body: { current_password, new_password } }),

  // Dashboard & months
  dashboard: () => request('/dashboard'),
  listMonths: () => request('/months'),
  getMonth: (id) => request(`/months/${id}`),
  createMonth: ({ year, month, openingBalance }) =>
    request('/months', { method: 'POST', body: { year, month, opening_balance: String(openingBalance ?? 0) } }),
  reopenMonth: (id, reason) => request(`/months/${id}/reopen`, { method: 'POST', body: { reason } }),
  deleteMonth: (id) => request(`/months/${id}`, { method: 'DELETE' }),
  adminListMonths: () => request('/admin/months'),

  // Sources
  listSources: (id) => request(`/months/${id}/sources`),
  uploadSource: (id, file) => {
    const form = new FormData();
    form.append('file', file);
    return request(`/months/${id}/sources`, { method: 'POST', body: form, isForm: true });
  },

  // Extraction
  extractionStatus: () => request('/extraction/status'),
  extract: (id) => request(`/months/${id}/extract`, { method: 'POST' }),
  uploadFirst: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/upload-first', { method: 'POST', body: form, isForm: true });
  },
  appConfig: () => request('/config'),
  testExtract: (file, provider) => {
    const form = new FormData();
    form.append('file', file);
    if (provider) form.append('provider', provider);
    return request('/test/extract', { method: 'POST', body: form, isForm: true });
  },

  // Move a row between sections
  moveReceiptToPayment: (rid) => request(`/receipts/${rid}/move`, { method: 'POST' }),
  movePaymentToReceipt: (pid) => request(`/payments/${pid}/move`, { method: 'POST' }),

  // Receipts & payments
  listReceipts: (id) => request(`/months/${id}/receipts`),
  addReceipt: (id, r) => request(`/months/${id}/receipts`, { method: 'POST', body: r }),
  updateReceipt: (rid, r) => request(`/receipts/${rid}`, { method: 'PUT', body: r }),
  deleteReceipt: (rid) => request(`/receipts/${rid}`, { method: 'DELETE' }),

  listPayments: (id) => request(`/months/${id}/payments`),
  addPayment: (id, p) => request(`/months/${id}/payments`, { method: 'POST', body: p }),
  updatePayment: (pid, p) => request(`/payments/${pid}`, { method: 'PUT', body: p }),
  deletePayment: (pid) => request(`/payments/${pid}`, { method: 'DELETE' }),

  // Corrections & notes
  listCorrections: (id) => request(`/months/${id}/corrections`),
  applyCorrection: (id, c) => request(`/months/${id}/corrections`, { method: 'POST', body: c }),
  listNotes: (id) => request(`/months/${id}/notes`),
  addNote: (id, n) => request(`/months/${id}/notes`, { method: 'POST', body: n }),
  updateNote: (noteId, n) => request(`/notes/${noteId}`, { method: 'PUT', body: n }),
  deleteNote: (noteId) => request(`/notes/${noteId}`, { method: 'DELETE' }),

  // Validation, approval, generation
  validate: (id) => request(`/months/${id}/validate`, { method: 'POST' }),
  getValidation: (id) => request(`/months/${id}/validation`),
  approve: (id) => request(`/months/${id}/approve`, { method: 'POST' }),
  generate: (id) => request(`/months/${id}/generate`, { method: 'POST' }),
  listReports: (id) => request(`/months/${id}/reports`),

  // Download URLs (used directly in <a href>)
  docxUrl: (reportId) => `${BASE}/reports/${reportId}/docx`,
  pdfUrl: (reportId) => `${BASE}/reports/${reportId}/pdf`,

  // Fetch a report file as an object URL (sends the auth token). Used to embed
  // the signed PDF inline and to download with auth. Caller must revoke the URL.
  async fileObjectUrl(path) {
    const token = auth.token;
    const res = await fetch(`${BASE}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Failed to load file (${res.status})`);
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },
  pdfObjectUrl(reportId) { return this.fileObjectUrl(`/reports/${reportId}/pdf`); },
  docxObjectUrl(reportId) { return this.fileObjectUrl(`/reports/${reportId}/docx`); },
};
