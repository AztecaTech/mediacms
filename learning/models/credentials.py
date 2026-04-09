from django.conf import settings
from django.db import models


class CertificateTemplate(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="certificate_templates",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    background_image = models.ImageField(
        upload_to="learning/cert_templates/%Y/%m/",
        blank=True,
        null=True,
    )
    layout = models.JSONField(default=dict, blank=True)
    font_family = models.CharField(max_length=100, blank=True, default="Helvetica")
    orientation = models.CharField(
        max_length=20,
        choices=[("landscape", "Landscape"), ("portrait", "Portrait")],
        default="landscape",
    )
    signature_image = models.ImageField(upload_to="learning/cert_signatures/", blank=True, null=True)


class CertificateIssuancePolicy(models.Model):
    course = models.OneToOneField(
        "learning.Course",
        on_delete=models.CASCADE,
        related_name="certificate_policy",
    )
    template = models.ForeignKey(CertificateTemplate, on_delete=models.PROTECT, related_name="policies")
    requires_passing_grade = models.BooleanField(default=True)
    minimum_grade_pct = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    requires_all_lessons_completed = models.BooleanField(default=True)
    auto_issue = models.BooleanField(default=True)


class Certificate(models.Model):
    enrollment = models.OneToOneField(
        "learning.Enrollment",
        on_delete=models.CASCADE,
        related_name="certificate",
    )
    template_snapshot = models.JSONField(default=dict, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="certificates_issued",
    )
    verification_code = models.CharField(max_length=32, unique=True, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to="learning/certificates/%Y/%m/", blank=True, null=True)


class Badge(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to="learning/badges/", blank=True, null=True)
    criteria_type = models.CharField(max_length=40, default="course_completion")
    criteria_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)


class BadgeAward(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badge_awards")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="awards")
    awarded_at = models.DateTimeField(auto_now_add=True)
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="badges_awarded",
    )
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "badge"], name="learning_badgeaward_unique_user_badge"),
        ]
