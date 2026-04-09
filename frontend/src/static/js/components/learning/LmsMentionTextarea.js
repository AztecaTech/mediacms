import React, { useCallback, useEffect, useRef, useState } from 'react';
import { lmsCourseMemberSearch } from '../../utils/helpers/lmsApi';

/**
 * Textarea with @username autocomplete against course roster (instructors + enrolled).
 * Parent owns `value` and `onChange` like a controlled textarea.
 */
export function LmsMentionTextarea({ slug, value, onChange, disabled, ...rest }) {
  const taRef = useRef(null);
  const [suggestions, setSuggestions] = useState([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [mentionStart, setMentionStart] = useState(null);
  const searchTimer = useRef(null);

  const runSearch = useCallback(
    (q) => {
      if (!slug || !q) {
        setSuggestions([]);
        return;
      }
      lmsCourseMemberSearch(slug, q)
        .then((r) => setSuggestions(r.results || []))
        .catch(() => setSuggestions([]));
    },
    [slug]
  );

  useEffect(() => {
    return () => {
      if (searchTimer.current) {
        clearTimeout(searchTimer.current);
      }
    };
  }, []);

  const handleChange = (e) => {
    onChange(e);
    const v = e.target.value;
    const pos = e.target.selectionStart ?? v.length;
    const before = v.slice(0, pos);
    const at = before.lastIndexOf('@');
    if (at === -1) {
      setPickerOpen(false);
      setMentionStart(null);
      setSuggestions([]);
      return;
    }
    const fragment = before.slice(at + 1);
    if (/[\s\n]/.test(fragment)) {
      setPickerOpen(false);
      setMentionStart(null);
      setSuggestions([]);
      return;
    }
    setMentionStart(at);
    setPickerOpen(true);
    if (searchTimer.current) {
      clearTimeout(searchTimer.current);
    }
    searchTimer.current = setTimeout(() => runSearch(fragment), 200);
  };

  const insertUsername = (username) => {
    if (mentionStart == null || !taRef.current) {
      return;
    }
    const v = value;
    const pos = taRef.current.selectionStart ?? v.length;
    const before = v.slice(0, mentionStart);
    const after = v.slice(pos);
    const inserted = `${before}@${username} `;
    const next = `${inserted}${after}`;
    const synthetic = { target: { value: next } };
    onChange(synthetic);
    setPickerOpen(false);
    setMentionStart(null);
    setSuggestions([]);
    requestAnimationFrame(() => {
      const el = taRef.current;
      if (!el) {
        return;
      }
      const caret = inserted.length;
      el.focus();
      el.setSelectionRange(caret, caret);
    });
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
      <textarea
        ref={taRef}
        value={value}
        onChange={handleChange}
        disabled={disabled}
        {...rest}
      />
      {pickerOpen && suggestions.length ? (
        <ul
          style={{
            position: 'absolute',
            zIndex: 20,
            left: 0,
            right: 0,
            margin: '2px 0 0',
            padding: '4px 0',
            listStyle: 'none',
            background: '#fff',
            border: '1px solid #ccc',
            borderRadius: 4,
            maxHeight: 180,
            overflowY: 'auto',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          }}
        >
          {suggestions.map((u) => (
            <li key={u.id}>
              <button
                type="button"
                onMouseDown={(ev) => ev.preventDefault()}
                onClick={() => insertUsername(u.username)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '6px 10px',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                <strong>{u.username}</strong>
                {u.name ? <span className="lms-meta"> — {u.name}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
