# LMS implementation status (rolling)

**Purpose:** Track what is implemented in the `learning/` app versus the eight phase specs. Update this file as features land; phase specs remain the source of truth for full scope.

**Remaining work (task-oriented):** [`2026-04-10-lms-remaining-implementation-plan.md`](2026-04-10-lms-remaining-implementation-plan.md)

**Last updated:** 2026-04-09 (gap closure: gradebook bulk, certs UI, org trends, analytics backfill)

## Summary

| Phase | Spec | Code status |
|-------|------|-------------|
| 1 Foundation | [`2026-04-08-lms-phase-1-foundation.md`](2026-04-08-lms-phase-1-foundation.md) | **Shipped:** models, DRF, admin, RBAC auto-enroll, React catalog/detail/player/dashboards, lesson progress heartbeat (HTML5 video). |
| 2 Rich content | [`2026-04-08-lms-phase-2-rich-content.md`](2026-04-08-lms-phase-2-rich-content.md) | **Shipped (MVP):** `/teach/<slug>` authoring page (`CourseAuthoringPage`), `GET …/authoring/`, module drag-reorder (`sortablejs` → `PATCH …/modules/<id>/`), markdown subset editor + player rendering (`renderLmsMarkdown.js`), prerequisite multi-select + server cycle guard (`LessonPrerequisiteCycleGuard`), debounced draft `POST …/lessons/<id>/drafts/`, path catalog `/learning-paths` + detail, file lesson `attachment_url` + “Mark complete”, link/text non-video completion via `POST …/lessons/<id>/progress/` with `{}`. |
| 3 Assessment | [`2026-04-08-lms-phase-3-assessment.md`](2026-04-08-lms-phase-3-assessment.md) | **Shipped (API + React):** quiz taker + per-question inputs, assignment submitter + grading queue tab, quiz countdown/auto-submit UX, assignment constraints UX (allowed submission types/extensions/max file size via `GET …/assignments/<id>/`), instructor question-bank authoring UI (`LmsQuestionBankManager`) with new bank/question APIs, lessons expose `quiz_id` / `assignment_id`. **Timed expiry:** Celery task `expire_overdue_quiz_attempts_task` + beat schedule every 5 minutes. **Missing:** deeper authoring polish and richer validation hints. |
| 4 Gradebook | [`2026-04-08-lms-phase-4-gradebook.md`](2026-04-08-lms-phase-4-gradebook.md) | **Shipped:** matrix inline edit + feedback (`POST …/gradebook/cells/`), **bulk** `POST …/gradebook/cells/bulk/`, React matrix **arrow-key focus + Enter**, optional **queue + batch save** (`LmsGradebookMatrixPanel`). |
| 5 Communication | [`2026-04-08-lms-phase-5-communication.md`](2026-04-08-lms-phase-5-communication.md) | **Shipped:** prior row + **calendar:** `CalendarEvent` model + signals (`learning.methods.calendar_sync`) from Assignment/Quiz/Cohort/Module, `GET …/courses/<slug>/calendar/`, `GET …/my/calendar/`, `/my/calendar` page (`MyCalendarPage`), `email_calendar` on `DiscussionNotificationPreference`. |
| 6 Credentials | [`2026-04-08-lms-phase-6-credentials.md`](2026-04-08-lms-phase-6-credentials.md) | **Shipped (API + React + backend):** as before, plus **instructor list** `GET …/courses/<slug>/certificates/` and **`/teach/<slug>/certificates`** page (`CourseCertificatesAdminPage`: list, issue, revoke, health summary). |
| 7 Integration | [`2026-04-08-lms-phase-7-integration.md`](2026-04-08-lms-phase-7-integration.md) | **Shipped:** prior row + **LTI:** course resolution from claims / resource link (`LtiCourseSlugResolver`), `LTIResourceLink` upsert on launch, browser **redirect to `/learn/<slug>`** when configured (vs JSON: `LMS_LTI_LAUNCH_JSON_RESPONSE`), optional `LMS_LTI_DEFAULT_COURSE_SLUG`. **Missing:** Deep Linking, AGS, NRPS, full LDAP attribute map, HRIS connectors. |
| 8 Analytics | [`2026-04-08-lms-phase-8-analytics.md`](2026-04-08-lms-phase-8-analytics.md) | **Shipped:** **LessonMetrics** / **StudentRiskScore** sync in Celery tasks (`LessonMetricsSyncManager`, `StudentRiskScoreSyncManager`); **funnel** active learner count; **time-in-content** from `LessonMetrics`; **at-risk** roster joined to `StudentRiskScore`; **org trends** aggregate `CourseMetricsDaily` with `?days=`; **org UI** sparkline charts (`LmsOrgTrendChartsPanel` on `/my/org/learning`); **`manage.py lms_backfill_analytics`** wires lesson-metrics sync + optional event-lesson FK + optional risk sync. **Still light / stubby:** engagement heatmap, funnel “active” depth, alerting. |

## Practical notes

- **Migrations:** Apply in order: `learning` migrations after `files` / `rbac` / users. Run `python manage.py migrate learning`.
- **Frontend:** Rebuild static bundles after adding pages in `frontend/config/mediacms.config.pages.js`.
- **Managers:** `/my/org/learning` (requires `user.is_manager`) hosts at-risk tools + LDAP source sync UI; non-managers receive 403 from Django.
- **Security:** Lesson content hiding for non-enrolled users is enforced in serializers (`hide_lesson_content`). Quiz/assignment endpoints must check enrollment separately (implemented in views). Manager CSV exports and future HRIS/LDAP credentials belong in security review before production hardening.
- **Dev settings:** `cms/dev_settings.py` defines `CELERY_BEAT_SCHEDULE = {}` so `cms.celery` can load when using docker dev settings without duplicating the full beat matrix.
- **LTI:** `LMS_LTI_LAUNCH_JSON_RESPONSE` (force JSON launch response for tools/tests), `LMS_LTI_DEFAULT_COURSE_SLUG` (fallback when claims do not resolve a course).

