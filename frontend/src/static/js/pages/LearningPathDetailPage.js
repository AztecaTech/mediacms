import React, { useEffect, useState } from 'react';
import { Page } from './Page';
import { lmsLearningPathDetail } from '../utils/helpers/lmsApi';
import { renderLmsMarkdownToHtml } from '../utils/helpers/renderLmsMarkdown';

import './LearningPathDetailPage.scss';

function readSlug() {
  if (typeof window !== 'undefined' && window.MediaCMS && window.MediaCMS.lmsPathSlug) {
    return window.MediaCMS.lmsPathSlug;
  }
  return '';
}

function descriptionHtml(text) {
  if (!text || typeof text !== 'string') {
    return '';
  }
  const trimmed = text.trim();
  if (!trimmed) {
    return '';
  }
  if (/<[a-z][\s\S]*>/i.test(trimmed)) {
    return trimmed;
  }
  return renderLmsMarkdownToHtml(trimmed);
}

export function LearningPathDetailPage({ id = 'lms_path_detail' }) {
  const [slug] = useState(readSlug);
  const [path, setPath] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug) {
      setError('Missing path slug.');
      return;
    }
    lmsLearningPathDetail(slug)
      .then(setPath)
      .catch((e) => setError(String(e.message || e)));
  }, [slug]);

  const courses = (path && path.path_courses) || [];
  const sorted = courses.slice().sort((a, b) => (a.order || 0) - (b.order || 0));

  return (
    <Page id={id}>
      <div className="lms-page lms-shell">
        <nav className="lms-breadcrumb" aria-label="Breadcrumb">
          <a href="/learning-paths">Learning paths</a>
          {path ? (
            <>
              {' / '}
              <span>{path.title}</span>
            </>
          ) : null}
        </nav>
        {error ? <p className="error-message">{error}</p> : null}
        {path ? (
          <>
            <header className="lms-page-head">
              <h1 className="page-title lms-page-head__title">{path.title}</h1>
              {path.status ? <span className="lms-pill">{path.status}</span> : null}
            </header>
            {path.description ? (
              <div
                className="lms-markdown-body lms-path-detail__desc"
                dangerouslySetInnerHTML={{ __html: descriptionHtml(path.description) }}
              />
            ) : null}

            <section className="lms-section" aria-labelledby="lms-path-steps-heading">
              <h2 id="lms-path-steps-heading" className="lms-section__title">
                Courses in this path
              </h2>
              <ol className="lms-path-detail__course-list">
                {sorted.map((row, index) => (
                  <li key={row.id} className="lms-path-detail__step">
                    <span className="lms-path-detail__step-num" aria-hidden>
                      {index + 1}
                    </span>
                    <div className="lms-path-detail__step-body">
                      {row.course ? (
                        <>
                          <h3 className="lms-path-detail__step-title">
                            <a href={`/courses/${encodeURIComponent(row.course.slug)}`}>{row.course.title}</a>
                          </h3>
                          <p className="lms-path-detail__step-meta">
                            {row.is_required ? 'Required step' : 'Optional step'}
                            {' · '}
                            <a href={`/learn/${encodeURIComponent(row.course.slug)}`}>Start learning</a>
                          </p>
                        </>
                      ) : (
                        <p className="lms-path-detail__step-title">Course #{row.course_id}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
              {!sorted.length ? <p className="lms-meta">No courses linked yet.</p> : null}
            </section>

            <nav className="lms-footer-links" aria-label="Related pages">
              <a href="/learning-paths">All paths</a>
              {' · '}
              <a href="/courses">Courses</a>
              {' · '}
              <a href="/my/learning">My learning</a>
            </nav>
          </>
        ) : null}
      </div>
    </Page>
  );
}
