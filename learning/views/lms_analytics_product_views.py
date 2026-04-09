"""Extended LMS analytics endpoints (funnel, heatmap, exports) — incremental product layer."""

import csv
from datetime import timedelta
from io import StringIO

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.models import (
    Course,
    CourseMetricsDaily,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
    LessonMetrics,
    StudentRiskScore,
)
from learning.permissions import is_course_instructor


class _CourseStaffMixin:
    def _course(self, slug):
        return get_object_or_404(Course, slug=slug)

    def _guard(self, request, course):
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=403)
        return None


class CourseAnalyticsFunnelView(APIView, _CourseStaffMixin):
    def get(self, request, slug):
        course = self._course(slug)
        err = self._guard(request, course)
        if err:
            return err
        active_students = Enrollment.objects.filter(
            course=course,
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        ).count()
        return Response(
            {
                "stages": [
                    {"id": "enrolled", "label": "Enrolled", "count": course.enrolled_count},
                    {"id": "active", "label": "Active learners", "count": active_students},
                ],
                "metrics_populated": LessonMetrics.objects.filter(lesson__module__course=course).exists(),
            }
        )


class CourseAnalyticsEngagementHeatmapView(APIView, _CourseStaffMixin):
    def get(self, request, slug):
        course = self._course(slug)
        err = self._guard(request, course)
        if err:
            return err
        return Response({"cells": [], "granularity": "week_hour", "note": "Populate from AnalyticsEvent rollups."})


class CourseAnalyticsDropOffView(APIView, _CourseStaffMixin):
    def get(self, request, slug):
        course = self._course(slug)
        err = self._guard(request, course)
        if err:
            return err
        rows = (
            LessonMetrics.objects.filter(lesson__module__course=course)
            .select_related("lesson")
            .order_by("-drop_off_after_seconds")[:25]
        )
        return Response(
            {
                "lessons": [
                    {
                        "lesson_id": m.lesson_id,
                        "title": m.lesson.title,
                        "drop_off_after_seconds": m.drop_off_after_seconds,
                        "completed_count": m.completed_count,
                    }
                    for m in rows
                ]
            }
        )


class CourseAnalyticsTimeInContentView(APIView, _CourseStaffMixin):
    def get(self, request, slug):
        course = self._course(slug)
        err = self._guard(request, course)
        if err:
            return err
        rows = (
            LessonMetrics.objects.filter(lesson__module__course=course, avg_time_seconds__gt=0)
            .select_related("lesson")
            .order_by("-avg_time_seconds")[:40]
        )
        return Response(
            {
                "avg_minutes_by_lesson": [
                    {
                        "lesson_id": m.lesson_id,
                        "title": m.lesson.title,
                        "avg_minutes": round(m.avg_time_seconds / 60, 2),
                    }
                    for m in rows
                ]
            }
        )


class CourseAnalyticsAtRiskStudentsView(APIView, _CourseStaffMixin):
    def get(self, request, slug):
        course = self._course(slug)
        err = self._guard(request, course)
        if err:
            return err
        qs = (
            Enrollment.objects.filter(
                course=course,
                role=EnrollmentRole.STUDENT,
                status=EnrollmentStatus.ACTIVE,
            )
            .select_related("user")
            .order_by("user__username")
        )
        risk_by_enr = {
            row.enrollment_id: row
            for row in StudentRiskScore.objects.filter(enrollment__in=qs).select_related("enrollment")
        }
        enrollments = []
        for e in qs:
            rs = risk_by_enr.get(e.id)
            disp = e.user.get_full_name() if hasattr(e.user, "get_full_name") else ""
            enrollments.append(
                {
                    "enrollment_id": e.id,
                    "username": e.user.username,
                    "name": (disp or "").strip(),
                    "progress_pct": str(e.progress_pct),
                    "current_grade_pct": str(e.current_grade_pct) if e.current_grade_pct is not None else None,
                    "risk_tier": rs.tier if rs else None,
                    "risk_score": str(rs.score) if rs else None,
                    "risk_factors": rs.factors if rs else {},
                }
            )
        return Response({"enrollments": enrollments})


class OrgEnrollmentTrendView(APIView):
    def get(self, request):
        if not request.user.is_authenticated or not getattr(request.user, "is_manager", False):
            return Response({"detail": "Forbidden"}, status=403)
        days = int(request.query_params.get("days") or 180)
        days = max(7, min(days, 730))
        since = timezone.now().date() - timedelta(days=days)
        rows = (
            CourseMetricsDaily.objects.filter(date__gte=since)
            .values("date")
            .annotate(enrollments_new=Sum("enrollments_new"))
            .order_by("date")
        )
        return Response(
            {
                "points": [
                    {"date": str(r["date"]), "enrollments_new": r["enrollments_new"] or 0}
                    for r in rows
                ]
            }
        )


class OrgCompletionTrendView(APIView):
    def get(self, request):
        if not request.user.is_authenticated or not getattr(request.user, "is_manager", False):
            return Response({"detail": "Forbidden"}, status=403)
        days = int(request.query_params.get("days") or 180)
        days = max(7, min(days, 730))
        since = timezone.now().date() - timedelta(days=days)
        rows = (
            CourseMetricsDaily.objects.filter(date__gte=since)
            .values("date")
            .annotate(completions_new=Sum("completions_new"))
            .order_by("date")
        )
        return Response(
            {
                "points": [
                    {"date": str(r["date"]), "completions_new": r["completions_new"] or 0}
                    for r in rows
                ]
            }
        )


class OrgAnalyticsExportCsvView(APIView):
    def get(self, request):
        if not request.user.is_authenticated or not getattr(request.user, "is_manager", False):
            return Response({"detail": "Forbidden"}, status=403)
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["course_slug", "metric", "value"])
        for c in Course.objects.filter(status="published").order_by("slug")[:500]:
            w.writerow([c.slug, "enrolled_count", c.enrolled_count])
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="org_learning_summary.csv"'
        return resp
