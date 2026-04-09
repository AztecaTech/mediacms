"""Detect invalid prerequisite chains on lessons (cycles)."""

from __future__ import annotations

from learning.models import Lesson


class LessonPrerequisiteCycleGuard:
    """DFS from proposed prerequisites; if we reach `lesson_pk`, the update would cycle."""

    @classmethod
    def would_create_cycle(cls, lesson_pk: int | None, prerequisite_ids: list[int]) -> bool:
        if not prerequisite_ids:
            return False
        clean = [int(x) for x in prerequisite_ids if x is not None]
        if lesson_pk is not None and lesson_pk in clean:
            return True
        if lesson_pk is None:
            return False
        stack = list(clean)
        seen: set[int] = set()
        while stack:
            lid = stack.pop()
            if lid == lesson_pk:
                return True
            if lid in seen:
                continue
            seen.add(lid)
            next_ids = Lesson.objects.filter(pk=lid).values_list("prerequisites__id", flat=True)
            stack.extend(int(x) for x in next_ids if x)
        return False
