import React, { useEffect, useState } from 'react';
import { api } from '../services/api';

function NoteEditor({ monthId, note, index, onChange, readOnly = false }) {
  const [editing, setEditing] = useState(false);
  const [f, setF] = useState({ title: note.title, body: note.body, highlight: note.highlight });

  async function save() {
    await api.updateNote(note.id, { ...f, sort_order: note.sort_order });
    setEditing(false);
    await onChange();
  }
  async function remove() {
    await api.deleteNote(note.id);
    await onChange();
  }

  if (editing) {
    return (
      <div className="attention" style={{ marginTop: 8 }}>
        <div className="field" style={{ marginBottom: 8 }}>
          <label>Title</label>
          <input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
        </div>
        <div className="field" style={{ marginBottom: 8 }}>
          <label>Body</label>
          <textarea rows={3} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })}
            style={{ font: 'inherit', padding: 9, border: '1px solid var(--line)', borderRadius: 8 }} />
        </div>
        <label style={{ fontSize: 13 }}>
          <input type="checkbox" checked={f.highlight} onChange={(e) => setF({ ...f, highlight: e.target.checked })} /> Highlight (attention)
        </label>
        <div className="actions" style={{ marginTop: 8 }}>
          <button className="ghost" onClick={() => setEditing(false)}>Cancel</button>
          <button className="primary" onClick={save}>Save</button>
        </div>
      </div>
    );
  }

  return (
    <div className={note.highlight ? 'note hl' : 'note'} style={{
      padding: '10px 12px', marginTop: 8, borderRadius: 8,
      background: note.highlight ? 'var(--amber-bg)' : '#f7f8fb',
      border: note.highlight ? '1px solid var(--amber-border)' : '1px solid var(--line)',
    }}>
      <div className="row-between">
        <div style={{ fontSize: 13 }}>
          <strong style={{ color: note.highlight ? 'var(--red)' : 'var(--navy)' }}>
            {index + 1}. {note.title ? `${note.title}: ` : ''}
          </strong>
          {note.body}
        </div>
        {!readOnly && (
          <div style={{ whiteSpace: 'nowrap' }}>
            <button className="link-btn" onClick={() => setEditing(true)}>edit</button>
            <button className="link-btn" style={{ marginLeft: 8 }} onClick={remove}>remove</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function NotesPanel({ monthId, readOnly = false }) {
  const [notes, setNotes] = useState([]);
  const [adding, setAdding] = useState({ title: '', body: '', highlight: true });
  const [busy, setBusy] = useState(false);

  async function load() {
    setNotes(await api.listNotes(monthId));
  }
  useEffect(() => { load(); }, [monthId]);

  async function add() {
    if (!adding.body.trim() && !adding.title.trim()) return;
    setBusy(true);
    try {
      await api.addNote(monthId, { ...adding, sort_order: notes.length + 1 });
      setAdding({ title: '', body: '', highlight: true });
      await load();
    } finally { setBusy(false); }
  }

  return (
    <div className="panel">
      <div className="row-between">
        <h3 style={{ margin: 0 }}>Notes</h3>
        <span className="muted" style={{ fontSize: 12 }}>These appear in the NOTES block at the bottom of the report.</span>
      </div>

      {notes.length === 0 && <div className="muted" style={{ marginTop: 10 }}>{readOnly ? 'No notes.' : 'No notes yet. Add attention notes (e.g. advance payments, direct deposits) below.'}</div>}
      {notes.map((n, i) => (
        <NoteEditor key={n.id} monthId={monthId} note={n} index={i} onChange={load} readOnly={readOnly} />
      ))}

      {!readOnly && (
      <div className="attention" style={{ marginTop: 14, background: '#f7f8fb', border: '1px dashed var(--line)' }}>
        <h4 style={{ color: 'var(--navy)' }}>ADD A NOTE</h4>
        <div className="field" style={{ marginBottom: 8 }}>
          <label>Title (optional)</label>
          <input value={adding.title} onChange={(e) => setAdding({ ...adding, title: e.target.value })} placeholder="e.g. Security Guard Advance" />
        </div>
        <div className="field" style={{ marginBottom: 8 }}>
          <label>Body</label>
          <textarea rows={2} value={adding.body} onChange={(e) => setAdding({ ...adding, body: e.target.value })}
            placeholder="e.g. An advance of 30,000 is referenced; 11,000 recorded as September salary."
            style={{ font: 'inherit', padding: 9, border: '1px solid var(--line)', borderRadius: 8 }} />
        </div>
        <div className="row-between">
          <label style={{ fontSize: 13 }}>
            <input type="checkbox" checked={adding.highlight} onChange={(e) => setAdding({ ...adding, highlight: e.target.checked })} /> Highlight (attention)
          </label>
          <button className="primary" disabled={busy} onClick={add}>Add Note</button>
        </div>
      </div>
      )}
    </div>
  );
}
