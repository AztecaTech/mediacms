# LMS Phase 5: Communication

**Status:** Planned, not started
**Branch:** `feat/lms-phase-5-communication`
**Prerequisites:** Phase 1 (Foundation); benefits from Phase 3/4 for notification triggers
**Unblocks:** Phase 8 (engagement analytics consume discussion + notification data)

## Goal

Turn a solo-study platform into an interactive one: per-course and per-lesson discussion forums (reusing the existing MPTT `Comment` tree), course-wide announcements with pinning, a calendar view of due dates and cohort milestones, in-app and email notifications, and @mentions with resolution to user profiles.

## New / extended models

### `Discussion` (`learning/models/discussion.py`)
- `course` FK, `lesson` FK (nullable; null = course-wide)
- `title`, `created_by` FK, `created_at`
- `is_pinned` (bool), `is_locked` (bool)
- `last_activity_at` (denormalized for sort)
- `reply_count` (denormalized)

### `DiscussionPost` (`learning/models/discussion.py`)
- `discussion` FK, `author` FK, `body` (TextField, markdown)
- Reuses MPTT via `django-mptt` (same pattern as existing `files.Comment`): `parent`, `lft`, `rght`, `level`, `tree_id`
- `is_instructor_answer` (bool, auto-set when author is a course instructor)
- `edited_at` (nullable)

### `Announcement` (`learning/models/announcement.py`)
- `course` FK, `author` FK
- `title`, `body` (TextField, markdown)
- `published_at`, `is_pinned` (bool)
- `send_email` (bool) — triggers notification fan-out on publish

### `Notification` (`learning/models/notification.py`)
- `recipient` FK → User
- `type`: `announcement` | `discussion_reply` | `mention` | `grade_posted` | `due_soon` | `enrollment_approved` | `course_update`
- `title`, `body`, `url` (target in app)
- `related_object_type`, `related_object_id` (generic FK pattern)
- `read_at` (nullable), `created_at`
- `email_sent` (bool)

### `NotificationPreference` (`learning/models/notification.py`)
- `user` OneToOne → User
- Per-type email toggles: `email_announcements`, `email_discussion_replies`, `email_mentions`, `email_grade_posted`, `email_due_soon`
- `digest_frequency`: `off` | `daily` | `weekly`
- Migration default: all enabled except `due_soon` weekly digest

### `CalendarEvent` (`learning/models/calendar.py`)
- `course` FK, `title`, `description`
- `event_type`: `cohort_start` | `cohort_end` | `module_release` | `assignment_due` | `quiz_due` | `live_session` | `custom`
- `starts_at`, `ends_at` (nullable)
- `source_type`, `source_id` — auto-linked to Assignment, Quiz, Cohort, Module; editable for custom
- `url` (optional; e.g., Zoom link for live sessions)

### Auto-population signals
- `Assignment.save` → upsert `CalendarEvent` with `event_type=assignment_due` if `due_at` set
- `Quiz.save` → same for quizzes
- `Cohort.save` → upsert `cohort_start` and `cohort_end` events
- `Module.save` → upsert `module_release` event if `release_offset_days > 0`

## @mention parsing

Utility in `learning/methods.py`: `parse_mentions(text)` → list of usernames → User resolution → `Notification(type=mention)` fan-out. Runs on `DiscussionPost.save` and `Announcement.save`. Frontend provides an autocomplete dropdown against enrolled users of the course.

## Email delivery

Reuse existing MediaCMS email infrastructure (check `cms/settings.py` for existing `EMAIL_*` config). A new `learning/tasks.py` background job processes the `Notification` queue — instant for high-priority (mentions, grades), batched for digests (daily/weekly cron).

## API

- `GET/POST /courses/{slug}/discussions/`
- `GET/PATCH/DELETE /discussions/{id}/`
- `POST /discussions/{id}/lock/`, `POST /discussions/{id}/unlock/` (instructor)
- `POST /discussions/{id}/pin/`, `POST /discussions/{id}/unpin/` (instructor)
- `GET/POST /discussions/{id}/posts/`
- `PATCH/DELETE /posts/{id}/`
- `GET/POST /courses/{slug}/announcements/`
- `PATCH/DELETE /announcements/{id}/`
- `GET /notifications/` — current user's unread
- `POST /notifications/{id}/read/`, `POST /notifications/read-all/`
- `GET/PATCH /me/notification-preferences/`
- `GET /courses/{slug}/calendar/` — events for a course
- `GET /my/calendar/` — events across all enrolled courses

## Frontend

- `CourseDiscussions.jsx` → `/learn/{slug}/discussions` (list + new thread button)
- `DiscussionThread.jsx` → `/learn/{slug}/discussions/{id}` (MPTT tree of posts, reply boxes, markdown)
- `LessonDiscussions.jsx` — sidebar/tab inside `CoursePlayer.jsx` for lesson-scoped discussions
- `CourseAnnouncements.jsx` → `/learn/{slug}/announcements`
- `AnnouncementAuthoring.jsx` (inside `CourseAuthoring.jsx`)
- `NotificationBell.jsx` — header component with unread count, dropdown list
- `NotificationPreferences.jsx` → `/me/settings/notifications`
- `Calendar.jsx` → `/my/calendar` (month/week/day views; click event → jumps to source)
- `MentionAutocomplete.jsx` — shared component used in post editor and announcement editor

## Verification

1. Student A posts in course-wide discussion → instructor + other enrolled students see unread notification.
2. Student B replies → A gets `discussion_reply` notification, email sent if preference on.
3. Student A types `@alice` in reply → Alice gets `mention` notification.
4. Instructor creates announcement with `send_email=true` → all enrolled students get notification + email.
5. Pin announcement → appears at top of announcement list.
6. Lock discussion → reply form disabled, existing posts visible.
7. Notification preferences: disable email announcements → Alice creates announcement → student with disabled pref has in-app notification but no email.
8. Create assignment with `due_at` → appears on student calendar and course calendar, click → jumps to assignment.
9. Digest: enable weekly digest for Bob → run digest cron → Bob gets single email with week's notifications.
10. Edit post → `edited_at` timestamp shown in UI.
11. Delete post → soft delete, shown as "[deleted]" in tree (preserves thread structure).
12. Unread count badge on `NotificationBell` updates in real-time after action (polling or WebSocket — prefer polling unless WS infra exists).

## Out of scope

- Real-time typing indicators / live updates (polling is fine)
- Direct messaging between users (this is forum-style only)
- Voice/video chat
- Reactions/emoji on posts (can add later)
- Threaded rich-media posts (markdown + images only)
- Push notifications to mobile (email-only)
