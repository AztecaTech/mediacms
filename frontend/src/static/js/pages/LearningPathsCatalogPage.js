import React, { useEffect, useState } from 'react';
import { Page } from './Page';
import { lmsLearningPaths } from '../utils/helpers/lmsApi';

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
      <div className="lms-page" style={{ maxWidth: 720, margin: '0 auto' }}>
        <h1 className="page-title">Learning paths</h1>
        {error ? <p className="error-message">{error}</p> : null}
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {rows.map((p) => (
            <li key={p.id} style={{ marginBottom: '0.75rem' }}>
              <a href={`/learning-paths/${encodeURIComponent(p.slug)}`} style={{ fontWeight: 600 }}>
                {p.title}
              </a>
              {p.description ? <p className="lms-meta" style={{ margin: '0.25rem 0 0' }}>{p.description}</p> : null}
            </li>
          ))}
        </ul>
        {!error && !rows.length ? <p className="lms-meta">No published paths yet.</p> : null}
      </div>
    </Page>
  );
}
