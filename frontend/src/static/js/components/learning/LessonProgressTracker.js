import { lmsLessonProgress } from '../../utils/helpers/lmsApi';

/**
 * Sends periodic heartbeats while an HTML5 video element plays (LMS Phase 1).
 * @param {number} lessonId
 * @param {HTMLVideoElement|null} videoEl
 * @returns {function} cleanup
 */
export function attachLessonProgressTracker(lessonId, videoEl) {
  if (!lessonId || !videoEl) {
    return () => {};
  }

  const site = typeof window !== 'undefined' ? window.MediaCMS?.site : null;
  const intervalSec = site && site.lmsHeartbeatIntervalSeconds ? site.lmsHeartbeatIntervalSeconds : 10;
  let lastSent = 0;

  const send = () => {
    const d = videoEl.duration;
    if (!d || !Number.isFinite(d) || d <= 0) {
      return;
    }
    const now = Date.now();
    if (now - lastSent < intervalSec * 1000) {
      return;
    }
    lastSent = now;
    const pos = Math.floor(videoEl.currentTime || 0);
    const dur = Math.floor(d);
    lmsLessonProgress(lessonId, pos, dur).catch(() => {});
  };

  const onTime = () => send();
  const onPause = () => send();
  const onEnded = () => {
    const d = videoEl.duration;
    if (d && Number.isFinite(d)) {
      lmsLessonProgress(lessonId, Math.floor(d), Math.floor(d)).catch(() => {});
    }
  };

  videoEl.addEventListener('timeupdate', onTime);
  videoEl.addEventListener('pause', onPause);
  videoEl.addEventListener('ended', onEnded);

  return () => {
    videoEl.removeEventListener('timeupdate', onTime);
    videoEl.removeEventListener('pause', onPause);
    videoEl.removeEventListener('ended', onEnded);
  };
}
