from django.db import models
from django.utils.text import slugify


class LearningPathStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class LearningPath(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, db_index=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="learning/path_thumbnails/%Y/%m/", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=LearningPathStatus.choices,
        default=LearningPathStatus.DRAFT,
    )
    courses = models.ManyToManyField(
        "learning.Course",
        through="learning.LearningPathCourse",
        related_name="learning_paths",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not (self.slug or "").strip():
            base = slugify(self.title)[:200] or "path"
            slug = base
            n = 1
            while LearningPath.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class LearningPathCourse(models.Model):
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="path_courses")
    course = models.ForeignKey("learning.Course", on_delete=models.CASCADE, related_name="path_links")
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["path", "course"], name="learning_pathcourse_unique_path_course"),
        ]
