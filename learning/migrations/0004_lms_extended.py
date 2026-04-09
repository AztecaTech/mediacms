import uuid

import django.db.models.deletion
import mptt.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0003_assessment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GradeCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("weight_pct", models.DecimalField(decimal_places=2, max_digits=5)),
                ("drop_lowest_n", models.PositiveIntegerField(default=0)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grade_categories",
                        to="learning.course",
                    ),
                ),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="GradeItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("quiz", "Quiz"),
                            ("assignment", "Assignment"),
                            ("manual", "Manual"),
                        ],
                        max_length=20,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("max_points", models.DecimalField(decimal_places=2, max_digits=8)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("visible_to_students", models.BooleanField(default=True)),
                ("auto_created", models.BooleanField(default=False)),
                (
                    "assignment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grade_items",
                        to="learning.assignment",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="learning.gradecategory",
                    ),
                ),
                (
                    "quiz",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grade_items",
                        to="learning.quiz",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Grade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("points_earned", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("feedback", models.TextField(blank=True)),
                ("graded_at", models.DateTimeField(blank=True, null=True)),
                ("is_override", models.BooleanField(default=False)),
                ("excused", models.BooleanField(default=False)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grades",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "grade_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grades",
                        to="learning.gradeitem",
                    ),
                ),
                (
                    "graded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="grades_given",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="grade",
            constraint=models.UniqueConstraint(
                fields=("enrollment", "grade_item"),
                name="learning_grade_unique_enrollment_item",
            ),
        ),
        migrations.CreateModel(
            name="LetterGradeScheme",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Default", max_length=100)),
                (
                    "bands",
                    models.JSONField(
                        default=list,
                        help_text='e.g. [{"letter": "A", "min_pct": 90, "max_pct": 100}]',
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="letter_schemes",
                        to="learning.course",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Discussion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_pinned", models.BooleanField(default=False)),
                ("is_locked", models.BooleanField(default=False)),
                ("last_activity_at", models.DateTimeField(auto_now=True)),
                ("reply_count", models.PositiveIntegerField(default=0)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discussions",
                        to="learning.course",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="discussions_started",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "lesson",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discussions",
                        to="learning.lesson",
                    ),
                ),
            ],
            options={"ordering": ["-is_pinned", "-last_activity_at"]},
        ),
        migrations.CreateModel(
            name="DiscussionPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("uid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_instructor_answer", models.BooleanField(default=False)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("lft", models.PositiveIntegerField(editable=False)),
                ("rght", models.PositiveIntegerField(editable=False)),
                ("tree_id", models.PositiveIntegerField(db_index=True, editable=False)),
                ("level", models.PositiveIntegerField(editable=False)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discussion_posts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "discussion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="posts",
                        to="learning.discussion",
                    ),
                ),
                (
                    "parent",
                    mptt.fields.TreeForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="learning.discussionpost",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("published_at", models.DateTimeField(auto_now_add=True)),
                ("is_pinned", models.BooleanField(default=False)),
                ("send_email", models.BooleanField(default=False)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcements",
                        to="learning.course",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(max_length=40)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField(blank=True)),
                ("url", models.CharField(blank=True, max_length=500)),
                ("related_object_type", models.CharField(blank=True, max_length=50)),
                ("related_object_id", models.PositiveIntegerField(blank=True, null=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("email_sent", models.BooleanField(default=False)),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lms_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CertificateTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "background_image",
                    models.ImageField(blank=True, null=True, upload_to="learning/cert_templates/%Y/%m/"),
                ),
                ("layout", models.JSONField(blank=True, default=dict)),
                ("font_family", models.CharField(blank=True, default="Helvetica", max_length=100)),
                (
                    "orientation",
                    models.CharField(
                        choices=[("landscape", "Landscape"), ("portrait", "Portrait")],
                        default="landscape",
                        max_length=20,
                    ),
                ),
                (
                    "signature_image",
                    models.ImageField(blank=True, null=True, upload_to="learning/cert_signatures/"),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificate_templates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CertificateIssuancePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requires_passing_grade", models.BooleanField(default=True)),
                ("minimum_grade_pct", models.DecimalField(decimal_places=2, default=70, max_digits=5)),
                ("requires_all_lessons_completed", models.BooleanField(default=True)),
                ("auto_issue", models.BooleanField(default=True)),
                (
                    "course",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificate_policy",
                        to="learning.course",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="policies",
                        to="learning.certificatetemplate",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Certificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("template_snapshot", models.JSONField(blank=True, default=dict)),
                ("issued_at", models.DateTimeField(auto_now_add=True)),
                ("verification_code", models.CharField(db_index=True, max_length=32, unique=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revoke_reason", models.TextField(blank=True)),
                (
                    "pdf_file",
                    models.FileField(blank=True, null=True, upload_to="learning/certificates/%Y/%m/"),
                ),
                (
                    "enrollment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificate",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "issued_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="certificates_issued",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Badge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                ("icon", models.ImageField(blank=True, null=True, upload_to="learning/badges/")),
                ("criteria_type", models.CharField(default="course_completion", max_length=40)),
                ("criteria_config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="BadgeAward",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("awarded_at", models.DateTimeField(auto_now_add=True)),
                ("context", models.JSONField(blank=True, default=dict)),
                (
                    "awarded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="badges_awarded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "badge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="awards",
                        to="learning.badge",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="badge_awards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="badgeaward",
            constraint=models.UniqueConstraint(
                fields=("user", "badge"),
                name="learning_badgeaward_unique_user_badge",
            ),
        ),
        migrations.CreateModel(
            name="Webhook",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("url", models.URLField(max_length=500)),
                ("secret", models.CharField(blank=True, max_length=255)),
                ("events", models.JSONField(default=list, help_text="List of event type strings")),
                ("is_active", models.BooleanField(default=True)),
                ("last_delivered_at", models.DateTimeField(blank=True, null=True)),
                ("failure_count", models.PositiveIntegerField(default=0)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lms_webhooks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="WebhookDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=80)),
                ("payload", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("delivered", "Delivered"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("response_code", models.PositiveIntegerField(blank=True, null=True)),
                ("response_body", models.TextField(blank=True)),
                ("attempted_at", models.DateTimeField(blank=True, null=True)),
                ("next_retry_at", models.DateTimeField(blank=True, null=True)),
                (
                    "webhook",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="learning.webhook",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AnalyticsEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(db_index=True, max_length=80)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analytics_events",
                        to="learning.course",
                    ),
                ),
                (
                    "lesson",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="analytics_events",
                        to="learning.lesson",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lms_analytics_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CourseMetricsDaily",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True)),
                ("enrollments_new", models.PositiveIntegerField(default=0)),
                ("enrollments_total", models.PositiveIntegerField(default=0)),
                ("completions_new", models.PositiveIntegerField(default=0)),
                ("completions_total", models.PositiveIntegerField(default=0)),
                ("avg_progress_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("active_students", models.PositiveIntegerField(default=0)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metrics_daily",
                        to="learning.course",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="coursemetricsdaily",
            constraint=models.UniqueConstraint(
                fields=("course", "date"),
                name="learning_coursemetrics_unique_course_date",
            ),
        ),
        migrations.AddIndex(
            model_name="analyticsevent",
            index=models.Index(fields=["type", "timestamp"], name="learning_an_type_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="analyticsevent",
            index=models.Index(fields=["course", "timestamp"], name="learning_an_course_ts_idx"),
        ),
    ]
