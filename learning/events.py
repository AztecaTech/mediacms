from learning.models import AnalyticsEvent
from learning.methods.webhook_dispatch import maybe_dispatch_event_webhooks


def emit_event(event_type, user=None, course=None, lesson=None, metadata=None):
    evt = AnalyticsEvent.objects.create(
        type=event_type,
        user=user if user and user.is_authenticated else None,
        course=course,
        lesson=lesson,
        metadata=metadata or {},
    )
    payload = {
        "event_id": evt.id,
        "type": evt.type,
        "timestamp": evt.timestamp.isoformat(),
        "user_id": evt.user_id,
        "course_id": evt.course_id,
        "lesson_id": evt.lesson_id,
        "metadata": evt.metadata or {},
    }
    maybe_dispatch_event_webhooks(event_type, payload, course=course)
    return evt
