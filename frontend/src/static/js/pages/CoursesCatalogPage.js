import React, { useEffect, useState } from 'react';
import { Page } from './Page';
import { lmsListCourses } from '../utils/helpers/lmsApi';

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
        {error ? <p className="error-message">{error}</p> : null}
        <ul className="lms-course-list">
          {courses.map((c) => (
            <li key={c.slug}>
              <a href={`/courses/${c.slug}`}>{c.title}</a>
              <span className="lms-meta"> — {c.mode}</span>
            </li>
          ))}
        </ul>
        {!error && !courses.length ? <p>No published courses yet.</p> : null}
        <p>
          <a href="/my/learning">My learning</a>
          {' · '}
          <a href="/my/teaching">My teaching</a>
        </p>
      </div>
    </Page>
  );
}
