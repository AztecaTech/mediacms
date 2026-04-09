from django.conf import settings
from django.db import models


class SubmissionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    GRADED = "graded", "Graded"
    RETURNED_FOR_REVISION = "returned_for_revision", "Returned for revision"


class Assignment(models.Model):
    lesson = models.OneToOneField(
        "learning.Lesson",
        on_delete=models.CASCADE,
        related_name="assignment_spec",
    )
    instructions = models.TextField(blank=True)
    max_points = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    submission_types = models.JSONField(
        default=list,
        help_text='Allowed types: "text", "file", "url"',
    )
    max_file_size_mb = models.PositiveIntegerField(default=25)
    allowed_extensions = models.CharField(max_length=500, blank=True, default="pdf,doc,docx,txt,zip")
    due_at = models.DateTimeField(null=True, blank=True)
    late_penalty_pct_per_day = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"Assignment:{self.lesson_id}"


class Submission(models.Model):
    enrollment = models.ForeignKey(
        "learning.Enrollment",
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
    )
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    submitted_at = models.DateTimeField(null=True, blank=True)
    text_content = models.TextField(blank=True)
    file = models.FileField(upload_to="learning/submissions/%Y/%m/", blank=True, null=True)
    url = models.URLField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.DRAFT,
    )
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    grader_feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="graded_submissions",
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-submitted_at", "-id"]
