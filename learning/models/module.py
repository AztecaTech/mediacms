from django.db import models


class Module(models.Model):
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    release_offset_days = models.PositiveIntegerField(
        default=0,
        help_text="Days after cohort start_date before this module unlocks (cohort mode).",
    )

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "order"], name="learning_module_unique_course_order"),
        ]

    def __str__(self):
        return f"{self.course.slug}: {self.title}"
