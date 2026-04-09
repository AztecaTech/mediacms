"""Recompute `LessonMetrics` from `LessonProgress` (and light `AnalyticsEvent` use)."""

from __future__ import annotations

from statistics import median

from django.db.models import Avg, Q

from learning.models import AnalyticsEvent, Lesson, LessonMetrics, LessonProgress, LessonProgressStatus


def _median_int(values: list[int]) -> int | None:
    if not values:
        return None
    return int(round(median(values)))


class LessonMetricsSyncManager:
    """One-shot sync for all lessons or a single course."""

    @classmethod
    def sync_lesson(cls, lesson: Lesson) -> LessonMetrics:
        qs = LessonProgress.objects.filter(lesson=lesson)
        completed = qs.filter(status=LessonProgressStatus.COMPLETED).count()
        started = qs.filter(
            status__in=(LessonProgressStatus.IN_PROGRESS, LessonProgressStatus.COMPLETED),
        ).count()
        viewed = qs.filter(
            ~Q(status=LessonProgressStatus.NOT_STARTED)
            | Q(time_spent_seconds__gt=0)
            | Q(last_position_seconds__gt=0)
        ).count()
        agg = qs.aggregate(avg_time=Avg("time_spent_seconds"))
        avg_time = int(round(agg["avg_time"] or 0))
        in_prog_positions = list(
            qs.filter(status=LessonProgressStatus.IN_PROGRESS).values_list("last_position_seconds", flat=True)
        )
        drop_off = _median_int([int(x) for x in in_prog_positions if x is not None])
        m, _ = LessonMetrics.objects.update_or_create(
            lesson=lesson,
            defaults={
                "view_count": max(viewed, started),
                "started_count": started,
                "completed_count": completed,
                "avg_time_seconds": max(0, avg_time),
                "drop_off_after_seconds": drop_off,
            },
        )
        return m

    @classmethod
    def sync_all(cls, *, course_id: int | None = None, limit: int | None = None) -> int:
        q = Lesson.objects.all().select_related("module__course")
        if course_id:
            q = q.filter(module__course_id=course_id)
        n = 0
        for lesson in q.iterator(chunk_size=200):
            cls.sync_lesson(lesson)
            n += 1
            if limit and n >= limit:
                break
        return n


class AnalyticsEventLessonBackfillManager:
    """Attach lesson FK on recent events where metadata carries lesson_id (best-effort)."""

    @classmethod
    def backfill_lesson_fk(cls, batch: int = 2000) -> int:
        fixed = 0
        qs = AnalyticsEvent.objects.filter(lesson__isnull=True, metadata__has_key="lesson_id").order_by("-id")[:batch]
        for ev in qs:
            lid = ev.metadata.get("lesson_id")
            if not lid:
                continue
            if not Lesson.objects.filter(pk=lid).exists():
                continue
            ev.lesson_id = int(lid)
            ev.save(update_fields=["lesson"])
            fixed += 1
        return fixed
