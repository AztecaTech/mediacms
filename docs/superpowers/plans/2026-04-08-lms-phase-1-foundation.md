# LMS Phase 1: Foundation

**Status:** Planned, not started
**Branch:** `feat/lms-phase-1-foundation` (off `main`; recommended to land after `feat/external-video-embed`)
**Prerequisites:** None (this phase is the foundation)
**Unblocks:** All other phases

## Goal

Ship the minimum viable LMS foundation: Course → Module → Lesson hierarchy, Enrollment with per-course roles, real progress tracking (resume position + % watched), cohort support with drip release, RBAC group auto-enrollment, and student/instructor React pages. Instructor authoring via Django admin only (custom UI deferred to Phase 2). Zero breaking changes to existing MediaCMS.

## New Django app: `learning`

```
learning/
├── __init__.py
├── apps.py
├── admin.py
├── models/
│   ├── __init__.py
│   ├── course.py
│   ├── cohort.py
│   ├── module.py
│   ├── lesson.py
│   ├── enrollment.py
│   ├── progress.py
│   └── audit.py
├── serializers.py
├── views.py
├── urls.py
├── permissions.py
├── signals.py       # RBAC group auto-enrollment
├── methods.py       # progress % calc, completion logic
├── tests/
└── migrations/
```

## Data model (7 new models)

### `Course` (`learning/models/course.py`)
- `title`, `slug` (unique), `description`, `thumbnail` (ImageField), `language`
- `difficulty`: `beginner` | `intermediate` | `advanced`
- `category` FK → `files.Category` (nullable)
- `mode`: `async` | `cohort`
- `enrollment_type`: `open` | `invite` | `rbac_group` | `approval`
- `rbac_group` FK → `rbac.RBACGroup` (nullable) — auto-enrolls group members via signal
- `prerequisites` M2M self → `Course` (symmetrical=False)
- `status`: `draft` | `published` | `archived`
- `instructors` M2M → `users.User`
- `estimated_hours` (int), `created_at`, `updated_at`
- Denormalized: `enrolled_count`, `avg_completion_pct`

### `Cohort` (`learning/models/cohort.py`)
- `course` FK → `Course`
- `name`, `start_date`, `end_date`, `capacity` (nullable)
- `status`: `upcoming` | `active` | `completed` | `cancelled`
- Used only when `Course.mode == 'cohort'`

### `Module` (`learning/models/module.py`)
- `course` FK, `title`, `description`, `order` (int)
- `release_offset_days` (int, default 0) — cohort drip release; ignored in async
- Unique: `(course, order)`

### `Lesson` (`learning/models/lesson.py`)
- `module` FK, `title`, `description`, `order` (int)
- `content_type`: `video` | `text` | `file` | `link` (TextChoices, extensible)
- `media` FK → `files.Media` (nullable; required if `content_type=video`)
- `text_body` (TextField, markdown), `attachment` (FileField), `external_url` (URLField)
- `is_required` (bool, default True), `estimated_minutes` (int)
- Unique: `(module, order)`

### `Enrollment` (`learning/models/enrollment.py`)
- `user` FK, `course` FK, `cohort` FK (nullable)
- `role`: `student` | `instructor` | `ta`  ← **per-course role lives here, not on User**
- `status`: `active` | `completed` | `withdrawn` | `expired`
- `enrolled_at`, `started_at` (nullable), `completed_at` (nullable)
- Denormalized: `progress_pct`, `completed_lessons_count`
- Unique: `(user, course, cohort)`

### `LessonProgress` (`learning/models/progress.py`)
- `enrollment` FK, `lesson` FK
- `status`: `not_started` | `in_progress` | `completed`
- `progress_pct` (0–100), `last_position_seconds` (int), `time_spent_seconds` (int)
- `started_at`, `completed_at`
- Unique: `(enrollment, lesson)`

### `CourseAuditLog` (`learning/models/audit.py`)
- `user` FK, `course` FK, `action` (enrolled/withdrew/completed/started/re-enrolled/role_changed)
- `metadata` (JSONField), `created_at`
- Append-only. Required foundation for Phases 4 and 6.

## API surface (DRF, `/api/v1/`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/courses/` | Catalog (filters: category, level, language, mode, status) |
| POST | `/courses/` | Create (instructor-only) |
| GET | `/courses/{slug}/` | Detail + modules + lessons with `is_locked` flag |
| PATCH | `/courses/{slug}/` | Update (instructor/owner) |
| DELETE | `/courses/{slug}/` | Soft-delete → `status=archived` |
| POST | `/courses/{slug}/enroll/` | Enroll; checks prerequisites, type, capacity |
| POST | `/courses/{slug}/withdraw/` | Withdraw |
| GET | `/courses/{slug}/roster/` | Instructor-only: student list + progress |
| GET/POST | `/courses/{slug}/modules/` | Module CRUD |
| GET/PATCH/DELETE | `/modules/{id}/` | Module detail |
| GET/POST | `/modules/{id}/lessons/` | Lesson CRUD |
| GET/PATCH/DELETE | `/lessons/{id}/` | Lesson detail |
| POST | `/lessons/{id}/progress/` | Heartbeat: `{position_seconds, duration_seconds}` |
| GET | `/enrollments/` | Current user's enrollments (student dashboard) |
| GET/POST | `/cohorts/` | Cohort list/create |
| GET/PATCH/DELETE | `/cohorts/{id}/` | Cohort detail |

