from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from learning.models import (
    Answer,
    Question,
    QuestionType,
    QuizAttempt,
    QuizAttemptStatus,
)


def _norm(s):
    return (s or "").strip().lower()


def grade_question(answer: Answer) -> None:
    q = answer.question
    pts = q.points
    if q.type == QuestionType.MC_SINGLE:
        sel = set(answer.selected_choices.values_list("pk", flat=True))
        correct = set(q.choices.filter(is_correct=True).values_list("pk", flat=True))
        ok = len(sel) == 1 and sel == correct
        answer.is_correct = ok
        answer.points_awarded = pts if ok else Decimal("0")
        answer.auto_graded = True
    elif q.type == QuestionType.TRUE_FALSE:
        sel = set(answer.selected_choices.values_list("pk", flat=True))
        correct = set(q.choices.filter(is_correct=True).values_list("pk", flat=True))
        ok = sel == correct and len(sel) == 1
        answer.is_correct = ok
        answer.points_awarded = pts if ok else Decimal("0")
        answer.auto_graded = True
    elif q.type == QuestionType.MC_MULTI:
        sel = set(answer.selected_choices.values_list("pk", flat=True))
        correct = set(q.choices.filter(is_correct=True).values_list("pk", flat=True))
        wrong = set(q.choices.filter(is_correct=False).values_list("pk", flat=True))
        ok = sel == correct and not (sel & wrong)
        allow_partial = bool((q.metadata or {}).get("allow_partial"))
        if ok:
            answer.is_correct = True
            answer.points_awarded = pts
        elif allow_partial and sel <= correct and sel:
            ratio = Decimal(len(sel)) / Decimal(max(len(correct), 1))
            answer.is_correct = False
            answer.points_awarded = (pts * ratio).quantize(Decimal("0.01"))
        else:
            answer.is_correct = False
            answer.points_awarded = Decimal("0")
        answer.auto_graded = True
    elif q.type == QuestionType.FILL_BLANK:
        accepted = (q.metadata or {}).get("accepted_answers") or []
        if not isinstance(accepted, list):
            accepted = []
        ta = _norm(answer.text_answer)
        ok = any(ta == _norm(x) for x in accepted)
        answer.is_correct = ok
        answer.points_awarded = pts if ok else Decimal("0")
        answer.auto_graded = True
    elif q.type == QuestionType.MATCHING:
        correct_pairs = (q.metadata or {}).get("correct_pairs") or {}
        submitted = answer.matching_answer or {}
        ok = isinstance(correct_pairs, dict) and submitted == correct_pairs
        answer.is_correct = ok
        answer.points_awarded = pts if ok else Decimal("0")
        answer.auto_graded = True
    elif q.type == QuestionType.SHORT_ANSWER:
        answer.is_correct = None
        answer.points_awarded = None
        answer.auto_graded = False
    else:
        answer.is_correct = False
        answer.points_awarded = Decimal("0")
        answer.auto_graded = True
    answer.save()


@transaction.atomic
def finalize_quiz_attempt(attempt: QuizAttempt, answers_payload: list | None = None):
    """Grade all answers; set attempt score and status. answers_payload optional for bulk set before grade."""
    from learning.models import Choice

    if attempt.status != QuizAttemptStatus.IN_PROGRESS:
        return attempt

    quiz = attempt.quiz
    questions = list(quiz.questions.all().order_by("order", "id"))

    if answers_payload:
        for row in answers_payload:
            qid = row.get("question_id")
            if not qid:
                continue
            ans, _ = Answer.objects.get_or_create(attempt=attempt, question_id=qid)
            if "choice_ids" in row:
                ans.selected_choices.set(Choice.objects.filter(pk__in=row["choice_ids"]))
            if "text_answer" in row:
                ans.text_answer = row.get("text_answer") or ""
            if "matching_answer" in row:
                ans.matching_answer = row.get("matching_answer") or {}
            ans.save()

    total_points = Decimal("0")
    earned = Decimal("0")
    pending_manual = False

    for q in questions:
        ans, _ = Answer.objects.get_or_create(attempt=attempt, question=q)
        grade_question(ans)
        ans.refresh_from_db()
        total_points += q.points
        if ans.points_awarded is not None:
            earned += ans.points_awarded
        else:
            pending_manual = True

    attempt.submitted_at = timezone.now()
    if total_points > 0:
        attempt.score_pct = (earned / total_points * Decimal("100")).quantize(Decimal("0.01"))
    else:
        attempt.score_pct = Decimal("0")

    if pending_manual:
        attempt.status = QuizAttemptStatus.SUBMITTED
    else:
        attempt.status = QuizAttemptStatus.GRADED
    attempt.save()

    from learning.methods.gradebook_sync import sync_quiz_grade_for_enrollment
    from learning.methods.lesson_completion import sync_assessment_lesson_progress

    sync_assessment_lesson_progress(attempt.enrollment, quiz.lesson)
    if attempt.status == QuizAttemptStatus.GRADED:
        sync_quiz_grade_for_enrollment(quiz=quiz, enrollment=attempt.enrollment)
    return attempt
