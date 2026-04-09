import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AuthoringSortableModules } from '../components/learning/AuthoringSortableModules';
import {
  lmsGetAuthoring,
  lmsPatchCourse,
  lmsPatchLesson,
  lmsPatchModule,
  lmsPostLessonDraft,
} from '../utils/helpers/lmsApi';
import { Page } from './Page';

import './CourseAuthoringPage.scss';

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
      <div className="lms-page lms-authoring lms-shell lms-shell--wide">
        <nav className="lms-breadcrumb" aria-label="Breadcrumb">
          <a href="/my/teaching">My teaching</a>
          {' / '}
          <span>Edit course</span>
        </nav>
        <h1 className="page-title">Edit course</h1>
        {slug ? (
          <p className="lms-intro">
            Update how this course appears to learners, reorder modules, and edit lesson text. Slug:{' '}
            <code>{slug}</code>
          </p>
        ) : null}
        {slug ? (
          <div className="lms-btn-row" style={{ marginTop: 0 }}>
            <a className="lms-btn lms-btn--secondary lms-btn--sm" href={`/learn/${encodeURIComponent(slug)}`}>
              Preview as learner
            </a>
            <a className="lms-btn lms-btn--secondary lms-btn--sm" href={`/teach/${encodeURIComponent(slug)}/certificates`}>
              Certificates
            </a>
            <a className="lms-btn lms-btn--secondary lms-btn--sm" href={`/courses/${encodeURIComponent(slug)}`}>
              Public overview
            </a>
          </div>
        ) : null}
        {error ? (
          <p className="error-message" style={{ whiteSpace: 'pre-line' }}>
            Something went wrong while saving or loading. {error}
          </p>
        ) : null}

        <section className="lms-section" aria-labelledby="lms-author-course-meta">
          <h2 id="lms-author-course-meta" className="lms-section__title">
            Course details
          </h2>
          <p className="lms-help-text" style={{ marginBottom: '0.75rem' }}>
            Title and description show on the catalog and course overview page.
          </p>
          <form className="lms-form-stack" onSubmit={saveCourseMeta}>
            <label>
              Title
              <input
                className="lms-input"
                type="text"
                value={courseTitle}
                onChange={(e) => setCourseTitle(e.target.value)}
              />
            </label>
            <label>
              Description
              <textarea
                className="lms-textarea lms-textarea--grow"
                value={courseDesc}
                onChange={(e) => setCourseDesc(e.target.value)}
                rows={4}
              />
            </label>
            <button type="submit" className="lms-btn lms-btn--primary lms-btn--sm" disabled={saving}>
              {saving ? 'Saving…' : 'Save course details'}
            </button>
          </form>
        </section>

        <section className="lms-section" aria-labelledby="lms-author-modules">
          <h2 id="lms-author-modules" className="lms-section__title">
            Module order
          </h2>
          <p className="lms-help-text" style={{ marginBottom: '0.75rem' }}>
            Drag modules to change the order learners see. Changes save immediately.
          </p>
          <AuthoringSortableModules modules={modulesSorted} onReorder={onReorderModules} />
        </section>

        <section className="lms-section" aria-labelledby="lms-author-lessons">
          <h2 id="lms-author-lessons" className="lms-section__title">
            Lessons
          </h2>
          <p className="lms-help-text" style={{ marginBottom: '0.85rem' }}>
            Pick a lesson on the left, then edit its title, text (markdown), and prerequisites.
          </p>
          <div className="lms-authoring-grid">
            <div>
              <h3 className="lms-section__title" style={{ fontSize: '0.95rem' }}>
                All lessons
              </h3>
              {flatLessons.length ? (
                <ul className="lms-lesson-picker">
                  {flatLessons.map((les) => (
                    <li key={les.id}>
                      <button
                        type="button"
                        className={
                          'lms-lesson-picker__btn' + (selectedLessonId === les.id ? ' is-active' : '')
                        }
                        onClick={() => setSelectedLessonId(les.id)}
                      >
                        <span className="lms-meta" style={{ display: 'block', fontSize: '0.78rem' }}>
                          {les._moduleTitle}
                        </span>
                        {les.title}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="lms-empty-hint">No lessons yet. Add modules and lessons in Django admin if needed.</p>
              )}
            </div>
            <div>
              <h3 className="lms-section__title" style={{ fontSize: '0.95rem' }}>
                Lesson editor
              </h3>
              {!selected ? (
                <p className="lms-empty-hint">Select a lesson from the list to edit its content.</p>
              ) : null}
              {selected ? (
                <form className="lms-form-stack" onSubmit={saveLesson}>
                  <label>
                    Title
                    <input className="lms-input" type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
                  </label>
                  <label>
                    Text body (markdown: **bold**, *italic*, `code`; blank line = new paragraph)
                    <textarea
                      className="lms-textarea lms-textarea--code"
                      value={textBody}
                      onChange={(e) => setTextBody(e.target.value)}
                      rows={14}
                    />
                  </label>
                  <label>
                    Prerequisites (same course)
                    <select
                      className="lms-input lms-prereq-multi"
                      multiple
                      value={prereqIds.map(String)}
                      onChange={(e) => {
                        const opts = [...e.target.selectedOptions].map((o) => Number(o.value));
                        setPrereqIds(opts);
                      }}
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
                  <button type="submit" className="lms-btn lms-btn--primary lms-btn--sm" disabled={saving}>
                    {saving ? 'Saving…' : 'Save lesson'}
                  </button>
                  <p className="lms-help-text">
                    Drafts auto-save while you type (short delay). Server drafts stored: {drafts.length}.
                  </p>
                </form>
              ) : null}
            </div>
          </div>
        </section>

        <nav className="lms-footer-links" aria-label="Related pages">
          <a href="/my/teaching">My teaching</a>
          {' · '}
          <a href="/courses">Course catalog</a>
        </nav>
      </div>
    </Page>
  );
}
