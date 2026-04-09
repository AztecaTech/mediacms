from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.models import Cohort, Course
from learning.permissions import is_course_instructor
from learning.serializers import CohortSerializer


class CohortListCreateView(APIView):
    def get(self, request):
        qs = Cohort.objects.select_related("course").order_by("-start_date")
        course_slug = request.query_params.get("course")
        if course_slug:
            qs = qs.filter(course__slug=course_slug)
        if not request.user.is_authenticated or not (
            request.user.is_superuser or getattr(request.user, "is_editor", False)
        ):
            qs = qs.filter(course__status="published")
        return Response(CohortSerializer(qs, many=True).data)

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        course_id = request.data.get("course")
        course = get_object_or_404(Course, pk=course_id)
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = CohortSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class CohortDetailView(APIView):
    def get(self, request, pk):
        cohort = get_object_or_404(Cohort.objects.select_related("course"), pk=pk)
        if cohort.course.status != "published" and not is_course_instructor(request.user, cohort.course):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CohortSerializer(cohort).data)

    def patch(self, request, pk):
        cohort = get_object_or_404(Cohort, pk=pk)
        if not is_course_instructor(request.user, cohort.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = CohortSerializer(cohort, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        cohort = get_object_or_404(Cohort, pk=pk)
        if not is_course_instructor(request.user, cohort.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        cohort.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
