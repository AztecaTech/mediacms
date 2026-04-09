from celery import shared_task
from datetime import date as date_cls
from django.contrib.auth import get_user_model
from django.utils import timezone

from learning.methods.analytics_rollups import rollup_course_metrics_for_date
from learning.methods.announcement_email import AnnouncementEmailFanoutManager
from learning.methods.certificate_issuance import (
    CertificateEligibilityError,
    issue_certificate_for_enrollment,
    regenerate_missing_certificate_pdfs,
)
from learning.methods.discussion_subscription_email import (
    DiscussionDigestEmailFanoutManager,
    DiscussionReplyEmailFanoutManager,
)
from learning.methods.mention_email import MentionEmailFanoutManager
from learning.methods.quiz_attempt_expiry import expire_overdue_quiz_attempts
from learning.methods.webhook_dispatch import dispatch_pending_delivery
from learning.models import Announcement, DiscussionPost, Enrollment, WebhookDelivery


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def issue_certificate_for_enrollment_task(self, enrollment_id: int, issued_by_id: int | None = None):
    enrollment = Enrollment.objects.select_related("course", "user").filter(pk=enrollment_id).first()
    if not enrollment:
        return {"ok": False, "detail": "Enrollment not found."}
    issued_by = None
    if issued_by_id:
        issued_by = get_user_model().objects.filter(pk=issued_by_id).first()
    try:
        cert = issue_certificate_for_enrollment(enrollment, issued_by=issued_by)
        return {"ok": True, "certificate_id": cert.id}
    except CertificateEligibilityError as exc:
        return {"ok": False, "detail": str(exc)}
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def dispatch_webhook_delivery_task(self, delivery_id: int):
    delivery = dispatch_pending_delivery(delivery_id)
    if not delivery:
        return {"ok": False, "detail": "Delivery missing or already delivered."}
    if delivery.status == "failed" and delivery.next_retry_at:
        raise self.retry(countdown=60)
    return {"ok": delivery.status == "delivered", "status": delivery.status, "delivery_id": delivery.id}


@shared_task
def retry_due_webhook_deliveries_task(limit: int = 200):
    now = timezone.now()
    due = WebhookDelivery.objects.filter(
        status="failed",
        next_retry_at__isnull=False,
        next_retry_at__lte=now,
    ).order_by("next_retry_at", "id")[: max(1, int(limit))]
    for d in due:
        dispatch_pending_delivery(d.id)
    return {"processed": len(due)}


@shared_task
def rollup_course_metrics_daily_task(date_iso: str | None = None):
    if date_iso:
        d = date_cls.fromisoformat(date_iso)
    else:
        d = timezone.now().date()
    processed = rollup_course_metrics_for_date(d)
    return {"processed_courses": processed, "date": d.isoformat()}


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_announcement_email_task(self, announcement_id: int, author_id: int | None = None):
    ann = Announcement.objects.select_related("course", "author").filter(pk=announcement_id).first()
    if not ann:
        return {"ok": False, "detail": "Announcement not found."}
    manager = AnnouncementEmailFanoutManager(ann, ann.course, author_id or ann.author_id)
    try:
        stats = manager.dispatch()
    except Exception as exc:
        raise self.retry(exc=exc)
    if stats["sent"] == 0 and stats["failed"] > 0:
        raise self.retry()
    return {"ok": True, **stats}


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_discussion_reply_email_task(self, post_id: int, author_id: int):
    post = DiscussionPost.objects.select_related("discussion", "discussion__course").filter(pk=post_id).first()
    if not post:
        return {"ok": False, "detail": "Discussion post not found."}
    manager = DiscussionReplyEmailFanoutManager(post.discussion, post, author_id)
    try:
        stats = manager.dispatch()
    except Exception as exc:
        raise self.retry(exc=exc)
    if stats["sent"] == 0 and stats["failed"] > 0:
        raise self.retry()
    return {"ok": True, **stats}


@shared_task
def send_discussion_digest_email_task(limit: int = 200):
    User = get_user_model()
    users = User.objects.filter(
        discussion_notification_preference__email_replies=True,
        discussion_notification_preference__frequency="daily",
    ).distinct()[: max(1, int(limit))]
    sent = 0
    failed = 0
    for user in users:
        stats = DiscussionDigestEmailFanoutManager(user).dispatch()
        sent += int(stats.get("sent", 0))
        failed += int(stats.get("failed", 0))
    return {"processed_users": len(users), "sent": sent, "failed": failed}


@shared_task
def regenerate_missing_certificate_pdfs_task(limit: int = 200):
    return {"processed_certificates": regenerate_missing_certificate_pdfs(limit=limit)}


@shared_task
def expire_overdue_quiz_attempts_task(limit: int = 500):
    return {"expired_attempts": expire_overdue_quiz_attempts(limit=limit)}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_mention_email_task(self, related_id: int, kind: str, actor_id: int):
    """kind: discussion_post | announcement"""
    if kind == "discussion_post":
        post = DiscussionPost.objects.select_related("discussion", "discussion__course").filter(pk=related_id).first()
        if not post:
            return {"ok": False, "detail": "Post not found."}
        course = post.discussion.course
        subject = f"[{course.title}] You were mentioned in {post.discussion.title}"
        intro = f"You were mentioned by a participant in the discussion “{post.discussion.title}”."
        manager = MentionEmailFanoutManager(
            course=course,
            actor_id=actor_id,
            body=post.body,
            subject=subject,
            intro_line=intro,
        )
    elif kind == "announcement":
        ann = Announcement.objects.select_related("course").filter(pk=related_id).first()
        if not ann:
            return {"ok": False, "detail": "Announcement not found."}
        subject = f"[{ann.course.title}] You were mentioned: {ann.title}"
        intro = f"You were mentioned in an announcement: {ann.title}"
        manager = MentionEmailFanoutManager(
            course=ann.course,
            actor_id=actor_id,
            body=ann.body,
            subject=subject,
            intro_line=intro,
        )
    else:
        return {"ok": False, "detail": "Unknown kind."}
    try:
        stats = manager.dispatch()
    except Exception as exc:
        raise self.retry(exc=exc)
    return {"ok": True, **stats}


@shared_task
def refresh_lesson_metrics_task():
    """Recompute LessonMetrics from LessonProgress."""
    from learning.methods.lesson_metrics_sync import LessonMetricsSyncManager

    n = LessonMetricsSyncManager.sync_all()
    return {"ok": True, "lessons_updated": n}


@shared_task
def recompute_risk_scores_task():
    """Refresh StudentRiskScore rows from progress + grades."""
    from learning.methods.student_risk_sync import StudentRiskScoreSyncManager

    n = StudentRiskScoreSyncManager.sync_all()
    return {"ok": True, "enrollments_updated": n}
