from django.conf import settings
from django.db import models


class CourseAuditAction(models.TextChoices):
    ENROLLED = "enrolled", "Enrolled"
    WITHDREW = "withdrew", "Withdrew"
    COMPLETED = "completed", "Completed"
    STARTED = "started", "Started"
    RE_ENROLLED = "re_enrolled", "Re-enrolled"
    ROLE_CHANGED = "role_changed", "Role changed"
    CERTIFICATE_ISSUED = "certificate_issued", "Certificate issued"


class CourseAuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lms_audit_logs",
    )
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=40, choices=CourseAuditAction.choices)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.course_id}"
