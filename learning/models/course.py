from django.conf import settings
from django.db import models
from django.utils.text import slugify


class CourseDifficulty(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"


class CourseMode(models.TextChoices):
    ASYNC = "async", "Async"
    COHORT = "cohort", "Cohort"


class CourseEnrollmentType(models.TextChoices):
    OPEN = "open", "Open"
    INVITE = "invite", "Invite only"
    RBAC_GROUP = "rbac_group", "RBAC group"
    APPROVAL = "approval", "Approval required"


class CourseStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, db_index=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="learning/course_thumbnails/%Y/%m/", blank=True, null=True)
    language = models.CharField(max_length=32, default="en")
    difficulty = models.CharField(
        max_length=20,
        choices=CourseDifficulty.choices,
        default=CourseDifficulty.BEGINNER,
    )
    category = models.ForeignKey(
        "files.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lms_courses",
    )
    mode = models.CharField(max_length=20, choices=CourseMode.choices, default=CourseMode.ASYNC)
    enrollment_type = models.CharField(
        max_length=20,
        choices=CourseEnrollmentType.choices,
        default=CourseEnrollmentType.OPEN,
    )
    rbac_group = models.ForeignKey(
        "rbac.RBACGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lms_courses",
    )
    prerequisites = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="dependent_courses",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=CourseStatus.choices,
        default=CourseStatus.DRAFT,
    )
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="courses_teaching",
        blank=True,
    )
    estimated_hours = models.PositiveIntegerField(default=0)
    enrolled_count = models.PositiveIntegerField(default=0)
    avg_completion_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "course"
            slug = base
            n = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)
