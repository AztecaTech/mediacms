import React, { useEffect, useState } from 'react';
import { LmsNotificationsBell } from '../components/learning/LmsNotificationsBell';
import { LmsQuestionBankManager } from '../components/learning/LmsQuestionBankManager';
import { Page } from './Page';
import { lmsListCourses, lmsCourseRoster, lmsCourseRosterImport } from '../utils/helpers/lmsApi';

import './InstructorDashboardPage.scss';

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
      <div className="lms-page lms-my-teaching lms-shell lms-shell--wide">
        <header className="lms-page-head">
          <h1 className="page-title lms-page-head__title">My teaching</h1>
          <LmsNotificationsBell />
        </header>
        <p className="lms-intro">
          Open the player to preview as a learner, edit content in authoring, manage rosters, and export CSV from
          here.
        </p>
        {error ? <p className="error-message">{error}</p> : null}
        {importMsg ? <p className="lms-hint-box">{importMsg}</p> : null}
        <p className="lms-hint-box">
          Org managers: <a href="/my/org/learning">Org learning (at-risk and directory sync)</a>
        </p>

        <section className="lms-section" aria-labelledby="lms-teach-courses-heading">
          <h2 id="lms-teach-courses-heading" className="lms-section__title">
            Your courses
          </h2>
          <div className="lms-teach-course-list">
            {courses.map((c) => {
              const inputId = `lms-roster-import-${c.slug}`;
              return (
                <article key={c.slug} className="lms-dash-card">
                  <div className="lms-dash-card__top">
                    <h3 className="lms-dash-card__title">{c.title}</h3>
                  </div>
                  <div className="lms-dash-card__actions">
                    <a
                      className="lms-btn lms-btn--secondary lms-btn--sm"
                      href={`/learn/${encodeURIComponent(c.slug)}`}
                    >
                      Preview
                    </a>
                    <a
                      className="lms-btn lms-btn--secondary lms-btn--sm"
                      href={`/teach/${encodeURIComponent(c.slug)}`}
                    >
                      Edit content
                    </a>
                    <a
                      className="lms-btn lms-btn--secondary lms-btn--sm"
                      href={`/teach/${encodeURIComponent(c.slug)}/certificates`}
                    >
                      Certificates
                    </a>
                    <a
                      className="lms-btn lms-btn--secondary lms-btn--sm"
                      href={`/api/v1/courses/${encodeURIComponent(c.slug)}/roster/export.csv`}
                    >
                      Export CSV
                    </a>
                    <label htmlFor={inputId} className="lms-btn lms-btn--secondary lms-btn--sm">
                      Import CSV
                    </label>
                    <input
                      id={inputId}
                      className="lms-sr-only"
                      type="file"
                      accept=".csv,text/csv"
                      onChange={async (ev) => {
                        const f = ev.target.files && ev.target.files[0];
                        ev.target.value = '';
                        if (!f) {
                          return;
                        }
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
                    <button type="button" className="lms-btn lms-btn--primary lms-btn--sm" onClick={() => loadRoster(c.slug)}>
                      View roster
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
          {!courses.length && !error ? <p className="lms-empty-hint">No courses found for your account.</p> : null}
        </section>

        {rosterSlug ? (
          <section className="lms-section" aria-labelledby="lms-roster-heading">
            <h2 id="lms-roster-heading" className="lms-section__title">
              Roster — {rosterSlug}
            </h2>
            {roster && roster.length ? (
              <div className="lms-table-wrap">
                <table className="lms-table">
                  <thead>
                    <tr>
                      <th scope="col">Learner</th>
                      <th scope="col">Username</th>
                      <th scope="col">Progress</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roster.map((r) => (
                      <tr key={r.id}>
                        <td>{r.name}</td>
                        <td>{r.username}</td>
                        <td>{r.progress_pct != null ? `${r.progress_pct}%` : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="lms-meta">{roster ? 'No learners in this roster.' : 'Loading roster…'}</p>
            )}
          </section>
        ) : null}

        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/courses">Public catalog</a>
          {' · '}
          <a href="/my/learning">My learning</a>
        </nav>

        <section className="lms-section" aria-labelledby="lms-qb-heading">
          <h2 id="lms-qb-heading" className="lms-section__title">
            Question banks
          </h2>
          <LmsQuestionBankManager />
        </section>
      </div>
    </Page>
  );
}
