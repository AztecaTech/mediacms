import React, { useEffect, useState } from 'react';
import { LearningPathCatalogCard } from '../components/lms/LearningPathCatalogCard';
import { Page } from './Page';
import { lmsLearningPaths } from '../utils/helpers/lmsApi';

import './LearningPathsCatalogPage.scss';

export function LearningPathsCatalogPage({ id = 'lms_paths' }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    lmsLearningPaths()
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((e) => setError(String(e.message || e)));
  }, []);

  return (
    <Page id={id}>
      <div className="lms-page lms-shell lms-shell--wide">
        <h1 className="page-title">Learning paths</h1>
        <p className="lms-intro">
          Paths group courses in order—use them for structured programs or certifications. Open a path to see each
          step.
        </p>
        {error ? <p className="error-message">{error}</p> : null}
        <div className="lms-grid-cards" role="list">
          {rows.map((p) => (
            <div key={p.id} role="listitem">
              <LearningPathCatalogCard path={p} />
            </div>
          ))}
        </div>
        {!error && !rows.length ? <p className="lms-empty-hint">No published paths yet.</p> : null}
        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/courses">Courses</a>
          {' · '}
          <a href="/my/learning">My learning</a>
        </nav>
      </div>
    </Page>
  );
}
