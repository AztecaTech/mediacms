from django.utils.html import strip_tags
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from learning.models import (
    Announcement,
    Discussion,
    DiscussionNotificationFrequency,
    DiscussionNotificationPreference,
    DiscussionPost,
    Notification,
)


def _display_user(u):
    if not u:
        return ""
    name = u.get_full_name() if hasattr(u, "get_full_name") else ""
    return (name or "").strip() or getattr(u, "username", str(u.pk))


class DiscussionListSerializer(serializers.ModelSerializer):
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = Discussion
        fields = (
            "id",
            "course",
            "lesson",
            "title",
            "created_by",
            "created_by_display",
            "created_at",
            "is_pinned",
            "is_locked",
            "reply_count",
            "last_activity_at",
        )
        read_only_fields = (
            "id",
            "course",
            "created_by",
            "created_at",
            "reply_count",
            "last_activity_at",
            "created_by_display",
        )

    def get_created_by_display(self, obj):
        return _display_user(obj.created_by) if obj.created_by_id else ""


class DiscussionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discussion
        fields = ("title", "lesson", "is_pinned", "is_locked")
        extra_kwargs = {"lesson": {"required": False, "allow_null": True}}

    def validate(self, data):
        lesson = data.get("lesson")
        course = self.context.get("course")
        if lesson is not None and course is not None and lesson.module.course_id != course.id:
            raise ValidationError({"lesson": "Lesson does not belong to this course."})
        return data


class DiscussionStaffPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discussion
        fields = ("is_pinned", "is_locked")


class AnnouncementSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            "id",
            "course",
            "author",
            "author_display",
            "title",
            "body",
            "published_at",
            "is_pinned",
            "send_email",
        )
        read_only_fields = ("id", "course", "author", "published_at", "author_display")

    def get_author_display(self, obj):
        return _display_user(obj.author)

    def validate_body(self, value):
        return strip_tags(value or "")[:50000]

    def validate_title(self, value):
        return (value or "").strip()[:255]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "type",
            "title",
            "body",
            "url",
            "related_object_type",
            "related_object_id",
            "read_at",
            "created_at",
            "email_sent",
        )
        read_only_fields = ("id", "type", "title", "body", "url", "related_object_type", "related_object_id", "created_at", "email_sent")


class DiscussionPostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionPost
        fields = ("parent", "body", "is_instructor_answer")
        extra_kwargs = {"parent": {"required": False, "allow_null": True}}

    def validate_body(self, value):
        return strip_tags(value or "")[:10000]

    def validate(self, data):
        discussion = self.context.get("discussion")
        parent = data.get("parent")
        if parent is not None and parent.discussion_id != discussion.id:
            raise ValidationError({"parent": "Parent post belongs to another thread."})
        if discussion.is_locked:
            user = self.context.get("request").user
            course = discussion.course
            from learning.permissions import is_course_staff

            if not is_course_staff(user, course):
                raise ValidationError("This discussion is locked.")
        return data


class DiscussionNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionNotificationPreference
        fields = ("email_replies", "email_mentions", "email_calendar", "frequency")

    def validate_frequency(self, value):
        valid = {choice[0] for choice in DiscussionNotificationFrequency.choices}
        if value not in valid:
            raise ValidationError("Invalid frequency.")
        return value
