import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0009_calendar_events"),
    ]

    operations = [
        migrations.CreateModel(
            name="LessonMetrics",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("view_count", models.PositiveIntegerField(default=0)),
                ("started_count", models.PositiveIntegerField(default=0)),
                ("completed_count", models.PositiveIntegerField(default=0)),
                ("avg_time_seconds", models.PositiveIntegerField(default=0)),
                ("drop_off_after_seconds", models.PositiveIntegerField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "lesson",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_metrics",
                        to="learning.lesson",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StudentRiskScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                (
                    "tier",
                    models.CharField(
                        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                        default="low",
                        max_length=16,
                    ),
                ),
                ("factors", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "enrollment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="risk_score_row",
                        to="learning.enrollment",
                    ),
                ),
            ],
        ),
    ]
