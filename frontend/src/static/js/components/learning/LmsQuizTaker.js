import React, { useCallback, useEffect, useState } from 'react';
import { lmsQuizAttemptSubmit, lmsQuizStart } from '../../utils/helpers/lmsApi';
import { LmsQuizQuestionInput } from './LmsQuizQuestionInput';

function buildInitialAnswers(questions) {
  const m = {};
  (questions || []).forEach((q) => {
    m[q.id] = { choice_ids: [], text_answer: '', matching_json: '{}' };
  });
  return m;
}

function toPayload(questions, answers) {
  return questions.map((q) => {
    const v = answers[q.id] || {};
    const row = { question_id: q.id };
    if (v.choice_ids && v.choice_ids.length) {
      row.choice_ids = v.choice_ids;
    }
    if (v.text_answer && v.text_answer.trim()) {
      row.text_answer = v.text_answer.trim();
    }
    if (q.type === 'matching') {
      try {
        const parsed = JSON.parse((v.matching_json || '{}').trim() || '{}');
        row.matching_answer = parsed && typeof parsed === 'object' ? parsed : {};
      } catch {
        row.matching_answer = {};
      }
    }
    return row;
  });
}

export function LmsQuizTaker({ quizId, lessonTitle }) {
  const [session, setSession] = useState(null);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [timeLeftSec, setTimeLeftSec] = useState(null);

  const load = useCallback(() => {
    setError(null);
    setSession(null);
    lmsQuizStart(quizId)
      .then((data) => {
        setSession(data);
        setAnswers(buildInitialAnswers(data.questions));
      })
      .catch((e) => setError(String(e.message || e)));
  }, [quizId]);

  useEffect(() => {
    load();
  }, [load]);

  const attempt = session && session.attempt;
  const questions = (session && session.questions) || [];
  const readOnly = attempt && attempt.status !== 'in_progress';

  useEffect(() => {
    if (!attempt || !attempt.expires_at || readOnly) {
      setTimeLeftSec(null);
      return undefined;
    }
    const tick = () => {
      const left = Math.max(0, Math.floor((new Date(attempt.expires_at).getTime() - Date.now()) / 1000));
      setTimeLeftSec(left);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [attempt, readOnly]);

  useEffect(() => {
    if (timeLeftSec !== 0 || !attempt || readOnly || busy) {
      return;
    }
    // Auto-submit when countdown reaches zero.
    lmsQuizAttemptSubmit(attempt.id, toPayload(questions, answers))
      .then(setSession)
      .catch((e) => setError(String(e.message || e)));
  }, [timeLeftSec, attempt, readOnly, busy, questions, answers]);

  const timerText = (() => {
    if (timeLeftSec == null) {
      return '';
    }
    const mm = Math.floor(timeLeftSec / 60);
    const ss = timeLeftSec % 60;
    return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`;
  })();

  const submit = (ev) => {
    ev.preventDefault();
    if (!attempt || readOnly) {
      return;
    }
    setBusy(true);
    setError(null);
    lmsQuizAttemptSubmit(attempt.id, toPayload(questions, answers))
      .then(setSession)
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setBusy(false));
  };

  if (error && !session) {
    return (
      <div className="lms-quiz-taker">
        <h1>{lessonTitle || 'Quiz'}</h1>
        <p className="error-message" style={{ whiteSpace: 'pre-line' }}>{error}</p>
        <button type="button" className="button-link" onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  if (!session) {
    return <p>Loading quiz…</p>;
  }

  return (
    <div className="lms-quiz-taker">
      <h1>{lessonTitle || 'Quiz'}</h1>
      <p className="lms-meta" style={{ fontSize: 14 }}>
        Attempt #{attempt.attempt_number} · {attempt.status}
        {attempt.expires_at ? ` · Expires ${new Date(attempt.expires_at).toLocaleString()}` : ''}
      </p>
      {timeLeftSec != null ? (
        <p style={{ fontSize: 16, fontWeight: 600, color: timeLeftSec <= 60 ? '#b71c1c' : 'inherit' }}>
          Time left: {timerText}
        </p>
      ) : null}
      {error ? <p className="error-message" style={{ whiteSpace: 'pre-line' }}>{error}</p> : null}
      <form onSubmit={submit}>
        {questions.map((q) => (
          <LmsQuizQuestionInput
            key={q.id}
            question={q}
            readOnly={readOnly}
            value={answers[q.id]}
            onChange={(nv) => setAnswers((prev) => ({ ...prev, [q.id]: nv }))}
          />
        ))}
        {!readOnly ? (
          <button type="submit" className="button-link" disabled={busy}>
            {busy ? 'Submitting…' : 'Submit quiz'}
          </button>
        ) : (
          <p style={{ fontSize: 18 }}>
            <strong>Score:</strong> {attempt.score_pct}%
          </p>
        )}
      </form>
    </div>
  );
}