## API routes (`learning.urls` included at `/api/v1/`)

| Method | Path | Role |
|--------|------|------|
| POST | `quizzes/<id>/start/` | Enrolled student |
| GET | `quiz-attempts/<id>/` | Owner or instructor |
| POST | `quiz-attempts/<id>/submit/` | Owner |
| POST | `assignments/<id>/submit/` | Enrolled student |
| GET | `submissions/` | Instructor/TA (optional `?course=<slug>`) |
| PATCH | `submissions/<id>/grade/` | Instructor/TA |
| GET | `courses/<slug>/gradebook/` | Instructor |
| GET | `courses/<slug>/gradebook/export.csv` | Instructor (CSV download) |
| POST | `courses/<slug>/gradebook/recalculate/` | Instructor |
| POST | `courses/<slug>/gradebook/cells/bulk/` | Instructor (`cells: [{ enrollment_id, grade_item_id, points_earned?, feedback?, excused? }]`) |
| POST | `courses/<slug>/gradebook/cells/` | Instructor |
| GET | `courses/<slug>/certificates/` | Instructor (issued rows for course) |
| GET, PUT | `courses/<slug>/gradebook/items/<item_id>/rubric/` | Instructor/TA |
| GET | `courses/<slug>/my-grades/` | Active course member (visible items) |
| GET, POST | `submissions/<id>/rubric-scores/` | Instructor/TA |
| GET | `courses/<slug>/analytics/summary/` | Instructor |
| GET | `courses/<slug>/analytics/funnel/` | Instructor |
| GET | `courses/<slug>/analytics/engagement-heatmap/` | Instructor |
| GET | `courses/<slug>/analytics/drop-off/` | Instructor |
| GET | `courses/<slug>/analytics/time-in-content/` | Instructor |
| GET | `courses/<slug>/analytics/at-risk-students/` | Instructor |
| GET | `courses/<slug>/calendar/` | Active member (`from`, `to` ISO datetimes optional) |
| GET | `my/calendar/` | Authenticated (`from`, `to`) |
| GET | `admin/analytics/enrollment-trend/` | `user.is_manager` (`?days=` 7–730, default 180) |
| GET | `admin/analytics/completion-trend/` | `user.is_manager` (`?days=`) |
| GET | `admin/analytics/export.csv` | `user.is_manager` (course summary CSV — review before sharing externally) |
| GET | `courses/<slug>/roster/export.csv` | Instructor (CSV download) |
| POST | `courses/<slug>/roster/import/` | Instructor (multipart field `file`; UTF-8 roster CSV) |
| GET | `admin/analytics/org-summary/` | `user.is_manager` |
| GET | `admin/analytics/at-risk-enrollments/` | `user.is_manager` (`min_tier`, `limit`) |
| POST | `admin/analytics/intervention-notes/` | `user.is_manager` (`enrollment_id`, `note`) |
| GET | `admin/directory/ldap-sources/` | `user.is_manager` |
| POST | `admin/directory/ldap-sources/<id>/sync/` | `user.is_manager` (placeholder until ldap3 import) |
| GET | `verify/<code>/` | Public |
| GET | `my/certificates/` | Authenticated user |
| GET | `my/badges/` | Authenticated user |
| GET | `my/transcript/` | Authenticated user |
| GET | `lti/jwks/` | Public (configured JWK set) |
| GET, POST | `lti/login/` | Public (LTI OIDC login initiation) |
| GET | `lti/login-resume/` | Browser (after portal login) |
| POST | `lti/launch/` | Public (form_post `id_token`; JWT validated when session + `jwks_uri` configured) |
| POST | `courses/<slug>/certificates/issue/` | Instructor (`enrollment_id`) |
| GET | `courses/<slug>/certificates/health/` | Instructor |
| POST | `certificates/<id>/revoke/` | Instructor |
| GET, POST | `courses/<slug>/discussions/` | Active course member (`?lesson=<id>` filters) |
| GET, PATCH | `discussions/<id>/` | GET: member; PATCH pin/lock: staff |
| GET, POST | `discussions/<id>/posts/` | Member; nested `replies` tree on GET |
| GET, POST | `courses/<slug>/announcements/` | GET: member; POST: instructor/TA |
| GET | `notifications/` | Recipient (`?unread=true`) |
| GET, PATCH | `notifications/<id>/` | Recipient; `PATCH {"read": true}` marks read |
| GET, PATCH | `notifications/discussion-preferences/` | Recipient (`email_replies`, `email_mentions`, `frequency`) |
| GET | `courses/<slug>/members/search/` | Active course member (`q`, optional `limit`; username/name/email match) |
| GET, POST | `question-banks/` | Instructor/global editor |
| GET, PATCH | `question-banks/<id>/` | Owner or global instructor |
| POST | `question-banks/<id>/questions/` | Owner or global instructor |

## Next priorities (suggested)

1. Analytics: heatmap / event rollups, alerting, richer funnel stages.
2. LTI: Deep Linking, AGS line items, NRPS.
3. LDAP: attribute map on `LdapDirectorySource`, user upsert + RBAC group rules.
