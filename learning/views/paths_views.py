from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.models import Course, LearningPath, Lesson, LessonDraft
from learning.permissions import get_active_enrollment, is_course_instructor
from learning.serializers.core import CourseDetailSerializer
from learning.serializers.paths import LearningPathSerializer, LessonDraftSerializer


class LearningPathListCreateView(APIView):
    def get(self, request):
        qs = (
            LearningPath.objects.filter(status="published")
            .order_by("title")
            .prefetch_related("path_courses__course")
        )
        return Response(LearningPathSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request):
        if not request.user.is_authenticated or not (
            request.user.is_superuser or getattr(request.user, "is_editor", False)
        ):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = LearningPathSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class LearningPathDetailView(APIView):
    def get(self, request, slug):
        path = get_object_or_404(
            LearningPath.objects.prefetch_related("path_courses__course"),
            slug=slug,
        )
        if path.status != "published" and not (
            request.user.is_authenticated
            and (request.user.is_superuser or getattr(request.user, "is_editor", False))
        ):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LearningPathSerializer(path, context={"request": request}).data)


class CourseAuthoringView(APIView):
    """Instructor-only aggregated authoring payload (Phase 2 foundation)."""

    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        enrollment = get_active_enrollment(request.user, course) if request.user.is_authenticated else None
        hide = enrollment is None and not is_course_instructor(request.user, course)
        ctx = {"request": request, "enrollment": enrollment, "hide_lesson_content": hide}
        drafts = LessonDraft.objects.filter(lesson__module__course=course).select_related("lesson", "author")
        return Response(
            {
                "course": CourseDetailSerializer(course, context=ctx).data,
                "drafts": LessonDraftSerializer(drafts, many=True).data,
            }
        )


class LessonDraftListCreateView(APIView):
    def post(self, request, pk):
        lesson = get_object_or_404(Lesson.objects.select_related("module__course"), pk=pk)
        course = lesson.module.course
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = LessonDraftSerializer(
            data={**request.data, "lesson": lesson.id},
            context={"request": request},
        )
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)
