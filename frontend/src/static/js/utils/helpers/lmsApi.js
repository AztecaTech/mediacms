import { csrfToken } from './csrfToken';

const LMS_PREFIX = '/api/v1';

/** Flatten DRF / Django REST validation payloads into readable lines (field: message). */
function formatFieldErrors(prefix, value) {
  if (value == null || value === '') {
    return [];
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return [`${prefix}: ${value}`];
  }
  if (Array.isArray(value)) {
    if (!value.length) {
      return [];
    }
    if (value.every((x) => typeof x === 'string' || typeof x === 'number')) {
      return [`${prefix}: ${value.join('; ')}`];
    }
    return value.flatMap((item, i) => formatFieldErrors(`${prefix}[${i}]`, item));
  }
  if (typeof value === 'object') {
    return Object.entries(value).flatMap(([k, v]) =>
      formatFieldErrors(prefix ? `${prefix}.${k}` : k, v)
    );
  }
  return [`${prefix}: ${String(value)}`];
}

export function formatLmsValidationResponse(j) {
  if (j == null || typeof j !== 'object') {
    return String(j);
  }
  if (typeof j.detail === 'string') {
    return j.detail;
  }
  if (Array.isArray(j.detail)) {
    return j.detail
      .map((d) => {
        if (d && typeof d === 'object' && !Array.isArray(d)) {
          return formatLmsValidationResponse({ ...d });
        }
        return String(d);
      })
      .filter(Boolean)
      .join('\n');
  }
  const lines = [];
  if (j.detail != null && typeof j.detail === 'object' && !Array.isArray(j.detail)) {
    lines.push(...formatFieldErrors('detail', j.detail));
  }
  Object.keys(j)
    .filter((k) => k !== 'detail')
    .forEach((k) => {
      lines.push(...formatFieldErrors(k, j[k]));
    });
  const out = lines.filter(Boolean).join('\n');
  return out || JSON.stringify(j);
}

async function parseError(res) {
  try {
    const j = await res.json();
    return formatLmsValidationResponse(j);
  } catch {
    return res.statusText;
  }
}

