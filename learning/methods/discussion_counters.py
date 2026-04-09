"""Keep discussion thread aggregates in sync when posts change."""

from django.db.models import Max

from learning.models import Discussion, DiscussionPost


def refresh_discussion_after_post_change(discussion_id: int) -> None:
    qs = DiscussionPost.objects.filter(discussion_id=discussion_id)
    n = qs.count()
    latest = qs.aggregate(m=Max("created_at"))["m"]
    disc = Discussion.objects.filter(pk=discussion_id).only("created_at").first()
    if not disc:
        return
    Discussion.objects.filter(pk=discussion_id).update(
        reply_count=max(0, n - 1),
        last_activity_at=latest or disc.created_at,
    )
