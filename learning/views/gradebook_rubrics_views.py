"""Rubric definition and scoring endpoints."""

from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.grade_aggregation import recalculate_enrollment_weighted_grade
from learning.methods.gradebook_sync import sync_submission_to_gradebook
from learning.models import Grade, GradeItem, Rubric, RubricCriterion, RubricScore, Submission, SubmissionStatus
from learning.permissions import is_course_staff
from learning.serializers.gradebook import RubricCriterionSerializer, RubricScoreSerializer, RubricSerializer


class CourseGradeItemRubricView(APIView):
    def get(self, request, slug, item_id):
        item = get_object_or_404(GradeItem.objects.select_related("category__course"), pk=item_id)
        if item.category.course.slug != slug:
            return Response({"detail": "Grade item not in course."}, status=status.HTTP_404_NOT_FOUND)
        if not is_course_staff(request.user, item.category.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        rubric = Rubric.objects.filter(grade_item=item).first()
        if not rubric:
            return Response({"rubric": None})
        return Response({"rubric": RubricSerializer(rubric).data})

    @transaction.atomic
    def put(self, request, slug, item_id):
        item = get_object_or_404(GradeItem.objects.select_related("category__course"), pk=item_id)
        if item.category.course.slug != slug:
            return Response({"detail": "Grade item not in course."}, status=status.HTTP_404_NOT_FOUND)
        if not is_course_staff(request.user, item.category.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        title = (request.data.get("title") or "").strip() or f"Rubric: {item.title}"
        description = request.data.get("description") or ""
        criteria = request.data.get("criteria") or []
        if not isinstance(criteria, list):
            return Response({"detail": "criteria must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        rubric, _ = Rubric.objects.get_or_create(
            grade_item=item,
            defaults={"title": title, "description": description},
        )
        rubric.title = title
        rubric.description = description
        rubric.save(update_fields=["title", "description"])

        existing = {c.id: c for c in rubric.criteria.all()}
        seen_ids = set()
        for i, row in enumerate(criteria):
            cid = row.get("id")
            payload = {
                "title": (row.get("title") or f"Criterion {i + 1}")[:255],
                "description": row.get("description") or "",
                "max_points": row.get("max_points") if row.get("max_points") is not None else Decimal("10"),
                "order": int(row.get("order") if row.get("order") is not None else i),
            }
            if cid and cid in existing:
                c = existing[cid]
                for k, v in payload.items():
                    setattr(c, k, v)
                c.save(update_fields=["title", "description", "max_points", "order"])
                seen_ids.add(c.id)
            else:
                c = RubricCriterion.objects.create(rubric=rubric, **payload)
                seen_ids.add(c.id)

        RubricCriterion.objects.filter(rubric=rubric).exclude(id__in=seen_ids).delete()
        rubric.refresh_from_db()
        return Response({"rubric": RubricSerializer(rubric).data})


class SubmissionRubricScoresView(APIView):
    def get(self, request, pk):
        sub = get_object_or_404(
            Submission.objects.select_related("assignment__lesson__module__course", "enrollment"),
            pk=pk,
        )
        course = sub.assignment.lesson.module.course
        if not is_course_staff(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        item = GradeItem.objects.filter(assignment=sub.assignment).first()
        if not item:
            return Response({"scores": [], "rubric": None})
        rubric = Rubric.objects.filter(grade_item=item).first()
        if not rubric:
            return Response({"scores": [], "rubric": None})
        grade = Grade.objects.filter(enrollment=sub.enrollment, grade_item=item).first()
        scores = RubricScore.objects.filter(grade=grade).select_related("criterion") if grade else []
        return Response(
            {
                "rubric": RubricSerializer(rubric).data,
                "scores": RubricScoreSerializer(scores, many=True).data,
            }
        )

    @transaction.atomic
    def post(self, request, pk):
        sub = get_object_or_404(
            Submission.objects.select_related("assignment__lesson__module__course", "enrollment"),
            pk=pk,
        )
        course = sub.assignment.lesson.module.course
        if not is_course_staff(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if sub.status != SubmissionStatus.GRADED:
            return Response({"detail": "Submission must be graded first."}, status=status.HTTP_400_BAD_REQUEST)

        sync_submission_to_gradebook(sub)
        item = GradeItem.objects.filter(assignment=sub.assignment).first()
        if not item:
            return Response({"detail": "No grade item for submission assignment."}, status=status.HTTP_400_BAD_REQUEST)
        rubric = Rubric.objects.filter(grade_item=item).first()
        if not rubric:
            return Response({"detail": "No rubric configured for this grade item."}, status=status.HTTP_400_BAD_REQUEST)
        grade = Grade.objects.filter(enrollment=sub.enrollment, grade_item=item).first()
        if not grade:
            return Response({"detail": "Grade row missing."}, status=status.HTTP_400_BAD_REQUEST)

        rows = request.data.get("scores") or []
        if not isinstance(rows, list):
            return Response({"detail": "scores must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        by_id = {c.id: c for c in rubric.criteria.all()}
        seen = set()
        total = Decimal("0")
        for row in rows:
            cid = row.get("criterion_id")
            if cid not in by_id:
                continue
            criterion = by_id[cid]
            points = Decimal(str(row.get("points_awarded") if row.get("points_awarded") is not None else "0"))
            if points < 0:
                points = Decimal("0")
            if points > criterion.max_points:
                points = criterion.max_points
            feedback = row.get("feedback") or ""
            RubricScore.objects.update_or_create(
                grade=grade,
                criterion=criterion,
                defaults={"points_awarded": points, "feedback": feedback},
            )
            seen.add(cid)
            total += points

        RubricScore.objects.filter(grade=grade).exclude(criterion_id__in=seen).delete()
        apply_total = bool(request.data.get("apply_total", True))
        if apply_total:
            grade.points_earned = total.quantize(Decimal("0.01"))
            grade.feedback = request.data.get("overall_feedback") or grade.feedback or ""
            grade.graded_by = request.user
            grade.save(update_fields=["points_earned", "feedback", "graded_by"])
            sub.score = grade.points_earned
            sub.grader_feedback = grade.feedback
            sub.save(update_fields=["score", "grader_feedback"])
            recalculate_enrollment_weighted_grade(sub.enrollment)

        out = RubricScore.objects.filter(grade=grade).select_related("criterion")
        return Response({"scores": RubricScoreSerializer(out, many=True).data})
