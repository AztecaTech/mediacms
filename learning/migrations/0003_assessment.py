import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0002_learning_paths_and_drafts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionBank",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="question_banks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="Quiz",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("instructions", models.TextField(blank=True)),
                ("time_limit_minutes", models.PositiveIntegerField(blank=True, null=True)),
                ("max_attempts", models.PositiveIntegerField(default=1)),
                ("passing_score_pct", models.PositiveIntegerField(default=70)),
                ("randomize_questions", models.BooleanField(default=False)),
                ("randomize_choices", models.BooleanField(default=False)),
                (
                    "show_correct_after",
                    models.CharField(
                        choices=[
                            ("never", "Never"),
                            ("after_attempt", "After attempt"),
                            ("after_passing", "After passing"),
                            ("after_due_date", "After due date"),
                        ],
                        default="never",
                        max_length=20,
                    ),
                ),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                (
                    "lesson",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_spec",
                        to="learning.lesson",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField(default=0)),
                ("prompt", models.TextField()),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("mc_single", "Multiple choice (single)"),
                            ("mc_multi", "Multiple choice (multi)"),
                            ("true_false", "True / false"),
                            ("short_answer", "Short answer"),
                            ("matching", "Matching"),
                            ("fill_blank", "Fill in the blank"),
                        ],
                        max_length=20,
                    ),
                ),
                ("points", models.DecimalField(decimal_places=2, default=1, max_digits=8)),
                ("explanation", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "bank",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="learning.questionbank",
                    ),
                ),
                (
                    "quiz",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="learning.quiz",
                    ),
                ),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Choice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=2000)),
                ("is_correct", models.BooleanField(default=False)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="learning.question",
                    ),
                ),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="QuizAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("score_pct", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("in_progress", "In progress"),
                            ("submitted", "Submitted"),
                            ("graded", "Graded"),
                            ("expired", "Expired"),
                        ],
                        default="in_progress",
                        max_length=20,
                    ),
                ),
                ("attempt_number", models.PositiveIntegerField(default=1)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_attempts",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "quiz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="learning.quiz",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Answer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text_answer", models.TextField(blank=True)),
                ("matching_answer", models.JSONField(blank=True, default=dict)),
                ("is_correct", models.BooleanField(blank=True, null=True)),
                ("points_awarded", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("auto_graded", models.BooleanField(default=False)),
                ("grader_feedback", models.TextField(blank=True)),
                (
                    "attempt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="learning.quizattempt",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="student_answers",
                        to="learning.question",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="answer",
            name="selected_choices",
            field=models.ManyToManyField(
                blank=True,
                related_name="answer_selections",
                to="learning.choice",
            ),
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.CheckConstraint(
                condition=models.Q(quiz__isnull=False) | models.Q(bank__isnull=False),
                name="learning_question_quiz_or_bank",
            ),
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.UniqueConstraint(
                condition=models.Q(quiz__isnull=False),
                fields=("quiz", "order"),
                name="learning_question_unique_quiz_order",
            ),
        ),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.UniqueConstraint(
                condition=models.Q(bank__isnull=False),
                fields=("bank", "order"),
                name="learning_question_unique_bank_order",
            ),
        ),
        migrations.AddConstraint(
            model_name="quizattempt",
            constraint=models.UniqueConstraint(
                fields=("enrollment", "quiz", "attempt_number"),
                name="learning_quizattempt_unique_enrollment_quiz_attemptnum",
            ),
        ),
        migrations.AddConstraint(
            model_name="answer",
            constraint=models.UniqueConstraint(
                fields=("attempt", "question"),
                name="learning_answer_unique_attempt_question",
            ),
        ),
        migrations.CreateModel(
            name="Assignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("instructions", models.TextField(blank=True)),
                ("max_points", models.DecimalField(decimal_places=2, default=100, max_digits=8)),
                ("submission_types", models.JSONField(default=list, help_text='Allowed types: "text", "file", "url"')),
                ("max_file_size_mb", models.PositiveIntegerField(default=25)),
                ("allowed_extensions", models.CharField(blank=True, default="pdf,doc,docx,txt,zip", max_length=500)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("late_penalty_pct_per_day", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                (
                    "lesson",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_spec",
                        to="learning.lesson",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("text_content", models.TextField(blank=True)),
                (
                    "file",
                    models.FileField(blank=True, null=True, upload_to="learning/submissions/%Y/%m/"),
                ),
                ("url", models.URLField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("graded", "Graded"),
                            ("returned_for_revision", "Returned for revision"),
                        ],
                        default="draft",
                        max_length=30,
                    ),
                ),
                ("score", models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ("grader_feedback", models.TextField(blank=True)),
                ("graded_at", models.DateTimeField(blank=True, null=True)),
                ("attempt_number", models.PositiveIntegerField(default=1)),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="learning.assignment",
                    ),
                ),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_submissions",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "graded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="graded_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-submitted_at", "-id"]},
        ),
    ]
