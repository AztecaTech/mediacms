from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from files.serializers import MediaSerializer
from learning.methods import (
    is_lesson_locked_for_enrollment,
    lesson_prerequisites_satisfied,
)
from learning.models import (
    Cohort,
    Course,
    Enrollment,
    Lesson,
    LessonContentType,
    LessonProgress,
    Module,
)

User = get_user_model()


class CohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohort
        fields = (
            "id",
            "course",
            "name",
            "start_date",
            "end_date",
            "capacity",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ModuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ("id", "course", "title", "description", "order", "release_offset_days")
        read_only_fields = ("id",)


class LessonWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = (
            "id",
            "module",
            "title",
            "description",
            "order",
            "content_type",
            "media",
            "text_body",
            "attachment",
            "external_url",
            "is_required",
            "estimated_minutes",
            "prerequisites",
        )
        read_only_fields = ("id",)

    def validate(self, data):
        ct = data.get("content_type") or getattr(self.instance, "content_type", None)
        media = data.get("media", getattr(self.instance, "media", None) if self.instance else None)
        if ct == LessonContentType.VIDEO and media is None:
            raise ValidationError({"media": "Required for video lessons."})
        prereqs = data.get("prerequisites")
        if prereqs is not None and self.instance:
            from learning.methods.lesson_prerequisite_validation import LessonPrerequisiteCycleGuard

            course_id = self.instance.module.course_id
            for p in prereqs:
                if p.module.course_id != course_id:
                    raise ValidationError(
                        {"prerequisites": "All prerequisites must belong to the same course as this lesson."}
                    )
            ids = [p.pk for p in prereqs]
            if LessonPrerequisiteCycleGuard.would_create_cycle(self.instance.pk, ids):
                raise ValidationError(
                    {"prerequisites": "This prerequisite set would create a cycle that includes this lesson."}
                )
        return data


class LessonSerializer(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField()
    prerequisite_locked = serializers.SerializerMethodField()
    prerequisite_ids = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    text_body = serializers.SerializerMethodField()
    external_url = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()
    quiz_id = serializers.SerializerMethodField()
    assignment_id = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "module",
            "title",
            "description",
            "order",
            "content_type",
            "media",
            "text_body",
            "external_url",
            "attachment_url",
            "is_required",
            "estimated_minutes",
            "content_version",
            "is_locked",
            "prerequisite_locked",
            "prerequisite_ids",
            "quiz_id",
            "assignment_id",
        )

    def _enrollment(self):
        return self.context.get("enrollment")

    def get_is_locked(self, obj):
        enr = self._enrollment()
        if not enr:
            return True
        return is_lesson_locked_for_enrollment(obj, enr)

    def get_prerequisite_locked(self, obj):
        enr = self._enrollment()
        if not enr:
            return True
        if is_lesson_locked_for_enrollment(obj, enr):
            return True
        return not lesson_prerequisites_satisfied(obj, enr)

    def get_prerequisite_ids(self, obj):
        return list(obj.prerequisites.values_list("id", flat=True))

    def get_media(self, obj):
        if self.context.get("hide_lesson_content"):
            return None
        if obj.media_id is None:
            return None
        return MediaSerializer(obj.media, context=self.context).data

    def get_text_body(self, obj):
        if self.context.get("hide_lesson_content"):
            return ""
        return obj.text_body

    def get_external_url(self, obj):
        if self.context.get("hide_lesson_content"):
            return ""
        return obj.external_url or ""

    def get_attachment_url(self, obj):
        if self.context.get("hide_lesson_content") or not obj.attachment:
            return None
        request = self.context.get("request")
        url = obj.attachment.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_quiz_id(self, obj):
        if self.context.get("hide_lesson_content") or obj.content_type != LessonContentType.QUIZ:
            return None
        try:
            return obj.quiz_spec.pk
        except ObjectDoesNotExist:
            return None

    def get_assignment_id(self, obj):
        if self.context.get("hide_lesson_content") or obj.content_type != LessonContentType.ASSIGNMENT:
            return None
        try:
            return obj.assignment_spec.pk
        except ObjectDoesNotExist:
            return None


class ModuleSerializer(serializers.ModelSerializer):
    lessons = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = (
            "id",
            "course",
            "title",
            "description",
            "order",
            "release_offset_days",
            "lessons",
        )

    def get_lessons(self, obj):
        qs = obj.lessons.all().order_by("order", "id")
        return LessonSerializer(qs, many=True, context=self.context).data


class CourseListSerializer(serializers.ModelSerializer):
    category_title = serializers.CharField(source="category.title", read_only=True, allow_null=True)

    class Meta:
        model = Course
        fields = (
            "title",
            "slug",
            "description",
            "thumbnail",
            "language",
            "difficulty",
            "category",
            "category_title",
            "mode",
            "enrollment_type",
            "status",
            "estimated_hours",
            "enrolled_count",
            "avg_completion_pct",
            "created_at",
            "updated_at",
        )


class CourseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = (
            "title",
            "slug",
            "description",
            "thumbnail",
            "language",
            "difficulty",
            "category",
            "mode",
            "enrollment_type",
            "rbac_group",
            "prerequisites",
            "status",
            "instructors",
            "estimated_hours",
        )

    def create(self, validated_data):
        prereqs = validated_data.pop("prerequisites", None)
        instructors = validated_data.pop("instructors", None)
        course = Course.objects.create(**validated_data)
        if prereqs is not None:
            course.prerequisites.set(prereqs)
        if instructors is not None:
            course.instructors.set(instructors)
        return course

    def update(self, instance, validated_data):
        prereqs = validated_data.pop("prerequisites", None)
        instructors = validated_data.pop("instructors", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if prereqs is not None:
            instance.prerequisites.set(prereqs)
        if instructors is not None:
            instance.instructors.set(instructors)
        return instance


class CourseDetailSerializer(serializers.ModelSerializer):
    modules = serializers.SerializerMethodField()
    category_title = serializers.CharField(source="category.title", read_only=True, allow_null=True)

    class Meta:
        model = Course
        fields = (
            "title",
            "slug",
            "description",
            "thumbnail",
            "language",
            "difficulty",
            "category",
            "category_title",
            "mode",
            "enrollment_type",
            "rbac_group",
            "prerequisites",
            "status",
            "instructors",
            "estimated_hours",
            "enrolled_count",
            "avg_completion_pct",
            "created_at",
            "updated_at",
            "modules",
        )

    def get_modules(self, obj):
        qs = obj.modules.all().order_by("order", "id")
        return ModuleSerializer(qs, many=True, context=self.context).data


class EnrollmentSerializer(serializers.ModelSerializer):
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "course",
            "course_slug",
            "course_title",
            "cohort",
            "role",
            "status",
            "enrolled_at",
            "started_at",
            "completed_at",
            "progress_pct",
            "completed_lessons_count",
            "current_grade_pct",
            "current_grade_letter",
        )
        read_only_fields = fields


class RosterEnrollmentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "username",
            "name",
            "cohort",
            "role",
            "status",
            "enrolled_at",
            "progress_pct",
            "completed_lessons_count",
            "current_grade_pct",
            "current_grade_letter",
        )


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = (
            "status",
            "progress_pct",
            "last_position_seconds",
            "time_spent_seconds",
            "started_at",
            "completed_at",
        )
