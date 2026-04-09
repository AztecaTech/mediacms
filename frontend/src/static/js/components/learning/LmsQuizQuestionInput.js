import React from 'react';

/** Controlled input for one quiz question (`value` matches API payload pieces). */
export function LmsQuizQuestionInput({ question, value, onChange = () => {}, readOnly }) {
  const q = question;
  const v = value || { choice_ids: [], text_answer: '', matching_json: '' };
  const set = (patch) => onChange({ ...v, ...patch });

  const choices = q.choices || [];
  const t = q.type;

  if (readOnly) {
    const ans = q.answer || {};
    return (
      <div style={{ marginBottom: '1rem', padding: '0.75rem', background: '#f9f9f9', borderRadius: 4 }}>
        <p style={{ margin: '0 0 0.5rem', fontWeight: 600, whiteSpace: 'pre-wrap' }}>{q.prompt}</p>
        <p className="lms-meta" style={{ fontSize: 13 }}>
          Points: {ans.points_awarded != null ? `${ans.points_awarded} / ${q.points}` : '—'} · Auto:{' '}
          {ans.auto_graded ? 'yes' : 'no'}
        </p>
        {ans.grader_feedback ? <p style={{ fontSize: 13 }}>{ans.grader_feedback}</p> : null}
      </div>
    );
  }

  if (t === 'mc_single' || t === 'true_false') {
    return (
      <fieldset style={{ marginBottom: '1.25rem', border: 'none', padding: 0 }}>
        <legend style={{ fontWeight: 600, marginBottom: 8 }}>{q.prompt}</legend>
        {choices.map((c) => (
          <label key={c.id} style={{ display: 'block', marginBottom: 6 }}>
            <input
              type="radio"
              name={`q_${q.id}`}
              checked={(v.choice_ids || []).includes(c.id)}
              onChange={() => set({ choice_ids: [c.id] })}
            />{' '}
            {c.text}
          </label>
        ))}
      </fieldset>
    );
  }

  if (t === 'mc_multi') {
    return (
      <fieldset style={{ marginBottom: '1.25rem', border: 'none', padding: 0 }}>
        <legend style={{ fontWeight: 600, marginBottom: 8 }}>{q.prompt}</legend>
        {choices.map((c) => {
          const sel = new Set(v.choice_ids || []);
          const on = sel.has(c.id);
          return (
            <label key={c.id} style={{ display: 'block', marginBottom: 6 }}>
              <input
                type="checkbox"
                checked={on}
                onChange={() => {
                  const next = new Set(v.choice_ids || []);
                  if (on) {
                    next.delete(c.id);
                  } else {
                    next.add(c.id);
                  }
                  set({ choice_ids: [...next] });
                }}
              />{' '}
              {c.text}
            </label>
          );
        })}
      </fieldset>
    );
  }

  if (t === 'short_answer' || t === 'fill_blank') {
    return (
      <div style={{ marginBottom: '1.25rem' }}>
        <label style={{ fontWeight: 600, display: 'block', marginBottom: 6 }}>{q.prompt}</label>
        <textarea
          rows={3}
          style={{ width: '100%', maxWidth: 560 }}
          value={v.text_answer || ''}
          onChange={(e) => set({ text_answer: e.target.value })}
        />
      </div>
    );
  }

  if (t === 'matching') {
    return (
      <div style={{ marginBottom: '1.25rem' }}>
        <label style={{ fontWeight: 600, display: 'block', marginBottom: 6 }}>{q.prompt}</label>
        <p className="lms-meta" style={{ fontSize: 12, margin: '0 0 6px' }}>
          Enter JSON object mapping left keys to right values, e.g. {`{"1":"a","2":"b"}`}
        </p>
        <textarea
          rows={3}
          style={{ width: '100%', maxWidth: 560, fontFamily: 'monospace', fontSize: 13 }}
          value={v.matching_json || ''}
          onChange={(e) => set({ matching_json: e.target.value })}
        />
      </div>
    );
  }

  return (
    <div style={{ marginBottom: '1.25rem' }}>
      <p style={{ fontWeight: 600 }}>{q.prompt}</p>
      <p className="lms-meta">Unsupported type: {t}</p>
    </div>
  );
}
