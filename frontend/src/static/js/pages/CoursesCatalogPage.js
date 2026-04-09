import React, { useEffect, useState } from 'react';
import { CourseCatalogCard } from '../components/lms/CourseCatalogCard';
import { Page } from './Page';
import { lmsListCourses } from '../utils/helpers/lmsApi';

import './CoursesCatalogPage.scss';

export function CoursesCatalogPage({ id = 'lms_courses' }) {
  const [courses, setCourses] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    lmsListCourses()
      .then((rows) => setCourses(Array.isArray(rows) ? rows : rows.results || []))
      .catch((e) => setError(String(e.message || e)));
  }, []);

  return (
    <Page id={id}>
      <div className="lms-page lms-catalog">
        <h1 className="page-title">Courses</h1>
        <p className="lms-catalog__intro">
          Browse available training. Open a course to see the outline, enroll, and start learning.
        </p>
        {error ? <p className="error-message">{error}</p> : null}
        <div className="lms-catalog__grid" role="list">
          {courses.map((c) => (
            <div key={c.slug} role="listitem">
              <CourseCatalogCard course={c} />
            </div>
          ))}
        </div>
        {!error && !courses.length ? <p className="lms-meta">No published courses yet.</p> : null}
        <p className="lms-catalog__footer-links">
          <a href="/my/learning">My learning</a>
          {' · '}
          <a href="/my/teaching">My teaching</a>
          {' · '}
          <a href="/learning-paths">Learning paths</a>
        </p>
      </div>
    </Page>
  );
}
