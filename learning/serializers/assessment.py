from rest_framework import serializers

from learning.models import Choice, Question, QuizAttempt, Submission


class ChoiceStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "text", "order")


class ChoiceInstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "text", "is_correct", "order")


class QuestionStudentSerializer(serializers.ModelSerializer):
    choices = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ("id", "order", "prompt", "type", "points", "metadata", "choices")

    def get_choices(self, obj):
        qs = obj.choices.all().order_by("order", "id")
        if self.context.get("hide_correct"):
            return ChoiceStudentSerializer(qs, many=True).data
        return ChoiceInstructorSerializer(qs, many=True).data


class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = (
            "id",
            "quiz",
            "enrollment",
            "started_at",
            "submitted_at",
            "expires_at",
            "score_pct",
            "status",
            "attempt_number",
        )
        read_only_fields = fields


class SubmissionSerializer(serializers.ModelSerializer):
    student_display = serializers.SerializerMethodField()
    assignment_lesson_title = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = (
            "id",
            "enrollment",
            "assignment",
            "student_display",
            "assignment_lesson_title",
            "submitted_at",
            "text_content",
            "file",
            "url",
            "status",
            "score",
            "grader_feedback",
            "graded_by",
            "graded_at",
            "attempt_number",
        )
        read_only_fields = ("graded_by", "graded_at", "status", "score", "student_display", "assignment_lesson_title")

    def get_student_display(self, obj):
        u = obj.enrollment.user
        name = (u.get_full_name() or "").strip()
        return name or getattr(u, "username", str(u.pk))

    def get_assignment_lesson_title(self, obj):
        return obj.assignment.lesson.title
