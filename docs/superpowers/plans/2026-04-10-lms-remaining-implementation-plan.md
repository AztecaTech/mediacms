# LMS remaining implementation plan

**Created:** 2026-04-10  
**Last codebase audit:** 2026-04-10 (repo search + file review)  
**Purpose:** Single checklist of work still required for the codebase to match the eight phase specifications (`2026-04-08-lms-phase-*.md`).  
**Baseline:** [`2026-04-08-lms-implementation-status.md`](2026-04-08-lms-implementation-status.md) (update that file as items ship).

**How to use:** Pick a stream below, break into PR-sized tasks, implement, verify, then update the rolling status doc. Phase specs remain authoritative for field-level and API detail.

---

## Summary: what is already broadly in place

| Area | Shipped (high level) |
|------|----------------------|
| Phase 1 | `learning` app, courses/modules/lessons/enrollments/progress, DRF, React catalog/detail/player/dashboards, video heartbeat, RBAC auto-enroll |
| Phase 3 (core) | Quizzes, attempts, assignments, submissions, grading queue, question banks, timers/expiry task |
| Phase 4 (core) | Gradebook matrix, categories, letter bands, CSV, rubrics API, recalculation, student my-grades |
| Phase 5 (core) | Discussions, announcements, notifications, email for announcements, discussion subscriptions/digests, pin/lock |
| Phase 6 (core) | Certificates, badges, transcripts, verify, PDF generation, learner credentials page |
| Phase 7 (partial) | Webhooks + delivery/retry, LTI OIDC + launch + JWT validation, JWKS, roster CSV import/export, LDAP source **scaffold** |
| Phase 8 (partial) | `AnalyticsEvent`, `CourseMetricsDaily`, rollup task, course + org summaries, instructor analytics tab, manager at-risk list + intervention notes |

Everything below is **gap closure** relative to the phase markdown specs.

---

## Codebase audit (plan items vs current repo)

Legend: **Yes** = meets intent in code · **Partial** = backend or fragment only · **No** = not found / spec gap remains

### Stream A — Phase 2

| ID | In codebase? | Evidence / notes |
|----|----------------|------------------|
| A1 | **Partial** | `GET /api/v1/courses/<slug>/authoring/` exists (`CourseAuthoringView` in `learning/views/paths_views.py`). No dedicated React **route** like `/teach/{slug}` in `files/urls.py` or `mediacms.config.pages.js`; authoring is API-first, not a full authoring SPA. |
| A2 | **No** | No module drag-reorder UI or dedicated reorder API usage found in frontend LMS components. |
| A3 | **Partial** | `CoursePlayerPage.js` renders `text` lessons as `<pre>{lesson.text_body}</pre>` — plain text, not markdown rendering or a markdown **editor** for instructors. |
| A4 | **Partial** | `Lesson.prerequisites` M2M exists on model; player shows `prerequisite_locked`. No instructor **graph/list editor** in React for prerequisites. |
| A5 | **Partial** | `GET/POST /api/v1/learning-paths/`, `GET …/learning-paths/<slug>/` exist. **No** LMS React pages or Django routes for `/paths` / `/paths/{slug}` in `mediacms.config.pages.js` / `files/urls.py` (grep: no path catalog page). |
| A6 | **Partial** | `text` and `link` content types render in `CoursePlayerPage.js`. **No** `file` / attachment branch in that player file; completion-on-download / completion-on-link-click must align with `mark_nonvideo_lesson_complete` call sites (not wired in the visible player JSX for link). |
| A7 | **Partial** | `POST /api/v1/lessons/<pk>/drafts/` + `LessonDraft` model + authoring payload lists drafts. **No** autosave/restore UX in a dedicated authoring page. |

### Stream B — Phase 3 & 4 polish

| ID | In codebase? | Evidence / notes |
|----|----------------|------------------|
| B1 | **Partial** | Assignment constraint fields exposed via API; question-bank UI exists. No dedicated “rich validation hints” layer beyond generic errors. |
| B2 | **Partial** | `LmsGradebookMatrixPanel.js`: per-cell edit, letter scheme, recalc. **No** bulk edit, feedback modal, or keyboard-first matrix workflow in that component. |

### Stream C — Phase 5

| ID | In codebase? | Evidence / notes |
|----|----------------|------------------|
| C1 | **No** | No `CalendarEvent` model or equivalent under `learning/models/`. |
| C2 | **No** | No calendar upsert signals on Assignment/Quiz/Cohort/Module. |
| C3 | **No** | No `…/calendar/` or `…/my/calendar/` routes in `learning/urls.py`. |
| C4 | **No** | No React calendar page in LMS `mediacms.config.pages.js`. |
| C5 | **No** | No `@mention` autocomplete API or component (no `mention` / `parse_mention` in `learning/`). |
| C6 | **No** | `Notification` model supports `type` string but no mention fan-out on `DiscussionPost`/`Announcement` save found. |
| C7 | **Partial** | `DiscussionNotificationPreference` + discussion digest tasks exist. Spec’s global `NotificationPreference` per notification **type** is not implemented as a separate model. |

