import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { OrgAtRiskListViewModel } from './org/OrgAtRiskListViewModel';

function tierStyle(tier) {
  const base = {
    display: 'inline-block',
    padding: '0.12rem 0.45rem',
    borderRadius: '4px',
    fontSize: '0.8rem',
    fontWeight: 600,
    textTransform: 'capitalize',
  };
  if (tier === 'high') return { ...base, background: '#fde8e8', color: '#9b1c1c' };
  if (tier === 'medium') return { ...base, background: '#fff8e6', color: '#8a6100' };
  if (tier === 'low') return { ...base, background: '#eef4ff', color: '#1e3a5f' };
  return { ...base, background: '#f0f0f0', color: '#333' };
}

export function LmsOrgAtRiskPanel() {
  const viewModel = useMemo(() => new OrgAtRiskListViewModel(), []);
  const [minTier, setMinTier] = useState('low');
  const [limit, setLimit] = useState(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [payload, setPayload] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [noteDraft, setNoteDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    setSaveMsg(null);
    viewModel
      .load(minTier, limit)
      .then(setPayload)
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setLoading(false));
  }, [viewModel, minTier, limit]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onSaveNote = async (enrollmentId) => {
    const text = noteDraft.trim();
    if (!text) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      await viewModel.postInterventionNote(enrollmentId, text);
      setSaveMsg('Note recorded.');
      setNoteDraft('');
      setExpandedId(null);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setSaving(false);
    }
  };

  const rows = (payload && payload.enrollments) || [];

  return (
    <section className="lms-org-at-risk" aria-labelledby="lms-org-at-risk-heading">
      <h2 id="lms-org-at-risk-heading" className="lms-subheading">
        At-risk enrollments
      </h2>
      <p className="lms-hint">
        Heuristic tiers from progress and course grades. Use notes to log follow-ups (stored as analytics
        events).
      </p>
      <div className="lms-toolbar" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
        <label>
          Min tier{' '}
          <select value={minTier} onChange={(e) => setMinTier(e.target.value)}>
            <option value="low">low+</option>
            <option value="medium">medium+</option>
            <option value="high">high</option>
          </select>
        </label>
        <label>
          Limit{' '}
          <input
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value) || 50)}
            style={{ width: '4.5rem' }}
          />
        </label>
        <button type="button" className="btn btn-secondary" onClick={refresh} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      {error ? <p className="error-message">{error}</p> : null}
      {saveMsg ? <p className="lms-hint">{saveMsg}</p> : null}
      {!loading && !error && !rows.length ? <p>No rows match the current filter.</p> : null}
      {rows.length ? (
        <div style={{ overflowX: 'auto' }}>
          <table className="lms-table">
            <thead>
              <tr>
                <th>Tier</th>
                <th>Learner</th>
                <th>Course</th>
                <th>Progress</th>
                <th>Grade</th>
                <th>Reasons</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <React.Fragment key={r.enrollment_id}>
                  <tr>
                    <td>
                      <span style={tierStyle(r.at_risk_tier)}>{r.at_risk_tier}</span>
                    </td>
                    <td>{r.username}</td>
                    <td>
                      <a href={`/courses/${encodeURIComponent(r.course_slug)}`}>{r.course_title}</a>
                    </td>
                    <td>{r.progress_pct}%</td>
                    <td>
                      {r.current_grade_pct != null ? `${r.current_grade_pct}%` : '—'}{' '}
                      {r.current_grade_letter ? `(${r.current_grade_letter})` : ''}
                    </td>
                    <td className="lms-meta">{(r.at_risk_reasons || []).join(', ')}</td>
                    <td>
                      <button
                        type="button"
                        className="link-like"
                        onClick={() => {
                          setExpandedId((id) => (id === r.enrollment_id ? null : r.enrollment_id));
                          setNoteDraft('');
                          setSaveMsg(null);
                        }}
                      >
                        {expandedId === r.enrollment_id ? 'Close' : 'Log note'}
                      </button>
                    </td>
                  </tr>
                  {expandedId === r.enrollment_id ? (
                    <tr>
                      <td colSpan={7}>
                        <textarea
                          rows={3}
                          style={{ width: '100%', maxWidth: '36rem' }}
                          placeholder="Intervention / follow-up note"
                          value={noteDraft}
                          onChange={(e) => setNoteDraft(e.target.value)}
                        />
                        <div style={{ marginTop: '0.35rem' }}>
                          <button
                            type="button"
                            className="btn btn-primary"
                            disabled={saving || !noteDraft.trim()}
                            onClick={() => onSaveNote(r.enrollment_id)}
                          >
                            {saving ? 'Saving…' : 'Save note'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
