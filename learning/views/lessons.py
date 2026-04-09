from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods import (
    apply_lesson_progress_heartbeat,
    is_lesson_locked_for_enrollment,
    lesson_prerequisites_satisfied,
    mark_nonvideo_lesson_complete,
)
from learning.models import Lesson, LessonContentType
from learning.permissions import get_active_enrollment, is_course_instructor
from learning.serializers import LessonSerializer, LessonWriteSerializer


class ModuleLessonsListCreateView(APIView):
    def get(self, request, pk):
        from learning.models import Module

        mod = get_object_or_404(Module, pk=pk)
        course = mod.course
        if course.status != "published" and not is_course_instructor(request.user, course):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        enrollment = (
            get_active_enrollment(request.user, course) if request.user.is_authenticated else None
        )
        hide = enrollment is None and not is_course_instructor(request.user, course)
        qs = mod.lessons.all().order_by("order", "id")
        return Response(
            LessonSerializer(
                qs,
                many=True,
                context={"request": request, "enrollment": enrollment, "hide_lesson_content": hide},
            ).data
        )

    def post(self, request, pk):
        from learning.models import Module

        mod = get_object_or_404(Module, pk=pk)
        if not is_course_instructor(request.user, mod.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        data = {**request.data, "module": mod.id}
        ser = LessonWriteSerializer(data=data)
        ser.is_valid(raise_exception=True)
        lesson = ser.save()
        return Response(LessonWriteSerializer(lesson).data, status=status.HTTP_201_CREATED)


class LessonDetailView(APIView):
    def get(self, request, pk):
        lesson = get_object_or_404(Lesson.objects.select_related("module__course", "media"), pk=pk)
        course = lesson.module.course
        if not is_course_instructor(request.user, course):
            enr = get_active_enrollment(request.user, course) if request.user.is_authenticated else None
            if not enr:
                return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        enrollment = (
            get_active_enrollment(request.user, course) if request.user.is_authenticated else None
        )
        hide = enrollment is None and not is_course_instructor(request.user, course)
        return Response(
            LessonSerializer(
                lesson,
                context={"request": request, "enrollment": enrollment, "hide_lesson_content": hide},
            ).data
        )

    def patch(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        if not is_course_instructor(request.user, lesson.module.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = LessonWriteSerializer(lesson, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        lesson = ser.save()
        return Response(LessonWriteSerializer(lesson).data)

    def delete(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        if not is_course_instructor(request.user, lesson.module.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        lesson.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LessonProgressPostView(APIView):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        lesson = get_object_or_404(Lesson, pk=pk)
        course = lesson.module.course
        enrollment = get_active_enrollment(request.user, course)
        if not enrollment:
            return Response({"detail": "Not enrolled."}, status=status.HTTP_403_FORBIDDEN)
        if is_lesson_locked_for_enrollment(lesson, enrollment) or not lesson_prerequisites_satisfied(
            lesson, enrollment
        ):
            return Response({"detail": "Lesson is locked."}, status=status.HTTP_403_FORBIDDEN)
        if lesson.content_type != LessonContentType.VIDEO:
            mark_nonvideo_lesson_complete(enrollment, lesson)
            from learning.models import LessonProgress

            lp = LessonProgress.objects.get(enrollment=enrollment, lesson=lesson)
            from learning.serializers import LessonProgressSerializer

            return Response(LessonProgressSerializer(lp).data)

        pos = int(request.data.get("position_seconds") or 0)
        dur = int(request.data.get("duration_seconds") or 0)
        if dur <= 0:
            return Response({"detail": "duration_seconds required"}, status=status.HTTP_400_BAD_REQUEST)
        lp = apply_lesson_progress_heartbeat(enrollment, lesson, pos, dur)
        from learning.serializers import LessonProgressSerializer

        return Response(LessonProgressSerializer(lp).data)
