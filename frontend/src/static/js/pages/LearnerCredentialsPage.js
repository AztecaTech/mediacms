import React, { useEffect, useState } from 'react';
import { LmsNotificationsBell } from '../components/learning/LmsNotificationsBell';
import { Page } from './Page';
import { lmsMyBadges, lmsMyCertificates, lmsMyTranscript } from '../utils/helpers/lmsApi';

import './LearnerCredentialsPage.scss';

const TABS = [
  { key: 'certificates', label: 'Certificates' },
  { key: 'badges', label: 'Badges' },
  { key: 'transcript', label: 'Transcript' },
];

export function LearnerCredentialsPage({ id = 'lms_my_credentials' }) {
  const [tab, setTab] = useState('certificates');
  const [certs, setCerts] = useState([]);
  const [badges, setBadges] = useState([]);
  const [transcript, setTranscript] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([lmsMyCertificates(), lmsMyBadges(), lmsMyTranscript()])
      .then(([c, b, t]) => {
        if (cancelled) {
          return;
        }
        setCerts(c.certificates || []);
        setBadges(b.badges || []);
        setTranscript(t.transcript || []);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(String(e.message || e));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Page id={id}>
      <div className="lms-page lms-my-credentials lms-shell lms-shell--wide">
        <header className="lms-page-head">
          <h1 className="page-title lms-page-head__title">My credentials</h1>
          <LmsNotificationsBell />
        </header>
        <p className="lms-intro">
          Certificates, badges, and your learning transcript stay here. Finish courses and assessments to populate
          this page.
        </p>
        {error ? (
          <p className="error-message">We couldn&apos;t load your credentials. {error}</p>
        ) : null}

        <div className="lms-tabs" role="tablist" aria-label="Credential views">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={tab === t.key}
              className={'lms-tab' + (tab === t.key ? ' is-active' : '')}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading ? <p className="lms-meta">Loading…</p> : null}

        {!loading && tab === 'certificates' ? (
          <section className="lms-section" aria-labelledby="lms-certs-heading">
            <h2 id="lms-certs-heading" className="lms-section__title">
              Certificates
            </h2>
            {!certs.length ? (
              <p className="lms-empty-hint">
                You don&apos;t have any certificates yet. Complete eligible courses to earn them, or{' '}
                <a href="/courses">browse courses</a>.
              </p>
            ) : null}
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {certs.map((row) => (
                <li key={row.id} className="lms-credential-card">
                  <h3 className="lms-credential-card__title">{row.course_title}</h3>
                  <div className="lms-meta" style={{ fontSize: '0.88rem' }}>
                    Issued {row.issued_at ? new Date(row.issued_at).toLocaleString() : '—'}
                    {row.revoked_at ? ' · Revoked' : ''}
                  </div>
                  <div className="lms-credential-card__actions">
                    Verification code: <code>{row.verification_code}</code>
                    {' · '}
                    <a href={`/api/v1/verify/${encodeURIComponent(row.verification_code)}/`} target="_blank" rel="noreferrer">
                      Verify (JSON)
                    </a>
                  </div>
                  {row.pdf_url ? (
                    <p style={{ margin: '0.65rem 0 0' }}>
                      <a className="lms-btn lms-btn--primary lms-btn--sm" href={row.pdf_url} target="_blank" rel="noreferrer">
                        Download PDF
                      </a>
                    </p>
                  ) : (
                    <p className="lms-help-text">A PDF will appear here when your certificate file is ready.</p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {!loading && tab === 'badges' ? (
          <section className="lms-section" aria-labelledby="lms-badges-heading">
            <h2 id="lms-badges-heading" className="lms-section__title">
              Badges
            </h2>
            {!badges.length ? (
              <p className="lms-empty-hint">
                No badges yet. They appear when your organization awards them for milestones or achievements.
              </p>
            ) : null}
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {badges.map((row) => (
                <li key={row.id} className="lms-credential-card">
                  <h3 className="lms-credential-card__title">{row.badge_name}</h3>
                  <div className="lms-meta" style={{ fontSize: '0.88rem' }}>
                    {row.badge_slug} · {row.awarded_at ? new Date(row.awarded_at).toLocaleString() : ''}
                  </div>
                  {row.badge_description ? <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>{row.badge_description}</p> : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {!loading && tab === 'transcript' ? (
          <section className="lms-section" aria-labelledby="lms-transcript-heading">
            <h2 id="lms-transcript-heading" className="lms-section__title">
              Transcript
            </h2>
            {!transcript.length ? (
              <p className="lms-empty-hint">
                Your transcript will list courses and grades as you enroll. Start from{' '}
                <a href="/courses">the course catalog</a>.
              </p>
            ) : null}
            {transcript.length ? (
              <div className="lms-table-wrap">
                <table className="lms-table">
                  <thead>
                    <tr>
                      <th scope="col">Course</th>
                      <th scope="col">Status</th>
                      <th scope="col">Progress</th>
                      <th scope="col">Grade</th>
                      <th scope="col">Completed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transcript.map((row) => (
                      <tr key={row.enrollment_id}>
                        <td>
                          <a href={`/learn/${encodeURIComponent(row.course_slug)}`}>{row.course_title}</a>
                        </td>
                        <td>{row.status}</td>
                        <td>{row.progress_pct}%</td>
                        <td>
                          {row.current_grade_pct != null ? `${row.current_grade_pct}%` : '—'}{' '}
                          {row.current_grade_letter || ''}
                        </td>
                        <td>{row.completed_at ? new Date(row.completed_at).toLocaleDateString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        ) : null}

        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/my/learning">My learning</a>
          {' · '}
          <a href="/my/calendar">My calendar</a>
          {' · '}
          <a href="/courses">Browse courses</a>
        </nav>
      </div>
    </Page>
  );
}
