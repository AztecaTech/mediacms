import uuid

from django.conf import settings
from django.db import models
from django.utils.html import strip_tags
from mptt.models import MPTTModel, TreeForeignKey


class Discussion(models.Model):
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="discussions")
    lesson = models.ForeignKey(
        "learning.Lesson",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="discussions",
    )
    title = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="discussions_started",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    last_activity_at = models.DateTimeField(auto_now=True)
    reply_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_pinned", "-last_activity_at"]


class DiscussionPost(MPTTModel):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="discussion_posts")
    body = models.TextField()
    parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_instructor_answer = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class MPTTMeta:
        order_insertion_by = ["created_at"]

    def save(self, *args, **kwargs):
        self.body = strip_tags(self.body or "")[:10000]
        super().save(*args, **kwargs)


class Announcement(models.Model):
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="announcements")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="announcements")
    title = models.CharField(max_length=255)
    body = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)
    send_email = models.BooleanField(default=False)


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lms_notifications",
    )
    type = models.CharField(max_length=40)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    email_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class DiscussionNotificationFrequency(models.TextChoices):
    OFF = "off", "Off"
    IMMEDIATE = "immediate", "Immediate"
    DAILY = "daily", "Daily digest"


class DiscussionNotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussion_notification_preference",
    )
    email_replies = models.BooleanField(default=True)
    email_mentions = models.BooleanField(
        default=True,
        help_text="When false, @mention emails are skipped (in-app mention notifications still created).",
    )
    email_calendar = models.BooleanField(
        default=True,
        help_text="When false, optional calendar/digest emails can be skipped (in-app calendar unchanged).",
    )
    frequency = models.CharField(
        max_length=20,
        choices=DiscussionNotificationFrequency.choices,
        default=DiscussionNotificationFrequency.IMMEDIATE,
    )
    updated_at = models.DateTimeField(auto_now=True)
