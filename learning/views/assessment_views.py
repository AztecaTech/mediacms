"""Quiz attempts, assignment submission, and instructor grading queue."""

from datetime import timedelta

from django.db.models import Max
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.events import emit_event
from learning.methods.gradebook_sync import sync_submission_to_gradebook
from learning.methods.lesson_completion import sync_assessment_lesson_progress
from learning.methods.quiz_grading import finalize_quiz_attempt
from learning.models import (
    Assignment,
    Course,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
    Quiz,
    QuizAttempt,
    QuizAttemptStatus,
    ShowCorrectAfter,
    Submission,
    SubmissionStatus,
)
from learning.permissions import _is_global_instructor, is_course_instructor, is_course_staff
from learning.serializers.assessment import QuizAttemptSerializer, SubmissionSerializer


def _staff_course_filter(user):
    if not user.is_authenticated:
        return Course.objects.none()
    if _is_global_instructor(user):
        return Course.objects.all()
    instructor_courses = Course.objects.filter(instructors=user)
    staff_enroll_courses = Course.objects.filter(
        enrollments__user=user,
        enrollments__status=EnrollmentStatus.ACTIVE,
        enrollments__role__in=(EnrollmentRole.INSTRUCTOR, EnrollmentRole.TA),
    )
    return (instructor_courses | staff_enroll_courses).distinct()


def _student_can_see_correct(quiz: Quiz, attempt: QuizAttempt) -> bool:
    if attempt.status not in (QuizAttemptStatus.GRADED, QuizAttemptStatus.SUBMITTED):
        return False
    pol = quiz.show_correct_after
    if pol == ShowCorrectAfter.NEVER:
        return False
    if pol == ShowCorrectAfter.AFTER_ATTEMPT:
        return True
    if pol == ShowCorrectAfter.AFTER_PASSING:
        return attempt.score_pct >= quiz.passing_score_pct
    if pol == ShowCorrectAfter.AFTER_DUE_DATE:
        return bool(quiz.due_at and timezone.now() >= quiz.due_at)
    return False


def _serialize_choice(c, show_correct: bool):
    row = {"id": c.id, "text": c.text, "order": c.order}
    if show_correct:
        row["is_correct"] = c.is_correct
    return row


def _serialize_attempt_detail(attempt: QuizAttempt, viewer, show_all_correct: bool):
    quiz = attempt.quiz
    questions = quiz.questions.all().order_by("order", "id")
    is_owner = viewer.is_authenticated and attempt.enrollment.user_id == viewer.id
    is_instr = is_course_instructor(viewer, quiz.lesson.module.course)
    hide_correct = True
    if is_instr or show_all_correct:
        hide_correct = False
    elif is_owner:
        hide_correct = not _student_can_see_correct(quiz, attempt)

    from learning.models import Answer

    out_questions = []
    for q in questions:
        ans = Answer.objects.filter(attempt=attempt, question=q).first()
        choice_ids = list(ans.selected_choices.values_list("pk", flat=True)) if ans else []
        out_questions.append(
            {
                "id": q.id,
                "order": q.order,
                "prompt": q.prompt,
                "type": q.type,
                "points": str(q.points),
                "metadata": q.metadata,
                "explanation": q.explanation if not hide_correct else "",
                "choices": [_serialize_choice(c, not hide_correct) for c in q.choices.all().order_by("order", "id")],
                "answer": (
                    {
                        "choice_ids": choice_ids,
                        "text_answer": ans.text_answer if ans else "",
                        "matching_answer": ans.matching_answer if ans else {},
                        "points_awarded": str(ans.points_awarded) if ans and ans.points_awarded is not None else None,
                        "is_correct": ans.is_correct if ans else None,
                        "auto_graded": ans.auto_graded if ans else None,
                        "grader_feedback": ans.grader_feedback if ans else "",
                    }
                    if (is_owner or is_instr)
                    else None
                ),
            }
        )
    return {"attempt": QuizAttemptSerializer(attempt).data, "questions": out_questions}


