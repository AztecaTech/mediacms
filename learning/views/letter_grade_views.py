from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.models import Course, LetterGradeScheme
from learning.permissions import is_course_instructor
from learning.serializers.letter_grades import LetterGradeSchemeSerializer


class CourseLetterGradeSchemeView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        scheme = (
            LetterGradeScheme.objects.filter(course=course).order_by("id").first()
            or LetterGradeScheme(name=f"{course.title} default", course=course, bands=[])
        )
        return Response(LetterGradeSchemeSerializer(scheme).data)

    def put(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        scheme = LetterGradeScheme.objects.filter(course=course).order_by("id").first()
        if not scheme:
            scheme = LetterGradeScheme(course=course)
        ser = LetterGradeSchemeSerializer(instance=scheme, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(course=course)
        return Response(ser.data)
