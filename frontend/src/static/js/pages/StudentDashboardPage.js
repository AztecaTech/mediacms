import React, { useEffect, useState } from 'react';
import { LmsNotificationsBell } from '../components/learning/LmsNotificationsBell';
import { Page } from './Page';
import { lmsMyEnrollments } from '../utils/helpers/lmsApi';

export function StudentDashboardPage({ id = 'lms_my_learning' }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    lmsMyEnrollments()
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((e) => setError(String(e.message || e)));
  }, []);

  return (
    <Page id={id}>
      <div className="lms-page lms-my-learning">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <h1 className="page-title" style={{ margin: 0 }}>
            My learning
          </h1>
          <LmsNotificationsBell />
        </div>
        {error ? <p className="error-message">{error}</p> : null}
        <ul>
          {rows.map((e) => (
            <li key={e.id}>
              <a href={`/learn/${e.course_slug}`}>{e.course_title}</a>
              <span className="lms-meta">
                {' '}
                — {e.progress_pct}% ({e.status})
              </span>
            </li>
          ))}
        </ul>
        {!error && !rows.length ? <p>No enrollments yet.</p> : null}
        <p>
          <a href="/my/calendar">My calendar</a>
          {' · '}
          <a href="/my/credentials">My credentials</a>
          {' · '}
          <a href="/courses">Browse courses</a>
        </p>
      </div>
    </Page>
  );
}
