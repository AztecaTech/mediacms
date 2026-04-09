import React, { useEffect, useRef } from 'react';
import Sortable from 'sortablejs';

/**
 * Renders module titles with drag handles; calls onReorder with ordered module ids after drag-end.
 */
export function AuthoringSortableModules({ modules, onReorder }) {
  const listRef = useRef(null);

  useEffect(() => {
    const el = listRef.current;
    if (!el || !modules || !modules.length) {
      return undefined;
    }
    const inst = Sortable.create(el, {
      animation: 150,
      handle: '.lms-mod-drag',
      onEnd: () => {
        const ids = [...el.querySelectorAll('[data-module-id]')].map((n) => Number(n.getAttribute('data-module-id')));
        if (ids.length && onReorder) {
          onReorder(ids);
        }
      },
    });
    return () => inst.destroy();
  }, [modules, onReorder]);

  if (!modules || !modules.length) {
    return <p className="lms-meta">No modules yet.</p>;
  }

  return (
    <ul ref={listRef} style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {modules.map((m) => (
        <li
          key={m.id}
          data-module-id={m.id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 8px',
            marginBottom: 6,
            border: '1px solid #e5e7eb',
            borderRadius: 6,
            background: '#fff',
          }}
        >
          <span className="lms-mod-drag" style={{ cursor: 'grab', userSelect: 'none' }}>
            ⣿
          </span>
          <span style={{ fontWeight: 600 }}>{m.title}</span>
          <span className="lms-meta">order {m.order}</span>
        </li>
      ))}
    </ul>
  );
}
