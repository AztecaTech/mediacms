"""Immediate email fan-out for @mentions (respects DiscussionNotificationPreference)."""

from django.conf import settings
from django.core.mail import send_mail

from learning.methods.mention_notifications import extract_mention_usernames, resolve_mentioned_user_ids
from learning.models import Course, DiscussionNotificationFrequency, DiscussionNotificationPreference


class MentionEmailFanoutManager:
    def __init__(
        self,
        *,
        course: Course,
        actor_id: int,
        body: str,
        subject: str,
        intro_line: str,
    ):
        self._course = course
        self._actor_id = actor_id
        self._body = body
        self._subject = subject
        self._intro_line = intro_line

    def _recipient_emails(self) -> list[tuple[int, str]]:
        from django.contrib.auth import get_user_model

        names = extract_mention_usernames(self._body)
        if not names:
            return []
        user_ids = resolve_mentioned_user_ids(self._course, names)
        user_ids = [uid for uid in user_ids if uid != self._actor_id]
        if not user_ids:
            return []
        User = get_user_model()
        out: list[tuple[int, str]] = []
        for uid in user_ids:
            pref = (
                DiscussionNotificationPreference.objects.filter(user_id=uid)
                .only("email_mentions", "frequency")
                .first()
            )
            if pref and not pref.email_mentions:
                continue
            if pref and pref.frequency != DiscussionNotificationFrequency.IMMEDIATE:
                continue
            user = User.objects.filter(pk=uid).first()
            if not user:
                continue
            email = (getattr(user, "email", "") or "").strip()
            if email:
                out.append((uid, email))
        return out

    def dispatch(self) -> dict:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost")
        body = f"{self._intro_line}\n\n{self._body}\n\nOpen: /learn/{self._course.slug}\n"
        sent = 0
        failed = 0
        for _uid, email in self._recipient_emails():
            try:
                send_mail(self._subject, body, from_email, [email], fail_silently=False)
                sent += 1
            except Exception:
                failed += 1
        return {"sent": sent, "failed": failed}
