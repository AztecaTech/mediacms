"""Email fan-out for LMS announcements."""

from django.conf import settings
from django.core.mail import send_mail

from learning.models import Announcement, Course, Enrollment, EnrollmentStatus, Notification


class AnnouncementEmailFanoutManager:
    """Send one email per recipient and mark related notifications as emailed."""

    def __init__(self, announcement: Announcement, course: Course, author_id: int):
        self._announcement = announcement
        self._course = course
        self._author_id = author_id

    def _recipient_emails(self):
        qs = (
            Enrollment.objects.filter(course=self._course, status=EnrollmentStatus.ACTIVE)
            .exclude(user_id=self._author_id)
            .select_related("user")
        )
        rows = []
        for e in qs:
            email = (getattr(e.user, "email", "") or "").strip()
            if not email:
                continue
            rows.append((e.user_id, email))
        return rows

    def dispatch(self) -> dict:
        subject = f"[{self._course.title}] {self._announcement.title}"
        body = (
            f"{self._announcement.title}\n\n"
            f"{self._announcement.body}\n\n"
            f"Open course: /courses/{self._course.slug}\n"
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")
        sent_user_ids = []
        failed = 0

        for user_id, email in self._recipient_emails():
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=from_email,
                    recipient_list=[email],
                    fail_silently=False,
                )
                sent_user_ids.append(user_id)
            except Exception:
                failed += 1

        if sent_user_ids:
            Notification.objects.filter(
                recipient_id__in=sent_user_ids,
                related_object_type="announcement",
                related_object_id=self._announcement.id,
            ).update(email_sent=True)

        return {"sent": len(sent_user_ids), "failed": failed}
