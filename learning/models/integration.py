from django.conf import settings
from django.db import models


class Webhook(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lms_webhooks",
    )
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=255, blank=True)
    events = models.JSONField(default=list, help_text="List of event type strings")
    is_active = models.BooleanField(default=True)
    last_delivered_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveIntegerField(default=0)


class WebhookDelivery(models.Model):
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE, related_name="deliveries")
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    response_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempted_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
