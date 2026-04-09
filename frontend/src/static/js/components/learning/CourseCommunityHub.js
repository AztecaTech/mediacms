import React, { useMemo, useState } from 'react';
import { LmsAnnouncementsPanel } from './LmsAnnouncementsPanel';
import { LmsDiscussionsPanel } from './LmsDiscussionsPanel';
import { LmsCourseAnalyticsPanel } from './LmsCourseAnalyticsPanel';
import { LmsGradebookMatrixPanel } from './LmsGradebookMatrixPanel';
import { LmsGradingQueuePanel } from './LmsGradingQueuePanel';
import { LmsMyGradesPanel } from './LmsMyGradesPanel';

function flattenLessons(course) {
  if (!course || !course.modules) {
    return [];
  }
  const out = [];
  course.modules.forEach((m) => {
    (m.lessons || []).forEach((l) => {
      out.push({ id: l.id, label: `${m.title}: ${l.title}` });
    });
  });
  return out;
}

export function CourseCommunityHub({ slug, course }) {
  const [tab, setTab] = useState('announcements');
  const lessons = useMemo(() => flattenLessons(course), [course]);
  const [lessonFilter, setLessonFilter] = useState('');

  const lessonId = lessonFilter ? parseInt(lessonFilter, 10) : null;

  return (
    <div className="lms-community-hub">
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: '1rem', alignItems: 'center' }}>
        {['announcements', 'discussions', 'grades', 'grading', 'gradebook', 'analytics'].map((key) => (
          <button
            key={key}
            type="button"
            className="button-link"
            style={{ fontWeight: tab === key ? 700 : 400 }}
            onClick={() => setTab(key)}
          >
            {key === 'announcements'
              ? 'Announcements'
              : key === 'discussions'
                ? 'Discussions'
                : key === 'grades'
                  ? 'My grades'
                  : key === 'grading'
                    ? 'Grade queue'
                    : key === 'gradebook'
                      ? 'Gradebook'
                      : 'Analytics'}
          </button>
        ))}
        {tab === 'discussions' && lessons.length ? (
          <label style={{ fontSize: 13, marginLeft: 'auto' }}>
            Filter by lesson{' '}
            <select value={lessonFilter} onChange={(e) => setLessonFilter(e.target.value)}>
              <option value="">All lessons</option>
              {lessons.map((l) => (
                <option key={l.id} value={String(l.id)}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      {tab === 'announcements' ? <LmsAnnouncementsPanel slug={slug} /> : null}
      {tab === 'discussions' ? <LmsDiscussionsPanel slug={slug} lessonFilter={lessonId} /> : null}
      {tab === 'grades' ? <LmsMyGradesPanel slug={slug} /> : null}
      {tab === 'grading' ? <LmsGradingQueuePanel courseSlug={slug} /> : null}
      {tab === 'gradebook' ? <LmsGradebookMatrixPanel slug={slug} /> : null}
      {tab === 'analytics' ? <LmsCourseAnalyticsPanel slug={slug} /> : null}
    </div>
  );
}
