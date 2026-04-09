# LMS Phase 7: Standards & Integration

**Status:** Planned, not started
**Branch:** `feat/lms-phase-7-integration`
**Prerequisites:** Phases 1–6 (LTI and HRIS sync both assume courses, enrollments, grades, and credentials all exist)
**Unblocks:** Enterprise / institutional adoption

## Goal

Make the LMS play well with other enterprise systems: LTI 1.3 so the platform can be embedded in (or embed) other LMSes like Canvas or Moodle, LDAP/Active Directory sync for user provisioning, HRIS hooks for automatic enrollment based on job role/department, webhooks for enrollment/completion events, and bulk CSV import/export tools for admins. Not SCORM (explicitly out of scope per scoping decision) and not xAPI in this phase.

## Subsystem 1: LTI 1.3 provider

**Goal:** External LMSes embed MediaCMS courses as an LTI tool.

### New models
- `LTIToolConfig` (`learning/models/lti.py`)
  - `name`, `client_id` (unique), `deployment_id`
  - `platform_issuer` (URL), `public_jwks_url`, `auth_login_url`, `auth_token_url`
  - `private_key` (encrypted), `public_key`
  - `is_active`
- `LTIResourceLink`
  - `config` FK, `resource_link_id`, `course` FK → `Course`
  - Created on first LTI launch; maps platform's resource link to our course
- `LTIUserMapping`
  - `config` FK, `platform_user_id`, `user` FK → `User`
  - Upserted on launch; used for SSO continuity

### Library
- Use `PyLTI1p3` (vendor-agnostic, actively maintained). Add to `requirements.txt`.

### Endpoints
- `POST /lti/launch/` — initiate login, validate JWT, resolve resource link, redirect to `CoursePlayer.jsx` with session
- `GET /lti/jwks/` — expose our public JWKS
- `POST /lti/deep-linking/` — return course picker for platforms that support deep linking
- `POST /lti/ags/lineitems/` — Assignment & Grade Services: push grades back to platform
- Background task: on `Grade` save → if enrollment came via LTI, push to platform gradebook

## Subsystem 2: LTI 1.3 consumer

**Goal:** Embed external tools (simulation labs, virtual machines, external video) inside a Course as a lesson type.

### Extensions
- `Lesson.content_type` gains `lti` value
- New `LTIExternalTool` (`learning/models/lti.py`):
  - `owner` FK, `name`, `client_id`, `deployment_id`, `platform_issuer`, `keys` (encrypted)
- `Lesson.lti_tool` FK → `LTIExternalTool` (nullable)
- On lesson open: outbound LTI launch wrapped in an iframe; completion reported back via LTI AGS

## Subsystem 3: LDAP / Active Directory sync

### New models
- `LDAPSource` (`learning/models/directory.py`)
  - `name`, `server_uri`, `bind_dn`, `bind_password` (encrypted), `base_dn`
  - `user_filter`, `group_filter`
  - `user_attribute_map` (JSONField: `{username: "sAMAccountName", email: "mail", first_name: "givenName", ...}`)
  - `sync_schedule` (cron string), `last_sync_at`, `last_sync_status`

### Sync job
- `learning/tasks.py::sync_ldap_source(source_id)`:
  - Pull users matching filter, upsert `User` rows
  - Pull groups, upsert `RBACGroup` rows (reuse existing RBAC)
  - Update `RBACMembership` based on LDAP group membership diff
  - Cascades: RBAC groups → course auto-enrollment (via Phase 1 signal)

## Subsystem 4: HRIS integration

Generic webhook + polling adapter for systems like BambooHR, Workday, SAP SuccessFactors.

### New models
- `HRISConnector` (`learning/models/hris.py`)
  - `system_type`: `bamboohr` | `workday` | `successfactors` | `generic_webhook`
  - `name`, `api_base_url`, `credentials` (encrypted JSON)
  - `field_map` (JSONField)
- `HRISRule` (`learning/models/hris.py`)
  - `connector` FK
  - `condition` (JSONField: e.g., `{department: "Engineering", job_title_contains: "Manager"}`)
  - `action` (enum: `enroll_in_course` | `enroll_in_path` | `add_to_rbac_group`)
  - `target_course` FK / `target_path` FK / `target_group` FK (one of)

