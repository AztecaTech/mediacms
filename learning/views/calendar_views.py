"""Course and cross-enrollment calendar API."""

from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_tz
from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.calendar_sync import calendar_events_in_range
from learning.models import CalendarEvent, Course, Enrollment, EnrollmentStatus
from learning.permissions import is_active_course_member
from learning.serializers.calendar import CalendarEventSerializer


def _parse_range_dt(value):
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is None:
        return None
    if dj_tz.is_naive(dt):
        return dj_tz.make_aware(dt, dj_tz.get_current_timezone())
    return dt


class CourseCalendarView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_active_course_member(request.user, course):
            return Response({"detail": "Forbidden"}, status=403)
        from_dt = _parse_range_dt(request.query_params.get("from"))
        to_dt = _parse_range_dt(request.query_params.get("to"))
        qs = CalendarEvent.objects.filter(course=course).select_related("course")
        qs = calendar_events_in_range(qs, from_dt, to_dt).order_by("starts_at", "id")
        return Response({"events": CalendarEventSerializer(qs[:500], many=True).data})


class MyCalendarView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Forbidden"}, status=403)
        from_dt = _parse_range_dt(request.query_params.get("from"))
        to_dt = _parse_range_dt(request.query_params.get("to"))
        course_ids = Enrollment.objects.filter(
            user=request.user,
            status=EnrollmentStatus.ACTIVE,
        ).values_list("course_id", flat=True)
        qs = CalendarEvent.objects.filter(course_id__in=course_ids).select_related("course")
        qs = calendar_events_in_range(qs, from_dt, to_dt).order_by("starts_at", "id")
        return Response({"events": CalendarEventSerializer(qs[:1000], many=True).data})