### Stream D — Phase 6

| ID | In codebase? | Evidence / notes |
|----|----------------|------------------|
| D1 | **No** | `LearnerCredentialsPage` serves students. **No** instructor React page for certificate **management** (list/revoke/issue beyond API) found in LMS pages config. |

### Stream E — Phase 7

| ID | In codebase? | Evidence / notes |
|----|----------------|------------------|
| E1 | **No** | No `LTIResourceLink` / `LTIUserMapping` models under `learning/models/`; only `lti_jwt.py` + `lti_launch_views.py`. |
| E2 | **Partial** | LTI launch validates JWT and returns JSON payload; **no** documented redirect into `CoursePlayer` with session handoff as primary UX. |
| E3 | **No** | No deep-linking endpoint or course picker API. |
| E4 | **No** | No AGS line items or grade push to platform. |
| E5 | **No** | No NRPS implementation. |
| E6 | **No** | No `lti` lesson content type or `LTIExternalTool` model. |
| E7 | **Partial** | `LdapDirectorySource` + admin + list/sync API + `run_placeholder_sync` — **not** real ldap3 user/RBAC sync. |
| E8 | **No** | No `HRISConnector` / `hris.py` models. |
| E9 | **Partial** | Roster CSV import/export **yes**. Spec’s broader **admin** imports/exports (courses meta, users+RBAC, grades/certs exports UI) **not** present. |

### Stream F — Phase 8

| ID | In codebase? | Evidence / notes |
|----|----------------|------------------|
| F1 | **No** | No `LessonMetrics` model. |
| F2 | **No** | No persisted `StudentRiskScore` model (heuristic scoring lives in `AtRiskScoringManager` only). |
| F3 | **Partial** | Tier logic in code; **no** nightly `recompute_risk_scores` job per spec formula/factors persistence. |
| F4 | **No** | No `refresh_lesson_metrics` task. |
| F5 | **Partial** | `GET …/courses/<slug>/analytics/summary/` **yes**. **No** `funnel`, `engagement-heatmap`, `drop-off`, course-scoped `at-risk-students`, or `time-in-content` routes. |
| F6 | **Partial** | `GET …/admin/analytics/org-summary/` **yes**. **No** `enrollment-trend`, `completion-trend`, or `export/{report_type}/` org routes. |
| F7 | **No** | No backfill management command found for historic `AnalyticsEvent` generation. |
| F8 | **Partial** | `LmsCourseAnalyticsPanel` (summary + tables) inside community hub — **not** multi-tab instructor dashboard (funnel/heatmap/drop-off/time). |
| F9 | **Partial** | `OrgManagerLearningPage` (`/my/org/learning`) covers at-risk + LDAP strip — **not** full org KPI/trend/export UI from spec. |
| F10 | **No** | No alerting subsystem. |

### Stream G — Cross-cutting

| ID | In codebase? | Evidence / notes |
|----|----------------|------------------|
| G1 | **Partial** | Tests under `learning/tests/` (`test_phase1`, `test_gradebook`, `test_roster_csv_import`, `test_at_risk_scoring`, `test_directory_api`, `test_lti_jwt`, etc.). Full-suite CI health depends on project env (`allauth`, settings). |
| G2 | **Yes** | Rolling status doc + this plan linked. |
| G3 | **Partial** | Permission checks on analytics/roster/LTI endpoints exist; no formal security review artifact in repo. |

### Quick reference — files that *do* exist for partial credit

| Area | Key locations |
|------|----------------|
| Authoring API + paths API | `learning/views/paths_views.py`, `learning/urls.py` |
| Learning paths models | `learning/models/path.py`, `learning/models/lesson_draft.py` |
| Player (text/link/video/quiz/assignment) | `frontend/src/static/js/pages/CoursePlayerPage.js` |
| Gradebook matrix | `frontend/src/static/js/components/learning/LmsGradebookMatrixPanel.js` |
| Discussions / notifications | `learning/models/communication.py`, `learning/views/communication_views.py` |
| Webhooks | `learning/models/integration.py`, `learning/methods/webhook_dispatch.py` |
| LTI launch + JWT | `learning/views/lti_launch_views.py`, `learning/methods/lti_jwt.py` |
| Roster CSV | `learning/views/roster_export_views.py`, `learning/methods/roster_csv_import.py` |
| LDAP scaffold | `learning/models/directory.py`, `learning/views/directory_views.py` |
| Analytics summary + org summary | `learning/views/lms_gradebook_analytics_views.py` |
| Course analytics UI tab | `frontend/src/static/js/components/learning/LmsCourseAnalyticsPanel.js` |
| Org at-risk + interventions | `learning/views/org_at_risk_views.py`, `learning/methods/at_risk_scoring.py`, `frontend/.../OrgManagerLearningPage.js` |

