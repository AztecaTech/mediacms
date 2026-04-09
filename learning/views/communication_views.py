"""Discussions, announcements, and in-app notifications (Phase 5 API)."""

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.events import emit_event
from learning.methods.announcement_notifications import AnnouncementInAppNotificationBroadcaster
from learning.methods.mention_notifications import MentionInAppNotificationDispatcher
from learning.models import Announcement, Course, Discussion, DiscussionPost, Notification
from learning.models import DiscussionNotificationPreference
from learning.permissions import is_active_course_member, is_course_staff
from learning.serializers.communication import (
    AnnouncementSerializer,
    DiscussionListSerializer,
    DiscussionNotificationPreferenceSerializer,
    DiscussionPostCreateSerializer,
    DiscussionStaffPatchSerializer,
    DiscussionWriteSerializer,
    NotificationSerializer,
)


def _author_display(post: DiscussionPost):
    u = post.author
    return (u.get_full_name() or "").strip() or u.username


def _build_post_tree(posts):
    """Build nested replies from a list ordered by MPTT lft (single-query friendly)."""
    nodes = {}
    roots = []
    for p in posts:
        nodes[p.id] = {
            "id": p.id,
            "parent_id": p.parent_id,
            "author_id": p.author_id,
            "author_display": _author_display(p),
            "body": p.body,
            "is_instructor_answer": p.is_instructor_answer,
            "edited_at": p.edited_at.isoformat() if p.edited_at else None,
            "created_at": p.created_at.isoformat(),
            "replies": [],
        }
    for p in posts:
        n = nodes[p.id]
        if p.parent_id is None:
            roots.append(n)
        else:
            parent = nodes.get(p.parent_id)
            if parent is not None:
                parent["replies"].append(n)
            else:
                roots.append(n)
    return roots


def _single_post_dict(post: DiscussionPost):
    return {
        "id": post.id,
        "parent_id": post.parent_id,
        "author_id": post.author_id,
        "author_display": _author_display(post),
        "body": post.body,
        "is_instructor_answer": post.is_instructor_answer,
        "edited_at": post.edited_at.isoformat() if post.edited_at else None,
        "created_at": post.created_at.isoformat(),
        "replies": [],
    }


