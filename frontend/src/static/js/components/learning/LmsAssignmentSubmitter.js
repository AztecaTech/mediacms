import React, { useEffect, useMemo, useState } from 'react';
import { lmsAssignmentSubmitMultipart, lmsGetAssignment } from '../../utils/helpers/lmsApi';

export function LmsAssignmentSubmitter({ assignmentId, lessonTitle }) {
  const [meta, setMeta] = useState(null);
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    lmsGetAssignment(assignmentId)
      .then(setMeta)
      .catch((e) => setErr(String(e.message || e)));
  }, [assignmentId]);

  const allowed = useMemo(() => (meta && meta.submission_types ? meta.submission_types : ['text']), [meta]);
  const allowText = allowed.includes('text');
  const allowUrl = allowed.includes('url');
  const allowFile = allowed.includes('file');
  const extHint = meta && meta.allowed_extensions ? meta.allowed_extensions : '';
  const allowedExt = (extHint || '')
    .split(',')
    .map((x) => x.trim().toLowerCase())
    .filter(Boolean);

  const submit = (ev) => {
    ev.preventDefault();
    if (allowFile && file && meta && meta.max_file_size_mb) {
      const maxBytes = Number(meta.max_file_size_mb) * 1024 * 1024;
      if (Number.isFinite(maxBytes) && file.size > maxBytes) {
        setErr(`File too large. Max allowed is ${meta.max_file_size_mb}MB.`);
        return;
      }
      if (allowedExt.length) {
        const parts = file.name.toLowerCase().split('.');
        const ext = parts.length > 1 ? parts[parts.length - 1] : '';
        if (ext && !allowedExt.includes(ext)) {
          setErr(`.${ext} is not allowed. Allowed: ${allowedExt.join(', ')}`);
          return;
        }
      }
    }
    const fd = new FormData();
    if (allowText && text.trim()) {
      fd.append('text_content', text.trim());
    }
    if (allowUrl && url.trim()) {
      fd.append('url', url.trim());
    }
    if (allowFile && file) {
      fd.append('file', file);
    }
    setBusy(true);
    setErr(null);
    setMsg(null);
    lmsAssignmentSubmitMultipart(assignmentId, fd)
      .then((r) => {
        setMsg(`Submitted successfully (status: ${r.status}).`);
        setFile(null);
      })
      .catch((e) => setErr(String(e.message || e)))
      .finally(() => setBusy(false));
  };

  return (
    <div className="lms-assignment-submit">
      <h1>{lessonTitle || 'Assignment'}</h1>
      <p className="lms-meta" style={{ fontSize: 14 }}>
        Submit using allowed types: {allowed.join(', ')}.
      </p>
      {meta && meta.due_at ? (
        <p className="lms-meta" style={{ fontSize: 13 }}>
          Due: {new Date(meta.due_at).toLocaleString()}
        </p>
      ) : null}
      {meta && meta.instructions ? <pre style={{ whiteSpace: 'pre-wrap' }}>{meta.instructions}</pre> : null}
      {err ? <p className="error-message" style={{ whiteSpace: 'pre-line' }}>{err}</p> : null}
      {msg ? <p style={{ color: '#2e7d32' }}>{msg}</p> : null}
      <form onSubmit={submit}>
        {allowText ? (
          <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Text</label>
          <textarea
            rows={6}
            style={{ width: '100%', maxWidth: 560 }}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          </div>
        ) : null}
        {allowUrl ? (
          <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>URL</label>
          <input
            type="url"
            style={{ width: '100%', maxWidth: 480 }}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          </div>
        ) : null}
        {allowFile ? (
          <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>File</label>
          <input type="file" onChange={(e) => setFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)} />
            {meta ? (
              <p className="lms-meta" style={{ fontSize: 12, marginTop: 4 }}>
                Max size: {meta.max_file_size_mb}MB{extHint ? ` · Extensions: ${extHint}` : ''}
              </p>
            ) : null}
          </div>
        ) : null}
        <button type="submit" className="button-link" disabled={busy}>
          {busy ? 'Submitting…' : 'Submit assignment'}
        </button>
      </form>
    </div>
  );
}
