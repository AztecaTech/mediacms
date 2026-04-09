from django.db import models

from learning.models.course import Course


class CalendarEventType(models.TextChoices):
    COHORT_START = "cohort_start", "Cohort start"
    COHORT_END = "cohort_end", "Cohort end"
    MODULE_RELEASE = "module_release", "Module release"
    ASSIGNMENT_DUE = "assignment_due", "Assignment due"
    QUIZ_DUE = "quiz_due", "Quiz due"
    LIVE_SESSION = "live_session", "Live session"
    CUSTOM = "custom", "Custom"


class CalendarEvent(models.Model):
    """Course-scoped calendar row; auto rows link to source via source_type + source_id."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="calendar_events")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=32, choices=CalendarEventType.choices)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    source_type = models.CharField(max_length=64, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "id"]
        indexes = [
            models.Index(fields=["course", "starts_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "event_type", "source_type", "source_id"],
                name="learning_calendarevent_unique_autogen_source",
                condition=models.Q(source_id__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.course.slug}: {self.title}"
