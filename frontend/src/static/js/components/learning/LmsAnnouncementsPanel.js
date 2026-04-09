import React, { useEffect, useState } from 'react';
import { lmsCreateAnnouncement, lmsListAnnouncements } from '../../utils/helpers/lmsApi';
import { LmsMentionTextarea } from './LmsMentionTextarea';

export function LmsAnnouncementsPanel({ slug }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [posting, setPosting] = useState(false);
  const [postErr, setPostErr] = useState(null);

  const load = () => {
    if (!slug) {
      return;
    }
    lmsListAnnouncements(slug)
      .then((d) => setRows(d.announcements || []))
      .catch((e) => setError(String(e.message || e)));
  };

  useEffect(() => {
    load();
  }, [slug]);

  const onPost = (ev) => {
    ev.preventDefault();
    if (!title.trim()) {
      return;
    }
    setPosting(true);
    setPostErr(null);
    lmsCreateAnnouncement(slug, { title: title.trim(), body: body.trim(), is_pinned: false, send_email: false })
      .then(() => {
        setTitle('');
        setBody('');
        load();
      })
      .catch((e) => setPostErr(String(e.message || e)))
      .finally(() => setPosting(false));
  };

  return (
    <div className="lms-announcements">
      {error ? <p className="error-message">{error}</p> : null}
      <form onSubmit={onPost} style={{ marginBottom: '1.25rem', padding: '0.75rem', background: '#f5f5f5' }}>
        <h4 style={{ margin: '0 0 0.5rem' }}>New announcement (instructors / TAs)</h4>
        <div style={{ marginBottom: 8 }}>
          <input
            type="text"
            placeholder="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ width: '100%', maxWidth: 480 }}
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <LmsMentionTextarea
            slug={slug}
            placeholder="Body — type @ for member suggestions"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            style={{ width: '100%', maxWidth: 560 }}
          />
        </div>
        {postErr ? <p className="error-message">{postErr}</p> : null}
        <button type="submit" className="button-link" disabled={posting}>
          {posting ? 'Posting…' : 'Post'}
        </button>
      </form>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {rows.map((a) => (
          <li
            key={a.id}
            style={{
              marginBottom: '1rem',
              paddingBottom: '1rem',
              borderBottom: '1px solid #ddd',
            }}
          >
            {a.is_pinned ? <span style={{ color: '#1565c0' }}>Pinned · </span> : null}
            <strong>{a.title}</strong>
            <div className="lms-meta" style={{ fontSize: 13, margin: '4px 0' }}>
              {a.author_display} — {a.published_at ? new Date(a.published_at).toLocaleString() : ''}
            </div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{a.body}</div>
          </li>
        ))}
      </ul>
      {!rows.length && !error ? <p>No announcements yet.</p> : null}
    </div>
  );
}
