import React, { useEffect, useState } from 'react';
import { lmsOrgCompletionTrend, lmsOrgEnrollmentTrend } from '../../utils/helpers/lmsApi';

function sparklinePoints(values, width, height, pad) {
  const n = values.length;
  if (!n) {
    return '';
  }
  const maxV = Math.max(1, ...values);
  const innerW = width - 2 * pad;
  const innerH = height - 2 * pad;
  const step = n <= 1 ? 0 : innerW / (n - 1);
  return values
    .map((v, i) => {
      const x = pad + i * step;
      const y = pad + innerH * (1 - v / maxV);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

function TrendChart({ title, points, valueKey, stroke }) {
  const w = 520;
  const h = 140;
  const pad = 20;
  const vals = (points || []).map((p) => Number(p[valueKey]) || 0);
  const pts = sparklinePoints(vals, w, h, pad);
  return (
    <div style={{ marginBottom: '1.25rem' }}>
      <h3 style={{ margin: '0 0 0.5rem' }}>{title}</h3>
      {!points?.length ? <p className="lms-hint">No daily metrics yet (CourseMetricsDaily).</p> : null}
      {points?.length ? (
        <svg width={w} height={h} role="img" aria-label={title} style={{ display: 'block' }}>
          <rect x={0} y={0} width={w} height={h} fill="rgba(0,0,0,0.02)" />
          <polyline
            fill="none"
            stroke={stroke}
            strokeWidth="2"
            points={pts}
          />
        </svg>
      ) : null}
    </div>
  );
}

export function LmsOrgTrendChartsPanel({ days = 180 }) {
  const [enrollment, setEnrollment] = useState(null);
  const [completion, setCompletion] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    Promise.all([lmsOrgEnrollmentTrend({ days }), lmsOrgCompletionTrend({ days })])
      .then(([e, c]) => {
        setEnrollment(e);
        setCompletion(c);
      })
      .catch((err) => setError(String(err.message || err)));
  }, [days]);

  if (error) {
    return <p className="error-message">{error}</p>;
  }
  if (!enrollment || !completion) {
    return <p className="lms-hint">Loading org trends…</p>;
  }

  return (
    <section className="lms-org-trends" style={{ marginBottom: '1.5rem' }}>
      <h2 style={{ marginTop: 0 }}>Enrollment & completion trends</h2>
      <p className="lms-hint" style={{ fontSize: 13 }}>
        Aggregated from CourseMetricsDaily (last {days} days).
      </p>
      <TrendChart
        title="New enrollments per day"
        points={enrollment.points}
        valueKey="enrollments_new"
        stroke="#2563eb"
      />
      <TrendChart
        title="New completions per day"
        points={completion.points}
        valueKey="completions_new"
        stroke="#059669"
      />
    </section>
  );
}