class CourseDiscussionsListView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_active_course_member(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        qs = Discussion.objects.filter(course=course).select_related("created_by")
        lesson_id = request.query_params.get("lesson")
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        data = DiscussionListSerializer(qs[:200], many=True).data
        return Response({"discussions": data})

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_active_course_member(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = DiscussionWriteSerializer(data=request.data, context={"course": course, "request": request})
        ser.is_valid(raise_exception=True)
        d = Discussion.objects.create(
            course=course,
            created_by=request.user,
            title=ser.validated_data["title"],
            lesson=ser.validated_data.get("lesson"),
            is_pinned=ser.validated_data.get("is_pinned", False) and is_course_staff(request.user, course),
            is_locked=ser.validated_data.get("is_locked", False) and is_course_staff(request.user, course),
        )
        emit_event(
            "discussion_created",
            user=request.user,
            course=course,
            lesson=d.lesson,
            metadata={"discussion_id": d.id},
        )
        return Response(DiscussionListSerializer(d).data, status=status.HTTP_201_CREATED)


class DiscussionDetailView(APIView):
    def get(self, request, pk):
        d = get_object_or_404(Discussion.objects.select_related("course", "created_by"), pk=pk)
        if not request.user.is_authenticated or not is_active_course_member(request.user, d.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(DiscussionListSerializer(d).data)

    def patch(self, request, pk):
        d = get_object_or_404(Discussion, pk=pk)
        if not request.user.is_authenticated or not is_course_staff(request.user, d.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = DiscussionStaffPatchSerializer(d, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        d.refresh_from_db()
        return Response(DiscussionListSerializer(d).data)


class DiscussionPostsListCreateView(APIView):
    def get(self, request, pk):
        d = get_object_or_404(Discussion, pk=pk)
        if not request.user.is_authenticated or not is_active_course_member(request.user, d.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ordered = list(d.posts.all().select_related("author").order_by("tree_id", "lft"))
        tree = _build_post_tree(ordered)
        return Response({"posts": tree})

    def post(self, request, pk):
        d = get_object_or_404(Discussion, pk=pk)
        if not request.user.is_authenticated or not is_active_course_member(request.user, d.course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = DiscussionPostCreateSerializer(
            data=request.data,
            context={"discussion": d, "request": request},
        )
        ser.is_valid(raise_exception=True)
        inst_flag = bool(ser.validated_data.get("is_instructor_answer"))
        if inst_flag and not is_course_staff(request.user, d.course):
            return Response({"detail": "Only staff can mark instructor answers."}, status=status.HTTP_403_FORBIDDEN)
        post = DiscussionPost.objects.create(
            discussion=d,
            author=request.user,
            parent=ser.validated_data.get("parent"),
            body=ser.validated_data["body"],
            is_instructor_answer=inst_flag and is_course_staff(request.user, d.course),
        )
        Notification.objects.bulk_create(
            [
                Notification(
                    recipient_id=uid,
                    type="discussion_reply",
                    title=f"New reply in {d.title}",
                    body=post.body[:300],
                    url=f"/learn/{d.course.slug}",
                    related_object_type="discussion_post",
                    related_object_id=post.id,
                )
                for uid in set(d.posts.exclude(author_id=request.user.id).values_list("author_id", flat=True))
                if uid and uid != request.user.id
            ]
        )
        try:
            from learning.tasks import send_discussion_reply_email_task

            if bool(getattr(settings, "LMS_DISCUSSION_SUBSCRIPTION_EMAIL_ASYNC", True)):
                send_discussion_reply_email_task.delay(post.id, request.user.id)
            else:
                send_discussion_reply_email_task(post.id, request.user.id)
        except Exception:
            from learning.methods.discussion_subscription_email import DiscussionReplyEmailFanoutManager

            DiscussionReplyEmailFanoutManager(d, post, request.user.id).dispatch()
        MentionInAppNotificationDispatcher(
            course=d.course,
            actor_id=request.user.id,
            body=post.body,
            title=f"You were mentioned in {d.title}",
            url=f"/learn/{d.course.slug}",
            related_object_type="discussion_post",
            related_object_id=post.id,
        ).dispatch()
        try:
            from learning.tasks import send_mention_email_task

            if bool(getattr(settings, "LMS_MENTION_EMAIL_ASYNC", True)):
                send_mention_email_task.delay(post.id, "discussion_post", request.user.id)
            else:
                send_mention_email_task(post.id, "discussion_post", request.user.id)
        except Exception:
            from learning.methods.mention_email import MentionEmailFanoutManager

            MentionEmailFanoutManager(
                course=d.course,
                actor_id=request.user.id,
                body=post.body,
                subject=f"[{d.course.title}] You were mentioned in {d.title}",
                intro_line=f"You were mentioned in the discussion “{d.title}”.",
            ).dispatch()
        emit_event(
            "discussion_post_created",
            user=request.user,
            course=d.course,
            lesson=d.lesson,
            metadata={"discussion_id": d.id, "post_id": post.id},
        )
        post = DiscussionPost.objects.select_related("author").get(pk=post.pk)
        return Response(_single_post_dict(post), status=status.HTTP_201_CREATED)


class CourseAnnouncementsListView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_active_course_member(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        qs = Announcement.objects.filter(course=course).select_related("author").order_by("-is_pinned", "-published_at")
        return Response({"announcements": AnnouncementSerializer(qs[:100], many=True).data})

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_course_staff(request.user, course):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = AnnouncementSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ann = Announcement.objects.create(
            course=course,
            author=request.user,
            title=ser.validated_data["title"],
            body=ser.validated_data["body"],
            is_pinned=ser.validated_data.get("is_pinned", False),
            send_email=ser.validated_data.get("send_email", False),
        )
        AnnouncementInAppNotificationBroadcaster(ann, course, request.user.id).dispatch()
        if ann.send_email:
            try:
                from learning.tasks import send_announcement_email_task

                if bool(getattr(settings, "LMS_ANNOUNCEMENT_EMAIL_ASYNC", True)):
                    send_announcement_email_task.delay(ann.id, request.user.id)
                else:
                    send_announcement_email_task(ann.id, request.user.id)
            except Exception:
                # Fall back to sync dispatch when celery isn't available in-process.
                from learning.methods.announcement_email import AnnouncementEmailFanoutManager

                AnnouncementEmailFanoutManager(ann, course, request.user.id).dispatch()
        MentionInAppNotificationDispatcher(
            course=course,
            actor_id=request.user.id,
            body=ann.body,
            title=f"You were mentioned: {ann.title}",
            url=f"/learn/{course.slug}",
            related_object_type="announcement",
            related_object_id=ann.id,
        ).dispatch()
        try:
            from learning.tasks import send_mention_email_task

            if bool(getattr(settings, "LMS_MENTION_EMAIL_ASYNC", True)):
                send_mention_email_task.delay(ann.id, "announcement", request.user.id)
            else:
                send_mention_email_task(ann.id, "announcement", request.user.id)
        except Exception:
            from learning.methods.mention_email import MentionEmailFanoutManager

            MentionEmailFanoutManager(
                course=course,
                actor_id=request.user.id,
                body=ann.body,
                subject=f"[{course.title}] You were mentioned: {ann.title}",
                intro_line=f"You were mentioned in an announcement: {ann.title}",
            ).dispatch()
        emit_event(
            "announcement_created",
            user=request.user,
            course=course,
            metadata={"announcement_id": ann.id},
        )
        return Response(AnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)


class NotificationsListView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        unread_only = request.query_params.get("unread") in ("1", "true", "yes")
        qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
        if unread_only:
            qs = qs.filter(read_at__isnull=True)
        return Response({"notifications": NotificationSerializer(qs[:100], many=True).data})


class NotificationDetailView(APIView):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        n = get_object_or_404(Notification, pk=pk, recipient=request.user)
        return Response(NotificationSerializer(n).data)

    def patch(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        n = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if request.data.get("read") is True or request.data.get("mark_read") is True:
            if n.read_at is None:
                n.read_at = timezone.now()
                n.save(update_fields=["read_at"])
        return Response(NotificationSerializer(n).data)


class DiscussionNotificationPreferencesView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        pref, _ = DiscussionNotificationPreference.objects.get_or_create(user=request.user)
        return Response(DiscussionNotificationPreferenceSerializer(pref).data)

    def patch(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        pref, _ = DiscussionNotificationPreference.objects.get_or_create(user=request.user)
        ser = DiscussionNotificationPreferenceSerializer(pref, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)
