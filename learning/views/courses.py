from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.events import emit_event
from learning.methods import can_self_enroll, refresh_course_enrolled_count
from learning.models import (
    Course,
    CourseAuditAction,
    CourseMode,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
)
from learning.permissions import (
    IsCourseEditorOrReadOnly,
    get_active_enrollment,
    is_course_instructor,
)
from learning.serializers import (
    CourseDetailSerializer,
    CourseListSerializer,
    CourseWriteSerializer,
    EnrollmentSerializer,
    RosterEnrollmentSerializer,
)
from learning.signals import write_audit


class CourseListCreateView(APIView):
    permission_classes = [IsCourseEditorOrReadOnly]

    def get(self, request):
        qs = Course.objects.all().select_related("category").order_by("-updated_at")
        show_all = request.user.is_authenticated and (
            request.user.is_superuser or getattr(request.user, "is_editor", False)
        )
        if not show_all:
            qs = qs.filter(status="published")
        mode = request.query_params.get("mode")
        if mode:
            qs = qs.filter(mode=mode)
        lang = request.query_params.get("language")
        if lang:
            qs = qs.filter(language=lang)
        diff = request.query_params.get("difficulty")
        if diff:
            qs = qs.filter(difficulty=diff)
        cat = request.query_params.get("category")
        if cat:
            qs = qs.filter(category_id=cat)
        return Response(CourseListSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request):
        ser = CourseWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        course = ser.save()
        return Response(CourseListSerializer(course, context={"request": request}).data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    permission_classes = [IsCourseEditorOrReadOnly]

    def get_course(self, slug):
        return get_object_or_404(Course, slug=slug)

    def get(self, request, slug):
        course = self.get_course(slug)
        if course.status != "published" and not is_course_instructor(request.user, course):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        enrollment = None
        if request.user.is_authenticated:
            enrollment = get_active_enrollment(request.user, course)
        hide = enrollment is None and not is_course_instructor(request.user, course)
        ctx = {"request": request, "enrollment": enrollment, "hide_lesson_content": hide}
        return Response(CourseDetailSerializer(course, context=ctx).data)

    def patch(self, request, slug):
        course = self.get_course(slug)
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = CourseWriteSerializer(course, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        enrollment = get_active_enrollment(request.user, course) if request.user.is_authenticated else None
        hide = enrollment is None and not is_course_instructor(request.user, course)
        return Response(
            CourseDetailSerializer(
                course,
                context={"request": request, "enrollment": enrollment, "hide_lesson_content": hide},
            ).data
        )

    def delete(self, request, slug):
        course = self.get_course(slug)
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        course.status = "archived"
        course.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class EnrollView(APIView):
    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        course = get_object_or_404(Course, slug=slug)
        cohort_id = request.data.get("cohort_id")
        cohort = None
        if course.mode == CourseMode.COHORT:
            if not cohort_id:
                return Response({"detail": "cohort_id required for cohort courses."}, status=status.HTTP_400_BAD_REQUEST)
            from learning.models import Cohort

            cohort = get_object_or_404(Cohort, pk=cohort_id, course=course)
            if cohort.capacity is not None:
                n = Enrollment.objects.filter(cohort=cohort, status=EnrollmentStatus.ACTIVE).count()
                if n >= cohort.capacity:
                    return Response({"detail": "Cohort is full."}, status=status.HTTP_400_BAD_REQUEST)

        ok, reason = can_self_enroll(request.user, course)
        if not ok:
            if reason == "missing_prerequisites":
                from learning.methods import missing_prerequisites

                miss = missing_prerequisites(request.user, course)
                return Response(
                    {
                        "detail": "Prerequisites not satisfied.",
                        "missing_prerequisite_slugs": [c.slug for c in miss],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response({"detail": reason or "Cannot enroll."}, status=status.HTTP_400_BAD_REQUEST)

        enr, created = Enrollment.objects.get_or_create(
            user=request.user,
            course=course,
            cohort=cohort,
            defaults={"role": EnrollmentRole.STUDENT, "status": EnrollmentStatus.ACTIVE},
        )
        if not created:
            if enr.status == EnrollmentStatus.WITHDRAWN:
                enr.status = EnrollmentStatus.ACTIVE
                enr.save(update_fields=["status"])
                write_audit(request.user, course, CourseAuditAction.RE_ENROLLED)
                emit_event("enrollment_reactivated", user=request.user, course=course)
            return Response(EnrollmentSerializer(enr).data, status=status.HTTP_200_OK)

        write_audit(request.user, course, CourseAuditAction.ENROLLED)
        refresh_course_enrolled_count(course)
        emit_event("enrollment_created", user=request.user, course=course)
        return Response(EnrollmentSerializer(enr).data, status=status.HTTP_201_CREATED)


class WithdrawView(APIView):
    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        course = get_object_or_404(Course, slug=slug)
        cohort_id = request.data.get("cohort_id")
        cohort = None
        if cohort_id:
            from learning.models import Cohort

            cohort = get_object_or_404(Cohort, pk=cohort_id, course=course)
        enr = get_active_enrollment(request.user, course, cohort)
        if not enr:
            return Response({"detail": "Not enrolled."}, status=status.HTTP_400_BAD_REQUEST)
        enr.status = EnrollmentStatus.WITHDRAWN
        enr.save(update_fields=["status"])
        write_audit(request.user, course, CourseAuditAction.WITHDREW)
        refresh_course_enrolled_count(course)
        return Response(EnrollmentSerializer(enr).data)


class CourseRosterView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        qs = (
            Enrollment.objects.filter(course=course)
            .select_related("user")
            .order_by("-enrolled_at")
        )
        return Response(RosterEnrollmentSerializer(qs, many=True).data)


class MyEnrollmentsListView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        qs = Enrollment.objects.filter(user=request.user).select_related("course").order_by("-enrolled_at")
        return Response(EnrollmentSerializer(qs, many=True).data)
