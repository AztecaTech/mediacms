from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.events import emit_event
from learning.methods.gradebook_bulk_cell_upsert import GradebookBulkCellUpsertManager
from learning.models import Course
from learning.permissions import is_course_instructor


class CourseGradebookCellsBulkUpsertView(APIView):
    """Instructor endpoint: apply many matrix cell updates in one request."""

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        manager = GradebookBulkCellUpsertManager(course, request.user)
        payload = manager.apply(request.data.get("cells") or [])
        if payload["results"]:
            emit_event(
                "gradebook_cells_bulk_upserted",
                user=request.user,
                course=course,
                metadata={"count": len(payload["results"])},
            )
        return Response(payload, status=status.HTTP_200_OK)


class CourseGradebookCellUpsertView(APIView):
    """Instructor endpoint for inline matrix grade editing (single cell; same logic as bulk)."""

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        manager = GradebookBulkCellUpsertManager(course, request.user)
        out = manager.apply(
            [
                {
                    "enrollment_id": request.data.get("enrollment_id"),
                    "grade_item_id": request.data.get("grade_item_id"),
                    "points_earned": request.data.get("points_earned"),
                    "feedback": request.data.get("feedback"),
                    "excused": request.data.get("excused", False),
                    "is_override": request.data.get("is_override", True),
                }
            ]
        )
        if out["errors"]:
            return Response({"detail": out["errors"][0]["detail"]}, status=status.HTTP_400_BAD_REQUEST)
        if not out["results"]:
            return Response({"detail": "Nothing to save."}, status=status.HTTP_400_BAD_REQUEST)
        row = out["results"][0]
        emit_event(
            "gradebook_cell_upserted",
            user=request.user,
            course=course,
            metadata={
                "grade_item_id": row["grade_item_id"],
                "grade_id": row["grade_id"],
                "enrollment_id": row["enrollment_id"],
            },
        )
        return Response(
            {
                "grade_id": row["grade_id"],
                "points_earned": row["points_earned"],
                "excused": row["excused"],
                "feedback": row["feedback"],
                "is_override": True,
            }
        )
