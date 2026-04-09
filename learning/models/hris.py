from django.conf import settings
from django.db import models


class HrisConnectorStatus(models.TextChoices):
    DISABLED = "disabled", "Disabled"
    IDLE = "idle", "Idle"
    ERROR = "error", "Error"


class HrisSyncRun(models.Model):
    """Audit row for HRIS / workforce sync jobs (connector implementation is environment-specific)."""

    name = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=HrisConnectorStatus.choices, default=HrisConnectorStatus.IDLE)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hris_sync_runs",
    )

    class Meta:
        ordering = ["-started_at"]
