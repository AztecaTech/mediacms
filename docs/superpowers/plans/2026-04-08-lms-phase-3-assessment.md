# LMS Phase 3: Assessment (Quizzes & Assignments)

**Status:** Planned, not started
**Branch:** `feat/lms-phase-3-assessment`
**Prerequisites:** Phase 1 (Foundation), Phase 2 (Rich Content) — lesson polymorphism pattern extended
**Unblocks:** Phase 4 (Gradebook consumes quiz/assignment scores)

## Goal

Introduce formal evaluation: a quiz engine with a reusable question bank, six question types, attempts, auto-grading for objective types, time limits and randomization; plus assignment submissions with a manual grading queue and feedback. Quizzes and assignments are both exposed as new `Lesson.content_type` values so they slot into the existing module/lesson/progress machinery without a parallel hierarchy.

## New models

### `Quiz` (`learning/models/quiz.py`)
- `lesson` OneToOne → `Lesson` (with `content_type='quiz'`)
- `instructions`, `time_limit_minutes` (nullable), `max_attempts` (int, default 1)
- `passing_score_pct` (int, default 70)
- `randomize_questions` (bool), `randomize_choices` (bool)
- `show_correct_after` (enum: `never` | `after_attempt` | `after_passing` | `after_due_date`)
- `due_at` (nullable datetime)

### `Question` (`learning/models/question.py`)
- `quiz` FK, `order` (int), `prompt` (TextField, markdown)
- `type`: `mc_single` | `mc_multi` | `true_false` | `short_answer` | `matching` | `fill_blank`
- `points` (decimal, default 1.0)
- `explanation` (TextField, shown after grading)
- `metadata` (JSONField) — type-specific extras (matching pairs, fill-blank slots)

### `Choice` (`learning/models/choice.py`)
- `question` FK, `text`, `is_correct` (bool), `order` (int)
- Used by `mc_single`, `mc_multi`, `true_false`

### `QuestionBank` (`learning/models/bank.py`)
- Library of reusable questions not tied to a specific quiz
- `owner` FK → User, `title`, `description`, `questions` M2M → `Question` (independent copies via clone on add to quiz)

### `QuizAttempt` (`learning/models/attempt.py`)
- `enrollment` FK, `quiz` FK
- `started_at`, `submitted_at` (nullable), `expires_at` (nullable; set on start if time limit)
- `score_pct` (decimal), `status`: `in_progress` | `submitted` | `graded` | `expired`
- `attempt_number` (int)
- Unique: `(enrollment, quiz, attempt_number)`

### `Answer` (`learning/models/answer.py`)
- `attempt` FK, `question` FK
- `selected_choices` M2M → `Choice` (for MC types)
- `text_answer` (TextField, for short_answer/fill_blank)
- `matching_answer` (JSONField)
- `is_correct` (nullable bool), `points_awarded` (decimal), `auto_graded` (bool)
- `grader_feedback` (TextField, for manual grading)
- Unique: `(attempt, question)`

### `Assignment` (`learning/models/assignment.py`)
- `lesson` OneToOne → `Lesson` (with `content_type='assignment'`)
- `instructions`, `max_points` (decimal)
- `submission_types` (multi-select: `text` | `file` | `url`)
- `max_file_size_mb` (int), `allowed_extensions` (comma-separated)
- `due_at` (nullable), `late_penalty_pct_per_day` (decimal)

### `Submission` (`learning/models/submission.py`)
- `enrollment` FK, `assignment` FK
- `submitted_at`, `text_content`, `file` (FileField), `url`
- `status`: `draft` | `submitted` | `graded` | `returned_for_revision`
- `score` (decimal, nullable), `grader_feedback` (TextField)
- `graded_by` FK → User (nullable), `graded_at` (nullable)
- `attempt_number` (int)

## Lesson content types extended

`Lesson.content_type` gains `quiz` and `assignment`. The lesson's `Quiz`/`Assignment` OneToOne provides the actual content. Existing `LessonProgress` logic updated: a quiz lesson is "completed" when the student has passed (`best_attempt.score_pct >= passing_score_pct`) or exhausted attempts; an assignment lesson is "completed" when `Submission.status == graded`.

## API

- `GET/POST /quizzes/`, `GET/PATCH/DELETE /quizzes/{id}/`
- `GET/POST /quizzes/{id}/questions/`, `GET/PATCH/DELETE /questions/{id}/`
- `POST /quizzes/{id}/start/` — creates `QuizAttempt`, returns questions (randomized if configured)
- `POST /attempts/{id}/answer/` — save in-progress answer
- `POST /attempts/{id}/submit/` — finalize, auto-grade, return score
- `GET /attempts/{id}/` — view results (respects `show_correct_after` rule)
- `GET/POST /question-banks/`, `POST /question-banks/{id}/clone-to-quiz/{quiz_id}/`
- `GET/POST /assignments/`, `POST /assignments/{id}/submit/`
- `GET /submissions/` — instructor grading queue (filter: ungraded, course, due_date)
- `POST /submissions/{id}/grade/` — instructor grades submission

## Frontend

- `QuizAuthoring.jsx` — question-type-aware form builder inside `CourseAuthoring.jsx`
- `QuizTaker.jsx` — student quiz UI with timer, progress, navigation, submit
- `QuizResults.jsx` — post-submission view respecting reveal rules
- `AssignmentAuthoring.jsx` — assignment setup form
- `AssignmentSubmitter.jsx` — student submission UI (text editor + file dropzone + URL)
- `GradingQueue.jsx` → `/teach/grading` — instructor grading inbox with filters
- `SubmissionGrader.jsx` — grader view: submission content, score entry, feedback field

## Auto-grading logic (`learning/methods.py`)

- `mc_single`: exact match of selected choice to `is_correct=true`
- `mc_multi`: all correct selected AND no incorrect selected (partial credit optional via `metadata.allow_partial`)
- `true_false`: trivial match
- `fill_blank`: case-insensitive match against `metadata.accepted_answers` list
- `short_answer`: queued for manual grading (no auto)
- `matching`: exact match of submitted pairs to `metadata.correct_pairs`

Time limit enforcement: background task (Celery or `APScheduler` — check existing MediaCMS job runner) marks expired attempts as `status=expired` and auto-submits.

## Verification

1. Create quiz with 5 questions (one of each auto-gradable type). Student takes, submits → score computed correctly.
2. Multi-attempt quiz: student fails twice, passes on 3rd → lesson marked complete, best attempt recorded.
3. Time-limited quiz: start → wait past expiry → confirm `status=expired`, auto-submit with partial answers graded.
4. Randomization: confirm different students see different orders.
5. Assignment: student submits file + text → instructor sees in grading queue → grades → student sees feedback and score.
6. Late penalty: submit after `due_at` → score reduced per `late_penalty_pct_per_day`.
7. Reveal rules: `show_correct_after=after_passing` → correct answers hidden until student passes.
8. Question bank: create bank, clone question to quiz, modify clone → original unchanged.

## Out of scope

- Peer grading (defer; Phase 5 or later)
- Rubric grading (that's Phase 4 Gradebook)
- Plagiarism detection
- Video-submission assignments (add later if needed via `submission_types`)
- Adaptive/branching quizzes
