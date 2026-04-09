import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("files", "0015_add_external_video_fields"),
        ("rbac", "0003_alter_rbacgroup_members"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(db_index=True, max_length=280, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "thumbnail",
                    models.ImageField(blank=True, null=True, upload_to="learning/course_thumbnails/%Y/%m/"),
                ),
                ("language", models.CharField(default="en", max_length=32)),
                (
                    "difficulty",
                    models.CharField(
                        choices=[("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")],
                        default="beginner",
                        max_length=20,
                    ),
                ),
                (
                    "mode",
                    models.CharField(choices=[("async", "Async"), ("cohort", "Cohort")], default="async", max_length=20),
                ),
                (
                    "enrollment_type",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("invite", "Invite only"),
                            ("rbac_group", "RBAC group"),
                            ("approval", "Approval required"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("published", "Published"), ("archived", "Archived")],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("estimated_hours", models.PositiveIntegerField(default=0)),
                ("enrolled_count", models.PositiveIntegerField(default=0)),
                ("avg_completion_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lms_courses",
                        to="files.category",
                    ),
                ),
                (
                    "instructors",
                    models.ManyToManyField(blank=True, related_name="courses_teaching", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "prerequisites",
                    models.ManyToManyField(
                        blank=True, related_name="dependent_courses", to="learning.course", symmetrical=False
                    ),
                ),
                (
                    "rbac_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lms_courses",
                        to="rbac.rbacgroup",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at", "title"],
            },
        ),
        migrations.CreateModel(
            name="Cohort",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("capacity", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("upcoming", "Upcoming"),
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="upcoming",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cohorts", to="learning.course"),
                ),
            ],
            options={
                "ordering": ["-start_date", "name"],
            },
        ),
        migrations.CreateModel(
            name="Module",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "release_offset_days",
                    models.PositiveIntegerField(
                        default=0, help_text="Days after cohort start_date before this module unlocks (cohort mode)."
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="modules", to="learning.course"),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="Lesson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "content_type",
                    models.CharField(
                        choices=[
                            ("video", "Video"),
                            ("text", "Text"),
                            ("file", "File"),
                            ("link", "Link"),
                            ("quiz", "Quiz"),
                            ("assignment", "Assignment"),
                            ("lti", "LTI tool"),
                        ],
                        default="video",
                        max_length=20,
                    ),
                ),
                ("text_body", models.TextField(blank=True)),
                (
                    "attachment",
                    models.FileField(blank=True, null=True, upload_to="learning/lesson_attachments/%Y/%m/"),
                ),
                ("external_url", models.URLField(blank=True)),
                ("is_required", models.BooleanField(default=True)),
                ("estimated_minutes", models.PositiveIntegerField(default=0)),
                ("content_version", models.PositiveIntegerField(default=1)),
                (
                    "media",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lms_lessons",
                        to="files.media",
                    ),
                ),
                (
                    "module",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lessons", to="learning.module"),
                ),
                (
                    "prerequisites",
                    models.ManyToManyField(
                        blank=True, related_name="dependent_lessons", symmetrical=False, to="learning.lesson"
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("student", "Student"),
                            ("instructor", "Instructor"),
                            ("ta", "Teaching assistant"),
                        ],
                        default="student",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("withdrawn", "Withdrawn"),
                            ("expired", "Expired"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("progress_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("completed_lessons_count", models.PositiveIntegerField(default=0)),
                ("current_grade_pct", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("current_grade_letter", models.CharField(blank=True, max_length=5)),
                (
                    "cohort",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="learning.cohort",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="learning.course"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lms_enrollments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="LessonProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("not_started", "Not started"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                        ],
                        default="not_started",
                        max_length=20,
                    ),
                ),
                ("progress_pct", models.PositiveSmallIntegerField(default=0)),
                ("last_position_seconds", models.PositiveIntegerField(default=0)),
                ("time_spent_seconds", models.PositiveIntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_progress",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "lesson",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="progress_records", to="learning.lesson"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CourseAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("enrolled", "Enrolled"),
                            ("withdrew", "Withdrew"),
                            ("completed", "Completed"),
                            ("started", "Started"),
                            ("re_enrolled", "Re-enrolled"),
                            ("role_changed", "Role changed"),
                            ("certificate_issued", "Certificate issued"),
                        ],
                        max_length=40,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_logs", to="learning.course"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="lms_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="module",
            constraint=models.UniqueConstraint(fields=("course", "order"), name="learning_module_unique_course_order"),
        ),
        migrations.AddConstraint(
            model_name="lesson",
            constraint=models.UniqueConstraint(fields=("module", "order"), name="learning_lesson_unique_module_order"),
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(
                condition=models.Q(cohort__isnull=True),
                fields=("user", "course"),
                name="learning_enrollment_unique_user_course_async",
            ),
        ),
        migrations.AddConstraint(
            model_name="enrollment",
            constraint=models.UniqueConstraint(
                condition=models.Q(cohort__isnull=False),
                fields=("user", "course", "cohort"),
                name="learning_enrollment_unique_user_course_cohort",
            ),
        ),
        migrations.AddConstraint(
            model_name="lessonprogress",
            constraint=models.UniqueConstraint(
                fields=("enrollment", "lesson"), name="learning_lessonprogress_unique_enrollment_lesson"
            ),
        ),
    ]