class QuizStartView(APIView):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        quiz = get_object_or_404(Quiz, pk=pk)
        course = quiz.lesson.module.course
        enr = (
            Enrollment.objects.filter(
                user=request.user,
                course=course,
                status=EnrollmentStatus.ACTIVE,
            )
            .first()
        )
        if not enr:
            return Response({"detail": "Not enrolled in this course."}, status=status.HTTP_403_FORBIDDEN)

        active = QuizAttempt.objects.filter(
            enrollment=enr,
            quiz=quiz,
            status=QuizAttemptStatus.IN_PROGRESS,
        ).first()
        if active:
            return Response(_serialize_attempt_detail(active, request.user, show_all_correct=False), status=status.HTTP_200_OK)

        used = QuizAttempt.objects.filter(
            enrollment=enr,
            quiz=quiz,
            status__in=(QuizAttemptStatus.SUBMITTED, QuizAttemptStatus.GRADED, QuizAttemptStatus.EXPIRED),
        ).count()
        if used >= quiz.max_attempts:
            return Response({"detail": "No attempts remaining."}, status=status.HTTP_400_BAD_REQUEST)

        last_num = (
            QuizAttempt.objects.filter(enrollment=enr, quiz=quiz).aggregate(m=Max("attempt_number"))["m"] or 0
        )
        expires_at = None
        if quiz.time_limit_minutes:
            expires_at = timezone.now() + timedelta(minutes=int(quiz.time_limit_minutes))
        attempt = QuizAttempt.objects.create(
            enrollment=enr,
            quiz=quiz,
            attempt_number=last_num + 1,
            expires_at=expires_at,
        )
        return Response(_serialize_attempt_detail(attempt, request.user, show_all_correct=False), status=status.HTTP_201_CREATED)


class QuizAttemptDetailView(APIView):
    def get(self, request, pk):
        attempt = get_object_or_404(QuizAttempt.objects.select_related("enrollment", "quiz__lesson__module__course"), pk=pk)
        course = attempt.quiz.lesson.module.course
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        if attempt.enrollment.user_id != request.user.id and not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(_serialize_attempt_detail(attempt, request.user, show_all_correct=False))


class QuizAttemptSubmitView(APIView):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        attempt = get_object_or_404(QuizAttempt.objects.select_related("enrollment", "quiz"), pk=pk)
        if attempt.enrollment.user_id != request.user.id:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if attempt.status != QuizAttemptStatus.IN_PROGRESS:
            return Response({"detail": "Attempt is not in progress."}, status=status.HTTP_400_BAD_REQUEST)
        if attempt.expires_at and timezone.now() > attempt.expires_at:
            attempt.status = QuizAttemptStatus.EXPIRED
            attempt.save(update_fields=["status"])
            return Response({"detail": "Attempt expired."}, status=status.HTTP_400_BAD_REQUEST)

        answers = request.data.get("answers")
        if not isinstance(answers, list):
            answers = []
        finalize_quiz_attempt(attempt, answers_payload=answers)
        attempt.refresh_from_db()
        emit_event(
            "quiz_submitted",
            user=request.user,
            course=attempt.quiz.lesson.module.course,
            lesson=attempt.quiz.lesson,
            metadata={"attempt_id": attempt.id, "quiz_id": attempt.quiz_id},
        )
        return Response(_serialize_attempt_detail(attempt, request.user, show_all_correct=False))


