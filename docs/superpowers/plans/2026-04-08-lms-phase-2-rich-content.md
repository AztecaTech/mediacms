# LMS Phase 2: Rich Content & Authoring UI

**Status:** Planned, not started
**Branch:** `feat/lms-phase-2-rich-content` (off Phase 1)
**Prerequisites:** Phase 1 (Foundation) landed
**Unblocks:** Phase 3 (quizzes need same lesson-type pattern)

## Goal

Make lessons more than just videos: markdown text, file attachments, external links, embedded external videos (reusing the existing external-video-embed feature). Add per-lesson prerequisites (not just per-course). Build a custom React authoring UI so instructors no longer need Django admin. Introduce "Learning Paths" — ordered sequences of courses.

## New / modified models

### `Lesson` (extend existing from Phase 1)
- Content-type fields already exist (`text_body`, `attachment`, `external_url`). Phase 2 activates them in API + UI.
- Add `prerequisites` M2M self → `Lesson` (within same course; validated at save)
- Add `content_version` (int) — incremented on save, used by Phase 5 notifications

### `LearningPath` (`learning/models/path.py`)
- `title`, `slug`, `description`, `thumbnail`
- `courses` M2M through `LearningPathCourse` (ordering field)
- `status`: `draft` | `published` | `archived`
- Enrollment happens at course level; path is a catalog/presentation concept

### `LearningPathCourse` (through model)
- `path` FK, `course` FK, `order` (int), `is_required` (bool)

### `LessonDraft` (`learning/models/draft.py`)
- For the authoring UI: autosave drafts before publish
- `lesson` FK (nullable for new), `author` FK, `content_snapshot` (JSONField), `updated_at`

## API

New/changed endpoints:
- `POST /lessons/` + `PATCH /lessons/{id}/` accept all content_type fields, validate that the matching field is populated
- `GET /learning-paths/`, `POST /learning-paths/`, `GET /learning-paths/{slug}/`
- `POST /lessons/{id}/drafts/`, `GET /lessons/{id}/drafts/latest/`
- `GET /courses/{slug}/authoring/` — instructor-only editing view with drafts loaded
- Lesson prerequisite gating added to `LessonListView.get_queryset()`

## Frontend

New React pages:
- `LearningPathCatalog.jsx` → `/paths`
- `LearningPathDetail.jsx` → `/paths/{slug}`
- `CourseAuthoring.jsx` → `/teach/{slug}` (instructor-only)
  - Course metadata form
  - Module list with drag-to-reorder
  - Lesson editor with content-type tabs (video picker, markdown editor, file upload, link)
  - Prerequisite graph editor (visual DAG)
  - Save draft / publish buttons
- Markdown renderer in `CoursePlayer.jsx` for text lessons
- File download widget + link opener for file/link lessons

New components:
- `MarkdownEditor.jsx` (reuse existing markdown lib if any; otherwise `react-markdown` + `react-mde`)
- `LessonTypeSelector.jsx`
- `PrerequisiteGraphEditor.jsx` (simple ordered list in v1, visual DAG optional)

## Integration with external-video-embed

If the external-video-embed feature (branch `feat/external-video-embed`) has landed by then:
- Video lessons can reference `Media` records that have `source_url`/`source_type`/`embed_html`
- `CoursePlayer.jsx` handles both HLS and iframe-embedded external videos transparently
- No new model changes required — the existing `Lesson.media` FK handles both

## Verification

1. Create text lesson with markdown → renders correctly in CoursePlayer
2. Create file lesson → student can download, completion registers on download
3. Create link lesson → student clicks link, completion registers on click
4. Create lesson with prerequisite → locked until prereq complete
5. Create Learning Path with 3 courses in order → student can enroll in each, path shows progress
6. Instructor creates course via React authoring UI (no Django admin) end-to-end
7. Autosave: type in lesson editor, close browser, reopen → draft restored
8. No regressions on Phase 1 video-lesson flow

## Out of scope

- Quizzes (Phase 3)
- Collaborative editing (single-author only in Phase 2)
- Version history / rollback (only current + latest draft)
