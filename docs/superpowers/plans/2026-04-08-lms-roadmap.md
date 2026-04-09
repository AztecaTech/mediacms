# MediaCMS → Full Academic LMS: Roadmap

**Date:** 2026-04-08
**Source plan:** `C:\Users\Ivan\.claude\plans\staged-prancing-sundae.md`
**Target:** Full academic LMS built as an additive evolution of the existing MediaCMS fork.

## Scoping decisions (locked)

- **Scope:** Full academic LMS — not a lightweight training portal.
- **SCORM / xAPI:** Not needed. All content authored inside MediaCMS.
- **Delivery modes:** Both async and scheduled cohorts (cohort = shared start + drip release, NOT live sessions).
- **Phase 1 authoring:** Django admin only. Custom authoring UI deferred to Phase 2.
- **Playlists:** Kept separate and untouched. Courses are a new parallel structure.
- **Backwards compat:** Zero breaking changes. Every phase is additive.

## Phase index

| # | Phase | Plan file | Prereqs | Unblocks |
|---|---|---|---|---|
| 1 | **Foundation** | [`2026-04-08-lms-phase-1-foundation.md`](2026-04-08-lms-phase-1-foundation.md) | None | All phases |
| 2 | **Rich content & authoring UI** | [`2026-04-08-lms-phase-2-rich-content.md`](2026-04-08-lms-phase-2-rich-content.md) | 1 | 3 |
| 3 | **Assessment (quizzes & assignments)** | [`2026-04-08-lms-phase-3-assessment.md`](2026-04-08-lms-phase-3-assessment.md) | 1, 2 | 4 |
| 4 | **Gradebook** | [`2026-04-08-lms-phase-4-gradebook.md`](2026-04-08-lms-phase-4-gradebook.md) | 1, 3 | 6 |
| 5 | **Communication** | [`2026-04-08-lms-phase-5-communication.md`](2026-04-08-lms-phase-5-communication.md) | 1 (benefits from 3/4) | 8 |
| 6 | **Credentials** | [`2026-04-08-lms-phase-6-credentials.md`](2026-04-08-lms-phase-6-credentials.md) | 1, 4 | 7 |
| 7 | **Standards & integration (LTI, LDAP, HRIS, webhooks)** | [`2026-04-08-lms-phase-7-integration.md`](2026-04-08-lms-phase-7-integration.md) | 1–6 | — |
| 8 | **Analytics** | [`2026-04-08-lms-phase-8-analytics.md`](2026-04-08-lms-phase-8-analytics.md) | 1–6 | — |

Suggested execution order: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**.
Phases 5 and 8 can parallelize against 6/7 if capacity allows, because they mostly read existing data rather than modifying earlier-phase schemas.

## What each phase adds (one-line summary)

1. **Foundation** — `learning` Django app: Course/Cohort/Module/Lesson/Enrollment/LessonProgress/CourseAuditLog, student/instructor React pages, video progress heartbeat, RBAC auto-enrollment, cohort drip release, prerequisites. Django admin for authoring.
2. **Rich content & authoring UI** — Multi-type lessons (text/file/link, plus video), per-lesson prerequisites, learning paths, custom React authoring UI (replaces Django admin dependency).
3. **Assessment** — Quiz engine (6 question types, banks, attempts, auto-grading, timers, randomization), assignment submissions with grading queue.
4. **Gradebook** — Per-course gradebook with weighted categories, rubrics, manual grading, feedback, letter grades, CSV export, student grade view.
5. **Communication** — Per-course/per-lesson discussions (MPTT), announcements with pinning, calendar, in-app + email notifications, @mentions, notification preferences.
6. **Credentials** — Certificate templates + auto-issuance with verification URLs, badges with auto-award rules, transcripts (student-facing), audit trail UI.
7. **Standards & integration** — LTI 1.3 provider + consumer, LDAP/AD sync, HRIS connectors (BambooHR/Workday), outbound webhooks, bulk CSV import/export.
8. **Analytics** — Event-driven aggregation layer, instructor dashboards (funnel, heatmap, drop-off, at-risk), org-wide dashboards, exports.

## Cross-cutting concerns

### New Django app
All LMS code lives under a new `learning/` app. Phases 1–8 each add files/models/migrations to this single app — no per-phase apps. Keeps imports and admin clean.

### Migrations
All additive. Never touch existing `files`, `users`, or `rbac` models except to add FKs from the new side. Each phase is a clean migration set that can be applied independently.

### Reuse from existing MediaCMS
| Existing | Reuse as |
|---|---|
| `files.Media` | `Lesson.media` FK (video content) |
| `files.Category` | `Course.category` FK |
| `rbac.RBACGroup` + `RBACMembership` | `Course.rbac_group` auto-enrollment source |
| `users.User` (+ `is_editor` global flag) | `Course.instructors`, `Enrollment.user`; `is_editor` gates course creation |
| `files.Comment` MPTT pattern | Copied for Phase 5 `DiscussionPost` tree |
| `cms/permissions.py` patterns | Copied for `learning/permissions.py` |
| DRF `/api/v1/` + serializer conventions | Followed throughout `learning/` |
| React SPA page + routing pattern | Followed for all new pages |
| Video player + event hooks | Phase 1 `LessonProgressTracker.js` subscribes without structural change |
| allauth (SAML, OAuth, email) | Existing auth; no changes |

### Settings flags
- `LMS_COMPLETION_THRESHOLD` (default 90) — % watched → complete
- `LMS_HEARTBEAT_INTERVAL_SECONDS` (default 10)
- `LMS_MAX_QUIZ_ATTEMPT_MINUTES` (default 180) — safety ceiling on time-limited quizzes
- `LMS_CERTIFICATE_GENERATOR` — `reportlab` | `weasyprint` (whichever is in `requirements.txt`)

### Branch strategy
One branch per phase, merged sequentially to `main`. Each phase branch cuts from the previous merged tip, never from a sibling in-progress phase.

### Current repo state impact
The `feat/external-video-embed` branch should land before Phase 1 begins — it adds `source_url`/`source_type`/`embed_html` fields on `Media` which makes external videos usable as lesson content from day one. Phase 1 does not depend on those fields (falls back to existing HLS-hosted Media), so it can proceed in parallel if needed.

## Next action

Start with **Phase 1**. Use the `writing-plans` skill against [`2026-04-08-lms-phase-1-foundation.md`](2026-04-08-lms-phase-1-foundation.md) to produce an executable implementation plan with per-task file paths and code sketches (matching the style of the existing `2026-04-02-external-video-embed.md` plan), then execute on `feat/lms-phase-1-foundation`.
