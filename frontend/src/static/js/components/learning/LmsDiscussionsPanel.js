import React, { useEffect, useState } from 'react';
import {
  lmsCreateDiscussion,
  lmsCreateDiscussionPost,
  lmsGetDiscussionNotificationPreferences,
  lmsListDiscussionPosts,
  lmsListDiscussions,
  lmsPatchDiscussionNotificationPreferences,
  lmsPatchDiscussion,
} from '../../utils/helpers/lmsApi';
import { LmsMentionTextarea } from './LmsMentionTextarea';

function ReplyForm({ slug, discussionId, parentId, onDone, disabled }) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const submit = (ev) => {
    ev.preventDefault();
    if (!text.trim() || !discussionId || disabled) {
      return;
    }
    setBusy(true);
    setErr(null);
    lmsCreateDiscussionPost(discussionId, { body: text.trim(), parent: parentId || null })
      .then(() => {
        setText('');
        if (onDone) {
          onDone();
        }
      })
      .catch((e) => setErr(String(e.message || e)))
      .finally(() => setBusy(false));
  };

  return (
    <form onSubmit={submit} style={{ marginTop: 8 }}>
      <LmsMentionTextarea
        slug={slug}
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write a reply… type @ for member suggestions"
        style={{ width: '100%', maxWidth: 520, fontSize: 13 }}
        disabled={disabled}
      />
      {err ? <p className="error-message" style={{ fontSize: 12 }}>{err}</p> : null}
      <button type="submit" className="button-link" disabled={busy || disabled} style={{ fontSize: 13 }}>
        {disabled ? 'Thread locked' : busy ? 'Sending…' : 'Send reply'}
      </button>
    </form>
  );
}

function PostTree({ nodes, depth, onPickReply }) {
  if (!nodes || !nodes.length) {
    return null;
  }
  return (
    <ul style={{ listStyle: 'none', paddingLeft: depth ? 16 : 0, margin: '0.5rem 0 0' }}>
      {nodes.map((n) => (
        <li key={n.id} style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontSize: 13 }}>
            <strong>{n.author_display}</strong>
            <span className="lms-meta" style={{ marginLeft: 8 }}>
              {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
            </span>
            {n.is_instructor_answer ? (
              <span style={{ marginLeft: 8, color: '#2e7d32' }}>Staff</span>
            ) : null}
          </div>
          <div style={{ whiteSpace: 'pre-wrap', marginTop: 4 }}>{n.body}</div>
          <button type="button" className="link-like" style={{ fontSize: 13 }} onClick={() => onPickReply(n.id)}>
            Reply to this post
          </button>
          <PostTree nodes={n.replies} depth={depth + 1} onPickReply={onPickReply} />
        </li>
      ))}
    </ul>
  );
}

