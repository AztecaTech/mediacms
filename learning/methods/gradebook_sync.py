"""Push quiz and assignment scores into GradeItem / Grade rows."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from learning.models import (
    Assignment,
    Enrollment,
    Grade,
    GradeCategory,
    GradeItem,
    GradeItemSourceType,
    Quiz,
    QuizAttempt,
    QuizAttemptStatus,
    Submission,
    SubmissionStatus,
)

_AUTO_CATEGORY_NAME = "Automatic assessments"


def _ensure_auto_category(course):
    cat, _ = GradeCategory.objects.get_or_create(
        course=course,
        name=_AUTO_CATEGORY_NAME,
        defaults={
            "weight_pct": Decimal("0"),
            "order": 999,
        },
    )
    return cat


def _quiz_max_points(quiz: Quiz) -> Decimal:
    total = quiz.questions.aggregate(s=Sum("points"))["s"] or Decimal("0")
    if total <= 0:
        return Decimal("100")
    return total


def obtain_grade_item_for_quiz(quiz: Quiz) -> GradeItem:
    existing = (
        GradeItem.objects.filter(source_type=GradeItemSourceType.QUIZ, quiz=quiz).select_related("category").first()
    )
    if existing:
        return existing
    course = quiz.lesson.module.course
    cat = _ensure_auto_category(course)
    title = f"Quiz: {quiz.lesson.title}"[:255]
    return GradeItem.objects.create(
        category=cat,
        source_type=GradeItemSourceType.QUIZ,
        quiz=quiz,
        title=title,
        max_points=_quiz_max_points(quiz),
        due_at=quiz.due_at,
        visible_to_students=True,
        auto_created=True,
    )


def obtain_grade_item_for_assignment(assignment: Assignment) -> GradeItem:
    existing = (
        GradeItem.objects.filter(source_type=GradeItemSourceType.ASSIGNMENT, assignment=assignment)
        .select_related("category")
        .first()
    )
    if existing:
        return existing
    course = assignment.lesson.module.course
    cat = _ensure_auto_category(course)
    title = f"Assignment: {assignment.lesson.title}"[:255]
    return GradeItem.objects.create(
        category=cat,
        source_type=GradeItemSourceType.ASSIGNMENT,
        assignment=assignment,
        title=title,
        max_points=assignment.max_points,
        due_at=assignment.due_at,
        visible_to_students=True,
        auto_created=True,
    )


@transaction.atomic
def sync_quiz_grade_for_enrollment(*, quiz: Quiz, enrollment: Enrollment) -> Grade | None:
    """Record best GRADED attempt as points on the gradebook (creates GradeItem if needed)."""
    best = (
        QuizAttempt.objects.filter(
            enrollment=enrollment,
            quiz=quiz,
            status=QuizAttemptStatus.GRADED,
        )
        .order_by("-score_pct", "-submitted_at", "-id")
        .first()
    )
    item = obtain_grade_item_for_quiz(quiz)
    item.max_points = _quiz_max_points(quiz)
    item.save(update_fields=["max_points"])

    if not best:
        return None

    points = (best.score_pct / Decimal("100")) * item.max_points
    points = points.quantize(Decimal("0.01"))

    grade, _ = Grade.objects.update_or_create(
        enrollment=enrollment,
        grade_item=item,
        defaults={
            "points_earned": points,
            "feedback": "",
            "graded_at": best.submitted_at or timezone.now(),
            "graded_by": None,
            "is_override": False,
            "excused": False,
        },
    )
    from learning.methods.grade_aggregation import recalculate_enrollment_weighted_grade
    from learning.methods.certificate_issuance import maybe_schedule_auto_issue

    recalculate_enrollment_weighted_grade(enrollment)
    maybe_schedule_auto_issue(enrollment)
    return grade


@transaction.atomic
def sync_submission_to_gradebook(submission: Submission) -> Grade | None:
    if submission.status != SubmissionStatus.GRADED or submission.score is None:
        return None
    assignment = submission.assignment
    item = obtain_grade_item_for_assignment(assignment)
    if item.max_points != assignment.max_points:
        item.max_points = assignment.max_points
        item.save(update_fields=["max_points"])

    grade, _ = Grade.objects.update_or_create(
        enrollment=submission.enrollment,
        grade_item=item,
        defaults={
            "points_earned": submission.score,
            "feedback": submission.grader_feedback or "",
            "graded_at": submission.graded_at or timezone.now(),
            "graded_by": submission.graded_by,
            "is_override": False,
            "excused": False,
        },
    )
    from learning.methods.grade_aggregation import recalculate_enrollment_weighted_grade
    from learning.methods.certificate_issuance import maybe_schedule_auto_issue

    recalculate_enrollment_weighted_grade(submission.enrollment)
    maybe_schedule_auto_issue(submission.enrollment)
    return grade
