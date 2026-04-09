"""Email fan-out for discussion reply subscriptions (phase 5 enhancement)."""

from django.conf import settings
from django.core.mail import send_mail

from learning.models import (
    Discussion,
    DiscussionNotificationFrequency,
    DiscussionNotificationPreference,
    DiscussionPost,
    Enrollment,
    EnrollmentStatus,
    Notification,
)


class DiscussionReplyEmailFanoutManager:
    """
    Basic subscription model: notify active participants in a discussion thread.
    Participants = prior post authors + discussion creator, excluding current author.
    """

    def __init__(self, discussion: Discussion, post: DiscussionPost, author_id: int):
        self._discussion = discussion
        self._post = post
        self._author_id = author_id

    def _participant_user_ids(self):
        ids = set(self._discussion.posts.values_list("author_id", flat=True))
        if self._discussion.created_by_id:
            ids.add(self._discussion.created_by_id)
        ids.discard(self._author_id)
        if not ids:
            return []
        enrolled = Enrollment.objects.filter(
            course=self._discussion.course,
            status=EnrollmentStatus.ACTIVE,
            user_id__in=ids,
        ).values_list("user_id", flat=True)
        return list(enrolled)

    def _recipient_emails(self):
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        emails = []
        for uid in self._participant_user_ids():
            pref = (
                DiscussionNotificationPreference.objects.filter(user_id=uid)
                .only("email_replies", "frequency")
                .first()
            )
            if pref and (not pref.email_replies or pref.frequency != DiscussionNotificationFrequency.IMMEDIATE):
                continue
            user = user_model.objects.filter(id=uid).first()
            if not user:
                continue
            email = (getattr(user, "email", "") or "").strip()
            if email:
                emails.append((uid, email))
        return emails

    def dispatch(self):
        course = self._discussion.course
        subject = f"[{course.title}] New reply in: {self._discussion.title}"
        body = (
            f"{self._discussion.title}\n\n"
            f"{self._post.body}\n\n"
            f"Open thread: /learn/{course.slug}\n"
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")
        sent_user_ids = []
        failed = 0
        for user_id, email in self._recipient_emails():
            try:
                send_mail(subject, body, from_email, [email], fail_silently=False)
                sent_user_ids.append(user_id)
            except Exception:
                failed += 1
        if sent_user_ids:
            Notification.objects.filter(
                recipient_id__in=sent_user_ids,
                related_object_type="discussion_post",
                related_object_id=self._post.id,
            ).update(email_sent=True)
        return {"sent": len(sent_user_ids), "failed": failed}


class DiscussionDigestEmailFanoutManager:
    """Daily digest for pending discussion_reply notifications."""

    def __init__(self, user):
        self._user = user

    def dispatch(self):
        pref = (
            DiscussionNotificationPreference.objects.filter(user=self._user)
            .only("email_replies", "frequency")
            .first()
        )
        if pref and (not pref.email_replies or pref.frequency != DiscussionNotificationFrequency.DAILY):
            return {"sent": 0, "failed": 0, "skipped": True}
        pending = list(
            Notification.objects.filter(
                recipient=self._user,
                type="discussion_reply",
                email_sent=False,
            )
            .order_by("-created_at")[:25]
        )
        if not pending:
            return {"sent": 0, "failed": 0}
        lines = [f"- {n.title}" for n in pending]
        subject = "Your LMS discussion digest"
        body = "You have new discussion replies:\n\n" + "\n".join(lines)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")
        email = (getattr(self._user, "email", "") or "").strip()
        if not email:
            return {"sent": 0, "failed": 1}
        try:
            send_mail(subject, body, from_email, [email], fail_silently=False)
        except Exception:
            return {"sent": 0, "failed": 1}
        Notification.objects.filter(id__in=[n.id for n in pending]).update(email_sent=True)
        return {"sent": 1, "failed": 0, "count": len(pending)}
