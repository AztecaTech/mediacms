"""Parse @username mentions and create in-app notifications for course members."""

from __future__ import annotations

import re

from django.contrib.auth import get_user_model

from learning.models import Course, Enrollment, EnrollmentStatus, Notification

MENTION_USERNAME_RE = re.compile(r"@([a-zA-Z0-9._-]+)")


def extract_mention_usernames(text: str) -> list[str]:
    if not text:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for match in MENTION_USERNAME_RE.finditer(text):
        raw = match.group(1)
        key = raw.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(raw)
    return ordered


def active_course_member_user_ids(course: Course) -> set[int]:
    enrolled = set(
        Enrollment.objects.filter(
            course=course,
            status=EnrollmentStatus.ACTIVE,
        ).values_list("user_id", flat=True)
    )
    instructors = set(course.instructors.values_list("id", flat=True))
    return enrolled | instructors


def resolve_mentioned_user_ids(course: Course, usernames: list[str]) -> list[int]:
    """Return user IDs that match usernames (case-insensitive) and are active course members."""
    if not usernames:
        return []
    allowed = active_course_member_user_ids(course)
    User = get_user_model()
    out: list[int] = []
    seen: set[int] = set()
    for un in usernames:
        u = User.objects.filter(username__iexact=un).first()
        if u and u.id in allowed and u.id not in seen:
            seen.add(u.id)
            out.append(u.id)
    return out


class MentionInAppNotificationDispatcher:
    """Creates Notification rows for @mentions; skips the actor."""

    def __init__(
        self,
        *,
        course: Course,
        actor_id: int,
        body: str,
        title: str,
        url: str,
        related_object_type: str,
        related_object_id: int,
    ):
        self._course = course
        self._actor_id = actor_id
        self._body = body
        self._title = title
        self._url = url
        self._related_object_type = related_object_type
        self._related_object_id = related_object_id

    def dispatch(self) -> int:
        names = extract_mention_usernames(self._body)
        if not names:
            return 0
        user_ids = resolve_mentioned_user_ids(self._course, names)
        rows = [
            Notification(
                recipient_id=uid,
                type="mention",
                title=self._title,
                body=(self._body or "")[:300],
                url=self._url,
                related_object_type=self._related_object_type,
                related_object_id=self._related_object_id,
            )
            for uid in user_ids
            if uid and uid != self._actor_id
        ]
        if not rows:
            return 0
        Notification.objects.bulk_create(rows)
        return len(rows)
