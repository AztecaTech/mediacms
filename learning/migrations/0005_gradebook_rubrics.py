import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("learning", "0004_lms_extended"),
    ]

    operations = [
        migrations.CreateModel(
            name="Rubric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "grade_item",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rubric",
                        to="learning.gradeitem",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RubricCriterion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("max_points", models.DecimalField(decimal_places=2, default=10, max_digits=8)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "rubric",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="criteria",
                        to="learning.rubric",
                    ),
                ),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="RubricScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("points_awarded", models.DecimalField(decimal_places=2, max_digits=8)),
                ("feedback", models.TextField(blank=True)),
                (
                    "criterion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scores",
                        to="learning.rubriccriterion",
                    ),
                ),
                (
                    "grade",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rubric_scores",
                        to="learning.grade",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="rubricscore",
            constraint=models.UniqueConstraint(
                fields=("grade", "criterion"),
                name="learning_rubricscore_unique_grade_criterion",
            ),
        ),
    ]
