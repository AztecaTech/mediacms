from django.conf import settings
from django.db import models

from learning.models.course import Course


class LTIResourceLink(models.Model):
    """Persisted LTI 1.3 resource link placement for a course (foundation for AGS/NRPS)."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lti_resource_links")
    context_id = models.CharField(max_length=512, db_index=True)
    resource_link_id = models.CharField(max_length=512, db_index=True)
    title = models.CharField(max_length=255, blank=True)
    custom_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["context_id", "resource_link_id"],
                name="learning_ltiresource_unique_context_rl",
            ),
        ]


class LTIUserMapping(models.Model):
    """Maps platform subject to local user after a successful launch."""

    issuer = models.CharField(max_length=512, db_index=True)
    subject = models.CharField(max_length=512, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lti_user_mappings",
    )
    last_launch_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["issuer", "subject"], name="learning_ltiuser_unique_issuer_sub"),
        ]
