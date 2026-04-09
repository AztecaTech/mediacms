from django.contrib import admin

from learning.models import (
    Cohort,
    Course,
    CourseAuditLog,
    Enrollment,
    LearningPath,
    LearningPathCourse,
    Lesson,
    LessonDraft,
    LessonProgress,
    Module,
)


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0
    show_change_link = True


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    raw_id_fields = ("media",)
    filter_horizontal = ("prerequisites",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "mode", "enrollment_type", "updated_at")
    list_filter = ("status", "mode", "enrollment_type", "difficulty")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("instructors", "prerequisites")
    raw_id_fields = ("category", "rbac_group")
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "release_offset_days")
    list_filter = ("course",)
    search_fields = ("title",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "order", "content_type")
    list_filter = ("content_type",)
    search_fields = ("title",)
    raw_id_fields = ("module", "media")
    filter_horizontal = ("prerequisites",)


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "start_date", "status")
    list_filter = ("status",)
    raw_id_fields = ("course",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "cohort", "role", "status", "progress_pct")
    list_filter = ("role", "status")
    raw_id_fields = ("user", "course", "cohort")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "lesson", "status", "progress_pct")
    raw_id_fields = ("enrollment", "lesson")


class LearningPathCourseInline(admin.TabularInline):
    model = LearningPathCourse
    extra = 0
    raw_id_fields = ("course",)


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LearningPathCourseInline]


@admin.register(LessonDraft)
class LessonDraftAdmin(admin.ModelAdmin):
    list_display = ("lesson", "author", "updated_at")
    raw_id_fields = ("lesson", "author")


@admin.register(CourseAuditLog)
class CourseAuditLogAdmin(admin.ModelAdmin):
    list_display = ("course", "action", "user", "created_at")
    list_filter = ("action",)
    raw_id_fields = ("user", "course")
    readonly_fields = ("user", "course", "action", "metadata", "created_at")


from learning import lms_admin  # noqa: E402, F401