---

## Stream A — Phase 2: Rich content & authoring UI

**Spec:** [`2026-04-08-lms-phase-2-rich-content.md`](2026-04-08-lms-phase-2-rich-content.md)

| ID | Deliverable | Notes |
|----|-------------|--------|
| A1 | **Course authoring route** — React page at `/teach/{slug}` (or aligned path) replacing Django-admin-only workflows for day-to-day edits | Wire to existing `GET/PATCH …/authoring/` or equivalent APIs; match permissions to instructors |
| A2 | **Module drag-and-reorder** | Persist order via modules API; optimistic UI |
| A3 | **Markdown editor** for text lessons | Authoring + ensure player renders markdown consistently (`CoursePlayerPage`) |
| A4 | **Lesson prerequisite editor** | Within course; validate DAG / no cycles server-side |
| A5 | **Learning path catalog** | Pages: list `/paths`, detail `/paths/{slug}` per spec; enroll still at course level |
| A6 | **File/link lesson completion UX** | Spec: download registers completion, link click registers completion — confirm API + player behavior |
| A7 | **Draft autosave polish** | If drafts API exists, align UX with spec (restore after close browser) |

**Verification (from spec):** Instructor completes full course structure without Django admin; path shows progress across ordered courses; text/file/link/prereq cases pass.

---

## Stream B — Phase 3 & 4: Assessment & gradebook polish

**Specs:** [`phase-3`](2026-04-08-lms-phase-3-assessment.md), [`phase-4`](2026-04-08-lms-phase-4-gradebook.md)

| ID | Deliverable | Notes |
|----|-------------|--------|
| B1 | **Assessment authoring UX** — clearer validation messages, constraints surfaced in UI | Status doc: “richer validation hints” |
| B2 | **Gradebook UX** — bulk operations, feedback modal, keyboard-first editing | Status doc: “bulk edit, feedback modal, keyboard-heavy workflows” |

---

## Stream C — Phase 5: Calendar, mentions, preferences parity

**Spec:** [`2026-04-08-lms-phase-5-communication.md`](2026-04-08-lms-phase-5-communication.md)

| ID | Deliverable | Notes |
|----|-------------|--------|
| C1 | **`CalendarEvent` model** + migration | Types: cohort/module/assignment/quiz/custom per spec |
| C2 | **Signals** — upsert calendar rows from `Assignment`, `Quiz`, `Cohort`, `Module` (due dates, releases, cohort dates) |
| C3 | **API** — `GET /courses/{slug}/calendar/`, `GET /my/calendar/` | Aggregate across enrollments for “my” |
| C4 | **React `Calendar` UI** — month/week view; click-through to source | Route e.g. `/my/calendar` |
| C5 | **`@mention` autocomplete** — enrolled users for course | Endpoint: search enrollments by username/name |
| C6 | **Mention notifications** — `parse_mentions` on post/announcement save → `Notification` type `mention` + email per prefs | Spec utility + fan-out |
| C7 | **Notification preference parity** — align with spec’s per-type model if still divergent (`NotificationPreference` vs current discussion-focused prefs) | May be merge or extension |

**Verification (from spec):** `@user` notifies; assignment due appears on calendar; prefs suppress email but keep in-app.

---

## Stream D — Phase 6: Instructor credentials UI

**Spec:** [`2026-04-08-lms-phase-6-credentials.md`](2026-04-08-lms-phase-6-credentials.md)

| ID | Deliverable | Notes |
|----|-------------|--------|
| D1 | **Instructor certificate management screen** | List/revoke/reissue flows beyond raw API; tie to existing issue/revoke/health endpoints |

---

## Stream E — Phase 7: LTI completion, LDAP sync, HRIS, bulk admin I/O

**Spec:** [`2026-04-08-lms-phase-7-integration.md`](2026-04-08-lms-phase-7-integration.md)

