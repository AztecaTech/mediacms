from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from learning.models import (
    Enrollment,
    EnrollmentStatus,
    Lesson,
    LessonContentType,
    LessonProgress,
    LessonProgressStatus,
)


def completion_threshold():
    return int(getattr(settings, "LMS_COMPLETION_THRESHOLD", 90))


def refresh_enrollment_progress(enrollment):
    lessons = Lesson.objects.filter(module__course=enrollment.course)
    total = lessons.count()
    if total == 0:
        enrollment.progress_pct = Decimal("0")
        enrollment.completed_lessons_count = 0
        enrollment.save(update_fields=["progress_pct", "completed_lessons_count"])
        return

    completed = LessonProgress.objects.filter(
        enrollment=enrollment,
        status=LessonProgressStatus.COMPLETED,
        lesson__module__course=enrollment.course,
    ).count()
    enrollment.completed_lessons_count = completed
    enrollment.progress_pct = Decimal(completed * 100 / total).quantize(Decimal("0.01"))
    update_fields = ["progress_pct", "completed_lessons_count"]
    if completed == total and enrollment.status == EnrollmentStatus.ACTIVE:
        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.completed_at = timezone.now()
        update_fields.extend(["status", "completed_at"])
    enrollment.save(update_fields=update_fields)
    from learning.methods.certificate_issuance import maybe_schedule_auto_issue

    maybe_schedule_auto_issue(enrollment)


def refresh_course_enrolled_count(course):
    n = course.enrollments.filter(status=EnrollmentStatus.ACTIVE).count()
    if course.enrolled_count != n:
        course.enrolled_count = n
        course.save(update_fields=["enrolled_count"])


def refresh_course_avg_completion(course):
    from django.db.models import Avg

    agg = course.enrollments.filter(status=EnrollmentStatus.ACTIVE).aggregate(
        avg=Avg("progress_pct")
    )
    avg = agg["avg"] or Decimal("0")
    course.avg_completion_pct = Decimal(avg).quantize(Decimal("0.01"))
    course.save(update_fields=["avg_completion_pct"])


@transaction.atomic
def apply_lesson_progress_heartbeat(enrollment, lesson, position_seconds, duration_seconds):
    if enrollment.course_id != lesson.module.course_id:
        raise ValueError("Lesson does not belong to enrollment course")

    lp, _created = LessonProgress.objects.select_for_update().get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={
            "status": LessonProgressStatus.IN_PROGRESS,
            "started_at": timezone.now(),
        },
    )
    if enrollment.started_at is None:
        enrollment.started_at = timezone.now()
        enrollment.save(update_fields=["started_at"])

    duration_seconds = max(int(duration_seconds or 0), 1)
    position_seconds = max(0, int(position_seconds or 0))
    pct = min(100, int(position_seconds * 100 / duration_seconds))

    threshold = completion_threshold()
    if lesson.content_type == LessonContentType.VIDEO:
        new_pct = max(lp.progress_pct, pct)
    else:
        new_pct = max(lp.progress_pct, min(100, pct))

    lp.progress_pct = new_pct
    lp.last_position_seconds = position_seconds
    lp.time_spent_seconds = lp.time_spent_seconds + getattr(
        settings, "LMS_HEARTBEAT_INTERVAL_SECONDS", 10
    )
    if lp.status == LessonProgressStatus.NOT_STARTED:
        lp.status = LessonProgressStatus.IN_PROGRESS
        lp.started_at = timezone.now()
    if new_pct >= threshold and lp.status != LessonProgressStatus.COMPLETED:
        lp.status = LessonProgressStatus.COMPLETED
        lp.completed_at = timezone.now()
        lp.progress_pct = 100
    lp.save()

    refresh_enrollment_progress(enrollment)
    refresh_course_avg_completion(enrollment.course)
    return lp


def mark_nonvideo_lesson_complete(enrollment, lesson):
    """Mark text/file/link lesson complete (Phase 2 UX); idempotent."""
    lp, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={
            "status": LessonProgressStatus.COMPLETED,
            "progress_pct": 100,
            "completed_at": timezone.now(),
            "started_at": timezone.now(),
        },
    )
    if lp.status != LessonProgressStatus.COMPLETED:
        lp.status = LessonProgressStatus.COMPLETED
        lp.progress_pct = 100
        lp.completed_at = timezone.now()
        if not lp.started_at:
            lp.started_at = timezone.now()
        lp.save()
    refresh_enrollment_progress(enrollment)
    refresh_course_avg_completion(enrollment.course)
