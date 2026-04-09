"""Student-facing credentials and transcript endpoints."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.models import BadgeAward, Certificate, Enrollment, EnrollmentStatus


class MyCertificatesView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        qs = (
            Certificate.objects.filter(enrollment__user=request.user)
            .select_related("enrollment__course")
            .order_by("-issued_at")
        )
        rows = [
            {
                "id": cert.id,
                "course_slug": cert.enrollment.course.slug,
                "course_title": cert.enrollment.course.title,
                "verification_code": cert.verification_code,
                "issued_at": cert.issued_at.isoformat(),
                "revoked_at": cert.revoked_at.isoformat() if cert.revoked_at else None,
                "pdf_url": cert.pdf_file.url if cert.pdf_file else "",
            }
            for cert in qs
        ]
        return Response({"certificates": rows})


class MyBadgesView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        qs = BadgeAward.objects.filter(user=request.user).select_related("badge").order_by("-awarded_at")
        rows = [
            {
                "id": ba.id,
                "badge_slug": ba.badge.slug,
                "badge_name": ba.badge.name,
                "badge_description": ba.badge.description or "",
                "awarded_at": ba.awarded_at.isoformat(),
            }
            for ba in qs
        ]
        return Response({"badges": rows})


class MyTranscriptView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        qs = (
            Enrollment.objects.filter(user=request.user, status__in=[EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED])
            .select_related("course")
            .order_by("-enrolled_at", "-id")
        )
        rows = [
            {
                "enrollment_id": enr.id,
                "course_slug": enr.course.slug,
                "course_title": enr.course.title,
                "status": enr.status,
                "progress_pct": str(enr.progress_pct),
                "current_grade_pct": str(enr.current_grade_pct) if enr.current_grade_pct is not None else None,
                "current_grade_letter": enr.current_grade_letter or "",
                "completed_at": enr.completed_at.isoformat() if enr.completed_at else None,
            }
            for enr in qs
        ]
        return Response({"transcript": rows})
