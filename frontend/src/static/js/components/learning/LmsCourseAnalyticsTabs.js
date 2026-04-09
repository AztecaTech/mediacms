import React, { useEffect, useState } from 'react';
import {
  lmsCourseAnalyticsDropOff,
  lmsCourseAnalyticsFunnel,
  lmsCourseAnalyticsHeatmap,
  lmsCourseAnalyticsTimeInContent,
} from '../../utils/helpers/lmsApi';

/**
 * Supplemental analytics tabs (funnel / heatmap / drop-off / time) for instructors.
 */
export function LmsCourseAnalyticsTabs({ slug }) {
  const [tab, setTab] = useState('funnel');
  const [payload, setPayload] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setErr(null);
    setPayload(null);
    const run =
      tab === 'funnel'
        ? lmsCourseAnalyticsFunnel(slug)
        : tab === 'heatmap'
          ? lmsCourseAnalyticsHeatmap(slug)
          : tab === 'dropoff'
            ? lmsCourseAnalyticsDropOff(slug)
            : lmsCourseAnalyticsTimeInContent(slug);
    run
      .then(setPayload)
      .catch((e) => setErr(String(e.message || e)))
      .finally(() => setLoading(false));
  }, [slug, tab]);

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        {['funnel', 'heatmap', 'dropoff', 'time'].map((k) => (
          <button
            key={k}
            type="button"
            className="button-link"
            style={{ fontWeight: tab === k ? 700 : 400 }}
            onClick={() => setTab(k)}
          >
            {k === 'dropoff' ? 'drop-off' : k}
          </button>
        ))}
      </div>
      {loading ? <p className="lms-meta">Loading…</p> : null}
      {err ? <p className="error-message">{err}</p> : null}
      {!loading && !err && payload ? (
        <pre style={{ fontSize: 12, overflow: 'auto', maxHeight: 280, background: '#f9fafb', padding: 8 }}>
          {JSON.stringify(payload, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
