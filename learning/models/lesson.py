from django.db import models


class LessonContentType(models.TextChoices):
    VIDEO = "video", "Video"
    TEXT = "text", "Text"
    FILE = "file", "File"
    LINK = "link", "Link"
    QUIZ = "quiz", "Quiz"
    ASSIGNMENT = "assignment", "Assignment"
    LTI = "lti", "LTI tool"


class Lesson(models.Model):
    module = models.ForeignKey("learning.Module", on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    content_type = models.CharField(
        max_length=20,
        choices=LessonContentType.choices,
        default=LessonContentType.VIDEO,
    )
    media = models.ForeignKey(
        "files.Media",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lms_lessons",
    )
    text_body = models.TextField(blank=True)
    attachment = models.FileField(upload_to="learning/lesson_attachments/%Y/%m/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    is_required = models.BooleanField(default=True)
    estimated_minutes = models.PositiveIntegerField(default=0)
    content_version = models.PositiveIntegerField(default=1)
    prerequisites = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="dependent_lessons",
        blank=True,
    )

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["module", "order"], name="learning_lesson_unique_module_order"),
        ]

    def __str__(self):
        return f"{self.module.course.slug}: {self.title}"
