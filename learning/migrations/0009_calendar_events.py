import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0008_discussion_email_mentions"),
    ]

    operations = [
        migrations.AddField(
            model_name="discussionnotificationpreference",
            name="email_calendar",
            field=models.BooleanField(
                default=True,
                help_text="When false, optional calendar/digest emails can be skipped (in-app calendar unchanged).",
            ),
        ),
        migrations.CreateModel(
            name="CalendarEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("cohort_start", "Cohort start"),
                            ("cohort_end", "Cohort end"),
                            ("module_release", "Module release"),
                            ("assignment_due", "Assignment due"),
                            ("quiz_due", "Quiz due"),
                            ("live_session", "Live session"),
                            ("custom", "Custom"),
                        ],
                        max_length=32,
                    ),
                ),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("source_type", models.CharField(blank=True, max_length=64)),
                ("source_id", models.PositiveIntegerField(blank=True, null=True)),
                ("url", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="calendar_events",
                        to="learning.course",
                    ),
                ),
            ],
            options={
                "ordering": ["starts_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="calendarevent",
            index=models.Index(fields=["course", "starts_at"], name="learning_cal_course__8218cd_idx"),
        ),
        migrations.AddConstraint(
            model_name="calendarevent",
            constraint=models.UniqueConstraint(
                condition=models.Q(source_id__isnull=False),
                fields=("course", "event_type", "source_type", "source_id"),
                name="learning_calendarevent_unique_autogen_source",
            ),
        ),
    ]
