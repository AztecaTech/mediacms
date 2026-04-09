import React, { useEffect, useState } from 'react';
import { lmsMyGrades } from '../../utils/helpers/lmsApi';

export function LmsMyGradesPanel({ slug }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!slug) {
      return;
    }
    lmsMyGrades(slug)
      .then(setData)
      .catch((e) => setError(String(e.message || e)));
  }, [slug]);

  if (error) {
    return <p className="error-message">{error}</p>;
  }
  if (!data) {
    return <p>Loading grades…</p>;
  }

  const cats = data.categories || [];
  if (!cats.length) {
    return <p>No graded items visible yet.</p>;
  }

  return (
    <div className="lms-grades">
      {cats.map((cat) => (
        <section key={cat.id} style={{ marginBottom: '1.25rem' }}>
          <h3 style={{ margin: '0 0 0.5rem' }}>{cat.name}</h3>
          <table className="table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>Item</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>Score</th>
                <th style={{ textAlign: 'left', borderBottom: '1px solid #ccc' }}>Feedback</th>
              </tr>
            </thead>
            <tbody>
              {(cat.items || []).map((it) => (
                <tr key={it.id}>
                  <td style={{ padding: '6px 0', verticalAlign: 'top' }}>{it.title}</td>
                  <td style={{ padding: '6px 0', verticalAlign: 'top' }}>
                    {it.excused ? (
                      <em>Excused</em>
                    ) : it.points_earned != null ? (
                      <>
                        {it.points_earned} / {it.max_points}
                      </>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td style={{ padding: '6px 0', verticalAlign: 'top', whiteSpace: 'pre-wrap' }}>
                    {it.feedback || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}
