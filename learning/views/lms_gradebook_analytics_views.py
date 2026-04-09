"""Gradebook matrix, analytics summaries, public certificate verification."""

import csv
from datetime import timedelta

from django.db.models import Avg, Count, Prefetch, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.certificate_issuance import (
    CertificateEligibilityError,
    issue_certificate_for_enrollment,
    revoke_certificate,
)
from learning.methods.grade_aggregation import recalculate_course_weighted_grades
from learning.events import emit_event
from learning.models import (
    AnalyticsEvent,
    Certificate,
    Course,
    CourseMetricsDaily,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
    Grade,
    GradeCategory,
    GradeItem,
)
from learning.permissions import is_active_course_member, is_course_instructor


class CourseGradebookView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        categories = []
        for cat in GradeCategory.objects.filter(course=course).prefetch_related(
            Prefetch("items", queryset=GradeItem.objects.order_by("id"))
        ).order_by("order", "id"):
            items = []
            for it in cat.items.all():
                items.append(
                    {
                        "id": it.id,
                        "title": it.title,
                        "max_points": str(it.max_points),
                        "source_type": it.source_type,
                        "due_at": it.due_at.isoformat() if it.due_at else None,
                        "visible_to_students": it.visible_to_students,
                    }
                )
            categories.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "weight_pct": str(cat.weight_pct),
                    "drop_lowest_n": cat.drop_lowest_n,
                    "items": items,
                }
            )

        student_enrollments = Enrollment.objects.filter(
            course=course,
            status=EnrollmentStatus.ACTIVE,
            role=EnrollmentRole.STUDENT,
        ).select_related("user")

        item_ids = []
        for cat in categories:
            for it in cat["items"]:
                item_ids.append(it["id"])

        grades_map = {}
        if item_ids:
            for g in Grade.objects.filter(grade_item_id__in=item_ids).select_related("enrollment"):
                key = (g.enrollment_id, g.grade_item_id)
                grades_map[key] = {
                    "points_earned": str(g.points_earned) if g.points_earned is not None else None,
                    "excused": g.excused,
                    "feedback": g.feedback,
                }

        rows = []
        for enr in student_enrollments:
            cell = {}
            for iid in item_ids:
                cell[str(iid)] = grades_map.get((enr.id, iid))
            rows.append(
                {
                    "enrollment_id": enr.id,
                    "user_id": enr.user_id,
                    "username": getattr(enr.user, "username", str(enr.user_id)),
                    "current_grade_pct": str(enr.current_grade_pct) if enr.current_grade_pct is not None else None,
                    "current_grade_letter": enr.current_grade_letter or "",
                    "grades": cell,
                }
            )

        return Response({"categories": categories, "rows": rows})


