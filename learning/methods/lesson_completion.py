from decimal import Decimal

from learning.models import (
    Lesson,
    LessonContentType,
    QuizAttempt,
    QuizAttemptStatus,
    Submission,
    SubmissionStatus,
)
from learning.methods.progress import mark_nonvideo_lesson_complete


def sync_assessment_lesson_progress(enrollment, lesson: Lesson):
    if lesson.content_type == LessonContentType.QUIZ:
        _sync_quiz(enrollment, lesson)
    elif lesson.content_type == LessonContentType.ASSIGNMENT:
        _sync_assignment(enrollment, lesson)


def _sync_quiz(enrollment, lesson):
    from django.core.exceptions import ObjectDoesNotExist

    try:
        quiz = lesson.quiz_spec
    except ObjectDoesNotExist:
        return
    attempts = QuizAttempt.objects.filter(enrollment=enrollment, quiz=quiz)
    if not attempts.exists():
        return
    best = Decimal("0")
    for a in attempts.filter(status=QuizAttemptStatus.GRADED):
        if a.score_pct > best:
            best = a.score_pct
    passed = best >= Decimal(quiz.passing_score_pct)
    used = attempts.filter(
        status__in=(QuizAttemptStatus.GRADED, QuizAttemptStatus.SUBMITTED, QuizAttemptStatus.EXPIRED)
    ).count()
    exhausted = used >= quiz.max_attempts
    if passed or exhausted:
        mark_nonvideo_lesson_complete(enrollment, lesson)


def _sync_assignment(enrollment, lesson):
    from django.core.exceptions import ObjectDoesNotExist

    try:
        spec = lesson.assignment_spec
    except ObjectDoesNotExist:
        return
    if Submission.objects.filter(
        enrollment=enrollment,
        assignment=spec,
        status=SubmissionStatus.GRADED,
    ).exists():
        mark_nonvideo_lesson_complete(enrollment, lesson)
