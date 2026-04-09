import React, { useEffect, useRef, useState } from 'react';
import { CoursePlayerSidebar } from '../components/lms/CoursePlayerSidebar';
import { CourseCommunityHub } from '../components/learning/CourseCommunityHub';
import { LmsAssignmentSubmitter } from '../components/learning/LmsAssignmentSubmitter';
import { LmsNotificationsBell } from '../components/learning/LmsNotificationsBell';
import { LmsQuizTaker } from '../components/learning/LmsQuizTaker';
import { attachLessonProgressTracker } from '../components/learning/LessonProgressTracker';
import { lmsCompleteNonVideoLesson, lmsGetCourse, lmsGetJson } from '../utils/helpers/lmsApi';
import { renderLmsMarkdownToHtml } from '../utils/helpers/renderLmsMarkdown';
import { Page } from './Page';

import './CoursePlayerPage.scss';

function readSlug() {
  if (typeof window !== 'undefined' && window.MediaCMS && window.MediaCMS.lmsCourseSlug) {
    return window.MediaCMS.lmsCourseSlug;
  }
  return '';
}

function pickVideoSrc(media) {
  if (!media) {
    return null;
  }
  if (media.source_type === 'external' && media.source_url) {
    return media.source_url;
  }
  if (media.original_media_url) {
    return media.original_media_url;
  }
  return null;
}

