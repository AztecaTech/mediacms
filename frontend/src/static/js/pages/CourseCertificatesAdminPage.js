import React, { useEffect, useMemo, useState } from 'react';
import { Page } from './Page';
import {
  lmsCertificateHealth,
  lmsCourseCertificatesList,
  lmsCourseRoster,
  lmsIssueCourseCertificate,
  lmsRevokeCertificate,
} from '../utils/helpers/lmsApi';

function readSlug() {
  if (typeof window !== 'undefined' && window.MediaCMS && window.MediaCMS.lmsCourseSlug) {
    return window.MediaCMS.lmsCourseSlug;
  }
  return '';
}

export function CourseCertificatesAdminPage({ id = 'lms_teach_certificates' }) {
  const [slug] = useState(readSlug);
  const [certs, setCerts] = useState([]);
  const [roster, setRoster] = useState([]);
  const [health, setHealth] = useState(null);
  const [issueId, setIssueId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = () => {
    if (!slug) {
      setError('Missing course slug.');
      return;
    }
    setError(null);
    Promise.all([
      lmsCourseCertificatesList(slug),
      lmsCourseRoster(slug),
      lmsCertificateHealth(slug),
    ])
      .then(([c, r, h]) => {
        setCerts(c.certificates || []);
        setRoster(Array.isArray(r) ? r : r.results || []);
        setHealth(h);
      })
      .catch((e) => setError(String(e.message || e)));
  };

  useEffect(() => {
    load();
  }, [slug]);

  const studentOptions = useMemo(() => {
    return (roster || []).filter((row) => (row.role || 'student') === 'student');
  }, [roster]);

  return (
    <Page id={id}>
      <div className="lms-page" style={{ maxWidth: 880, margin: '0 auto' }}>
        <h1 className="page-title">Certificates</h1>
        {slug ? (
          <p className="lms-meta">
            Course: {slug} · <a href={`/teach/${slug}`}>Edit course</a> ·{' '}
            <a href={`/learn/${slug}`}>Player</a>
          </p>
        ) : null}
        {error ? <p className="error-message">{error}</p> : null}
        {health ? (
          <p className="lms-hint" style={{ fontSize: 13 }}>
            Active: {health.active_certificates} · Revoked: {health.revoked_certificates} · Issued (7d):{' '}
            {health.issued_last_7d}
          </p>
        ) : null}

        <section style={{ marginBottom: '1.5rem' }}>
          <h2>Issue certificate</h2>
          <p className="lms-hint" style={{ fontSize: 13 }}>
            Requires a certificate policy for this course. Eligibility rules still apply on the server.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
            <select
              value={issueId}
              onChange={(e) => setIssueId(e.target.value)}
              style={{ minWidth: 220 }}
            >
              <option value="">Select enrollment…</option>
              {studentOptions.map((r) => (
                <option key={r.id} value={String(r.id)}>
                  {r.name || r.username} ({r.username})
                </option>
              ))}
            </select>
            <button
              type="button"
              disabled={busy || !issueId}
              onClick={() => {
                setBusy(true);
                lmsIssueCourseCertificate(slug, Number(issueId))
                  .then(() => {
                    setIssueId('');
                    load();
                  })
                  .catch((e) => setError(String(e.message || e)))
                  .finally(() => setBusy(false));
              }}
            >
              {busy ? 'Working…' : 'Issue'}
            </button>
          </div>
        </section>

        <section>
          <h2>Issued in this course</h2>
          {!certs.length ? <p className="lms-hint">No rows yet.</p> : null}
          {certs.length ? (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: 6 }}>Learner</th>
                  <th style={{ textAlign: 'left', padding: 6 }}>Issued</th>
                  <th style={{ textAlign: 'left', padding: 6 }}>Status</th>
                  <th style={{ textAlign: 'left', padding: 6 }}>Verify</th>
                  <th style={{ textAlign: 'left', padding: 6 }} />
                </tr>
              </thead>
              <tbody>
                {certs.map((c) => (
                  <tr key={c.certificate_id}>
                    <td style={{ padding: 6, borderTop: '1px solid #ddd' }}>
                      {c.recipient_display} ({c.username})
                    </td>
                    <td style={{ padding: 6, borderTop: '1px solid #ddd' }}>{c.issued_at}</td>
                    <td style={{ padding: 6, borderTop: '1px solid #ddd' }}>
                      {c.revoked_at ? `Revoked ${c.revoked_at}` : 'Active'}
                    </td>
                    <td style={{ padding: 6, borderTop: '1px solid #ddd' }}>
                      <a href={`/api/v1/verify/${encodeURIComponent(c.verification_code)}/`} target="_blank" rel="noreferrer">
                        Link
                      </a>
                    </td>
                    <td style={{ padding: 6, borderTop: '1px solid #ddd' }}>
                      {!c.revoked_at ? (
                        <button
                          type="button"
                          className="link-like"
                          disabled={busy}
                          onClick={() => {
                            const reason = window.prompt('Revocation reason (optional)', '') || '';
                            setBusy(true);
                            lmsRevokeCertificate(c.certificate_id, reason)
                              .then(() => load())
                              .catch((e) => setError(String(e.message || e)))
                              .finally(() => setBusy(false));
                          }}
                        >
                          Revoke
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </section>
      </div>
    </Page>
  );
}
