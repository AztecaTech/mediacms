from django.conf import settings
from django.db import models


class LessonDraft(models.Model):
    lesson = models.ForeignKey(
        "learning.Lesson",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="drafts",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_drafts",
    )
    content_snapshot = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