export function CoursePlayerPage({ id = 'lms_learn' }) {
  const [slug] = useState(readSlug);
  const [course, setCourse] = useState(null);
  const [panel, setPanel] = useState('lesson');
  const [error, setError] = useState(null);
  const [lesson, setLesson] = useState(null);
  const [media, setMedia] = useState(null);
  const [mediaError, setMediaError] = useState(null);
  const [progressMsg, setProgressMsg] = useState(null);
  const videoRef = useRef(null);
  const detachRef = useRef(() => {});

  useEffect(() => {
    if (!slug) {
      setError('Missing course slug.');
      return;
    }
    lmsGetCourse(slug)
      .then(setCourse)
      .catch((e) => setError(String(e.message || e)));
  }, [slug]);

  useEffect(() => {
    detachRef.current();
    detachRef.current = () => {};
    if (!lesson || !lesson.id || lesson.content_type !== 'video') {
      return;
    }
    const el = videoRef.current;
    if (!el) {
      return;
    }
    detachRef.current = attachLessonProgressTracker(lesson.id, el);
    return () => detachRef.current();
  }, [lesson]);

  const openLesson = (les) => {
    setLesson(les);
    setProgressMsg(null);
    setMedia(null);
    setMediaError(null);
    if (les.content_type !== 'video' || !les.media || !les.media.friendly_token) {
      return;
    }
    const token = les.media.friendly_token;
    lmsGetJson(`/media/${encodeURIComponent(token)}`)
      .then(setMedia)
      .catch((e) => setMediaError(String(e.message || e)));
  };

  const videoSrc = pickVideoSrc(media);
  const activeLessonId = lesson && lesson.id != null ? lesson.id : null;

  return (
    <Page id={id}>
      <div className="lms-page lms-player">
        <CoursePlayerSidebar
          course={course}
          panel={panel}
          setPanel={setPanel}
          activeLessonId={activeLessonId}
          openLesson={openLesson}
        />
        <div className="lms-player__main">
          <div className="lms-player__main-header">
            <h2 className="lms-player__main-title">{course ? course.title : 'Learn'}</h2>
            <LmsNotificationsBell />
          </div>
          {error ? <p className="error-message">{error}</p> : null}
          {panel === 'community' && slug ? <CourseCommunityHub slug={slug} course={course} /> : null}
          {panel === 'lesson' ? (
            <>
              {!lesson ? <p className="lms-player__empty">Select a lesson from the list to get started.</p> : null}
              {lesson && (lesson.is_locked || lesson.prerequisite_locked) ? (
                <p className="error-message">This lesson is locked until prerequisites are met or the module opens.</p>
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'quiz' &&
              lesson.quiz_id ? (
                <LmsQuizTaker quizId={lesson.quiz_id} lessonTitle={lesson.title} />
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'quiz' &&
              !lesson.quiz_id ? (
                <p className="error-message">This lesson is marked as a quiz but no quiz is attached yet.</p>
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'assignment' &&
              lesson.assignment_id ? (
                <LmsAssignmentSubmitter assignmentId={lesson.assignment_id} lessonTitle={lesson.title} />
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'assignment' &&
              !lesson.assignment_id ? (
                <p className="error-message">This lesson is marked as an assignment but none is attached yet.</p>
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'video' ? (
                <>
                  <h3 className="lms-player__lesson-heading">{lesson.title}</h3>
                  {mediaError ? <p className="error-message">{mediaError}</p> : null}
                  {videoSrc ? (
                    <div className="lms-player__video-wrap">
                      <video ref={videoRef} controls src={videoSrc} />
                    </div>
                  ) : media && media.url ? (
                    <p>
                      No direct video URL in API response.{' '}
                      <a href={media.url} target="_blank" rel="noreferrer">
                        Open in media viewer
                      </a>
                    </p>
                  ) : (
                    <p>Loading media…</p>
                  )}
                </>
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'text' ? (
                <div>
                  <h3 className="lms-player__lesson-heading">{lesson.title}</h3>
                  <div
                    className="lms-markdown-body"
                    dangerouslySetInnerHTML={{ __html: renderLmsMarkdownToHtml(lesson.text_body || '') }}
                  />
                  <p style={{ marginTop: 12 }}>
                    <button
                      type="button"
                      className="button-link"
                      onClick={() => {
                        setProgressMsg(null);
                        lmsCompleteNonVideoLesson(lesson.id)
                          .then(() => setProgressMsg('Marked complete.'))
                          .catch((e) => setProgressMsg(String(e.message || e)));
                      }}
                    >
                      Mark as complete
                    </button>
                  </p>
                  {progressMsg ? <p className="lms-meta">{progressMsg}</p> : null}
                </div>
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'link' &&
              lesson.external_url ? (
                <div>
                  <h3 className="lms-player__lesson-heading">{lesson.title}</h3>
                  <a href={lesson.external_url} target="_blank" rel="noreferrer">
                    {lesson.external_url}
                  </a>
                  <p style={{ marginTop: 12 }}>
                    <button
                      type="button"
                      className="button-link"
                      onClick={() => {
                        setProgressMsg(null);
                        lmsCompleteNonVideoLesson(lesson.id)
                          .then(() => setProgressMsg('Marked complete.'))
                          .catch((e) => setProgressMsg(String(e.message || e)));
                      }}
                    >
                      Mark as complete
                    </button>
                  </p>
                  {progressMsg ? <p className="lms-meta">{progressMsg}</p> : null}
                </div>
              ) : null}
              {lesson &&
              !(lesson.is_locked || lesson.prerequisite_locked) &&
              lesson.content_type === 'file' ? (
                <div>
                  <h3 className="lms-player__lesson-heading">{lesson.title}</h3>
                  {lesson.attachment_url ? (
                    <p>
                      <a href={lesson.attachment_url} download>
                        Download file
                      </a>
                    </p>
                  ) : (
                    <p className="error-message">No file attached to this lesson.</p>
                  )}
                  <p style={{ marginTop: 12 }}>
                    <button
                      type="button"
                      className="button-link"
                      onClick={() => {
                        setProgressMsg(null);
                        lmsCompleteNonVideoLesson(lesson.id)
                          .then(() => setProgressMsg('Marked complete.'))
                          .catch((e) => setProgressMsg(String(e.message || e)));
                      }}
                    >
                      Mark as complete
                    </button>
                  </p>
                  {progressMsg ? <p className="lms-meta">{progressMsg}</p> : null}
                </div>
              ) : null}
              <p className="lms-player__footer-nav">
                <a href={`/courses/${slug}`}>← Course overview</a>
              </p>
            </>
          ) : null}
        </div>
      </div>
    </Page>
  );
}
