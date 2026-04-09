import React, { useEffect, useMemo, useState } from 'react';
import { Page } from './Page';
import { useUser } from '../utils/hooks/';
import { lmsEnroll, lmsGetCourse } from '../utils/helpers/lmsApi';
import { renderLmsMarkdownToHtml } from '../utils/helpers/renderLmsMarkdown';

import './CourseDetailPage.scss';

function readSlug() {
  if (typeof window !== 'undefined' && window.MediaCMS && window.MediaCMS.lmsCourseSlug) {
    return window.MediaCMS.lmsCourseSlug;
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

function enrollmentLabel(type) {
  const map = {
    open: 'Open enrollment',
    invite: 'Invite only',
    rbac_group: 'Group access',
    approval: 'Approval required',
  };
  return map[type] || type || '';
}

export function CourseDetailPage({ id = 'lms_course_detail' }) {
  const { isAnonymous } = useUser();
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

  const canAccessLessons = useMemo(() => {
    if (!course || !Array.isArray(course.modules)) {
      return false;
    }
    // When not enrolled, API hides lesson payloads (no media, quiz_id, body, etc.).
    const lessonContentUnlocked = (l) =>
      !!l.media ||
      l.quiz_id != null ||
      l.assignment_id != null ||
      (typeof l.text_body === 'string' && l.text_body.trim().length > 0) ||
      !!l.attachment_url ||
      (typeof l.external_url === 'string' && l.external_url.trim().length > 0);
    return course.modules.some((m) => (m.lessons || []).some(lessonContentUnlocked));
  }, [course]);

  const loginHref = useMemo(() => {
    const next = encodeURIComponent(`/courses/${slug}`);
    return `/accounts/login/?next=${next}`;
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
        if (e.status === 401) {
          window.location.href = loginHref;
          return;
        }
        setError(String(e.message || e));
        setEnrolling(false);
      });
  };

  const pills = course
    ? [
        course.mode,
        course.difficulty,
        course.category_title,
        enrollmentLabel(course.enrollment_type),
        course.estimated_hours ? `${course.estimated_hours} h est.` : null,
        course.enrolled_count != null ? `${course.enrolled_count} enrolled` : null,
      ].filter(Boolean)
    : [];

  return (
    <Page id={id}>
      <div className="lms-page lms-course-detail">
        <nav className="lms-breadcrumb" aria-label="Breadcrumb">
          <a href="/courses">Courses</a>
          {course ? (
            <>
              {' / '}
              <span>{course.title}</span>
            </>
          ) : null}
        </nav>

        {error ? <p className="error-message">{error}</p> : null}

        {course ? (
          <>
            <div className="lms-course-detail__hero">
              {course.thumbnail ? (
                <div className="lms-course-detail__thumb">
                  <img src={course.thumbnail} alt="" />
                </div>
              ) : (
                <div className="lms-course-detail__thumb-placeholder" aria-hidden>
                  {(course.title || '?').trim().charAt(0).toUpperCase()}
                </div>
              )}
              <div>
                <h1 className="lms-course-detail__title">{course.title}</h1>
                {pills.length ? (
                  <ul className="lms-pill-row" aria-label="Course details">
                    {pills.map((p) => (
                      <li key={p}>
                        <span className="lms-pill">{p}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}

                <div className="lms-btn-row">
                  {canAccessLessons ? (
                    <a className="lms-btn lms-btn--primary" href={`/learn/${course.slug}`}>
                      Continue to course
                    </a>
                  ) : null}
                  {!canAccessLessons && isAnonymous ? (
                    <a className="lms-btn lms-btn--primary" href={loginHref}>
                      Sign in to enroll
                    </a>
                  ) : null}
                  {!canAccessLessons && !isAnonymous ? (
                    <button
                      type="button"
                      className="lms-btn lms-btn--primary"
                      onClick={onEnroll}
                      disabled={enrolling}
                    >
                      {enrolling ? 'Enrolling…' : 'Enroll in this course'}
                    </button>
                  ) : null}
                  <a className="lms-btn lms-btn--secondary" href="/courses">
                    Browse more courses
                  </a>
                </div>
                {!canAccessLessons ? (
                  <p className="lms-course-detail__hint">
                    Lesson videos and materials unlock after you enroll (and sign in if required).
                  </p>
                ) : null}
              </div>
            </div>

            {course.description ? (
              <div
                className="lms-course-detail__description lms-markdown-body"
                dangerouslySetInnerHTML={{ __html: descriptionHtml(course.description) }}
              />
            ) : null}

            {course.modules && course.modules.length ? (
              <section className="lms-course-detail__outline" aria-labelledby="lms-outline-heading">
                <h2 id="lms-outline-heading">What you&apos;ll cover</h2>
                {course.modules.map((mod) => (
                  <div key={mod.id} className="lms-course-detail__module">
                    <h3 className="lms-course-detail__module-title">{mod.title}</h3>
                    {(mod.lessons || []).length ? (
                      <ol className="lms-course-detail__lessons">
                        {(mod.lessons || []).map((les) => {
                          const locked = les.is_locked || les.prerequisite_locked;
                          return (
                            <li key={les.id}>
                              {les.title}
                              {locked ? (
                                <span className="lms-course-detail__locked"> — locked until enrolled / prerequisites</span>
                              ) : null}
                            </li>
                          );
                        })}
                      </ol>
                    ) : (
                      <p className="lms-meta">No lessons in this module yet.</p>
                    )}
                  </div>
                ))}
              </section>
            ) : null}
          </>
        ) : null}

        <p style={{ marginTop: '2rem' }}>
          <a href="/courses">← All courses</a>
        </p>
      </div>
    </Page>
  );
}
