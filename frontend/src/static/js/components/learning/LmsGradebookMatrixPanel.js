import React, { useEffect, useMemo, useState } from 'react';
import {
  lmsCourseGradebook,
  lmsGetLetterScheme,
  lmsPutLetterScheme,
  lmsRecalculateGradebook,
  lmsUpsertGradebookCell,
  lmsUpsertGradebookCellsBulk,
} from '../../utils/helpers/lmsApi';

export function LmsGradebookMatrixPanel({ slug }) {
  const [data, setData] = useState(null);
  const [scheme, setScheme] = useState(null);
  const [schemeDraft, setSchemeDraft] = useState('[]');
  const [editingKey, setEditingKey] = useState(null);
  const [editingValue, setEditingValue] = useState('');
  const [editingFeedback, setEditingFeedback] = useState('');
  const [savingCell, setSavingCell] = useState(false);
  const [busyRecalc, setBusyRecalc] = useState(false);
  const [error, setError] = useState(null);
  const [focus, setFocus] = useState(null);
  const [queueMode, setQueueMode] = useState(false);
  const [stagedCells, setStagedCells] = useState([]);

  const loadGradebook = () =>
    lmsCourseGradebook(slug)
      .then(setData)
      .catch((e) => setError(String(e.message || e)));

  useEffect(() => {
    setFocus(null);
    setStagedCells([]);
    loadGradebook();
  }, [slug]);

  useEffect(() => {
    lmsGetLetterScheme(slug)
      .then((res) => {
        setScheme(res);
        setSchemeDraft(JSON.stringify(res.bands || [], null, 2));
      })
      .catch((e) => setError(String(e.message || e)));
  }, [slug]);

  const headers = useMemo(() => {
    if (!data?.categories) {
      return [];
    }
    const out = [];
    data.categories.forEach((cat) => {
      (cat.items || []).forEach((item) => {
        out.push({
          key: String(item.id),
          label: item.title,
          max: item.max_points,
          category: cat.name,
        });
      });
    });
    return out;
  }, [data]);

  const rows = data?.rows || [];
  const nRows = rows.length;
  const nCols = headers.length;

  useEffect(() => {
    if (nCols > 0 && nRows > 0 && focus === null) {
      setFocus({ row: 0, col: 0 });
    }
  }, [nCols, nRows, focus]);

  const moveFocus = (dr, dc) => {
    if (!focus || !nRows || !nCols) {
      return;
    }
    const nr = Math.max(0, Math.min(nRows - 1, focus.row + dr));
    const nc = Math.max(0, Math.min(nCols - 1, focus.col + dc));
    setFocus({ row: nr, col: nc });
  };

  const advanceAfterSave = () => {
    if (!focus || !nCols) {
      return;
    }
    if (focus.col + 1 < nCols) {
      setFocus({ row: focus.row, col: focus.col + 1 });
    } else if (focus.row + 1 < nRows) {
      setFocus({ row: focus.row + 1, col: 0 });
    }
  };

  const openEditor = (rowIndex, colIndex) => {
    const row = rows[rowIndex];
    const h = headers[colIndex];
    if (!row || !h) {
      return;
    }
    const grade = row.grades?.[h.key];
    setEditingKey(`${row.enrollment_id}:${h.key}`);
    setEditingValue(grade?.points_earned ?? '');
    setEditingFeedback(grade?.feedback ?? '');
  };

  const onMatrixKeyDown = (e) => {
    if (editingKey) {
      return;
    }
    if (!nRows || !nCols) {
      return;
    }
    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault();
        moveFocus(-1, 0);
        break;
      case 'ArrowDown':
        e.preventDefault();
        moveFocus(1, 0);
        break;
      case 'ArrowLeft':
        e.preventDefault();
        moveFocus(0, -1);
        break;
      case 'ArrowRight':
        e.preventDefault();
        moveFocus(0, 1);
        break;
      case 'Enter':
        e.preventDefault();
        if (focus) {
          openEditor(focus.row, focus.col);
        }
        break;
      default:
        break;
    }
  };

  const flushStaged = () => {
    if (!stagedCells.length) {
      return;
    }
    setSavingCell(true);
    lmsUpsertGradebookCellsBulk(slug, { cells: stagedCells })
      .then((res) => {
        if (res.errors?.length) {
          setError(
            res.errors.map((e) => (e.index != null ? `#${e.index}: ${e.detail}` : e.detail)).join('\n')
          );
          return;
        }
        setStagedCells([]);
        return loadGradebook();
      })
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setSavingCell(false));
  };

  if (error) {
    return <p className="error-message">{error}</p>;
  }
  if (!data) {
    return <p>Loading gradebook...</p>;
  }
  if (!headers.length) {
    return (
      <div>
        <p>No gradebook items yet.</p>
        <LetterGradeEditor
          scheme={scheme}
          schemeDraft={schemeDraft}
          setSchemeDraft={setSchemeDraft}
          onSaved={setScheme}
          slug={slug}
          setError={setError}
        />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
        <button
          type="button"
          disabled={busyRecalc}
          onClick={() => {
            setBusyRecalc(true);
            lmsRecalculateGradebook(slug)
              .then(() => loadGradebook())
              .catch((e) => setError(String(e.message || e)))
              .finally(() => setBusyRecalc(false));
          }}
        >
          {busyRecalc ? 'Recalculating...' : 'Recalculate totals'}
        </button>
        <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontSize: 13 }}>
          <input
            type="checkbox"
            checked={queueMode}
            onChange={(e) => setQueueMode(e.target.checked)}
          />
          Queue edits (batch save)
        </label>
        {queueMode ? (
          <button type="button" disabled={savingCell || !stagedCells.length} onClick={flushStaged}>
            {savingCell ? 'Saving…' : `Save queued (${stagedCells.length})`}
          </button>
        ) : null}
      </div>
      <p className="lms-hint" style={{ fontSize: 12, marginTop: 0 }}>
        Focus the grid (click below), then use arrow keys and Enter to edit. Tab out of the grid for page navigation.
      </p>
      <div
        role="grid"
        tabIndex={0}
        onKeyDown={onMatrixKeyDown}
        style={{ outline: 'none' }}
        className="lms-gradebook-matrix-focus"
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: 6 }}>Student</th>
                {headers.map((h) => (
                  <th key={h.key} style={{ textAlign: 'left', padding: 6, minWidth: 130 }}>
                    <div>{h.label}</div>
                    <div style={{ fontWeight: 400, opacity: 0.75 }}>
                      {h.category} (/{h.max})
                    </div>
                  </th>
                ))}
                <th style={{ textAlign: 'left', padding: 6 }}>Total</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={row.enrollment_id}>
                  <td style={{ padding: 6, borderTop: '1px solid #ddd' }}>{row.username}</td>
                  {headers.map((h, colIndex) => {
                    const grade = row.grades?.[h.key];
                    const cellKey = `${row.enrollment_id}:${h.key}`;
                    const isEditing = editingKey === cellKey;
                    const isFocused = focus && focus.row === rowIndex && focus.col === colIndex;
                    return (
                      <td
                        key={h.key}
                        style={{
                          padding: 6,
                          borderTop: '1px solid #ddd',
                          boxShadow: isFocused && !isEditing ? 'inset 0 0 0 2px #2563eb' : 'none',
                        }}
                      >
                        {isEditing ? (
                          <form
                            onSubmit={(event) => {
                              event.preventDefault();
                              const payload = {
                                enrollment_id: row.enrollment_id,
                                grade_item_id: Number(h.key),
                                points_earned: editingValue,
                                feedback: editingFeedback,
                              };
                              if (queueMode) {
                                setStagedCells((prev) => [...prev, payload]);
                                setEditingKey(null);
                                advanceAfterSave();
                                return;
                              }
                              setSavingCell(true);
                              lmsUpsertGradebookCell(slug, payload)
                                .then(() => loadGradebook())
                                .then(() => {
                                  setEditingKey(null);
                                  advanceAfterSave();
                                })
                                .catch((e) => setError(String(e.message || e)))
                                .finally(() => setSavingCell(false));
                            }}
                            style={{ display: 'flex', gap: 6 }}
                          >
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={editingValue}
                              onChange={(e) => setEditingValue(e.target.value)}
                              style={{ width: 74 }}
                              autoFocus
                            />
                            <input
                              type="text"
                              placeholder="Feedback (optional)"
                              value={editingFeedback}
                              onChange={(e) => setEditingFeedback(e.target.value)}
                              style={{ flex: 1, minWidth: 120 }}
                            />
                            <button type="submit" disabled={savingCell}>
                              {savingCell ? '...' : queueMode ? 'Queue' : 'Save'}
                            </button>
                          </form>
                        ) : (
                          <button
                            type="button"
                            className="link-like"
                            title="Edit points and feedback"
                            onClick={() => {
                              setFocus({ row: rowIndex, col: colIndex });
                              setEditingKey(cellKey);
                              setEditingValue(grade?.points_earned ?? '');
                              setEditingFeedback(grade?.feedback ?? '');
                            }}
                          >
                            {grade?.points_earned ?? '-'}
                          </button>
                        )}
                      </td>
                    );
                  })}
                  <td style={{ padding: 6, borderTop: '1px solid #ddd' }}>
                    {row.current_grade_pct ? `${row.current_grade_pct}%` : '-'} {row.current_grade_letter || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <LetterGradeEditor
        scheme={scheme}
        schemeDraft={schemeDraft}
        setSchemeDraft={setSchemeDraft}
        onSaved={setScheme}
        slug={slug}
        setError={setError}
      />
    </div>
  );
}

function LetterGradeEditor({ scheme, schemeDraft, setSchemeDraft, onSaved, slug, setError }) {
  const [saving, setSaving] = useState(false);
  const saveScheme = (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const bands = JSON.parse(schemeDraft || '[]');
      lmsPutLetterScheme(slug, { name: scheme?.name || 'Default', bands })
        .then((res) => onSaved(res))
        .catch((e) => setError(String(e.message || e)))
        .finally(() => setSaving(false));
    } catch (e) {
      setSaving(false);
      setError(`Invalid JSON: ${String(e.message || e)}`);
    }
  };

  return (
    <form onSubmit={saveScheme} style={{ marginTop: '1rem', display: 'grid', gap: 8 }}>
      <h3 style={{ margin: 0 }}>Letter grade scheme</h3>
      <textarea rows={8} value={schemeDraft} onChange={(e) => setSchemeDraft(e.target.value)} />
      <button type="submit" disabled={saving}>
        {saving ? 'Saving...' : 'Save letter bands'}
      </button>
    </form>
  );
}
