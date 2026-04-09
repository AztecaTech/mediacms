import React from 'react';
import PropTypes from 'prop-types';

export function CoursePlayerSidebar({ course, panel, setPanel, activeLessonId, openLesson }) {
  return (
    <nav className="lms-player__sidebar" aria-label="Course navigation">
      <h2 className="lms-player__sidebar-title">Course</h2>
      <div className="lms-player__panel-tabs" role="tablist" aria-label="Player section">
        <button
          type="button"
          role="tab"
          aria-selected={panel === 'lesson'}
          className={'lms-player__tab' + (panel === 'lesson' ? ' is-active' : '')}
          onClick={() => setPanel('lesson')}
        >
          Lessons
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={panel === 'community'}
          className={'lms-player__tab' + (panel === 'community' ? ' is-active' : '')}
          onClick={() => setPanel('community')}
        >
          Community & grades
        </button>
      </div>
      {course && course.modules
        ? course.modules.map((m) => (
            <div key={m.id} className="lms-player__module">
              <div className="lms-player__module-title">{m.title}</div>
              <ul className="lms-player__lesson-list">
                {(m.lessons || []).map((les) => {
                  const locked = les.is_locked || les.prerequisite_locked;
                  const active = activeLessonId != null && les.id === activeLessonId;
                  return (
                    <li key={les.id}>
                      <button
                        type="button"
                        className={'lms-player__lesson-btn' + (active ? ' is-active' : '')}
                        onClick={() => {
                          setPanel('lesson');
                          openLesson(les);
                        }}
                      >
                        <span className="lms-player__lesson-title">{les.title}</span>
                        {locked ? <span className="lms-player__lesson-lock">Locked</span> : null}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))
        : null}
    </nav>
  );
}

CoursePlayerSidebar.propTypes = {
  course: PropTypes.object,
  panel: PropTypes.oneOf(['lesson', 'community']).isRequired,
  setPanel: PropTypes.func.isRequired,
  activeLessonId: PropTypes.number,
  openLesson: PropTypes.func.isRequired,
};
