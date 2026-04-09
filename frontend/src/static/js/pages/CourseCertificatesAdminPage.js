import React, { useEffect, useMemo, useState } from 'react';
import { Page } from './Page';
import {
  lmsCertificateHealth,
  lmsCourseCertificatesList,
  lmsCourseRoster,
  lmsIssueCourseCertificate,
  lmsRevokeCertificate,
} from '../utils/helpers/lmsApi';

import './CourseCertificatesAdminPage.scss';

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
      <div className="lms-page lms-shell lms-shell--wide">
        <nav className="lms-breadcrumb" aria-label="Breadcrumb">
          <a href="/my/teaching">My teaching</a>
          {' / '}
          <span>Certificates</span>
        </nav>
        <h1 className="page-title">Course certificates</h1>
        {slug ? (
          <p className="lms-intro">
            Issue and review PDF certificates for this course. Learners see their certificates under{' '}
            <strong>My credentials</strong>.
          </p>
        ) : null}
        {slug ? (
          <div className="lms-btn-row" style={{ marginTop: 0 }}>
            <a className="lms-btn lms-btn--secondary lms-btn--sm" href={`/teach/${encodeURIComponent(slug)}`}>
              Edit course
            </a>
            <a className="lms-btn lms-btn--secondary lms-btn--sm" href={`/learn/${encodeURIComponent(slug)}`}>
              Preview player
            </a>
          </div>
        ) : null}
        {error ? (
          <p className="error-message">We couldn&apos;t load certificate data. {error}</p>
        ) : null}
        {health ? (
          <p className="lms-hint-box">
            Active: {health.active_certificates} · Revoked: {health.revoked_certificates} · Issued (last 7 days):{' '}
            {health.issued_last_7d}
          </p>
        ) : null}

        <section className="lms-section" aria-labelledby="lms-cert-issue-heading">
          <h2 id="lms-cert-issue-heading" className="lms-section__title">
            Issue a certificate
          </h2>
          <p className="lms-help-text" style={{ marginBottom: '0.65rem' }}>
            Choose a learner with an enrollment. The server checks your course&apos;s certificate policy and eligibility
            rules.
          </p>
          <div className="lms-cert-issue-row">
            <select
              className="lms-select"
              value={issueId}
              onChange={(e) => setIssueId(e.target.value)}
              aria-label="Select learner enrollment"
            >
              <option value="">Select learner…</option>
              {studentOptions.map((r) => (
                <option key={r.id} value={String(r.id)}>
                  {r.name || r.username} ({r.username})
                </option>
              ))}
            </select>
            <button
              type="button"
              className="lms-btn lms-btn--primary lms-btn--sm"
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
              {busy ? 'Working…' : 'Issue certificate'}
            </button>
          </div>
        </section>

        <section className="lms-section" aria-labelledby="lms-cert-list-heading">
          <h2 id="lms-cert-list-heading" className="lms-section__title">
            Issued in this course
          </h2>
          {!certs.length ? (
            <p className="lms-empty-hint">No certificates issued yet. Use the form above when a learner is eligible.</p>
          ) : null}
          {certs.length ? (
            <div className="lms-table-wrap">
              <table className="lms-table">
                <thead>
                  <tr>
                    <th scope="col">Learner</th>
                    <th scope="col">Issued</th>
                    <th scope="col">Status</th>
                    <th scope="col">Verify</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {certs.map((c) => (
                    <tr key={c.certificate_id}>
                      <td>
                        {c.recipient_display} ({c.username})
                      </td>
                      <td>{c.issued_at}</td>
                      <td>{c.revoked_at ? `Revoked ${c.revoked_at}` : 'Active'}</td>
                      <td>
                        <a href={`/api/v1/verify/${encodeURIComponent(c.verification_code)}/`} target="_blank" rel="noreferrer">
                          Verification link
                        </a>
                      </td>
                      <td>
                        {!c.revoked_at ? (
                          <button
                            type="button"
                            className="lms-btn lms-btn--secondary lms-btn--sm"
                            disabled={busy}
                            onClick={() => {
                              const reason = window.prompt('Optional reason for revocation', '') || '';
                              setBusy(true);
                              lmsRevokeCertificate(c.certificate_id, reason)
                                .then(() => load())
                                .catch((e) => setError(String(e.message || e)))
                                .finally(() => setBusy(false));
                            }}
                          >
                            Revoke
                          </button>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>

        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/my/teaching">My teaching</a>
          {' · '}
          <a href="/courses">Course catalog</a>
        </nav>
      </div>
    </Page>
  );
}
