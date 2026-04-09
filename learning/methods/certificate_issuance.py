"""Certificate issuance and revocation helpers."""

import secrets
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from learning.methods.certificate_pdf import generate_certificate_pdf_bytes
from learning.models import (
    Certificate,
    CertificateIssuancePolicy,
    Enrollment,
    EnrollmentStatus,
    Lesson,
    LessonProgress,
    LessonProgressStatus,
)


class CertificateEligibilityError(ValueError):
    pass


def _random_code():
    return secrets.token_urlsafe(24)[:32]


def _certificate_context(*, enrollment: Enrollment, code: str) -> dict:
    user = enrollment.user
    name = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return {
        "recipient": (name or "").strip() or getattr(user, "username", str(user.pk)),
        "course_title": enrollment.course.title,
        "verification_code": code,
        "issued_at": timezone.now().isoformat(),
    }


def _attach_pdf(cert: Certificate, enrollment: Enrollment, template=None):
    generator = getattr(settings, "LMS_CERTIFICATE_GENERATOR", "reportlab")
    context = _certificate_context(enrollment=enrollment, code=cert.verification_code)
    if template is not None:
        context["layout"] = template.layout or {}
        context["orientation"] = template.orientation
        context["font_family"] = template.font_family or "Helvetica"
        try:
            context["background_image_path"] = template.background_image.path if template.background_image else None
        except Exception:
            context["background_image_path"] = None
        try:
            context["signature_path"] = template.signature_image.path if template.signature_image else None
        except Exception:
            context["signature_path"] = None
    data = generate_certificate_pdf_bytes(context, generator=generator)
    cert.pdf_file.save(
        f"cert-{enrollment.course.slug}-{enrollment.user_id}-{cert.verification_code}.pdf",
        ContentFile(data),
        save=False,
    )


def _course_completion_ratio(enrollment: Enrollment) -> Decimal:
    total = Lesson.objects.filter(module__course=enrollment.course).count()
    if total == 0:
        return Decimal("0")
    completed = LessonProgress.objects.filter(
        enrollment=enrollment,
        status=LessonProgressStatus.COMPLETED,
        lesson__module__course=enrollment.course,
    ).count()
    return (Decimal(completed) / Decimal(total) * Decimal("100")).quantize(Decimal("0.01"))


def _ensure_policy_requirements(policy: CertificateIssuancePolicy, enrollment: Enrollment):
    if enrollment.status not in (EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED):
        raise CertificateEligibilityError("Enrollment is not active/completed.")
    if policy.requires_all_lessons_completed:
        ratio = _course_completion_ratio(enrollment)
        if ratio < Decimal("100"):
            raise CertificateEligibilityError("All lessons are not completed.")
    if policy.requires_passing_grade:
        current = enrollment.current_grade_pct
        if current is None:
            raise CertificateEligibilityError("Current grade is missing for this enrollment.")
        if Decimal(current) < Decimal(policy.minimum_grade_pct):
            raise CertificateEligibilityError("Minimum passing grade is not met.")


@transaction.atomic
def issue_certificate_for_enrollment(enrollment: Enrollment, issued_by=None) -> Certificate:
    course = enrollment.course
    policy = CertificateIssuancePolicy.objects.filter(course=course).select_related("template").first()
    if not policy:
        raise CertificateEligibilityError("No certificate issuance policy configured for this course.")

    _ensure_policy_requirements(policy, enrollment)

    existing = Certificate.objects.filter(enrollment=enrollment).first()
    if existing:
        if existing.revoked_at:
            existing.revoked_at = None
            existing.revoke_reason = ""
            existing.issued_by = issued_by
            existing.template_snapshot = {
                "template_id": policy.template_id,
                "template_name": policy.template.name,
                "course_id": course.id,
                "course_title": course.title,
                "issued_at": timezone.now().isoformat(),
            }
            existing.verification_code = _random_code()
            _attach_pdf(existing, enrollment, template=policy.template)
            existing.save(
                update_fields=[
                    "revoked_at",
                    "revoke_reason",
                    "issued_by",
                    "template_snapshot",
                    "verification_code",
                    "pdf_file",
                ]
            )
        elif not existing.pdf_file:
            _attach_pdf(existing, enrollment, template=policy.template)
            existing.save(update_fields=["pdf_file"])
        return existing

    cert = Certificate(
        enrollment=enrollment,
        issued_by=issued_by,
        verification_code=_random_code(),
        template_snapshot={
            "template_id": policy.template_id,
            "template_name": policy.template.name,
            "course_id": course.id,
            "course_title": course.title,
            "issued_at": timezone.now().isoformat(),
        },
    )
    _attach_pdf(cert, enrollment, template=policy.template)
    cert.save()
    return cert


def maybe_auto_issue_certificate(enrollment: Enrollment, issued_by=None) -> Certificate | None:
    policy = CertificateIssuancePolicy.objects.filter(course=enrollment.course, auto_issue=True).first()
    if not policy:
        return None
    try:
        return issue_certificate_for_enrollment(enrollment, issued_by=issued_by)
    except CertificateEligibilityError:
        return None


def maybe_schedule_auto_issue(enrollment: Enrollment, issued_by=None):
    """Schedule async auto-issue when enabled, otherwise run immediately."""
    async_enabled = bool(getattr(settings, "LMS_CERTIFICATE_ASYNC_ISSUE", False))
    if async_enabled:
        try:
            from learning.tasks import issue_certificate_for_enrollment_task

            return issue_certificate_for_enrollment_task.delay(enrollment.id, getattr(issued_by, "id", None))
        except Exception:
            return maybe_auto_issue_certificate(enrollment, issued_by=issued_by)
    return maybe_auto_issue_certificate(enrollment, issued_by=issued_by)


@transaction.atomic
def revoke_certificate(cert: Certificate, reason: str = "", revoked_by=None) -> Certificate:
    if cert.revoked_at:
        return cert
    cert.revoked_at = timezone.now()
    cert.revoke_reason = (reason or "").strip()
    if revoked_by:
        cert.issued_by = revoked_by
    cert.save(update_fields=["revoked_at", "revoke_reason", "issued_by"])
    return cert


def regenerate_missing_certificate_pdfs(*, course_id: int | None = None, limit: int = 200) -> int:
    qs = Certificate.objects.filter(revoked_at__isnull=True).select_related("enrollment__course")
    if course_id is not None:
        qs = qs.filter(enrollment__course_id=course_id)
    processed = 0
    for cert in qs.order_by("id")[: max(1, int(limit))]:
        if cert.pdf_file:
            continue
        policy = CertificateIssuancePolicy.objects.filter(course=cert.enrollment.course).select_related("template").first()
        template = policy.template if policy else None
        _attach_pdf(cert, cert.enrollment, template=template)
        cert.save(update_fields=["pdf_file"])
        processed += 1
    return processed
