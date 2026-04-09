"""Rollup helpers for `CourseMetricsDaily`."""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Q

from learning.models import Course, CourseMetricsDaily, Enrollment, EnrollmentRole


def _course_rollup_values(course: Course, target_date: date) -> dict:
    student_enrollments = Enrollment.objects.filter(course=course, role=EnrollmentRole.STUDENT)
    enrollments_new = student_enrollments.filter(enrolled_at__date=target_date).count()
    enrollments_total = student_enrollments.filter(
        status__in=("active", "completed"),
    ).count()
    completions_new = student_enrollments.filter(completed_at__date=target_date).count()
    completions_total = student_enrollments.filter(status="completed").count()
    avg_progress = student_enrollments.filter(status="active").aggregate(avg=Avg("progress_pct"))["avg"] or Decimal("0")
    active_students = student_enrollments.filter(
        status="active",
    ).filter(Q(progress_pct__gt=0) | Q(started_at__isnull=False)).count()

    return {
        "enrollments_new": enrollments_new,
        "enrollments_total": enrollments_total,
        "completions_new": completions_new,
        "completions_total": completions_total,
        "avg_progress_pct": Decimal(avg_progress).quantize(Decimal("0.01")),
        "active_students": active_students,
    }


def rollup_course_metrics_for_date(target_date: date) -> int:
    """Upsert `CourseMetricsDaily` rows for all courses; returns number processed."""
    count = 0
    for course in Course.objects.all().only("id"):
        values = _course_rollup_values(course, target_date)
        CourseMetricsDaily.objects.update_or_create(
            course=course,
            date=target_date,
            defaults=values,
        )
        count += 1
    return count
