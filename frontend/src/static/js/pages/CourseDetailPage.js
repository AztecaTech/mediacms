import React, { useEffect, useState } from 'react';
import { Page } from './Page';
import { lmsEnroll, lmsGetCourse } from '../utils/helpers/lmsApi';

function readSlug() {
  if (typeof window !== 'undefined' && window.MediaCMS && window.MediaCMS.lmsCourseSlug) {
    return window.MediaCMS.lmsCourseSlug;
  }
  return '';
}

export function CourseDetailPage({ id = 'lms_course_detail' }) {
  const [slug] = useState(readSlug);
  const [course, setCourse] = useState(null);
  const [error, setError] = useState(null);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    if (!slug) {
      setError('Missing course slug.');
      return;
    }
    lmsGetCourse(slug)
      .then(setCourse)
      .catch((e) => setError(String(e.message || e)));
  }, [slug]);

  const onEnroll = () => {
    if (!slug) {
      return;
    }
    setEnrolling(true);
    lmsEnroll(slug, null)
      .then(() => {
        window.location.href = `/learn/${slug}`;
      })
      .catch((e) => {
        setError(String(e.message || e));
        setEnrolling(false);
      });
  };

  return (
    <Page id={id}>
      <div className="lms-page lms-course-detail">
        {error ? <p className="error-message">{error}</p> : null}
        {course ? (
          <>
            <h1 className="page-title">{course.title}</h1>
            <p>{course.description}</p>
            <p>
              <button type="button" className="button-link" onClick={onEnroll} disabled={enrolling}>
                {enrolling ? 'Enrolling…' : 'Enroll'}
              </button>
              {' '}
              <a className="button-link" href={`/learn/${course.slug}`}>
                Go to course player
              </a>
            </p>
          </>
        ) : null}
        <p>
          <a href="/courses">All courses</a>
        </p>
      </div>
    </Page>
  );
}