export async function lmsGetJson(path) {
  const res = await fetch(`${LMS_PREFIX}${path}`, { credentials: 'same-origin' });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function lmsPostJson(path, body = {}) {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  const tok = csrfToken();
  if (tok) {
    headers['X-CSRFToken'] = tok;
  }
  const res = await fetch(`${LMS_PREFIX}${path}`, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = new Error(await parseError(res));
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function lmsPatchJson(path, body = {}) {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  const tok = csrfToken();
  if (tok) {
    headers['X-CSRFToken'] = tok;
  }
  const res = await fetch(`${LMS_PREFIX}${path}`, {
    method: 'PATCH',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function lmsPutJson(path, body = {}) {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  const tok = csrfToken();
  if (tok) {
    headers['X-CSRFToken'] = tok;
  }
  const res = await fetch(`${LMS_PREFIX}${path}`, {
    method: 'PUT',
    credentials: 'same-origin',
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export function lmsListCourses() {
  return lmsGetJson('/courses/');
}

export function lmsGetCourse(slug) {
  return lmsGetJson(`/courses/${encodeURIComponent(slug)}/`);
}

export function lmsEnroll(slug, cohortId) {
  return lmsPostJson(`/courses/${encodeURIComponent(slug)}/enroll/`, {
    cohort_id: cohortId || null,
  });
}

export function lmsMyEnrollments() {
  return lmsGetJson('/enrollments/');
}

export function lmsCourseRoster(slug) {
  return lmsGetJson(`/courses/${encodeURIComponent(slug)}/roster/`);
}

export async function lmsCourseRosterImport(slug, file) {
  const fd = new FormData();
  fd.append('file', file);
  const headers = { Accept: 'application/json' };
  const tok = csrfToken();
  if (tok) {
    headers['X-CSRFToken'] = tok;
  }
  const res = await fetch(
    `${LMS_PREFIX}/courses/${encodeURIComponent(slug)}/roster/import/`,
    {
      method: 'POST',
      credentials: 'same-origin',
      headers,
      body: fd,
    }
  );
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export function lmsLessonProgress(lessonId, positionSeconds, durationSeconds) {
  return lmsPostJson(`/lessons/${lessonId}/progress/`, {
    position_seconds: positionSeconds,
    duration_seconds: durationSeconds,
  });
}

/** Mark text/file/link (non-video) lesson complete for the current user. */
export function lmsCompleteNonVideoLesson(lessonId) {
  return lmsPostJson(`/lessons/${lessonId}/progress/`, {});
}

export function lmsGetAuthoring(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/authoring/`);
}

export function lmsPatchCourse(slug, body) {
  return lmsPatchJson(`/courses/${encSlug(slug)}/`, body);
}

export function lmsPatchModule(moduleId, body) {
  return lmsPatchJson(`/modules/${moduleId}/`, body);
}

export function lmsPatchLesson(lessonId, body) {
  return lmsPatchJson(`/lessons/${lessonId}/`, body);
}

export function lmsPostLessonDraft(lessonId, contentSnapshot) {
  return lmsPostJson(`/lessons/${lessonId}/drafts/`, {
    content_snapshot: contentSnapshot,
  });
}

export function lmsLearningPaths() {
  return lmsGetJson('/learning-paths/');
}

export function lmsLearningPathDetail(slug) {
  return lmsGetJson(`/learning-paths/${encSlug(slug)}/`);
}

function encSlug(slug) {
  return encodeURIComponent(slug);
}

export function lmsListDiscussions(slug, lessonId) {
  const q = lessonId ? `?lesson=${encodeURIComponent(String(lessonId))}` : '';
  return lmsGetJson(`/courses/${encSlug(slug)}/discussions/${q}`);
}

/** @param {string} slug course slug
 * @param {string} q search fragment (after @)
 * @param {number} [limit]
 */
export function lmsCourseMemberSearch(slug, q, limit = 15) {
  const params = new URLSearchParams();
  if (q) {
    params.set('q', q);
  }
  if (limit) {
    params.set('limit', String(limit));
  }
  const qs = params.toString();
  return lmsGetJson(`/courses/${encSlug(slug)}/members/search/${qs ? `?${qs}` : ''}`);
}

export function lmsCourseCalendar(slug, params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== '') {
      q.set(k, String(v));
    }
  });
  const qs = q.toString();
  return lmsGetJson(`/courses/${encSlug(slug)}/calendar/${qs ? `?${qs}` : ''}`);
}

export function lmsMyCalendar(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v != null && v !== '') {
      q.set(k, String(v));
    }
  });
  const qs = q.toString();
  return lmsGetJson(`/my/calendar/${qs ? `?${qs}` : ''}`);
}

export function lmsCreateDiscussion(slug, payload) {
  return lmsPostJson(`/courses/${encSlug(slug)}/discussions/`, payload);
}

export function lmsPatchDiscussion(discussionId, payload) {
  return lmsPatchJson(`/discussions/${discussionId}/`, payload);
}

export function lmsGetDiscussionNotificationPreferences() {
  return lmsGetJson('/notifications/discussion-preferences/');
}

export function lmsPatchDiscussionNotificationPreferences(payload) {
  return lmsPatchJson('/notifications/discussion-preferences/', payload);
}

export function lmsListDiscussionPosts(discussionId) {
  return lmsGetJson(`/discussions/${discussionId}/posts/`);
}

export function lmsCreateDiscussionPost(discussionId, payload) {
  return lmsPostJson(`/discussions/${discussionId}/posts/`, payload);
}

export function lmsListAnnouncements(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/announcements/`);
}

export function lmsCreateAnnouncement(slug, payload) {
  return lmsPostJson(`/courses/${encSlug(slug)}/announcements/`, payload);
}

export function lmsListNotifications(options = {}) {
  const q = options.unread ? '?unread=true' : '';
  return lmsGetJson(`/notifications/${q}`);
}

export function lmsMarkNotificationRead(notificationId) {
  return lmsPatchJson(`/notifications/${notificationId}/`, { read: true });
}

export function lmsMyGrades(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/my-grades/`);
}

export function lmsCourseGradebook(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/gradebook/`);
}

export function lmsGetLetterScheme(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/gradebook/letter-scheme/`);
}

export function lmsPutLetterScheme(slug, payload) {
  return lmsPutJson(`/courses/${encSlug(slug)}/gradebook/letter-scheme/`, payload);
}

export function lmsUpsertGradebookCellsBulk(slug, body) {
  return lmsPostJson(`/courses/${encSlug(slug)}/gradebook/cells/bulk/`, body);
}

export async function lmsUpsertGradebookCell(slug, payload) {
  const res = await lmsUpsertGradebookCellsBulk(slug, { cells: [payload] });
  if (res.errors?.length) {
    throw new Error(res.errors.map((e) => e.detail).join('; ') || 'Could not save grade.');
  }
  if (!res.results?.length) {
    throw new Error('Could not save grade.');
  }
  return res.results[0];
}

export function lmsRecalculateGradebook(slug) {
  return lmsPostJson(`/courses/${encSlug(slug)}/gradebook/recalculate/`, {});
}

export function lmsCourseAnalyticsSummary(slug, days = 30) {
  const q = new URLSearchParams({ days: String(days) }).toString();
  return lmsGetJson(`/courses/${encSlug(slug)}/analytics/summary/?${q}`);
}

export function lmsCourseAnalyticsFunnel(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/analytics/funnel/`);
}

export function lmsCourseAnalyticsDropOff(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/analytics/drop-off/`);
}

export function lmsCourseAnalyticsHeatmap(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/analytics/engagement-heatmap/`);
}

export function lmsCourseAnalyticsTimeInContent(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/analytics/time-in-content/`);
}

export function lmsOrgEnrollmentTrend(options = {}) {
  const q = new URLSearchParams();
  if (options.days != null) {
    q.set('days', String(options.days));
  }
  const qs = q.toString();
  return lmsGetJson(`/admin/analytics/enrollment-trend${qs ? `?${qs}` : ''}`);
}

export function lmsOrgCompletionTrend(options = {}) {
  const q = new URLSearchParams();
  if (options.days != null) {
    q.set('days', String(options.days));
  }
  const qs = q.toString();
  return lmsGetJson(`/admin/analytics/completion-trend${qs ? `?${qs}` : ''}`);
}

export function lmsCertificateHealth(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/certificates/health/`);
}

export function lmsCourseCertificatesList(slug) {
  return lmsGetJson(`/courses/${encSlug(slug)}/certificates/`);
}

export function lmsIssueCourseCertificate(slug, enrollmentId) {
  return lmsPostJson(`/courses/${encSlug(slug)}/certificates/issue/`, {
    enrollment_id: enrollmentId,
  });
}

export function lmsRevokeCertificate(certificateId, reason = '') {
  return lmsPostJson(`/certificates/${certificateId}/revoke/`, { reason });
}

export function lmsMyCertificates() {
  return lmsGetJson('/my/certificates/');
}

export function lmsMyBadges() {
  return lmsGetJson('/my/badges/');
}

export function lmsMyTranscript() {
  return lmsGetJson('/my/transcript/');
}

export function lmsQuizStart(quizId) {
  return lmsPostJson(`/quizzes/${quizId}/start/`, {});
}

export function lmsQuizAttemptSubmit(attemptId, answers) {
  return lmsPostJson(`/quiz-attempts/${attemptId}/submit/`, { answers });
}

export async function lmsAssignmentSubmitMultipart(assignmentId, formData) {
  const headers = {};
  const tok = csrfToken();
  if (tok) {
    headers['X-CSRFToken'] = tok;
  }
  const res = await fetch(`${LMS_PREFIX}/assignments/${assignmentId}/submit/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers,
    body: formData,
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export function lmsGetAssignment(assignmentId) {
  return lmsGetJson(`/assignments/${assignmentId}/`);
}

export function lmsGradingQueue(courseSlug) {
  const q = courseSlug ? `?course=${encodeURIComponent(courseSlug)}` : '';
  return lmsGetJson(`/submissions${q}`);
}

export function lmsGradeSubmission(submissionId, payload) {
  return lmsPatchJson(`/submissions/${submissionId}/grade/`, payload);
}

export function lmsListQuestionBanks() {
  return lmsGetJson('/question-banks/');
}

export function lmsCreateQuestionBank(payload) {
  return lmsPostJson('/question-banks/', payload);
}

export function lmsGetQuestionBank(bankId) {
  return lmsGetJson(`/question-banks/${bankId}/`);
}

export function lmsCreateBankQuestion(bankId, payload) {
  return lmsPostJson(`/question-banks/${bankId}/questions/`, payload);
}
