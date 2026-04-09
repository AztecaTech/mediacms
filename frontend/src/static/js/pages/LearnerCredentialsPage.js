import React, { useEffect, useState } from 'react';
import { LmsNotificationsBell } from '../components/learning/LmsNotificationsBell';
import { Page } from './Page';
import { lmsMyBadges, lmsMyCertificates, lmsMyTranscript } from '../utils/helpers/lmsApi';

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
      <div className="lms-page lms-my-credentials">
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
            My credentials
          </h1>
          <LmsNotificationsBell />
        </div>
        <p className="lms-meta" style={{ marginTop: 8 }}>
          <a href="/my/learning">My learning</a>
          {' · '}
          <a href="/courses">Browse courses</a>
        </p>
        {error ? <p className="error-message">{error}</p> : null}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '1rem 0' }}>
          {['certificates', 'badges', 'transcript'].map((key) => (
            <button
              key={key}
              type="button"
              className="button-link"
              style={{ fontWeight: tab === key ? 700 : 400 }}
              onClick={() => setTab(key)}
            >
              {key === 'certificates' ? 'Certificates' : key === 'badges' ? 'Badges' : 'Transcript'}
            </button>
          ))}
        </div>
        {loading ? <p>Loading…</p> : null}
        {!loading && tab === 'certificates' ? (
          <section>
            {!certs.length ? <p>No certificates yet.</p> : null}
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {certs.map((row) => (
                <li
                  key={row.id}
                  style={{
                    border: '1px solid #e5e7eb',
                    borderRadius: 8,
                    padding: 12,
                    marginBottom: 10,
                  }}
                >
                  <strong>{row.course_title}</strong>
                  <div className="lms-meta" style={{ fontSize: 13 }}>
                    Issued {row.issued_at ? new Date(row.issued_at).toLocaleString() : ''}
                    {row.revoked_at ? ' · Revoked' : ''}
                  </div>
                  <div style={{ fontSize: 13, marginTop: 6 }}>
                    Code: <code>{row.verification_code}</code>
                    {' · '}
                    <a href={`/api/v1/verify/${encodeURIComponent(row.verification_code)}/`} target="_blank" rel="noreferrer">
                      Verification (JSON)
                    </a>
                  </div>
                  {row.pdf_url ? (
                    <p style={{ margin: '8px 0 0' }}>
                      <a href={row.pdf_url} target="_blank" rel="noreferrer">
                        Download PDF
                      </a>
                    </p>
                  ) : (
                    <p className="lms-meta" style={{ marginTop: 6 }}>
                      PDF not available yet.
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {!loading && tab === 'badges' ? (
          <section>
            {!badges.length ? <p>No badges yet.</p> : null}
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {badges.map((row) => (
                <li
                  key={row.id}
                  style={{
                    border: '1px solid #e5e7eb',
                    borderRadius: 8,
                    padding: 12,
                    marginBottom: 10,
                  }}
                >
                  <strong>{row.badge_name}</strong>
                  <div className="lms-meta" style={{ fontSize: 13 }}>
                    {row.badge_slug} · {row.awarded_at ? new Date(row.awarded_at).toLocaleString() : ''}
                  </div>
                  {row.badge_description ? <p style={{ fontSize: 13, marginTop: 6 }}>{row.badge_description}</p> : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {!loading && tab === 'transcript' ? (
          <section>
            {!transcript.length ? <p>No transcript rows yet.</p> : null}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: 8 }}>Course</th>
                    <th style={{ textAlign: 'left', padding: 8 }}>Status</th>
                    <th style={{ textAlign: 'left', padding: 8 }}>Progress</th>
                    <th style={{ textAlign: 'left', padding: 8 }}>Grade</th>
                    <th style={{ textAlign: 'left', padding: 8 }}>Completed</th>
                  </tr>
                </thead>
                <tbody>
                  {transcript.map((row) => (
                    <tr key={row.enrollment_id} style={{ borderTop: '1px solid #eee' }}>
                      <td style={{ padding: 8 }}>
                        <a href={`/learn/${row.course_slug}`}>{row.course_title}</a>
                      </td>
                      <td style={{ padding: 8 }}>{row.status}</td>
                      <td style={{ padding: 8 }}>{row.progress_pct}%</td>
                      <td style={{ padding: 8 }}>
                        {row.current_grade_pct != null ? `${row.current_grade_pct}%` : '—'}{' '}
                        {row.current_grade_letter || ''}
                      </td>
                      <td style={{ padding: 8 }}>
                        {row.completed_at ? new Date(row.completed_at).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </div>
    </Page>
  );
}
