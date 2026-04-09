from django.conf import settings
from django.db import models


class GradeItemSourceType(models.TextChoices):
    QUIZ = "quiz", "Quiz"
    ASSIGNMENT = "assignment", "Assignment"
    MANUAL = "manual", "Manual"


class GradeCategory(models.Model):
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="grade_categories")
    name = models.CharField(max_length=255)
    weight_pct = models.DecimalField(max_digits=5, decimal_places=2)
    drop_lowest_n = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class GradeItem(models.Model):
    category = models.ForeignKey(GradeCategory, on_delete=models.CASCADE, related_name="items")
    source_type = models.CharField(max_length=20, choices=GradeItemSourceType.choices)
    quiz = models.ForeignKey(
        "learning.Quiz",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="grade_items",
    )
    assignment = models.ForeignKey(
        "learning.Assignment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="grade_items",
    )
    title = models.CharField(max_length=255)
    max_points = models.DecimalField(max_digits=8, decimal_places=2)
    due_at = models.DateTimeField(null=True, blank=True)
    visible_to_students = models.BooleanField(default=True)
    auto_created = models.BooleanField(default=False)


class Rubric(models.Model):
    grade_item = models.OneToOneField(
        GradeItem,
        on_delete=models.CASCADE,
        related_name="rubric",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)


class RubricCriterion(models.Model):
    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE, related_name="criteria")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    max_points = models.DecimalField(max_digits=8, decimal_places=2, default=10)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Grade(models.Model):
    enrollment = models.ForeignKey("learning.Enrollment", on_delete=models.CASCADE, related_name="grades")
    grade_item = models.ForeignKey(GradeItem, on_delete=models.CASCADE, related_name="grades")
    points_earned = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grades_given",
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    is_override = models.BooleanField(default=False)
    excused = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "grade_item"],
                name="learning_grade_unique_enrollment_item",
            ),
        ]


class RubricScore(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="rubric_scores")
    criterion = models.ForeignKey(RubricCriterion, on_delete=models.CASCADE, related_name="scores")
    points_awarded = models.DecimalField(max_digits=8, decimal_places=2)
    feedback = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["grade", "criterion"],
                name="learning_rubricscore_unique_grade_criterion",
            ),
        ]


class LetterGradeScheme(models.Model):
    course = models.ForeignKey(
        "learning.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="letter_schemes",
    )
    name = models.CharField(max_length=100, default="Default")
    bands = models.JSONField(
        default=list,
        help_text='e.g. [{"letter": "A", "min_pct": 90, "max_pct": 100}]',
    )
