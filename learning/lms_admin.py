"""Django admin registrations for extended LMS models (imported from learning.admin)."""

from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from learning.models import (
    AnalyticsEvent,
    Announcement,
    Answer,
    Assignment,
    Badge,
    BadgeAward,
    Certificate,
    CertificateIssuancePolicy,
    CertificateTemplate,
    Choice,
    CourseMetricsDaily,
    Discussion,
    DiscussionNotificationPreference,
    DiscussionPost,
    Grade,
    GradeCategory,
    GradeItem,
    LetterGradeScheme,
    LdapDirectorySource,
    Notification,
    Question,
    QuestionBank,
    Quiz,
    QuizAttempt,
    Rubric,
    RubricCriterion,
    RubricScore,
    Submission,
    Webhook,
    WebhookDelivery,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


@admin.register(QuestionBank)
class QuestionBankAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at")
    search_fields = ("title",)
    raw_id_fields = ("owner",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "max_attempts", "passing_score_pct")
    raw_id_fields = ("lesson",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "bank", "order", "type", "points")
    list_filter = ("type",)
    raw_id_fields = ("quiz", "bank")
    inlines = [ChoiceInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "enrollment", "status", "score_pct", "attempt_number", "submitted_at")
    list_filter = ("status",)
    raw_id_fields = ("quiz", "enrollment")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "auto_graded", "points_awarded")
    raw_id_fields = ("attempt", "question")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "max_points", "due_at")
    raw_id_fields = ("lesson",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "assignment", "enrollment", "status", "score", "submitted_at")
    list_filter = ("status",)
    raw_id_fields = ("assignment", "enrollment", "graded_by")


class GradeItemInline(admin.TabularInline):
    model = GradeItem
    extra = 0
    raw_id_fields = ("quiz", "assignment")


@admin.register(GradeCategory)
class GradeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "weight_pct", "order")
    list_filter = ("course",)
    raw_id_fields = ("course",)
    inlines = [GradeItemInline]


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "grade_item", "points_earned", "excused")
    raw_id_fields = ("enrollment", "grade_item", "graded_by")


class RubricCriterionInline(admin.TabularInline):
    model = RubricCriterion
    extra = 0


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ("id", "grade_item", "title")
    raw_id_fields = ("grade_item",)
    inlines = [RubricCriterionInline]


@admin.register(RubricScore)
class RubricScoreAdmin(admin.ModelAdmin):
    list_display = ("grade", "criterion", "points_awarded")
    raw_id_fields = ("grade", "criterion")


@admin.register(LetterGradeScheme)
class LetterGradeSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "course")
    raw_id_fields = ("course",)


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "lesson", "is_pinned", "last_activity_at")
    list_filter = ("course",)
    raw_id_fields = ("course", "lesson", "created_by")


@admin.register(DiscussionPost)
class DiscussionPostAdmin(MPTTModelAdmin):
    list_display = ("discussion", "author", "created_at", "is_instructor_answer")
    raw_id_fields = ("discussion", "author", "parent")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "author", "published_at", "is_pinned")
    raw_id_fields = ("course", "author")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "type", "title", "read_at", "created_at")
    list_filter = ("type",)
    raw_id_fields = ("recipient",)
    readonly_fields = ("created_at",)


@admin.register(DiscussionNotificationPreference)
class DiscussionNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "email_replies", "frequency", "updated_at")
    list_filter = ("email_replies", "frequency")
    raw_id_fields = ("user",)


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "owner")
    raw_id_fields = ("owner",)


@admin.register(CertificateIssuancePolicy)
class CertificateIssuancePolicyAdmin(admin.ModelAdmin):
    list_display = ("course", "template", "auto_issue")
    raw_id_fields = ("course", "template")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "verification_code", "issued_at", "revoked_at")
    raw_id_fields = ("enrollment", "issued_by")
    search_fields = ("verification_code",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BadgeAward)
class BadgeAwardAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_at")
    raw_id_fields = ("user", "badge", "awarded_by")


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "owner", "is_active", "last_delivered_at")
    raw_id_fields = ("owner",)


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("webhook", "event_type", "status", "response_code", "attempted_at")
    raw_id_fields = ("webhook",)


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("type", "user", "course", "timestamp")
    list_filter = ("type",)
    raw_id_fields = ("user", "course", "lesson")
    date_hierarchy = "timestamp"


@admin.register(CourseMetricsDaily)
class CourseMetricsDailyAdmin(admin.ModelAdmin):
    list_display = ("course", "date", "enrollments_total", "completions_total")
    raw_id_fields = ("course",)


@admin.register(LdapDirectorySource)
class LdapDirectorySourceAdmin(admin.ModelAdmin):
    list_display = ("name", "server_uri", "enabled", "last_sync_at")
    list_filter = ("enabled",)
    search_fields = ("name", "server_uri")