class CourseMyGradesView(APIView):
    """Student (or any enrolled member) view of visible grade items and their scores."""

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_active_course_member(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        enr = (
            Enrollment.objects.filter(user=request.user, course=course, status=EnrollmentStatus.ACTIVE)
            .order_by("id")
            .first()
        )
        if not enr:
            return Response({"detail": "No active enrollment."}, status=status.HTTP_404_NOT_FOUND)

        categories_out = []
        for cat in (
            GradeCategory.objects.filter(course=course)
            .prefetch_related(Prefetch("items", queryset=GradeItem.objects.order_by("id")))
            .order_by("order", "id")
        ):
            items_out = []
            visible_items = [it for it in cat.items.all() if it.visible_to_students]
            if not visible_items:
                continue
            grade_by_item = {
                g.grade_item_id: g
                for g in Grade.objects.filter(enrollment=enr, grade_item__in=visible_items).select_related(
                    "grade_item"
                )
            }
            for it in visible_items:
                g = grade_by_item.get(it.id)
                items_out.append(
                    {
                        "id": it.id,
                        "title": it.title,
                        "max_points": str(it.max_points),
                        "source_type": it.source_type,
                        "points_earned": str(g.points_earned) if g and g.points_earned is not None else None,
                        "excused": g.excused if g else False,
                        "feedback": (g.feedback if g else "") or "",
                        "graded_at": g.graded_at.isoformat() if g and g.graded_at else None,
                    }
                )
            if items_out:
                categories_out.append(
                    {
                        "id": cat.id,
                        "name": cat.name,
                        "weight_pct": str(cat.weight_pct),
                        "items": items_out,
                    }
                )

        return Response(
            {
                "enrollment_id": enr.id,
                "current_grade_pct": str(enr.current_grade_pct) if enr.current_grade_pct is not None else None,
                "current_grade_letter": enr.current_grade_letter or "",
                "categories": categories_out,
            }
        )


class CourseGradebookExportView(APIView):
    """Instructor CSV export of the same matrix as ``CourseGradebookView``."""

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        cats = list(
            GradeCategory.objects.filter(course=course).prefetch_related(
                Prefetch("items", queryset=GradeItem.objects.order_by("id"))
            )
        )
        flat_items = []
        for cat in cats:
            for it in cat.items.all():
                flat_items.append((cat.name, it))

        student_enrollments = list(
            Enrollment.objects.filter(
                course=course,
                status=EnrollmentStatus.ACTIVE,
                role=EnrollmentRole.STUDENT,
            ).select_related("user")
        )

        item_ids = [it.id for _, it in flat_items]
        grades_map = {}
        if item_ids:
            for g in Grade.objects.filter(grade_item_id__in=item_ids).select_related("enrollment"):
                grades_map[(g.enrollment_id, g.grade_item_id)] = g

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{course.slug}_gradebook.csv"'

        writer = csv.writer(response)
        header = ["username", "user_id", "enrollment_id", "current_grade_pct", "current_grade_letter"]
        for cat_name, it in flat_items:
            header.append(f"{cat_name} / {it.title} (max {it.max_points})")
        writer.writerow(header)

        for enr in student_enrollments:
            row = [
                getattr(enr.user, "username", ""),
                enr.user_id,
                enr.id,
                str(enr.current_grade_pct) if enr.current_grade_pct is not None else "",
                enr.current_grade_letter or "",
            ]
            for _, it in flat_items:
                g = grades_map.get((enr.id, it.id))
                if g and g.excused:
                    row.append("excused")
                elif g and g.points_earned is not None:
                    row.append(str(g.points_earned))
                else:
                    row.append("")
            writer.writerow(row)

        return response


class CourseGradebookRecalculateView(APIView):
    """Instructor action to recompute weighted totals + letters for all student enrollments."""

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        processed = recalculate_course_weighted_grades(course)
        emit_event("gradebook_recalculated", user=request.user, course=course, metadata={"processed": processed})
        return Response({"processed_enrollments": processed})


class CourseAnalyticsSummaryView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        days = int(request.query_params.get("days") or 30)
        since = timezone.now() - timedelta(days=max(1, min(days, 365)))
        qs = AnalyticsEvent.objects.filter(course=course, timestamp__gte=since)
        by_type = list(qs.values("type").annotate(count=Count("id")).order_by("-count")[:50])
        total = qs.count()
        events_by_day = list(
            qs.annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        daily = list(
            CourseMetricsDaily.objects.filter(course=course, date__gte=since.date())
            .order_by("date")
            .values(
                "date",
                "enrollments_new",
                "enrollments_total",
                "completions_new",
                "completions_total",
                "avg_progress_pct",
                "active_students",
            )
        )
        return Response(
            {
                "period_days": days,
                "total_events": total,
                "by_type": by_type,
                "events_by_day": events_by_day,
                "daily_metrics": daily,
            }
        )


class OrgAnalyticsSummaryView(APIView):
    def get(self, request):
        if not request.user.is_authenticated or not getattr(request.user, "is_manager", False):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        days = int(request.query_params.get("days") or 30)
        since = timezone.now() - timedelta(days=max(1, min(days, 365)))
        qs = AnalyticsEvent.objects.filter(timestamp__gte=since)
        by_type = list(qs.values("type").annotate(count=Count("id")).order_by("-count")[:50])
        events_by_day = list(
            qs.annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        active_students = Enrollment.objects.filter(
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        )
        at_risk_students = active_students.filter(progress_pct__lt=25).count()
        top_courses = list(
            Course.objects.annotate(
                students_total=Count(
                    "enrollments",
                    filter=Q(
                        enrollments__role=EnrollmentRole.STUDENT,
                        enrollments__status__in=(EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED),
                    ),
                ),
                students_active=Count(
                    "enrollments",
                    filter=Q(
                        enrollments__role=EnrollmentRole.STUDENT,
                        enrollments__status=EnrollmentStatus.ACTIVE,
                    ),
                ),
                avg_progress=Avg(
                    "enrollments__progress_pct",
                    filter=Q(
                        enrollments__role=EnrollmentRole.STUDENT,
                        enrollments__status=EnrollmentStatus.ACTIVE,
                    ),
                ),
            )
            .order_by("-students_total", "id")
            .values("id", "slug", "title", "students_total", "students_active", "avg_progress")[:10]
        )
        return Response(
            {
                "period_days": days,
                "total_events": qs.count(),
                "by_type": by_type,
                "events_by_day": events_by_day,
                "students_active_total": active_students.count(),
                "students_at_risk_count": at_risk_students,
                "avg_active_progress_pct": str(
                    (active_students.aggregate(avg=Avg("progress_pct"))["avg"] or 0)
                ),
                "top_courses": top_courses,
            }
        )


class CertificateVerifyView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, code):
        cert = Certificate.objects.filter(verification_code=code).select_related("enrollment__user", "enrollment__course").first()
        if not cert:
            return Response({"valid": False, "detail": "Unknown code."})
        if cert.revoked_at:
            return Response(
                {
                    "valid": False,
                    "revoked": True,
                    "detail": cert.revoke_reason or "Revoked.",
                }
            )
        enr = cert.enrollment
        user = enr.user
        name = user.get_full_name() if hasattr(user, "get_full_name") else ""
        if not name.strip():
            name = getattr(user, "username", str(user.pk))
        return Response(
            {
                "valid": True,
                "issued_at": cert.issued_at.isoformat(),
                "course_title": enr.course.title,
                "course_slug": enr.course.slug,
                "recipient_display": name,
            }
        )


class CourseCertificatesListView(APIView):
    """Instructor endpoint: list certificates issued for enrollments in this course."""

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        qs = (
            Certificate.objects.filter(enrollment__course=course)
            .select_related("enrollment__user")
            .order_by("-issued_at")
        )
        rows = []
        for c in qs:
            u = c.enrollment.user
            disp = u.get_full_name() if hasattr(u, "get_full_name") else ""
            if not (disp or "").strip():
                disp = getattr(u, "username", str(u.pk))
            rows.append(
                {
                    "certificate_id": c.id,
                    "enrollment_id": c.enrollment_id,
                    "username": getattr(u, "username", str(u.pk)),
                    "recipient_display": disp.strip() or getattr(u, "username", str(u.pk)),
                    "issued_at": c.issued_at.isoformat(),
                    "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                    "revoke_reason": c.revoke_reason or "",
                    "verification_code": c.verification_code,
                    "has_pdf": bool(c.pdf_file),
                }
            )
        return Response({"certificates": rows})


class CourseCertificateIssueView(APIView):
    """Instructor endpoint: issue certificate for one enrollment in the course."""

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        enrollment_id = request.data.get("enrollment_id")
        if not enrollment_id:
            return Response({"detail": "enrollment_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        enrollment = get_object_or_404(
            Enrollment.objects.select_related("course", "user"),
            pk=enrollment_id,
            course=course,
        )
        try:
            cert = issue_certificate_for_enrollment(enrollment, issued_by=request.user)
        except CertificateEligibilityError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        emit_event(
            "certificate_issued",
            user=request.user,
            course=course,
            metadata={"certificate_id": cert.id, "enrollment_id": enrollment.id},
        )
        return Response(
            {
                "certificate_id": cert.id,
                "enrollment_id": enrollment.id,
                "verification_code": cert.verification_code,
                "issued_at": cert.issued_at.isoformat(),
                "revoked_at": cert.revoked_at.isoformat() if cert.revoked_at else None,
            },
            status=status.HTTP_200_OK,
        )


class CertificateRevokeView(APIView):
    """Instructor endpoint: revoke an existing certificate by id."""

    def post(self, request, pk):
        cert = get_object_or_404(
            Certificate.objects.select_related("enrollment__course"),
            pk=pk,
        )
        course = cert.enrollment.course
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get("reason", "")
        cert = revoke_certificate(cert, reason=reason, revoked_by=request.user)
        emit_event(
            "certificate_revoked",
            user=request.user,
            course=course,
            metadata={"certificate_id": cert.id},
        )
        return Response(
            {
                "certificate_id": cert.id,
                "revoked_at": cert.revoked_at.isoformat() if cert.revoked_at else None,
                "revoke_reason": cert.revoke_reason,
            }
        )


class CourseCertificateHealthView(APIView):
    """Instructor monitoring snapshot for certificate issuance health."""

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        qs = Certificate.objects.filter(enrollment__course=course)
        active = qs.filter(revoked_at__isnull=True)
        missing_pdf = active.filter(Q(pdf_file="") | Q(pdf_file__isnull=True)).count()
        recent_30d = qs.filter(issued_at__gte=timezone.now() - timedelta(days=30))
        recent_7d = qs.filter(issued_at__gte=timezone.now() - timedelta(days=7))
        return Response(
            {
                "course_slug": course.slug,
                "total_certificates": qs.count(),
                "active_certificates": active.count(),
                "revoked_certificates": qs.filter(revoked_at__isnull=False).count(),
                "active_missing_pdf_count": missing_pdf,
                "issued_last_30d": recent_30d.count(),
                "issued_last_7d": recent_7d.count(),
                "recent_30d_missing_pdf_count": recent_30d.filter(Q(pdf_file="") | Q(pdf_file__isnull=True)).count(),
            }
        )
