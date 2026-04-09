from rest_framework import serializers

from learning.models import Course, LearningPath, LearningPathCourse, LessonDraft
from learning.serializers.core import CourseListSerializer


class LearningPathCourseSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        source="course",
        write_only=True,
    )

    class Meta:
        model = LearningPathCourse
        fields = ("id", "path", "course", "course_id", "order", "is_required")


class LearningPathSerializer(serializers.ModelSerializer):
    path_courses = LearningPathCourseSerializer(many=True, read_only=True)

    class Meta:
        model = LearningPath
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "thumbnail",
            "status",
            "created_at",
            "updated_at",
            "path_courses",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class LessonDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonDraft
        fields = ("id", "lesson", "author", "content_snapshot", "updated_at")
        read_only_fields = ("id", "author", "updated_at")

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        return LessonDraft.objects.create(author=user, **validated_data)
