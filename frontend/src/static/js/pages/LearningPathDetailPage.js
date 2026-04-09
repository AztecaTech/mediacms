import React, { useEffect, useState } from 'react';
import { Page } from './Page';
import { lmsLearningPathDetail } from '../utils/helpers/lmsApi';

function readSlug() {
  if (typeof window !== 'undefined' && window.MediaCMS && window.MediaCMS.lmsPathSlug) {
    return window.MediaCMS.lmsPathSlug;
  }
  return '';
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

  return (
    <Page id={id}>
      <div className="lms-page" style={{ maxWidth: 720, margin: '0 auto' }}>
        {error ? <p className="error-message">{error}</p> : null}
        {path ? (
          <>
            <h1 className="page-title">{path.title}</h1>
            {path.description ? <p>{path.description}</p> : null}
            <h2>Courses in this path</h2>
            <ol>
              {courses
                .slice()
                .sort((a, b) => (a.order || 0) - (b.order || 0))
                .map((row) => (
                  <li key={row.id} style={{ marginBottom: 8 }}>
                    {row.course ? (
                      <>
                        <a href={`/courses/${encodeURIComponent(row.course.slug)}`}>{row.course.title}</a>
                        {row.is_required ? (
                          <span className="lms-meta" style={{ marginLeft: 8 }}>
                            required
                          </span>
                        ) : null}
                      </>
                    ) : (
                      <span>Course #{row.course_id}</span>
                    )}
                  </li>
                ))}
            </ol>
            {!courses.length ? <p className="lms-meta">No courses linked yet.</p> : null}
            <p>
              <a href="/learning-paths">All paths</a>
            </p>
          </>
        ) : null}
      </div>
    </Page>
  );
}
