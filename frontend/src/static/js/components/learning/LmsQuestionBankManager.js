import React, { useEffect, useMemo, useState } from 'react';
import {
  lmsCreateBankQuestion,
  lmsCreateQuestionBank,
  lmsGetQuestionBank,
  lmsListQuestionBanks,
} from '../../utils/helpers/lmsApi';

const QUESTION_TYPES = [
  { value: 'mc_single', label: 'Multiple choice (single)' },
  { value: 'mc_multi', label: 'Multiple choice (multi)' },
  { value: 'true_false', label: 'True/False' },
  { value: 'short_answer', label: 'Short answer' },
];

function parseChoiceLines(lines) {
  return lines
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const isCorrect = line.startsWith('*');
      return { text: isCorrect ? line.slice(1).trim() : line, is_correct: isCorrect, order: index };
    })
    .filter((row) => row.text);
}

export function LmsQuestionBankManager() {
  const [banks, setBanks] = useState([]);
  const [selectedBankId, setSelectedBankId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);

  const [newBankTitle, setNewBankTitle] = useState('');
  const [newBankDescription, setNewBankDescription] = useState('');

  const [prompt, setPrompt] = useState('');
  const [type, setType] = useState('mcq_single');
  const [points, setPoints] = useState('1');
  const [choiceLines, setChoiceLines] = useState('* Correct answer\nDistractor 1\nDistractor 2');

  const canSubmitQuestion = useMemo(() => prompt.trim().length > 0, [prompt]);

  const loadBanks = () =>
    lmsListQuestionBanks()
      .then((res) => {
        const rows = res.question_banks || [];
        setBanks(rows);
        if (!selectedBankId && rows.length) {
          setSelectedBankId(rows[0].id);
        }
      })
      .catch((e) => setError(String(e.message || e)));

  const loadSelected = (bankId) =>
    lmsGetQuestionBank(bankId)
      .then((res) => setSelected(res))
      .catch((e) => setError(String(e.message || e)));

  useEffect(() => {
    loadBanks();
  }, []);

  useEffect(() => {
    if (selectedBankId) {
      loadSelected(selectedBankId);
    } else {
      setSelected(null);
    }
  }, [selectedBankId]);

  const createBank = (event) => {
    event.preventDefault();
    if (!newBankTitle.trim()) {
      return;
    }
    lmsCreateQuestionBank({ title: newBankTitle.trim(), description: newBankDescription.trim() })
      .then((bank) => {
        setNewBankTitle('');
        setNewBankDescription('');
        setSelectedBankId(bank.id);
        return loadBanks();
      })
      .catch((e) => setError(String(e.message || e)));
  };

  const createQuestion = (event) => {
    event.preventDefault();
    if (!selectedBankId || !canSubmitQuestion) {
      return;
    }
    const payload = {
      prompt: prompt.trim(),
      type,
      points: Number(points) || 1,
      choices: type.startsWith('mc_') || type === 'true_false' ? parseChoiceLines(choiceLines) : [],
    };
    lmsCreateBankQuestion(selectedBankId, payload)
      .then(() => {
        setPrompt('');
        if (type === 'short_answer') {
          setChoiceLines('');
        }
        return loadSelected(selectedBankId);
      })
      .catch((e) => setError(String(e.message || e)));
  };

  return (
    <section style={{ marginTop: '1.5rem' }}>
      <h2>Question banks</h2>
      {error ? <p className="error-message" style={{ whiteSpace: 'pre-line' }}>{error}</p> : null}
      <form onSubmit={createBank} style={{ display: 'grid', gap: 8, marginBottom: '1rem' }}>
        <input
          type="text"
          value={newBankTitle}
          onChange={(e) => setNewBankTitle(e.target.value)}
          placeholder="New bank title"
        />
        <textarea
          value={newBankDescription}
          onChange={(e) => setNewBankDescription(e.target.value)}
          rows={2}
          placeholder="Optional description"
        />
        <button type="submit">Create question bank</button>
      </form>

      <label>
        Select bank{' '}
        <select value={selectedBankId || ''} onChange={(e) => setSelectedBankId(Number(e.target.value) || null)}>
          <option value="">-- choose --</option>
          {banks.map((bank) => (
            <option key={bank.id} value={bank.id}>
              {bank.title}
            </option>
          ))}
        </select>
      </label>

      {selectedBankId ? (
        <form onSubmit={createQuestion} style={{ display: 'grid', gap: 8, marginTop: '1rem' }}>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Question prompt"
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <select value={type} onChange={(e) => setType(e.target.value)}>
              {QUESTION_TYPES.map((row) => (
                <option key={row.value} value={row.value}>
                  {row.label}
                </option>
              ))}
            </select>
            <input
              type="number"
              min="0"
              step="0.1"
              value={points}
              onChange={(e) => setPoints(e.target.value)}
              placeholder="Points"
            />
          </div>
          {type !== 'short_answer' ? (
            <textarea
              rows={4}
              value={choiceLines}
              onChange={(e) => setChoiceLines(e.target.value)}
              placeholder="One option per line. Prefix correct options with *"
            />
          ) : null}
          <button type="submit" disabled={!canSubmitQuestion}>
            Add question
          </button>
        </form>
      ) : null}

      {selected?.questions?.length ? (
        <ul style={{ marginTop: '1rem' }}>
          {selected.questions.map((q) => (
            <li key={q.id}>
              <strong>{q.prompt}</strong> ({q.type}, {q.points} pts)
            </li>
          ))}
        </ul>
      ) : selectedBankId ? (
        <p style={{ marginTop: '1rem' }}>No questions yet.</p>
      ) : null}
    </section>
  );
}
