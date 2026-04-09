# LMS Phase 8: Analytics

**Status:** Planned, not started
**Branch:** `feat/lms-phase-8-analytics`
**Prerequisites:** Phases 1–6 (analytics consume all the event data)
**Unblocks:** — (terminal phase)

## Goal

Transform raw LMS data into decision-useful insights: instructor dashboards with engagement heatmaps and completion funnels, an at-risk student detector, admin/org dashboards with completion trends and enrollment velocity, per-lesson drop-off analysis, and time-in-content reports. This phase does not add new learning features — it surfaces what the earlier phases already record.

## Architecture: event-driven aggregation

Rather than aggregating on every query (slow at scale), Phase 8 introduces a lightweight analytics layer: **events emitted by Phases 1–6 → periodic aggregation into denormalized fact tables → fast dashboard queries**.

### Event emission (retroactively added to earlier-phase code paths)

A new `learning/events.py::emit_event(type, user, course, metadata)` helper writes to a single `AnalyticsEvent` table. Call sites:
- Phase 1: lesson view, lesson completion, enrollment, withdrawal
- Phase 3: quiz start, quiz submit, assignment submit
- Phase 4: grade posted
- Phase 5: discussion post, announcement read
- Phase 6: certificate issued

Backfill script: walk existing `Enrollment`, `LessonProgress`, `QuizAttempt`, `Submission`, `Grade`, `CourseAuditLog` and generate historic events so dashboards show history from day one of this phase.

## New models

### `AnalyticsEvent` (`learning/models/analytics.py`)
- `type` (TextChoices; ~20 event types)
- `user` FK (nullable for anonymous catalog views)
- `course` FK (nullable)
- `lesson` FK (nullable)
- `timestamp`, `metadata` (JSONField for event-specific fields)
- Indexed by `(type, timestamp)` and `(course, timestamp)`
- Partitioned by month if table grows huge (>10M rows)

### `CourseMetricsDaily` (`learning/models/analytics.py`)
- Denormalized daily rollup per course
- `course` FK, `date`
- `enrollments_new` (int), `enrollments_total` (int)
- `completions_new` (int), `completions_total` (int)
- `avg_progress_pct` (decimal), `median_time_to_complete_days` (decimal)
- `active_students` (int — accessed ≥1 lesson that day)
- `new_discussions` (int), `new_posts` (int)
- Unique: `(course, date)`

### `LessonMetrics` (`learning/models/analytics.py`)
- `lesson` FK (unique)
- `total_views` (int), `unique_viewers` (int)
- `completion_rate_pct` (decimal)
- `avg_time_spent_seconds` (int)
- `drop_off_rate_pct` (decimal — fraction of starters who didn't finish)
- `last_refreshed_at`

### `StudentRiskScore` (`learning/models/analytics.py`)
- `enrollment` FK (unique)
- `score` (decimal 0–100; higher = more at-risk)
- `risk_level`: `low` | `medium` | `high`
- `factors` (JSONField: e.g., `{days_since_login: 14, missed_deadlines: 2, grade_pct: 55, lesson_completion_rate: 40}`)
- `last_computed_at`

### Risk calculation (`learning/methods.py::compute_risk_score`)
Weighted formula (tunable):
- Days since last course access (up to 30) × 2
- Missed deadlines count × 10
- Current grade delta from 70 (if below) × 1.5
- Lesson completion rate gap from cohort median × 1
- Clamp 0–100
- Band: `<30 = low`, `30–60 = medium`, `>60 = high`

## Aggregation jobs

`learning/tasks.py`:
- `aggregate_course_metrics_daily()` — cron nightly, writes `CourseMetricsDaily` rows for yesterday
- `refresh_lesson_metrics(course_id=None)` — cron hourly for active courses, on-demand otherwise
- `recompute_risk_scores(course_id=None)` — cron nightly per course
- `aggregate_org_metrics_daily()` — rolls CourseMetricsDaily into an org-wide view

Use existing MediaCMS task infrastructure (check for Celery or similar in `cms/settings.py`; if only cron jobs exist, add management commands).

## API

- `GET /courses/{slug}/analytics/summary/` — instructor overview: enrollments, completion rate, avg time, active students
- `GET /courses/{slug}/analytics/funnel/` — completion funnel: enrolled → started → 25% → 50% → 75% → 100%
- `GET /courses/{slug}/analytics/engagement-heatmap/` — lesson × day-of-week matrix showing views
- `GET /courses/{slug}/analytics/drop-off/` — per-lesson drop-off rates ordered descending
- `GET /courses/{slug}/analytics/at-risk-students/` — list ordered by risk score, with factors
- `GET /courses/{slug}/analytics/time-in-content/` — median/avg/p90 per lesson
- `GET /admin/analytics/org-summary/` — org-wide: total enrollments, completions, top courses by enrollment, by completion
- `GET /admin/analytics/enrollment-trend/?period=90d`
- `GET /admin/analytics/completion-trend/?period=90d`
- `GET /admin/analytics/export/{report_type}/?filters=...` — CSV export of any report

Permissions: all course-scoped analytics gated by `IsCourseInstructorOrReadOnly`; org analytics gated by `IsManagerOrSuperuser`.

## Frontend

- `InstructorAnalytics.jsx` → `/teach/{slug}/analytics`
  - Tabs: Overview, Funnel, Heatmap, Drop-off, At-Risk, Time in Content
  - Charting library: check if any already in MediaCMS frontend; otherwise prefer `recharts` (small, React-native)
- `AtRiskStudentList.jsx` — table sortable by risk score, click → student detail modal with factors and suggested intervention
- `OrgAnalytics.jsx` → `/admin/analytics`
  - KPI cards (total enrollments, completions, active students today)
  - Trend charts (enrollment, completion, active students over 30/90/365 days)
  - Top courses tables
  - Export buttons
- `EngagementHeatmap.jsx` — reusable component (day-of-week × hour-of-day grid)

## Verification

1. Backfill runs on a populated staging DB → historic events generated, `CourseMetricsDaily` populated back to day 1.
2. Instructor opens `/teach/{slug}/analytics` → summary matches known ground truth (enrollments, completions).
3. Funnel: create course, enroll 10 students, have 6 start, 4 reach 50%, 2 complete → funnel reflects correctly.
4. Drop-off: lesson 3 of a module has 80% of students stop → appears at top of drop-off list.
5. At-risk: student hasn't accessed course in 20 days, grade 55%, 1 missed deadline → computed score places in `medium` or `high`.
6. Heatmap: activity patterns visible by day-of-week.
7. Org dashboard: sum of per-course enrollments matches org total.
8. Export report to CSV → row counts match API response.
9. Performance: dashboard loads for a course with 10k enrollments and 100 lessons in < 500ms (denormalized tables make this feasible).
10. Aggregation job runs nightly → rows written idempotently (rerunning the same day's job doesn't duplicate).

## Out of scope

- Real-time analytics (batch nightly is fine for v1)
- ML-based predictive models (heuristic risk score only)
- Cohort comparison analytics (can add if requested)
- A/B testing infrastructure
- Learning analytics standards (xAPI / Caliper) — explicitly excluded
- Student-facing personal analytics dashboard (defer)
- External BI tool integration (consumers should use webhook + exports from Phase 7)
