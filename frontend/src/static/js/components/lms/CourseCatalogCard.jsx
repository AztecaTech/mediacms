import React from 'react';
import PropTypes from 'prop-types';

import './CourseCatalogCard.scss';

function plainTextExcerpt(raw, maxLen) {
  if (!raw || typeof raw !== 'string') {
    return '';
  }
  const text = raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  if (text.length <= maxLen) {
    return text;
  }
  return `${text.slice(0, maxLen).trim()}…`;
}

export function CourseCatalogCard({ course }) {
  const href = `/courses/${encodeURIComponent(course.slug)}`;
  const excerpt = plainTextExcerpt(course.description, 180);
  const thumb = course.thumbnail || '';
  const metaParts = [course.mode, course.difficulty, course.category_title].filter(Boolean);

  return (
    <article className="lms-course-card">
      <a className="lms-course-card__media" href={href}>
        {thumb ? (
          <img src={thumb} alt="" loading="lazy" />
        ) : (
          <div className="lms-course-card__placeholder" aria-hidden>
            <span className="lms-course-card__placeholder-letter">
              {(course.title || '?').trim().charAt(0).toUpperCase()}
            </span>
          </div>
        )}
      </a>
      <div className="lms-course-card__body">
        <h2 className="lms-course-card__title">
          <a href={href}>{course.title}</a>
        </h2>
        {metaParts.length ? <p className="lms-course-card__meta">{metaParts.join(' · ')}</p> : null}
        {excerpt ? <p className="lms-course-card__desc">{excerpt}</p> : null}
        <div className="lms-course-card__stats">
          {course.estimated_hours != null && course.estimated_hours !== '' ? (
            <span>{course.estimated_hours} h est.</span>
          ) : null}
          {course.enrolled_count != null ? <span>{course.enrolled_count} enrolled</span> : null}
        </div>
        <a className="lms-course-card__cta" href={href}>
          View course
        </a>
      </div>
    </article>
  );
}

CourseCatalogCard.propTypes = {
  course: PropTypes.shape({
    slug: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    description: PropTypes.string,
    thumbnail: PropTypes.string,
    mode: PropTypes.string,
    difficulty: PropTypes.string,
    category_title: PropTypes.string,
    estimated_hours: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    enrolled_count: PropTypes.number,
  }).isRequired,
};