| ID | Deliverable | Notes |
|----|-------------|--------|
| E1 | **LTI provider: resource link + user mapping models** (if not already aligned with spec) | `LTIResourceLink`, `LTIUserMapping` or equivalent persistence for SSO continuity |
| E2 | **Post-launch UX** — redirect/session handoff into `CoursePlayer` with authenticated user | Today: launch returns JSON; productize browser flow per spec |
| E3 | **Deep Linking** — `POST /lti/deep-linking/` + course picker | Spec subsystem 1 |
| E4 | **AGS** — line items + grade push on grade events | Spec: grades back to Canvas/Moodle |
| E5 | **NRPS** (if required by target platforms) | Named in status as missing |
| E6 | **LTI consumer** — `Lesson.content_type=lti`, `LTIExternalTool`, iframe launch | Spec subsystem 2 |
| E7 | **LDAP: real sync** | Extend `LdapDirectorySource`: ldap3 (or chosen lib), attribute map, upsert `User`, map groups → `RBACGroup` / `RBACMembership`, Celery schedule |
| E8 | **HRIS** — `HRISConnector`, `HRISRule`, scheduled pull + idempotent enroll actions | Spec subsystem 4 |
| E9 | **Bulk admin I/O** — imports/exports beyond roster | Spec: courses meta, users+RBAC, enrollments, grade/certificate exports with filters; UI under manage pattern |

**Dependencies:** E7–E9 need secrets handling review (encrypted credentials); align header name with existing webhooks if spec says `X-Learning-Signature` vs current `X-MediaCMS-Signature` (document choice).

---

## Stream F — Phase 8: Analytics parity with spec

**Spec:** [`2026-04-08-lms-phase-8-analytics.md`](2026-04-08-lms-phase-8-analytics.md)

| ID | Deliverable | Notes |
|----|-------------|--------|
| F1 | **`LessonMetrics` model** + migration | Per-lesson aggregates per spec |
| F2 | **`StudentRiskScore` model** (or merge strategy with current heuristic API) | Persist score, level, factors, `last_computed_at` |
| F3 | **`compute_risk_score` / `recompute_risk_scores` task** | Weighted formula in spec; nightly job |
| F4 | **`refresh_lesson_metrics` task** | Hourly/on-demand |
| F5 | **APIs** — `…/analytics/funnel/`, `…/engagement-heatmap/`, `…/drop-off/`, `…/at-risk-students/` (course-scoped), `…/time-in-content/` | Some overlap with existing summary; avoid duplicate semantics |
| F6 | **Org APIs** — `enrollment-trend`, `completion-trend`, `export/{report_type}/` | Extend beyond current `org-summary` |
| F7 | **Backfill management command** — historic `AnalyticsEvent` from existing tables | Spec: staging verification |
| F8 | **Instructor analytics UI** — tabs: Overview, Funnel, Heatmap, Drop-off, At-Risk, Time in content | Chart lib (`recharts` or existing stack) |
| F9 | **Org analytics UI** — `/admin/analytics` style page: KPIs, trends, top courses, exports | Managers |
| F10 | **Alerting** (if in product scope) | Not fully specified in phase 8 v1; define MVP (email/webhook on threshold) |

**Note:** Spec’s “ML-based predictive models” stay out of scope; heuristic risk is in scope.

---

## Stream G — Cross-cutting

| ID | Deliverable | Notes |
|----|-------------|--------|
| G1 | **Tests** — run full `learning` test suite in CI; add coverage for new streams | Fix env deps (`allauth`, settings) if blocking |
| G2 | **Docs** — keep [`2026-04-08-lms-implementation-status.md`](2026-04-08-lms-implementation-status.md) updated per stream | Single source for “what’s left” day to day |
| G3 | **Security review** — LDAP/HRIS/LTI secrets, CSV import authorization, analytics exports | Manager/instructor gates |

---

## Suggested implementation order

1. **C5–C6 + B1** — high user-visible value, smaller than calendar.  
2. **C1–C4** — calendar is a coherent vertical slice.  
3. **A1–A5** — authoring + paths unlock less admin dependency.  
4. **F1–F9** — analytics spec is large but mostly additive tables + APIs + UI.  
5. **E1–E6** — LTI enterprise blockers.  
6. **E7–E9** — LDAP/HRIS/bulk (ops-heavy).  
7. **D1, B2** — polish.  
8. **G1–G3** — continuous.

Parallelization: **C** and **A** can split across people; **E** and **F** touch different subsystems but both need task/ops discipline.

---

## Definition of done (for this plan)

A stream is **done** when:

1. Behavior matches the **acceptance / verification** section of the corresponding phase spec (or an explicitly documented MVP subset).  
2. APIs are listed in [`2026-04-08-lms-implementation-status.md`](2026-04-08-lms-implementation-status.md) API table if new routes were added.  
3. Migrations are backward-compatible (additive), per roadmap rules.  
4. Frontend bundles rebuilt and any new Django routes/templates wired for new pages.

---

## Explicit non-goals (per original roadmap)

- SCORM / xAPI  
- Real-time typing indicators (Phase 5 out of scope)  
- ML predictive models for risk (Phase 8 out of scope)  

If product priorities change, update the **phase spec** first, then trim this plan.
