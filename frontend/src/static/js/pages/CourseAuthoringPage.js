import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Page } from './Page';
import { AuthoringSortableModules } from '../components/learning/AuthoringSortableModules';
import {
  lmsGetAuthoring,
  lmsPatchCourse,
  lmsPatchLesson,
  lmsPatchModule,
  lmsPostLessonDraft,
} from '../utils/helpers/lmsApi';

function readSlug() {
  if (typeof window !== 'undefined' && window.MediaCMS && window.MediaCMS.lmsCourseSlug) {
    return window.MediaCMS.lmsCourseSlug;
  }
  return '';
}

function flattenLessons(course) {
  const out = [];
  (course.modules || []).forEach((m) => {
    (m.lessons || []).forEach((les) => {
      out.push({ ...les, _moduleTitle: m.title });
    });
  });
  return out;
}

export function CourseAuthoringPage({ id = 'lms_teach' }) {
  const [slug] = useState(readSlug);
  const [course, setCourse] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [error, setError] = useState(null);
  const [selectedLessonId, setSelectedLessonId] = useState(null);
  const [title, setTitle] = useState('');
  const [textBody, setTextBody] = useState('');
  const [prereqIds, setPrereqIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const [courseTitle, setCourseTitle] = useState('');
  const [courseDesc, setCourseDesc] = useState('');
  const draftTimer = useRef(null);

  const load = useCallback(() => {
    if (!slug) {
      setError('Missing course slug.');
      return;
    }
    setError(null);
    lmsGetAuthoring(slug)
      .then((payload) => {
        setCourse(payload.course);
        setDrafts(payload.drafts || []);
        setCourseTitle(payload.course.title || '');
        setCourseDesc(payload.course.description || '');
      })
      .catch((e) => setError(String(e.message || e)));
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const flatLessons = useMemo(() => (course ? flattenLessons(course) : []), [course]);
  const selected = useMemo(
    () => flatLessons.find((l) => l.id === selectedLessonId) || null,
    [flatLessons, selectedLessonId]
  );

  useEffect(() => {
    if (!selected) {
      setTitle('');
      setTextBody('');
      setPrereqIds([]);
      return;
    }
    setTitle(selected.title || '');
    setTextBody(selected.text_body || '');
    setPrereqIds(Array.isArray(selected.prerequisite_ids) ? selected.prerequisite_ids : []);
  }, [selected]);

  useEffect(() => {
    return () => {
      if (draftTimer.current) {
        clearTimeout(draftTimer.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!selectedLessonId || !slug) {
      return;
    }
    if (draftTimer.current) {
      clearTimeout(draftTimer.current);
    }
    draftTimer.current = setTimeout(() => {
      lmsPostLessonDraft(selectedLessonId, { title, text_body: textBody }).catch(() => null);
    }, 1200);
  }, [selectedLessonId, title, textBody, slug]);

  const onReorderModules = async (orderedIds) => {
    if (!orderedIds.length) {
      return;
    }
    setError(null);
    try {
      const updates = orderedIds.map((mid, idx) => lmsPatchModule(mid, { order: idx }));
      await Promise.all(updates);
      load();
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const saveLesson = (ev) => {
    ev.preventDefault();
    if (!selectedLessonId) {
      return;
    }
    setSaving(true);
    setError(null);
    lmsPatchLesson(selectedLessonId, {
      title: title.trim(),
      text_body: textBody,
      prerequisites: prereqIds,
    })
      .then(() => load())
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setSaving(false));
  };

  const saveCourseMeta = (ev) => {
    ev.preventDefault();
    if (!slug) {
      return;
    }
    setSaving(true);
    setError(null);
    lmsPatchCourse(slug, { title: courseTitle.trim(), description: courseDesc })
      .then(() => load())
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setSaving(false));
  };

  const modulesSorted = useMemo(() => {
    if (!course || !course.modules) {
      return [];
    }
    return [...course.modules].sort((a, b) => (a.order || 0) - (b.order || 0));
  }, [course]);

  return (
    <Page id={id}>
      <div className="lms-page lms-authoring" style={{ maxWidth: 960, margin: '0 auto' }}>
        <h1 className="page-title">Edit course</h1>
        {slug ? (
          <p className="lms-meta">
            Slug: {slug} · <a href={`/learn/${slug}`}>Preview player</a> ·{' '}
            <a href={`/teach/${slug}/certificates`}>Certificates</a>
          </p>
        ) : null}
        {error ? <p className="error-message" style={{ whiteSpace: 'pre-line' }}>{error}</p> : null}

        <section style={{ marginBottom: '1.5rem' }}>
          <h2>Course details</h2>
          <form onSubmit={saveCourseMeta} style={{ display: 'grid', gap: 8 }}>
            <label>
              Title
              <input
                type="text"
                value={courseTitle}
                onChange={(e) => setCourseTitle(e.target.value)}
                style={{ width: '100%', maxWidth: 480 }}
              />
            </label>
            <label>
              Description
              <textarea
                value={courseDesc}
                onChange={(e) => setCourseDesc(e.target.value)}
                rows={3}
                style={{ width: '100%', maxWidth: 560 }}
              />
            </label>
            <button type="submit" className="button-link" disabled={saving}>
              Save course
            </button>
          </form>
        </section>

        <section style={{ marginBottom: '1.5rem' }}>
          <h2>Module order</h2>
          <p className="lms-meta" style={{ fontSize: 13 }}>
            Drag to reorder; saves new order indices to the server.
          </p>
          <AuthoringSortableModules modules={modulesSorted} onReorder={onReorderModules} />
        </section>

        <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div>
            <h2>Lessons</h2>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {flatLessons.map((les) => (
                <li key={les.id} style={{ marginBottom: 6 }}>
                  <button
                    type="button"
                    className="link-like"
                    style={{ fontWeight: selectedLessonId === les.id ? 700 : 400 }}
                    onClick={() => setSelectedLessonId(les.id)}
                  >
                    {les._moduleTitle}: {les.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2>Lesson editor</h2>
            {!selected ? <p className="lms-meta">Select a lesson.</p> : null}
            {selected ? (
              <form onSubmit={saveLesson} style={{ display: 'grid', gap: 8 }}>
                <label>
                  Title
                  <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: '100%' }} />
                </label>
                <label>
                  Text body (markdown: **bold**, *italic*, `code`, blank line = paragraph)
                  <textarea
                    value={textBody}
                    onChange={(e) => setTextBody(e.target.value)}
                    rows={12}
                    style={{ width: '100%', fontFamily: 'monospace', fontSize: 13 }}
                  />
                </label>
                <label>
                  Prerequisites (same course)
                  <select
                    multiple
                    value={prereqIds.map(String)}
                    onChange={(e) => {
                      const opts = [...e.target.selectedOptions].map((o) => Number(o.value));
                      setPrereqIds(opts);
                    }}
                    style={{ width: '100%', minHeight: 120 }}
                  >
                    {flatLessons
                      .filter((l) => l.id !== selected.id)
                      .map((l) => (
                        <option key={l.id} value={l.id}>
                          {l._moduleTitle}: {l.title}
                        </option>
                      ))}
                  </select>
                </label>
                <button type="submit" className="button-link" disabled={saving}>
                  {saving ? 'Saving…' : 'Save lesson'}
                </button>
                <p className="lms-meta" style={{ fontSize: 12 }}>
                  Draft autosave to server runs while you type (debounced). Recent drafts: {drafts.length}.
                </p>
              </form>
            ) : null}
          </div>
        </section>
      </div>
    </Page>
  );
}
