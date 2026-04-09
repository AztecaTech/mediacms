import React, { useEffect, useMemo, useState } from 'react';
import { lmsMyCalendar } from '../utils/helpers/lmsApi';

function monthRangeUtcIso(d) {
  const start = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1, 0, 0, 0));
  const end = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0, 23, 59, 59));
  return {
    from: start.toISOString().replace(/\.\d{3}Z$/, 'Z'),
    to: end.toISOString().replace(/\.\d{3}Z$/, 'Z'),
  };
}

function formatWhen(ev) {
  if (!ev.starts_at) {
    return 'Date TBD';
  }
  try {
    return new Date(ev.starts_at).toLocaleString();
  } catch {
    return ev.starts_at;
  }
}

export function MyCalendarPage({ id = 'lms_my_calendar' }) {
  const [cursor, setCursor] = useState(() => new Date());
  const [events, setEvents] = useState([]);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);

  const { from, to } = useMemo(() => monthRangeUtcIso(cursor), [cursor]);

  useEffect(() => {
    setLoading(true);
    setErr(null);
    lmsMyCalendar({ from, to })
      .then((r) => setEvents(r.events || []))
      .catch((e) => setErr(String(e.message || e)))
      .finally(() => setLoading(false));
  }, [from, to]);

  const label = useMemo(
    () =>
      cursor.toLocaleString(undefined, {
        month: 'long',
        year: 'numeric',
        timeZone: 'UTC',
      }),
    [cursor]
  );

  const shiftMonth = (delta) => {
    setCursor((prev) => new Date(Date.UTC(prev.getUTCFullYear(), prev.getUTCMonth() + delta, 15)));
  };

  return (
    <div id={id} style={{ maxWidth: 720, margin: '0 auto', padding: '1rem' }}>
      <h1 style={{ marginTop: 0 }}>My calendar</h1>
      <p className="lms-meta" style={{ marginBottom: '1rem' }}>
        Due dates and milestones from your active enrollments ({label}, UTC month window).
      </p>
      <div style={{ display: 'flex', gap: 8, marginBottom: '1rem', flexWrap: 'wrap' }}>
        <button type="button" className="button-link" onClick={() => shiftMonth(-1)}>
          ← Previous month
        </button>
        <button type="button" className="button-link" onClick={() => shiftMonth(1)}>
          Next month →
        </button>
      </div>
      {loading ? <p>Loading…</p> : null}
      {err ? <p className="error-message" style={{ whiteSpace: 'pre-line' }}>{err}</p> : null}
      {!loading && !err && !events.length ? <p>No events in this range.</p> : null}
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {events.map((ev) => (
          <li
            key={ev.id}
            style={{
              marginBottom: '0.75rem',
              padding: '0.75rem',
              border: '1px solid #e5e7eb',
              borderRadius: 8,
              background: '#fafafa',
            }}
          >
            <div style={{ fontWeight: 600 }}>{ev.title}</div>
            <div className="lms-meta" style={{ fontSize: 13 }}>
              {ev.course_title}{' '}
              <span style={{ opacity: 0.85 }}>({ev.course_slug})</span>
            </div>
            <div className="lms-meta" style={{ fontSize: 13 }}>
              {formatWhen(ev)} · {ev.event_type.replace(/_/g, ' ')}
            </div>
            {ev.description ? (
              <p style={{ fontSize: 13, margin: '0.35rem 0 0', whiteSpace: 'pre-wrap' }}>{ev.description}</p>
            ) : null}
            {ev.url ? (
              <a href={ev.url} style={{ fontSize: 13 }}>
                Open course
              </a>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