class AssignmentSubmitView(APIView):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        assignment = get_object_or_404(Assignment.objects.select_related("lesson__module__course"), pk=pk)
        course = assignment.lesson.module.course
        enr = (
            Enrollment.objects.filter(
                user=request.user,
                course=course,
                status=EnrollmentStatus.ACTIVE,
            )
            .first()
        )
        if not enr:
            return Response({"detail": "Not enrolled."}, status=status.HTTP_403_FORBIDDEN)

        allowed = assignment.submission_types or ["text"]
        text_content = (request.data.get("text_content") or "").strip()
        url = (request.data.get("url") or "").strip()
        upload = request.FILES.get("file")

        if "text" in allowed and text_content:
            pass
        elif "url" in allowed and url:
            pass
        elif "file" in allowed and upload:
            pass
        else:
            return Response(
                {"detail": "Provide a submission matching allowed types.", "allowed": allowed},
                status=status.HTTP_400_BAD_REQUEST,
            )

        last_num = (
            Submission.objects.filter(enrollment=enr, assignment=assignment).aggregate(m=Max("attempt_number"))["m"] or 0
        )
        sub = Submission.objects.create(
            enrollment=enr,
            assignment=assignment,
            text_content=text_content,
            url=url,
            status=SubmissionStatus.SUBMITTED,
            submitted_at=timezone.now(),
            attempt_number=last_num + 1,
        )
        if upload:
            sub.file = upload
            sub.save(update_fields=["file"])

        return Response(SubmissionSerializer(sub).data, status=status.HTTP_201_CREATED)


class AssignmentDetailView(APIView):
    def get(self, request, pk):
        assignment = get_object_or_404(Assignment.objects.select_related("lesson__module__course"), pk=pk)
        course = assignment.lesson.module.course
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        enrolled = Enrollment.objects.filter(
            user=request.user,
            course=course,
            status=EnrollmentStatus.ACTIVE,
        ).exists()
        if not (enrolled or is_course_staff(request.user, course)):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        allowed = assignment.submission_types or ["text"]
        return Response(
            {
                "id": assignment.id,
                "lesson_id": assignment.lesson_id,
                "instructions": assignment.instructions,
                "max_points": str(assignment.max_points),
                "submission_types": allowed,
                "max_file_size_mb": assignment.max_file_size_mb,
                "allowed_extensions": assignment.allowed_extensions,
                "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
            }
        )


class GradingQueueView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        staff_courses = _staff_course_filter(request.user)
        qs = (
            Submission.objects.filter(
                status=SubmissionStatus.SUBMITTED,
                assignment__lesson__module__course__in=staff_courses,
            )
            .select_related("enrollment__user", "assignment__lesson__module__course")
            .order_by("submitted_at", "id")
        )
        course_slug = request.query_params.get("course")
        if course_slug:
            qs = qs.filter(assignment__lesson__module__course__slug=course_slug)
        return Response({"submissions": SubmissionSerializer(qs[:200], many=True).data})


class GradeSubmissionView(APIView):
    def patch(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        sub = get_object_or_404(
            Submission.objects.select_related("assignment__lesson__module__course", "enrollment"),
            pk=pk,
        )
        course = sub.assignment.lesson.module.course
        if not is_course_staff(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if sub.status not in (SubmissionStatus.SUBMITTED, SubmissionStatus.RETURNED_FOR_REVISION):
            return Response({"detail": "Submission is not awaiting a grade."}, status=status.HTTP_400_BAD_REQUEST)

        score = request.data.get("score")
        feedback = request.data.get("grader_feedback", "")
        if score is None:
            return Response({"detail": "score is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from decimal import Decimal

            score_dec = Decimal(str(score))
        except Exception:
            return Response({"detail": "Invalid score."}, status=status.HTTP_400_BAD_REQUEST)

        sub.score = score_dec
        sub.grader_feedback = feedback or ""
        sub.graded_by = request.user
        sub.graded_at = timezone.now()
        sub.status = SubmissionStatus.GRADED
        sub.save(
            update_fields=["score", "grader_feedback", "graded_by", "graded_at", "status"],
        )
        sync_assessment_lesson_progress(sub.enrollment, sub.assignment.lesson)
        sync_submission_to_gradebook(sub)
        return Response(SubmissionSerializer(sub).data)
