"""Instructor roster CSV import (administrative enroll / upsert)."""

import csv
import io
from dataclasses import dataclass

from django.contrib.auth import get_user_model

from learning.events import emit_event
from learning.methods.progress import refresh_course_enrolled_count
from learning.models import (
    Cohort,
    CourseAuditAction,
    CourseMode,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
)
from learning.signals import write_audit


class RosterCsvImportError(ValueError):
    """Fatal parse error (e.g. missing header row)."""


@dataclass(frozen=True)
class RosterCsvImportSummary:
    created: int
    updated: int
    failed: int
    rows: list[dict]


_ROLE_ALIASES = {
    "student": EnrollmentRole.STUDENT,
    "instructor": EnrollmentRole.INSTRUCTOR,
    "ta": EnrollmentRole.TA,
    "teaching assistant": EnrollmentRole.TA,
    "teaching_assistant": EnrollmentRole.TA,
}

_STATUS_ALIASES = {
    "active": EnrollmentStatus.ACTIVE,
    "completed": EnrollmentStatus.COMPLETED,
    "withdrawn": EnrollmentStatus.WITHDRAWN,
    "expired": EnrollmentStatus.EXPIRED,
}


def _normalize_header(name: str) -> str:
    return (name or "").strip().lower()


def _coerce_role(raw: str) -> str | None:
    if not (raw or "").strip():
        return EnrollmentRole.STUDENT
    return _ROLE_ALIASES.get(raw.strip().lower())


def _coerce_status(raw: str) -> str | None:
    if not (raw or "").strip():
        return EnrollmentStatus.ACTIVE
    return _STATUS_ALIASES.get(raw.strip().lower())


class RosterCsvImportManager:
    """Parses CSV rows and upserts enrollments; bypasses self-enrollment rules."""

    def __init__(self, course, acting_user):
        self._course = course
        self._acting_user = acting_user

    def run(self, decoded_text: str) -> RosterCsvImportSummary:
        stream = io.StringIO(decoded_text)
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise RosterCsvImportError("CSV must include a header row.")

        header_map = {_normalize_header(h): h for h in reader.fieldnames if h is not None}
        if "username" not in header_map and "email" not in header_map:
            raise RosterCsvImportError("CSV must include a username and/or email column.")

        created = updated = failed = 0
        rows_out: list[dict] = []
        line_no = 1

        for row in reader:
            line_no += 1
            norm = {
                _normalize_header(k): (v or "").strip() if v is not None else ""
                for k, v in row.items()
            }
            outcome = self._process_row(norm, line_no)
            rows_out.append(outcome)
            if outcome["ok"]:
                if outcome.get("action") == "created":
                    created += 1
                elif outcome.get("action") == "updated":
                    updated += 1
            else:
                failed += 1

        refresh_course_enrolled_count(self._course)
        return RosterCsvImportSummary(
            created=created, updated=updated, failed=failed, rows=rows_out
        )

    def _resolve_user(self, norm: dict) -> tuple[object | None, str | None]:
        username = norm.get("username", "").strip()
        email = norm.get("email", "").strip()
        User = get_user_model()
        if not username and not email:
            return None, "username or email is required."

        u_name = User.objects.filter(username__iexact=username).first() if username else None
        u_mail_qs = User.objects.filter(email__iexact=email) if email else User.objects.none()
        u_mail = u_mail_qs.first() if email else None

        if username and email and u_name and u_mail and u_name.pk != u_mail.pk:
            return None, "username and email refer to different users."

        picked = u_name or u_mail
        if not picked:
            return None, "user not found."
        if email and u_mail_qs.count() > 1:
            return picked, "ambiguous email; matched first user."
        return picked, None

    def _resolve_cohort(self, norm: dict) -> tuple[Cohort | None, str | None]:
        raw = norm.get("cohort_id", "").strip()
        if self._course.mode != CourseMode.COHORT:
            return None, None
        if not raw:
            return None, "cohort_id is required for cohort-mode courses."
        try:
            pk = int(raw)
        except ValueError:
            return None, "cohort_id must be an integer."
        cohort = Cohort.objects.filter(pk=pk, course=self._course).first()
        if not cohort:
            return None, "cohort not found for this course."
        return cohort, None

    def _existing_enrollment_qs(self, user, cohort):
        qs = Enrollment.objects.filter(user=user, course=self._course)
        if cohort is None:
            return qs.filter(cohort__isnull=True)
        return qs.filter(cohort=cohort)

    def _process_row(self, norm: dict, line_no: int) -> dict:
        user, warn = self._resolve_user(norm)
        if user is None:
            return {"line": line_no, "ok": False, "detail": warn or "user not found."}

        role = _coerce_role(norm.get("role", ""))
        status = _coerce_status(norm.get("status", ""))
        if role is None:
            return {"line": line_no, "ok": False, "detail": "invalid role."}
        if status is None:
            return {"line": line_no, "ok": False, "detail": "invalid status."}

        cohort, cerr = self._resolve_cohort(norm)
        if cerr:
            return {"line": line_no, "ok": False, "detail": cerr}

        already = self._existing_enrollment_qs(user, cohort).first()
        if not already and cohort is not None and cohort.capacity is not None:
            n = Enrollment.objects.filter(cohort=cohort, status=EnrollmentStatus.ACTIVE).count()
            if n >= cohort.capacity:
                return {"line": line_no, "ok": False, "detail": "cohort is full."}

        enr, created = Enrollment.objects.get_or_create(
            user=user,
            course=self._course,
            cohort=cohort,
            defaults={"role": role, "status": status},
        )

        if created:
            write_audit(user, self._course, CourseAuditAction.ENROLLED)
            emit_event("enrollment_created", user=user, course=self._course)
            detail = "created."
            if warn:
                detail = f"{detail} ({warn})"
            return {"line": line_no, "ok": True, "action": "created", "detail": detail, "enrollment_id": enr.id}

        return self._update_existing(enr, role, status, line_no, warn)

    def _update_existing(self, enr, role, status, line_no, warn: str | None) -> dict:
        prior_status = enr.status
        prior_role = enr.role
        fields: list[str] = []

        if enr.role != role:
            enr.role = role
            fields.append("role")
        if enr.status != status:
            enr.status = status
            fields.append("status")

        if not fields:
            detail = "unchanged."
            if warn:
                detail = f"{detail} ({warn})"
            return {"line": line_no, "ok": True, "action": "unchanged", "detail": detail, "enrollment_id": enr.id}

        if prior_status == EnrollmentStatus.WITHDRAWN and status == EnrollmentStatus.ACTIVE:
            write_audit(enr.user, self._course, CourseAuditAction.RE_ENROLLED)
            emit_event("enrollment_reactivated", user=enr.user, course=self._course)
        elif prior_role != role:
            write_audit(
                enr.user,
                self._course,
                CourseAuditAction.ROLE_CHANGED,
                metadata={
                    "source": "roster_csv_import",
                    "by_user_id": self._acting_user.pk,
                    "fields": fields,
                },
            )

        enr.save(update_fields=fields)
        detail = f"updated ({', '.join(fields)})."
        if warn:
            detail = f"{detail} ({warn})"
        return {"line": line_no, "ok": True, "action": "updated", "detail": detail, "enrollment_id": enr.id}
