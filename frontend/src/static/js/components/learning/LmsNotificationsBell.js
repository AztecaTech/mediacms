import React, { useCallback, useEffect, useRef, useState } from 'react';
import { lmsListNotifications, lmsMarkNotificationRead } from '../../utils/helpers/lmsApi';

function isAnonymous() {
  if (typeof window === 'undefined' || !window.MediaCMS || !window.MediaCMS.user) {
    return true;
  }
  return !!window.MediaCMS.user.is?.anonymous;
}

export function LmsNotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState(null);
  const wrapRef = useRef(null);

  const refresh = useCallback(() => {
    if (isAnonymous()) {
      return;
    }
    Promise.all([lmsListNotifications({ unread: true }), lmsListNotifications({ unread: false })])
      .then(([unreadRes, allRes]) => {
        setUnreadCount((unreadRes.notifications || []).length);
        setItems(allRes.notifications || []);
        setError(null);
      })
      .catch((e) => {
        setError(String(e.message || e));
        setItems([]);
        setUnreadCount(0);
      });
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60000);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const onDoc = (ev) => {
      if (wrapRef.current && !wrapRef.current.contains(ev.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('click', onDoc);
    return () => document.removeEventListener('click', onDoc);
  }, [open]);

  const onMarkRead = (id) => {
    lmsMarkNotificationRead(id)
      .then(() => refresh())
      .catch(() => {});
  };

  if (isAnonymous()) {
    return null;
  }

  return (
    <div ref={wrapRef} style={{ position: 'relative' }}>
      <button type="button" className="button-link" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        Notifications
        {unreadCount > 0 ? (
          <span
            style={{
              marginLeft: 6,
              background: '#c62828',
              color: '#fff',
              borderRadius: 10,
              padding: '0 6px',
              fontSize: 12,
            }}
          >
            {unreadCount}
          </span>
        ) : null}
      </button>
      {open ? (
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: '100%',
            marginTop: 4,
            minWidth: 280,
            maxWidth: 360,
            maxHeight: 360,
            overflowY: 'auto',
            background: '#fff',
            border: '1px solid #ccc',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            zIndex: 50,
            padding: 8,
          }}
        >
          {error ? <p className="error-message" style={{ fontSize: 13 }}>{error}</p> : null}
          {!items.length && !error ? <p style={{ fontSize: 13, margin: 0 }}>No notifications.</p> : null}
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {items.map((n) => (
              <li
                key={n.id}
                style={{
                  borderBottom: '1px solid #eee',
                  padding: '8px 0',
                  fontSize: 13,
                  opacity: n.read_at ? 0.75 : 1,
                }}
              >
                <strong>{n.title}</strong>
                {n.body ? <div style={{ marginTop: 4 }}>{n.body}</div> : null}
                <div style={{ marginTop: 6, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {!n.read_at ? (
                    <button type="button" className="link-like" onClick={() => onMarkRead(n.id)}>
                      Mark read
                    </button>
                  ) : null}
                  {n.url ? (
                    <a href={n.url} className="link-like">
                      Open
                    </a>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