### Sync job
- Scheduled pull from HRIS → for each employee, evaluate rules → perform action (idempotent).

## Subsystem 5: Webhooks (outbound)

### New models
- `Webhook` (`learning/models/webhook.py`)
  - `owner` FK, `name`, `url`, `secret` (HMAC signing key)
  - `events` (multi-select: `enrollment.created`, `enrollment.completed`, `course.published`, `certificate.issued`, `grade.posted`, `quiz.submitted`, `discussion.post.created`)
  - `is_active`, `last_delivered_at`, `failure_count`
- `WebhookDelivery` (`learning/models/webhook.py`)
  - `webhook` FK, `event_type`, `payload` (JSONField)
  - `status`: `pending` | `delivered` | `failed`
  - `response_code`, `response_body`
  - `attempted_at`, `next_retry_at`

### Delivery
- Signal-based: registered LMS events trigger webhook payload build + queue for delivery
- Background task with exponential backoff, max 5 retries
- HMAC-SHA256 signature header (`X-Learning-Signature`)

## Subsystem 6: Bulk CSV import/export

Admin tools under `/manage/learning/`:
- Import courses (meta only; modules/lessons separately)
- Import users (create + RBAC group assignment)
- Import enrollments (bulk enroll users into courses/cohorts)
- Export: enrollments, completions, grades, certificates — filtered by date range, course, cohort

Use existing MediaCMS admin interface pattern (`/manage-media` style).

## API

- `/api/v1/lti/*` (see LTI endpoints above)
- `GET/POST /ldap-sources/`, `POST /ldap-sources/{id}/sync-now/`
- `GET/POST /hris-connectors/`, `GET/POST /hris-rules/`
- `GET/POST /webhooks/`, `POST /webhooks/{id}/test/`, `GET /webhooks/{id}/deliveries/`
- `POST /admin/imports/courses/`, `POST /admin/imports/users/`, `POST /admin/imports/enrollments/`
- `GET /admin/exports/{type}/?filters=...`

## Frontend (admin-only pages)

- `LTIToolList.jsx`, `LTIToolForm.jsx` → `/admin/lti-providers`
- `LDAPSourceList.jsx`, `LDAPSourceForm.jsx` → `/admin/ldap`
- `HRISConnectorList.jsx`, `HRISConnectorForm.jsx` → `/admin/hris`
- `WebhookList.jsx`, `WebhookForm.jsx`, `WebhookDeliveries.jsx` → `/admin/webhooks`
- `BulkImport.jsx`, `BulkExport.jsx` → `/admin/imports`, `/admin/exports`

## Verification

### LTI provider
1. Register MediaCMS as LTI 1.3 tool inside a Canvas sandbox.
2. Launch a course from Canvas → lands in `CoursePlayer.jsx`, user SSO-mapped.
3. Student completes quiz → grade appears in Canvas gradebook via AGS push.
4. Deep linking: Canvas teacher picks a specific course from our picker.

### LTI consumer
1. Configure external tool (e.g., a sandbox lab).
2. Create LTI lesson in a course → student launches → iframe loads external tool → completion reported back.

### LDAP
1. Point at a test OpenLDAP instance. Run sync → users + groups created.
2. Add user to LDAP group → next sync → RBAC membership updated → auto-enrollment fires.

### HRIS
1. Configure BambooHR mock (or real sandbox). Rule: `department=Safety` → enroll in "Annual Safety Training".
2. Run sync → matching employees auto-enrolled; re-run → no duplicates.

### Webhooks
1. Configure webhook listener (e.g., requestbin).
2. Student enrolls → webhook delivered with signed payload.
3. Force failure → retries with exponential backoff → marked failed after 5 attempts.

### Bulk I/O
1. Import 100 users from CSV → all created with correct RBAC.
2. Export enrollments for Q1 2026 → CSV matches admin views.

## Out of scope

- SCORM / xAPI (explicitly excluded per scoping decision)
- LTI 1.1 legacy support
- SAML (already supported by allauth in existing MediaCMS)
- OAuth2 custom provider (allauth handles)
- Two-way HRIS sync (we consume, don't write back)
- GraphQL API
