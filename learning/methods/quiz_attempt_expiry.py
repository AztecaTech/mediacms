"""Background expiry for timed quiz attempts."""

from django.utils import timezone

from learning.methods.lesson_completion import sync_assessment_lesson_progress
from learning.models import QuizAttempt, QuizAttemptStatus


def expire_overdue_quiz_attempts(limit: int = 500):
    now = timezone.now()
    qs = (
        QuizAttempt.objects.select_related("quiz__lesson", "enrollment")
        .filter(
            status=QuizAttemptStatus.IN_PROGRESS,
            expires_at__isnull=False,
            expires_at__lt=now,
        )
        .order_by("expires_at", "id")[: max(1, int(limit))]
    )
    changed = 0
    for attempt in qs:
        attempt.status = QuizAttemptStatus.EXPIRED
        attempt.save(update_fields=["status"])
        sync_assessment_lesson_progress(attempt.enrollment, attempt.quiz.lesson)
        changed += 1
    return changed
