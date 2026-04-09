import React from 'react';
import PropTypes from 'prop-types';

import './LearningPathCatalogCard.scss';

function excerpt(raw, maxLen) {
  if (!raw || typeof raw !== 'string') {
    return '';
  }
  const text = raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  if (text.length <= maxLen) {
    return text;
  }
  return `${text.slice(0, maxLen).trim()}…`;
}

export function LearningPathCatalogCard({ path }) {
  const href = `/learning-paths/${encodeURIComponent(path.slug)}`;
  const desc = excerpt(path.description, 160);
  const thumb = path.thumbnail || '';

  return (
    <article className="lms-path-card">
      <a className="lms-path-card__media" href={href}>
        {thumb ? (
          <img src={thumb} alt="" loading="lazy" />
        ) : (
          <div className="lms-path-card__placeholder" aria-hidden>
            <span className="lms-path-card__placeholder-letter">
              {(path.title || '?').trim().charAt(0).toUpperCase()}
            </span>
          </div>
        )}
      </a>
      <div className="lms-path-card__body">
        <h2 className="lms-path-card__title">
          <a href={href}>{path.title}</a>
        </h2>
        {path.status ? (
          <p className="lms-path-card__meta">
            <span className="lms-path-card__status">{path.status}</span>
          </p>
        ) : null}
        {desc ? <p className="lms-path-card__desc">{desc}</p> : null}
        <a className="lms-path-card__cta" href={href}>
          View path
        </a>
      </div>
    </article>
  );
}

LearningPathCatalogCard.propTypes = {
  path: PropTypes.shape({
    slug: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    description: PropTypes.string,
    thumbnail: PropTypes.string,
    status: PropTypes.string,
  }).isRequired,
};
