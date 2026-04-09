import React, { useEffect, useMemo, useState } from 'react';
import { Page } from './Page';
import { lmsMyCalendar } from '../utils/helpers/lmsApi';

import './MyCalendarPage.scss';

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
    return 'Date to be announced';
  }
  try {
    return new Date(ev.starts_at).toLocaleString();
  } catch {
    return ev.starts_at;
  }
}

function formatEventType(t) {
  if (!t || typeof t !== 'string') {
    return '';
  }
  return t.replace(/_/g, ' ');
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
    <Page id={id}>
      <div className="lms-page lms-shell">
        <h1 className="page-title">My calendar</h1>
        <p className="lms-intro">
          See due dates and milestones from your active courses. Times use a <strong>UTC month window</strong> for{' '}
          {label}.
        </p>
        <div className="lms-calendar-toolbar">
          <button type="button" className="lms-btn lms-btn--secondary lms-btn--sm" onClick={() => shiftMonth(-1)}>
            ← Previous month
          </button>
          <button type="button" className="lms-btn lms-btn--secondary lms-btn--sm" onClick={() => shiftMonth(1)}>
            Next month →
          </button>
        </div>
        {loading ? <p className="lms-meta">Loading your calendar…</p> : null}
        {err ? (
          <p className="error-message" style={{ whiteSpace: 'pre-line' }}>
            We couldn&apos;t load your calendar. {err}
          </p>
        ) : null}
        {!loading && !err && !events.length ? (
          <p className="lms-empty-hint">
            Nothing scheduled in this month. Try another month, or{' '}
            <a href="/my/learning">return to My learning</a> to keep making progress.
          </p>
        ) : null}
        <ul className="lms-event-list">
          {events.map((ev) => (
            <li key={ev.id} className="lms-event-card">
              <div className="lms-event-card__title">{ev.title}</div>
              <div className="lms-event-card__meta">
                {ev.course_title}
                {ev.course_slug ? <span> · {ev.course_slug}</span> : null}
              </div>
              <div className="lms-event-card__meta">
                {formatWhen(ev)} · {formatEventType(ev.event_type)}
              </div>
              {ev.description ? <p className="lms-event-card__desc">{ev.description}</p> : null}
              {ev.url ? (
                <a className="lms-event-card__link" href={ev.url}>
                  Open in course
                </a>
              ) : null}
            </li>
          ))}
        </ul>
        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/my/learning">My learning</a>
          {' · '}
          <a href="/courses">Browse courses</a>
          {' · '}
          <a href="/my/credentials">My credentials</a>
        </nav>
      </div>
    </Page>
  );
}
