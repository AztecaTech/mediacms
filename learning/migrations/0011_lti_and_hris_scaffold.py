import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("learning", "0010_lesson_metrics_and_risk"),
    ]

    operations = [
        migrations.CreateModel(
            name="LTIResourceLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("context_id", models.CharField(db_index=True, max_length=512)),
                ("resource_link_id", models.CharField(db_index=True, max_length=512)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("custom_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lti_resource_links",
                        to="learning.course",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="LTIUserMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("issuer", models.CharField(db_index=True, max_length=512)),
                ("subject", models.CharField(db_index=True, max_length=512)),
                ("last_launch_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lti_user_mappings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="HrisSyncRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("disabled", "Disabled"), ("idle", "Idle"), ("error", "Error")],
                        default="idle",
                        max_length=32,
                    ),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("message", models.TextField(blank=True)),
                (
                    "triggered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="hris_sync_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.AddConstraint(
            model_name="ltiresourcelink",
            constraint=models.UniqueConstraint(
                fields=("context_id", "resource_link_id"),
                name="learning_ltiresource_unique_context_rl",
            ),
        ),
        migrations.AddConstraint(
            model_name="ltiusermapping",
            constraint=models.UniqueConstraint(fields=("issuer", "subject"), name="learning_ltiuser_unique_issuer_sub"),
        ),
    ]
