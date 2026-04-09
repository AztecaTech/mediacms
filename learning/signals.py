from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from learning.methods import refresh_course_enrolled_count
from learning.methods.discussion_counters import refresh_discussion_after_post_change
from learning.models import (
    CourseAuditAction,
    CourseAuditLog,
    CourseEnrollmentType,
    CourseMode,
    DiscussionPost,
    Enrollment,
    EnrollmentRole,
    EnrollmentStatus,
)
from rbac.models import RBACMembership


@receiver(post_save, sender=RBACMembership)
def rbac_membership_auto_enroll(sender, instance, **kwargs):
    from learning.models import Course

    group = instance.rbac_group
    for course in Course.objects.filter(
        enrollment_type=CourseEnrollmentType.RBAC_GROUP,
        rbac_group=group,
        status="published",
    ):
        if course.mode == CourseMode.COHORT:
            continue
        Enrollment.objects.get_or_create(
            user=instance.user,
            course=course,
            cohort=None,
            defaults={
                "role": EnrollmentRole.STUDENT,
                "status": EnrollmentStatus.ACTIVE,
            },
        )
        refresh_course_enrolled_count(course)


def write_audit(user, course, action, metadata=None):
    CourseAuditLog.objects.create(
        user=user,
        course=course,
        action=action,
        metadata=metadata or {},
    )


@receiver(post_save, sender=DiscussionPost)
@receiver(post_delete, sender=DiscussionPost)
def discussion_post_refresh_thread(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    refresh_discussion_after_post_change(instance.discussion_id)
