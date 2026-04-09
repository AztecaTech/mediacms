from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.models import Course, Module
from learning.permissions import is_course_instructor
from learning.serializers import ModuleSerializer, ModuleWriteSerializer


class CourseModulesListCreateView(APIView):
    def get_course(self, slug):
        return get_object_or_404(Course, slug=slug)

    def get(self, request, slug):
        course = self.get_course(slug)
        if course.status != "published" and not is_course_instructor(request.user, course):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        from learning.permissions import get_active_enrollment

        enrollment = (
            get_active_enrollment(request.user, course) if request.user.is_authenticated else None
        )
        hide = enrollment is None and not is_course_instructor(request.user, course)
        qs = course.modules.all().order_by("order", "id")
        return Response(
            ModuleSerializer(
                qs,
                many=True,
                context={"request": request, "enrollment": enrollment, "hide_lesson_content": hide},
            ).data
        )

    def post(self, request, slug):
        course = self.get_course(slug)
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        data = {**request.data, "course": course.id}
        ser = ModuleWriteSerializer(data=data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class ModuleDetailView(APIView):
    def get_object(self, pk):
        return get_object_or_404(Module, pk=pk)

    def get(self, request, pk):
        mod = self.get_object(pk)
        course = mod.course
        if course.status != "published" and not is_course_instructor(request.user, course):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        from learning.permissions import get_active_enrollment

        enrollment = (
            get_active_enrollment(request.user, course) if request.user.is_authenticated else None
        )
        hide = enrollment is None and not is_course_instructor(request.user, course)
        return Response(
            ModuleSerializer(
                mod,
                context={"request": request, "enrollment": enrollment, "hide_lesson_content": hide},
            ).data
        )

    def patch(self, request, pk):
        mod = self.get_object(pk)
        if not is_course_instructor(request.user, mod.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = ModuleWriteSerializer(mod, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        mod = self.get_object(pk)
        if not is_course_instructor(request.user, mod.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        mod.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
