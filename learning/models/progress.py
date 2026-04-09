from django.db import models


class LessonProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(
        "learning.Enrollment",
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey("learning.Lesson", on_delete=models.CASCADE, related_name="progress_records")
    status = models.CharField(
        max_length=20,
        choices=LessonProgressStatus.choices,
        default=LessonProgressStatus.NOT_STARTED,
    )
    progress_pct = models.PositiveSmallIntegerField(default=0)
    last_position_seconds = models.PositiveIntegerField(default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "lesson"],
                name="learning_lessonprogress_unique_enrollment_lesson",
            ),
        ]

    def __str__(self):
        return f"{self.enrollment_id}:{self.lesson_id}"
