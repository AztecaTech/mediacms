# LMS Phase 6: Credentials

**Status:** Planned, not started
**Branch:** `feat/lms-phase-6-credentials`
**Prerequisites:** Phase 1 (Foundation), Phase 4 (Gradebook — needed for pass-threshold certificates)
**Unblocks:** Phase 7 (LTI gradebook sync includes credential data)

## Goal

Reward learners and satisfy compliance: issue verifiable completion certificates on course completion, award badges for specific achievements, generate student transcripts (list of completed courses + grades), and surface the existing `CourseAuditLog` as a read-only audit UI for managers and auditors.

## New models

### `CertificateTemplate` (`learning/models/certificate.py`)
- `owner` FK → User (manager/admin)
- `name`, `description`
- `background_image` (ImageField; full-bleed PDF backdrop)
- `layout` (JSONField: positions of `{student_name}`, `{course_title}`, `{completion_date}`, `{instructor_name}`, `{grade}`, `{verification_url}`)
- `font_family`, `orientation` (`landscape` | `portrait`)
- `signature_image` (ImageField, optional)

### `CertificateIssuancePolicy` (`learning/models/certificate.py`)
- `course` FK
- `template` FK → `CertificateTemplate`
- `requires_passing_grade` (bool, default true)
- `minimum_grade_pct` (decimal, default 70; ignored if gradebook not used on course)
- `requires_all_lessons_completed` (bool, default true)
- `auto_issue` (bool) — true: issue immediately on qualification; false: instructor approval required

### `Certificate` (`learning/models/certificate.py`)
- `enrollment` FK (unique)
- `template_snapshot` (JSONField) — frozen layout+fields at issue time (template can change later without breaking existing certs)
- `issued_at`, `issued_by` FK → User (nullable; nullable = auto-issued)
- `verification_code` (unique, 12 char alphanumeric, publicly verifiable)
- `revoked_at` (nullable), `revoke_reason` (TextField, nullable)
- `pdf_file` (FileField) — generated on issuance, served for download

### `Badge` (`learning/models/badge.py`)
- `name`, `slug`, `description`
- `icon` (ImageField)
- `criteria_type`: `course_completion` | `path_completion` | `quiz_perfect_score` | `streak` | `manual`
- `criteria_config` (JSONField: e.g., `{course_id: 5}`, `{streak_days: 30}`)
- `is_active` (bool)

### `BadgeAward` (`learning/models/badge.py`)
- `user` FK, `badge` FK
- `awarded_at`, `awarded_by` FK → User (nullable = auto)
- `context` (JSONField) — what triggered it
- Unique: `(user, badge)` (one-time awards)

### `TranscriptEntry` (`learning/models/transcript.py`)
- Computed view-model, not a stored table in v1. Derived on-demand from `Enrollment` + `Grade`:
  - Course title, completion date, final grade %, letter grade, credit hours (nullable; from `Course.estimated_hours`)
- If performance becomes an issue, materialize with a periodic task.

## Certificate PDF generation

`learning/methods.py::generate_certificate_pdf(certificate_id)`:
- Uses `reportlab` or `weasyprint` (check if either is already in `requirements.txt`; prefer existing choice)
- Renders template background + text overlays at positions from `layout`
- Embeds QR code linking to `/verify/{verification_code}` for public verification
- Saves to `Certificate.pdf_file` and returns file path

Background task triggered by `Certificate` post-save signal when `pdf_file` is empty.

## Auto-issuance flow

Signal handler in `learning/signals.py` on `Enrollment.save`:
- If `status` transitioned to `completed` AND the course has a `CertificateIssuancePolicy`:
  - Check `requires_passing_grade` against `enrollment.current_grade_pct` (from Phase 4)
  - Check `requires_all_lessons_completed` against `LessonProgress`
  - If qualified and `auto_issue=true`: create `Certificate`, generate PDF, write `CourseAuditLog` (action=`certificate_issued`)
  - If qualified and `auto_issue=false`: write pending review record (or reuse `Notification` type `cert_pending` to instructor)

## Badge evaluation

Background task `learning/tasks.py::evaluate_badges_for_user(user_id)` runs on relevant events:
- `Enrollment` completion → check `course_completion` and `path_completion` badges
- `QuizAttempt` graded → check `quiz_perfect_score` badges
- Daily cron → check `streak` badges
- Idempotent (unique constraint on `BadgeAward(user, badge)`)

## API

- `GET/POST /certificate-templates/` (admin/manager)
- `GET/PATCH/DELETE /certificate-templates/{id}/`
- `GET/POST /courses/{slug}/certificate-policy/`
- `GET /certificates/{id}/` — owner or instructor view
- `GET /certificates/{id}/pdf/` — serves PDF download
- `POST /certificates/{id}/revoke/` (instructor/admin)
- `GET /verify/{verification_code}/` — public endpoint: returns certificate validity + metadata
- `GET/POST /badges/` (admin)
- `GET /my/badges/` — user's earned badges
- `GET /users/{username}/badges/` — public badge showcase (respects privacy setting)
- `GET /my/transcript/` — current user's transcript data (JSON)
- `GET /my/transcript/pdf/` — downloadable PDF transcript
- `GET /audit/courses/{slug}/` — read-only audit trail (manager/admin only)

## Frontend

- `CertificateTemplateEditor.jsx` → `/admin/certificates/templates` (drag-place fields on background image)
- `CertificatePolicyForm.jsx` (inside `CourseAuthoring.jsx`)
- `CertificateViewer.jsx` → `/certificates/{id}` (embedded PDF, download button, share link)
- `CertificateVerifyPage.jsx` → `/verify/{code}` (public, shows issued to / course / date / valid|revoked)
- `BadgeShowcase.jsx` → `/my/badges`
- `PublicBadgeShowcase.jsx` → `/users/{username}/badges`
- `Transcript.jsx` → `/my/transcript` (table view + PDF export button)
- `AuditTrail.jsx` → `/teach/{slug}/audit` (filters by action, date, user)

## Verification

1. Create certificate template with name, date, course fields positioned on background image.
2. Create course with `CertificateIssuancePolicy(auto_issue=true, requires_passing_grade=true, min=70)`.
3. Student completes all lessons with final grade 85% → certificate auto-issued, PDF generated, notification sent.
4. Open `/verify/{code}` as anonymous user → sees valid certificate.
5. Revoke certificate → `/verify/{code}` shows "revoked" with reason.
6. Student with grade 65% completes course → no certificate issued.
7. `auto_issue=false` policy: student qualifies → instructor sees pending in queue → approves → issued.
8. Create badge "Python Master" (criteria: complete course id=5). Student completes course 5 → badge awarded.
9. Create badge "Perfect Scorer" (criteria: quiz perfect score). Student scores 100% → badge awarded once (not on retake).
10. Transcript: student with 3 completed courses → lists all 3 with grades and dates.
11. Transcript PDF export → matches JSON view.
12. Audit: manager opens course audit trail → sees enrollments, completions, certificate issuance chronologically.
13. Template edit: modify template → existing certificates keep old `template_snapshot` (unchanged PDF).

## Out of scope

- Blockchain-verified credentials (Open Badges 2.0 optional — defer)
- Credential wallet export (Credly, LinkedIn auto-share) — Phase 7
- Multi-language certificate templates
- Per-cohort certificate variations
- Custom verification UI per organization
