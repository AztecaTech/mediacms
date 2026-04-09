# LMS Phase 4: Gradebook

**Status:** Planned, not started
**Branch:** `feat/lms-phase-4-gradebook`
**Prerequisites:** Phase 1 (Foundation), Phase 3 (Assessment — provides `QuizAttempt` and `Submission` scores)
**Unblocks:** Phase 6 (certificates check final grade)

## Goal

Introduce a real gradebook per course: weighted grade categories, rubric-based grading for assignments, grade calculations with letter-grade bands, manual grade entry/override, feedback, student-facing grade view with optional hidden-until-released semantics, and CSV export for instructors.

## New models

### `GradeCategory` (`learning/models/grade_category.py`)
- `course` FK, `name` (e.g., "Quizzes", "Homework", "Final Exam")
- `weight_pct` (decimal; all categories in a course must sum to 100)
- `drop_lowest_n` (int, default 0)
- `order` (int)

### `GradeItem` (`learning/models/grade_item.py`)
- `category` FK → `GradeCategory`
- `source_type`: `quiz` | `assignment` | `manual`
- `quiz` FK (nullable), `assignment` FK (nullable)
- `title`, `max_points` (decimal)
- `due_at` (nullable), `visible_to_students` (bool)
- `auto_created` (bool) — true when created from a Phase 3 quiz/assignment via signal

### `Grade` (`learning/models/grade.py`)
- `enrollment` FK, `grade_item` FK
- `points_earned` (decimal, nullable)
- `feedback` (TextField)
- `graded_by` FK → User (nullable)
- `graded_at` (nullable)
- `is_override` (bool) — true when manually overridden vs auto-computed from quiz/assignment
- `excused` (bool) — excused assignments don't count toward totals
- Unique: `(enrollment, grade_item)`

### `Rubric` (`learning/models/rubric.py`)
- `owner` FK → User, `title`, `description`
- Reusable across courses

### `RubricCriterion` (`learning/models/rubric.py`)
- `rubric` FK, `title`, `description`, `max_points` (decimal), `order` (int)

### `RubricLevel` (`learning/models/rubric.py`)
- `criterion` FK, `title` (e.g., "Excellent", "Needs Improvement")
- `description`, `points` (decimal), `order` (int)

### `RubricGrading` (`learning/models/rubric.py`)
- `grade` FK, `criterion` FK, `level` FK (nullable)
- `points_awarded` (decimal), `comment` (TextField)
- Unique: `(grade, criterion)`

### `LetterGradeScheme` (`learning/models/letter_grade.py`)
- `course` FK (nullable; nullable = org default scheme)
- `name`, `bands` (JSONField: `[{letter: "A", min_pct: 90, max_pct: 100}, ...]`)

## Signal-driven auto-grade flow

When a `QuizAttempt` is graded (Phase 3) or a `Submission` is graded (Phase 3):
- Signal handler in `learning/signals.py` creates/updates the corresponding `Grade` row on the linked `GradeItem`
- `is_override=false`
- Manual instructor changes set `is_override=true` and stop auto-sync

`GradeItem` auto-creation: when a `Quiz` or `Assignment` is published inside a course that has gradebook categories defined, a matching `GradeItem` is created automatically. Instructor can override the category assignment.

## Grade calculation (`learning/methods.py`)

`enrollment.calculate_course_grade()`:
1. For each `GradeCategory` in the course:
   - Gather all `Grade` rows in that category for this enrollment
   - Drop lowest N if `drop_lowest_n > 0`
   - Skip excused grades
   - `category_pct = sum(points_earned) / sum(max_points) * 100`
2. `course_pct = sum(category_pct * weight_pct) / 100`
3. Map `course_pct` to letter via active `LetterGradeScheme`

Results stored denormalized on `Enrollment` as `current_grade_pct` and `current_grade_letter`, recalculated on any Grade change.

## API

- `GET/POST /courses/{slug}/grade-categories/`
- `PATCH/DELETE /grade-categories/{id}/`
- `GET/POST /courses/{slug}/grade-items/`
- `PATCH/DELETE /grade-items/{id}/`
- `GET /courses/{slug}/gradebook/` — instructor view: matrix of students × grade items
- `PATCH /grades/{id}/` — instructor override
- `POST /courses/{slug}/gradebook/export/` — CSV export
- `GET /my/grades/{slug}/` — student's grades for one course (respects `visible_to_students`)
- `GET/POST /rubrics/`, `POST /rubrics/{id}/clone/`

## Frontend

- `Gradebook.jsx` → `/teach/{slug}/gradebook` (matrix view, click cell to edit, bulk operations)
- `GradebookSettings.jsx` → `/teach/{slug}/gradebook/settings` (categories, weights, letter scheme)
- `StudentGradeView.jsx` → `/learn/{slug}/grades` (student sees own grades, hidden items excluded)
- `RubricBuilder.jsx` (reusable component inside `AssignmentAuthoring.jsx` from Phase 3)
- `RubricGrader.jsx` (reusable inside `SubmissionGrader.jsx` from Phase 3)

## Verification

1. Create course with 3 categories (Quizzes 40%, Homework 30%, Final 30%). Confirm weights sum to 100.
2. Publish 3 quizzes → 3 GradeItems auto-created in Quizzes category.
3. Student takes quizzes, submits homework, takes final → auto-grades populate.
4. Instructor opens gradebook → sees matrix with current grade per student.
5. Override one quiz grade manually → auto-sync stops for that grade, override flag true.
6. Drop-lowest: category with 4 items and `drop_lowest_n=1` → lowest is excluded from calc.
7. Excused assignment: student marked excused → not counted in totals.
8. Letter grade: create custom scheme (A≥93, B≥85, ...), apply to course, verify calculated letter.
9. Export CSV → matches gradebook view.
10. Student view: item with `visible_to_students=false` hidden from student.
11. Rubric: create rubric with 3 criteria × 4 levels, use to grade assignment, confirm points sum correctly.

## Out of scope

- Curves / standard deviation-based grading
- Grade change history log (audit via existing `CourseAuditLog` only)
- Extra credit categories (workaround: use weights >100 discouraged but possible)
- Cross-course GPA (defer to transcript in Phase 6)
