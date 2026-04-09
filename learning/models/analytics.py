from django.conf import settings
from django.db import models


class AnalyticsEvent(models.Model):
    type = models.CharField(max_length=80, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lms_analytics_events",
    )
    course = models.ForeignKey(
        "learning.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="analytics_events",
    )
    lesson = models.ForeignKey(
        "learning.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["type", "timestamp"]),
            models.Index(fields=["course", "timestamp"]),
        ]


class LessonMetrics(models.Model):
    """Aggregated lesson engagement (refreshed by analytics tasks)."""

    lesson = models.OneToOneField(
        "learning.Lesson",
        on_delete=models.CASCADE,
        related_name="lesson_metrics",
    )
    view_count = models.PositiveIntegerField(default=0)
    started_count = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)
    avg_time_seconds = models.PositiveIntegerField(default=0)
    drop_off_after_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Median time when learners stop (best-effort).",
    )
    updated_at = models.DateTimeField(auto_now=True)


class StudentRiskScore(models.Model):
    """Per-enrollment risk heuristic snapshot."""

    class RiskTier(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    enrollment = models.OneToOneField(
        "learning.Enrollment",
        on_delete=models.CASCADE,
        related_name="risk_score_row",
    )
    score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    tier = models.CharField(max_length=16, choices=RiskTier.choices, default=RiskTier.LOW)
    factors = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class CourseMetricsDaily(models.Model):
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="metrics_daily")
    date = models.DateField(db_index=True)
    enrollments_new = models.PositiveIntegerField(default=0)
    enrollments_total = models.PositiveIntegerField(default=0)
    completions_new = models.PositiveIntegerField(default=0)
    completions_total = models.PositiveIntegerField(default=0)
    avg_progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    active_students = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "date"], name="learning_coursemetrics_unique_course_date"),
        ]
