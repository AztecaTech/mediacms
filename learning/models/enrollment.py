from django.conf import settings
from django.db import models


class EnrollmentRole(models.TextChoices):
    STUDENT = "student", "Student"
    INSTRUCTOR = "instructor", "Instructor"
    TA = "ta", "Teaching assistant"


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    WITHDRAWN = "withdrawn", "Withdrawn"
    EXPIRED = "expired", "Expired"


class Enrollment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lms_enrollments",
    )
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="enrollments")
    cohort = models.ForeignKey(
        "learning.Cohort",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    role = models.CharField(
        max_length=20,
        choices=EnrollmentRole.choices,
        default=EnrollmentRole.STUDENT,
    )
    status = models.CharField(
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completed_lessons_count = models.PositiveIntegerField(default=0)
    current_grade_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    current_grade_letter = models.CharField(max_length=5, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                condition=models.Q(cohort__isnull=True),
                name="learning_enrollment_unique_user_course_async",
            ),
            models.UniqueConstraint(
                fields=["user", "course", "cohort"],
                condition=models.Q(cohort__isnull=False),
                name="learning_enrollment_unique_user_course_cohort",
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.course.slug}"
