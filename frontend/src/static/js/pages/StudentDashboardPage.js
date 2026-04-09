import React, { useEffect, useState } from 'react';
import { LmsNotificationsBell } from '../components/learning/LmsNotificationsBell';
import { Page } from './Page';
import { lmsMyEnrollments } from '../utils/helpers/lmsApi';

import './StudentDashboardPage.scss';

function progressValue(pct) {
  const n = Number(pct);
  if (Number.isNaN(n)) {
    return 0;
  }
  return Math.min(100, Math.max(0, n));
}

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
      <div className="lms-page lms-my-learning lms-shell">
        <header className="lms-page-head">
          <h1 className="page-title lms-page-head__title">My learning</h1>
          <LmsNotificationsBell />
        </header>
        <p className="lms-intro">
          Continue where you left off. Progress is saved as you complete lessons, videos, and assessments.
        </p>
        {error ? <p className="error-message">{error}</p> : null}
        <div className="lms-dash-list">
          {rows.map((e) => {
            const p = progressValue(e.progress_pct);
            return (
              <article key={e.id} className="lms-dash-card">
                <div className="lms-dash-card__top">
                  <h2 className="lms-dash-card__title">
                    <a href={`/learn/${encodeURIComponent(e.course_slug)}`}>{e.course_title}</a>
                  </h2>
                  {e.status ? <span className="lms-pill">{e.status}</span> : null}
                </div>
                <div
                  className="lms-progress"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(p)}
                  aria-label={`Progress in ${e.course_title}`}
                >
                  <div className="lms-progress__fill" style={{ width: `${p}%` }} />
                </div>
                <p className="lms-progress__label">{Math.round(p)}% complete</p>
                <div className="lms-dash-card__actions">
                  <a
                    className="lms-btn lms-btn--primary lms-btn--sm"
                    href={`/learn/${encodeURIComponent(e.course_slug)}`}
                  >
                    Continue
                  </a>
                  <a
                    className="lms-btn lms-btn--secondary lms-btn--sm"
                    href={`/courses/${encodeURIComponent(e.course_slug)}`}
                  >
                    Course overview
                  </a>
                </div>
              </article>
            );
          })}
        </div>
        {!error && !rows.length ? (
          <p className="lms-empty-hint">
            You are not enrolled in any courses yet.{' '}
            <a href="/courses">Browse the catalog</a> to get started.
          </p>
        ) : null}
        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/my/calendar">My calendar</a>
          {' · '}
          <a href="/my/credentials">My credentials</a>
          {' · '}
          <a href="/courses">Browse courses</a>
          {' · '}
          <a href="/learning-paths">Learning paths</a>
        </nav>
      </div>
    </Page>
  );
}
