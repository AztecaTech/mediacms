import React, { useEffect, useState } from 'react';
import { LmsNotificationsBell } from '../components/learning/LmsNotificationsBell';
import { LmsQuestionBankManager } from '../components/learning/LmsQuestionBankManager';
import { Page } from './Page';
import { lmsListCourses, lmsCourseRoster, lmsCourseRosterImport } from '../utils/helpers/lmsApi';

export function InstructorDashboardPage({ id = 'lms_my_teaching' }) {
  const [courses, setCourses] = useState([]);
  const [roster, setRoster] = useState(null);
  const [rosterSlug, setRosterSlug] = useState(null);
  const [error, setError] = useState(null);
  const [importMsg, setImportMsg] = useState(null);

  useEffect(() => {
    lmsListCourses()
      .then((rows) => setCourses(Array.isArray(rows) ? rows : rows.results || []))
      .catch((e) => setError(String(e.message || e)));
  }, []);

  const loadRoster = (slug) => {
    setRosterSlug(slug);
    setRoster(null);
    lmsCourseRoster(slug)
      .then(setRoster)
      .catch((e) => setError(String(e.message || e)));
  };

  return (
    <Page id={id}>
      <div className="lms-page lms-my-teaching">
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
            My teaching
          </h1>
          <LmsNotificationsBell />
        </div>
        {error ? <p className="error-message">{error}</p> : null}
        {importMsg ? <p className="lms-hint">{importMsg}</p> : null}
        <p className="lms-hint">
          Org managers: <a href="/my/org/learning">Org learning (at-risk and directory sync)</a>
        </p>
        <h2>Courses</h2>
        <ul>
          {courses.map((c) => (
            <li key={c.slug}>
              {c.title}{' '}
              <a className="link-like" href={`/learn/${c.slug}`}>
                Open player
              </a>{' '}
              <a className="link-like" href={`/teach/${c.slug}`}>
                Edit content
              </a>{' '}
              <a className="link-like" href={`/teach/${c.slug}/certificates`}>
                Certificates
              </a>{' '}
              <a className="link-like" href={`/api/v1/courses/${encodeURIComponent(c.slug)}/roster/export.csv`}>
                Roster CSV
              </a>{' '}
              <label className="link-like" style={{ cursor: 'pointer' }}>
                Import CSV
                <input
                  type="file"
                  accept=".csv,text/csv"
                  style={{ display: 'none' }}
                  onChange={async (e) => {
                    const f = e.target.files && e.target.files[0];
                    e.target.value = '';
                    if (!f) return;
                    setImportMsg(null);
                    setError(null);
                    try {
                      const r = await lmsCourseRosterImport(c.slug, f);
                      setImportMsg(
                        `${c.slug}: created ${r.created}, updated ${r.updated}, failed ${r.failed}`
                      );
                    } catch (err) {
                      setError(String(err.message || err));
                    }
                  }}
                />
              </label>{' '}
              <button type="button" className="link-like" onClick={() => loadRoster(c.slug)}>
                Roster
              </button>
            </li>
          ))}
        </ul>
        {rosterSlug ? (
          <>
            <h2>Roster ({rosterSlug})</h2>
            <ul>
              {(roster || []).map((r) => (
                <li key={r.id}>
                  {r.name} ({r.username}) — {r.progress_pct}%
                </li>
              ))}
            </ul>
          </>
        ) : null}
        <p>
          <a href="/courses">Public catalog</a>
        </p>
        <LmsQuestionBankManager />
      </div>
    </Page>
  );
}
