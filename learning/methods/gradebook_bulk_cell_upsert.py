"""Batch upsert of gradebook cells for instructor matrix editing."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from learning.methods.grade_aggregation import recalculate_enrollment_weighted_grade
from learning.models import Enrollment, Grade, GradeItem


class GradebookBulkCellUpsertManager:
    """Applies multiple cell updates within one course; recalculates each affected enrollment once."""

    def __init__(self, course, actor):
        self._course = course
        self._actor = actor

    def apply(self, cells: Any) -> dict[str, list]:
        results: list[dict] = []
        errors: list[dict] = []
        recalc_ids: set[int] = set()

        if not isinstance(cells, list):
            return {"results": [], "errors": [{"index": None, "detail": "cells must be a list."}]}

        for i, cell in enumerate(cells):
            if not isinstance(cell, dict):
                errors.append({"index": i, "detail": "Each cell must be an object."})
                continue
            enr_id = cell.get("enrollment_id")
            item_id = cell.get("grade_item_id")
            if enr_id is None or item_id is None:
                errors.append({"index": i, "detail": "enrollment_id and grade_item_id are required."})
                continue

            enrollment = Enrollment.objects.filter(id=enr_id, course=self._course).first()
            if not enrollment:
                errors.append({"index": i, "detail": "Unknown enrollment for this course."})
                continue
            grade_item = GradeItem.objects.filter(id=item_id, category__course=self._course).first()
            if not grade_item:
                errors.append({"index": i, "detail": "Unknown grade item for this course."})
                continue

            defaults = {
                "feedback": str(cell.get("feedback") or ""),
                "excused": bool(cell.get("excused", False)),
                "is_override": bool(cell.get("is_override", True)),
                "graded_by": self._actor,
                "graded_at": timezone.now(),
            }
            points = cell.get("points_earned")
            defaults["points_earned"] = points if points not in ("", None) else None

            grade, _ = Grade.objects.update_or_create(
                enrollment=enrollment,
                grade_item=grade_item,
                defaults=defaults,
            )
            recalc_ids.add(enrollment.id)
            results.append(
                {
                    "index": i,
                    "grade_id": grade.id,
                    "enrollment_id": enrollment.id,
                    "grade_item_id": grade_item.id,
                    "points_earned": str(grade.points_earned) if grade.points_earned is not None else None,
                    "excused": grade.excused,
                    "feedback": grade.feedback,
                }
            )

        for eid in recalc_ids:
            enr = Enrollment.objects.get(pk=eid)
            recalculate_enrollment_weighted_grade(enr)

        return {"results": results, "errors": errors}
