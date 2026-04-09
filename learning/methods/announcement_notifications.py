"""Create in-app notifications when staff publish course announcements."""

from learning.models import Announcement, Course, Enrollment, EnrollmentStatus, Notification


class AnnouncementInAppNotificationBroadcaster:
    """Fan-out lightweight Notification rows to active enrollments (excludes author)."""

    def __init__(self, announcement: Announcement, course: Course, author_id: int):
        self._announcement = announcement
        self._course = course
        self._author_id = author_id

    def dispatch(self) -> int:
        enrollments = Enrollment.objects.filter(course=self._course, status=EnrollmentStatus.ACTIVE).exclude(
            user_id=self._author_id
        )
        rows = [
            Notification(
                recipient=e.user,
                type="announcement",
                title=self._announcement.title[:255],
                body=(self._announcement.body or "")[:2000],
                url=f"/courses/{self._course.slug}",
                related_object_type="announcement",
                related_object_id=self._announcement.id,
            )
            for e in enrollments
        ]
        Notification.objects.bulk_create(rows, batch_size=500)
        return len(rows)