### Permissions (`learning/permissions.py`)
- `IsCourseInstructorOrReadOnly` — write ops only for instructors of that course
- `IsEnrolledOrInstructor` — lesson content visible only to enrolled students or instructors
- `IsOwnerOrInstructor` — progress records visible only to owner or course instructor

Pattern: copy existing `cms/permissions.py` conventions.

## Frontend (React SPA)

New pages in `frontend/src/static/js/pages/`:
- `CoursesCatalog.jsx` → `/courses`
- `CourseDetail.jsx` → `/courses/{slug}`
- `CoursePlayer.jsx` → `/learn/{slug}` (sidebar modules/lessons, main player, next-lesson nav)
- `StudentDashboard.jsx` → `/my/learning`
- `InstructorDashboard.jsx` → `/my/teaching`

New component in `frontend/src/static/js/components/media-player/`:
- `LessonProgressTracker.js` — subscribes to player events (`timeupdate`, `pause`, `ended`), POSTs heartbeat every 10s to `/api/v1/lessons/{id}/progress/`. Activated only inside `CoursePlayer.jsx`. **No structural change** to the existing player.

## Key design decisions

1. **Course ≠ Playlist.** Playlists kept untouched. Courses are a new parallel structure.
2. **Per-course role on `Enrollment.role`**, not on `User`. Global "can create courses" reuses `User.is_editor`.
3. **Progress via heartbeat.** POST every 10s from video player. Completion threshold: `progress_pct >= 90` → `status=completed` (configurable setting `LMS_COMPLETION_THRESHOLD`).
4. **Cohort drip release.** Lesson locked if `module.release_offset_days + cohort.start_date > today`. Enforced in `LessonListView.get_queryset()`, surfaced as `is_locked` in serializer.
5. **RBAC auto-enrollment.** Django signal on `RBACMembership.save` → if any `Course.rbac_group == membership.rbac_group`, create `Enrollment(role=student)` (idempotent).
6. **Prerequisites.** Server-side check at enrollment POST. 400 response lists missing prereqs.
7. **Additive only.** No migrations touch `files.Media`, `users.User`, `rbac.*`. All new tables + new FKs from the new side.
8. **Authoring = Django admin only.** `learning/admin.py` uses inlines: `Module` inline under `Course`, `Lesson` inline under `Module`. Filters by status, mode, category.

## Critical files

### New
- Everything in `learning/` (see layout above)
- 5 React pages + 1 progress tracker component (see Frontend)

### Modified (minimal)
- `cms/settings.py` — add `'learning'` to `INSTALLED_APPS`, add `LMS_COMPLETION_THRESHOLD = 90`
- `cms/urls.py` — `path('api/v1/', include('learning.urls'))` and page routes
- `frontend/src/static/js/components/media-player/` — wire `LessonProgressTracker` to player events
- Frontend route registration (wherever page routes live in this fork)

### Reused (no changes)
- `files/models/media.py` — referenced by `Lesson.media` FK
- `files/models/category.py` — referenced by `Course.category` FK
- `rbac/models.py` — `RBACGroup` referenced; `RBACMembership.save` signal consumed
- `users/models.py` — `User` referenced
- `cms/permissions.py` — patterns copied

## Verification

End-to-end manual flow:
1. Django admin: create async course "Intro to Python" with 2 modules, 3 video lessons (using existing Media). Publish.
2. Student: navigate `/courses` → enroll → open `/learn/intro-to-python` → watch 30s → close browser → reopen → confirm resume.
3. Student: watch to 95% → `LessonProgress.status=completed`, `Enrollment.progress_pct` updates. Check `/my/learning` shows correct %.
4. Instructor: `/my/teaching` → roster shows student with progress %.
5. Cohort drip: create cohort course, module 1 `release_offset_days=0`, module 2 `release_offset_days=7`. Enroll → confirm module 2 `is_locked=true`. Patch `cohort.start_date` to 8 days ago → module 2 unlocks.
6. Prerequisites: course C requires A. Enroll in C without A → 400 listing missing prereq. Complete A → enroll in C → 201.
7. RBAC auto-enroll: course with `rbac_group=trainees`. Add user to group → `Enrollment` auto-created.
8. Withdraw: POST withdraw → status updates, progress preserved, audit log row written.
9. **No regressions:** `/api/v1/media/`, `/api/v1/playlists/`, `/api/v1/categories/` still respond. Existing React pages still render. RBAC category gating still works.

### Automated tests (`learning/tests/`)
- Model: prerequisite check, capacity enforcement, cohort drip lock, progress % calc
- API: enroll/withdraw flows, permission boundaries
- Signal: RBAC membership → auto-enrollment (idempotent)
- Heartbeat: multiple POSTs accumulate correctly, trigger completion at threshold

## Out of scope (handled in later phases)

- Quizzes, assignments, grading → Phase 3/4
- Discussions, announcements, notifications → Phase 5
- Custom React authoring UI → Phase 2
- Certificates, transcripts → Phase 6
- LTI, LDAP, HRIS → Phase 7
- Analytics dashboards → Phase 8
- Live sessions (cohort = drip release only, not Zoom)
- SCORM/xAPI (not planned at all)
