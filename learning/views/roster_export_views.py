"""Instructor roster CSV export (bulk integration helper)."""

import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from learning.models import Course, Enrollment
from learning.permissions import is_course_instructor


class CourseRosterCsvExportView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return HttpResponse("Forbidden", status=403, content_type="text/plain")
        qs = (
            Enrollment.objects.filter(course=course)
            .select_related("user")
            .order_by("role", "user__username", "id")
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{course.slug}_roster.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "enrollment_id",
                "username",
                "email",
                "name",
                "role",
                "status",
                "progress_pct",
                "current_grade_pct",
                "current_grade_letter",
                "enrolled_at",
            ]
        )
        for enr in qs:
            u = enr.user
            email = getattr(u, "email", "") or ""
            name = getattr(u, "name", None) or (u.get_full_name() if hasattr(u, "get_full_name") else "") or ""
            writer.writerow(
                [
                    enr.id,
                    getattr(u, "username", ""),
                    email,
                    name,
                    enr.role,
                    enr.status,
                    str(enr.progress_pct),
                    str(enr.current_grade_pct) if enr.current_grade_pct is not None else "",
                    enr.current_grade_letter or "",
                    enr.enrolled_at.isoformat() if enr.enrolled_at else "",
                ]
            )
        return response
