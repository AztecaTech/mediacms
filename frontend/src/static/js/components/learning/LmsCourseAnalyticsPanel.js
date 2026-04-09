import React, { useEffect, useState } from 'react';
import { lmsCourseAnalyticsSummary } from '../../utils/helpers/lmsApi';
import { LmsCourseAnalyticsTabs } from './LmsCourseAnalyticsTabs';

export function LmsCourseAnalyticsPanel({ slug }) {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    lmsCourseAnalyticsSummary(slug, days)
      .then((res) => {
        setData(res);
      })
      .catch((e) => {
        const msg = String(e.message || e);
        if (msg.includes('Forbidden') || msg.includes('403')) {
          setForbidden(true);
          setData(null);
          return;
        }
        setError(msg);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [slug, days]);

  if (loading) {
    return <p>Loading analytics…</p>;
  }
  if (error) {
    return <p className="error-message">{error}</p>;
  }
  if (forbidden || !data) {
    return <p className="lms-meta">Course analytics are visible to instructors only.</p>;
  }

  return (
    <div className="lms-course-analytics">
      <label style={{ fontSize: 13, display: 'block', marginBottom: 12 }}>
        Period (days){' '}
        <select value={String(days)} onChange={(e) => setDays(Number(e.target.value, 10))}>
          <option value="7">7</option>
          <option value="30">30</option>
          <option value="90">90</option>
        </select>
      </label>
      <p style={{ fontSize: 14 }}>
        <strong>{data.total_events}</strong> events in the last {data.period_days} days
      </p>
      {data.by_type && data.by_type.length ? (
        <>
          <h4 style={{ marginBottom: 8 }}>By type</h4>
          <ul style={{ fontSize: 13 }}>
            {data.by_type.map((row) => (
              <li key={row.type}>
                {row.type}: {row.count}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="lms-meta">No events in this period.</p>
      )}
      {data.events_by_day && data.events_by_day.length ? (
        <>
          <h4 style={{ marginBottom: 8 }}>Events by day</h4>
          <div style={{ overflowX: 'auto', fontSize: 12 }}>
            <table style={{ borderCollapse: 'collapse' }}>
              <tbody>
                {data.events_by_day.map((row) => (
                  <tr key={String(row.day)}>
                    <td style={{ padding: '4px 8px', borderBottom: '1px solid #eee' }}>{row.day}</td>
                    <td style={{ padding: '4px 8px', borderBottom: '1px solid #eee' }}>{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      {data.daily_metrics && data.daily_metrics.length ? (
        <>
          <h4 style={{ marginBottom: 8 }}>Daily rollups</h4>
          <div style={{ overflowX: 'auto', fontSize: 12 }}>
            <table style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: 4 }}>Date</th>
                  <th style={{ textAlign: 'left', padding: 4 }}>Enrolled</th>
                  <th style={{ textAlign: 'left', padding: 4 }}>Active</th>
                  <th style={{ textAlign: 'left', padding: 4 }}>Avg %</th>
                </tr>
              </thead>
              <tbody>
                {data.daily_metrics.map((row) => (
                  <tr key={String(row.date)}>
                    <td style={{ padding: 4, borderBottom: '1px solid #eee' }}>{row.date}</td>
                    <td style={{ padding: 4, borderBottom: '1px solid #eee' }}>{row.enrollments_total}</td>
                    <td style={{ padding: 4, borderBottom: '1px solid #eee' }}>{row.active_students}</td>
                    <td style={{ padding: 4, borderBottom: '1px solid #eee' }}>{row.avg_progress_pct}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      <LmsCourseAnalyticsTabs slug={slug} />
    </div>
  );
}
