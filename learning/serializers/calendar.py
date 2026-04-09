from rest_framework import serializers

from learning.models import CalendarEvent


class CalendarEventSerializer(serializers.ModelSerializer):
    course_slug = serializers.SlugField(source="course.slug", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = CalendarEvent
        fields = (
            "id",
            "course_slug",
            "course_title",
            "title",
            "description",
            "event_type",
            "starts_at",
            "ends_at",
            "source_type",
            "source_id",
            "url",
        )