export function LmsDiscussionsPanel({ slug, lessonFilter }) {
  const [threads, setThreads] = useState([]);
  const [error, setError] = useState(null);
  const [newTitle, setNewTitle] = useState('');
  const [creating, setCreating] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const [posts, setPosts] = useState([]);
  const [postsErr, setPostsErr] = useState(null);
  const [replyParentId, setReplyParentId] = useState(null);
  const [busyModeration, setBusyModeration] = useState(false);
  const [prefs, setPrefs] = useState({
    email_replies: true,
    email_mentions: true,
    email_calendar: true,
    frequency: 'immediate',
  });
  const [savingPrefs, setSavingPrefs] = useState(false);

  const loadThreads = () => {
    if (!slug) {
      return;
    }
    lmsListDiscussions(slug, lessonFilter || null)
      .then((d) => setThreads(d.discussions || []))
      .catch((e) => setError(String(e.message || e)));
  };

  useEffect(() => {
    loadThreads();
  }, [slug, lessonFilter]);

  useEffect(() => {
    lmsGetDiscussionNotificationPreferences()
      .then((res) => setPrefs(res))
      .catch(() => null);
  }, []);

  const loadPosts = (id) => {
    setPostsErr(null);
    lmsListDiscussionPosts(id)
      .then((d) => setPosts(d.posts || []))
      .catch((e) => setPostsErr(String(e.message || e)));
  };

  useEffect(() => {
    if (activeId) {
      loadPosts(activeId);
      setReplyParentId(null);
    } else {
      setPosts([]);
    }
  }, [activeId]);

  const createThread = (ev) => {
    ev.preventDefault();
    if (!newTitle.trim()) {
      return;
    }
    setCreating(true);
    const payload = { title: newTitle.trim() };
    if (lessonFilter) {
      payload.lesson = lessonFilter;
    }
    lmsCreateDiscussion(slug, payload)
      .then(() => {
        setNewTitle('');
        loadThreads();
      })
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setCreating(false));
  };

  const activeThread = threads.find((t) => t.id === activeId) || null;

  const patchActiveThread = (payload) => {
    if (!activeId) {
      return;
    }
    setBusyModeration(true);
    lmsPatchDiscussion(activeId, payload)
      .then(() => loadThreads())
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setBusyModeration(false));
  };

  return (
    <div className="lms-discussions" style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12 }}>
      {error ? <p className="error-message">{error}</p> : null}
      <form onSubmit={createThread} style={{ marginBottom: '1rem' }}>
        <input
          type="text"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="Start a new discussion (title)"
          style={{ width: '100%', maxWidth: 400, marginRight: 8 }}
        />
        <button type="submit" className="button-link" disabled={creating}>
          {creating ? 'Creating…' : 'Create'}
        </button>
      </form>
      <div style={{ marginBottom: 12, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ fontSize: 13 }}>
          <input
            type="checkbox"
            checked={Boolean(prefs.email_replies)}
            onChange={(e) => setPrefs((prev) => ({ ...prev, email_replies: e.target.checked }))}
          />{' '}
          Email me discussion replies
        </label>
        <label style={{ fontSize: 13 }}>
          <input
            type="checkbox"
            checked={Boolean(prefs.email_mentions)}
            onChange={(e) => setPrefs((prev) => ({ ...prev, email_mentions: e.target.checked }))}
          />{' '}
          Email me @mentions
        </label>
        <label style={{ fontSize: 13 }}>
          <input
            type="checkbox"
            checked={Boolean(prefs.email_calendar)}
            onChange={(e) => setPrefs((prev) => ({ ...prev, email_calendar: e.target.checked }))}
          />{' '}
          Email me calendar / due-date reminders
        </label>
        <label style={{ fontSize: 13 }}>
          Frequency{' '}
          <select
            value={prefs.frequency || 'immediate'}
            onChange={(e) => setPrefs((prev) => ({ ...prev, frequency: e.target.value }))}
          >
            <option value="off">Off</option>
            <option value="immediate">Immediate</option>
            <option value="daily">Daily digest</option>
          </select>
        </label>
        <button
          type="button"
          className="button-link"
          disabled={savingPrefs}
          onClick={() => {
            setSavingPrefs(true);
            lmsPatchDiscussionNotificationPreferences(prefs)
              .then(setPrefs)
              .catch((e) => setError(String(e.message || e)))
              .finally(() => setSavingPrefs(false));
          }}
        >
          {savingPrefs ? 'Saving...' : 'Save notification preferences'}
        </button>
      </div>
      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ flex: '0 0 220px', minWidth: 200 }}>
          <h4 style={{ marginTop: 0 }}>Threads</h4>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {threads.map((t) => (
              <li
                key={t.id}
                style={{
                  marginBottom: 8,
                  border: '1px solid #eee',
                  borderRadius: 6,
                  padding: 8,
                  background: activeId === t.id ? '#f9fafb' : '#fff',
                }}
              >
                <button
                  type="button"
                  className="link-like"
                  style={{ fontWeight: activeId === t.id ? 700 : 400, textAlign: 'left' }}
                  onClick={() => setActiveId(t.id)}
                >
                  {t.title}
                </button>
                <div className="lms-meta" style={{ fontSize: 12 }}>
                  {t.is_pinned ? 'pinned · ' : ''}
                  {t.reply_count} replies
                  {t.is_locked ? ' · locked' : ''}
                </div>
              </li>
            ))}
          </ul>
          {!threads.length ? <p style={{ fontSize: 13 }}>No discussions yet.</p> : null}
        </div>
        <div style={{ flex: 1, minWidth: 280 }}>
          {!activeId ? <p>Select a thread.</p> : null}
          {activeId && postsErr ? <p className="error-message">{postsErr}</p> : null}
          {activeId && !postsErr ? (
            <>
              <div style={{ marginBottom: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="button-link"
                  disabled={busyModeration}
                  onClick={() => patchActiveThread({ is_pinned: !activeThread?.is_pinned })}
                >
                  {activeThread?.is_pinned ? 'Unpin thread' : 'Pin thread'}
                </button>
                <button
                  type="button"
                  className="button-link"
                  disabled={busyModeration}
                  onClick={() => patchActiveThread({ is_locked: !activeThread?.is_locked })}
                >
                  {activeThread?.is_locked ? 'Unlock thread' : 'Lock thread'}
                </button>
              </div>
              <PostTree nodes={posts} depth={0} onPickReply={(id) => setReplyParentId(id)} />
              <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #ddd' }}>
                <p style={{ fontSize: 13, margin: '0 0 0.5rem' }}>
                  {replyParentId ? `Replying to post #${replyParentId}` : 'Reply to thread (top level)'}
                  {replyParentId ? (
                    <button type="button" className="link-like" style={{ marginLeft: 8 }} onClick={() => setReplyParentId(null)}>
                      Clear
                    </button>
                  ) : null}
                </p>
                <ReplyForm
                  slug={slug}
                  discussionId={activeId}
                  parentId={replyParentId}
                  onDone={() => loadPosts(activeId)}
                  disabled={Boolean(activeThread?.is_locked)}
                />
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
