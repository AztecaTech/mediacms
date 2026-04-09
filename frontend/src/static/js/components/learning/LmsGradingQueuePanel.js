import React, { useEffect, useState } from 'react';
import { lmsGradeSubmission, lmsGradingQueue } from '../../utils/helpers/lmsApi';

export function LmsGradingQueuePanel({ courseSlug }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [score, setScore] = useState('');
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const [gradeErr, setGradeErr] = useState(null);

  const load = () => {
    if (!courseSlug) {
      return;
    }
    lmsGradingQueue(courseSlug)
      .then((d) => {
        setRows(d.submissions || []);
        setError(null);
      })
      .catch((e) => setError(String(e.message || e)));
  };

  useEffect(() => {
    load();
  }, [courseSlug]);

  const startGrade = (row) => {
    setOpenId(row.id);
    setScore(row.score != null ? String(row.score) : '');
    setFeedback(row.grader_feedback || '');
    setGradeErr(null);
  };

  const submitGrade = (submissionId) => {
    setBusy(true);
    setGradeErr(null);
    lmsGradeSubmission(submissionId, { score, grader_feedback: feedback })
      .then(() => {
        setOpenId(null);
        load();
      })
      .catch((e) => setGradeErr(String(e.message || e)))
      .finally(() => setBusy(false));
  };

  if (error) {
    return <p className="error-message">{error}</p>;
  }

  if (!rows.length) {
    return <p className="lms-meta">No submissions awaiting grades for this course (or you do not have staff access).</p>;
  }

  return (
    <div className="lms-grading-queue">
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {rows.map((r) => (
          <li
            key={r.id}
            style={{
              marginBottom: '1rem',
              padding: '0.75rem',
              border: '1px solid #ddd',
              borderRadius: 4,
            }}
          >
            <div style={{ fontSize: 14 }}>
              <strong>{r.student_display}</strong>
              <span className="lms-meta" style={{ marginLeft: 8 }}>
                {r.assignment_lesson_title} · attempt {r.attempt_number}
              </span>
            </div>
            {r.submitted_at ? (
              <div className="lms-meta" style={{ fontSize: 12 }}>
                Submitted {new Date(r.submitted_at).toLocaleString()}
              </div>
            ) : null}
            {r.text_content ? (
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, margin: '8px 0' }}>{r.text_content}</pre>
            ) : null}
            {r.url ? (
              <p style={{ fontSize: 13 }}>
                <a href={r.url} target="_blank" rel="noreferrer">
                  {r.url}
                </a>
              </p>
            ) : null}
            {r.file ? (
              <p style={{ fontSize: 13 }}>
                File:{' '}
                <a href={r.file} target="_blank" rel="noreferrer">
                  Download
                </a>
              </p>
            ) : null}
            {openId === r.id ? (
              <div style={{ marginTop: 12 }}>
                {gradeErr ? <p className="error-message">{gradeErr}</p> : null}
                <div style={{ marginBottom: 8 }}>
                  <label style={{ display: 'block', fontWeight: 600 }}>Score</label>
                  <input
                    type="text"
                    value={score}
                    onChange={(e) => setScore(e.target.value)}
                    style={{ width: 120 }}
                  />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <label style={{ display: 'block', fontWeight: 600 }}>Feedback</label>
                  <textarea rows={3} style={{ width: '100%', maxWidth: 480 }} value={feedback} onChange={(e) => setFeedback(e.target.value)} />
                </div>
                <button type="button" className="button-link" disabled={busy} onClick={() => submitGrade(r.id)}>
                  {busy ? 'Saving…' : 'Save grade'}
                </button>{' '}
                <button type="button" className="link-like" onClick={() => setOpenId(null)}>
                  Cancel
                </button>
              </div>
            ) : (
              <button type="button" className="button-link" style={{ marginTop: 8 }} onClick={() => startGrade(r)}>
                Grade
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
