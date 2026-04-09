"""Weighted course total + letter grade aggregation."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch

from learning.models import Enrollment, Grade, GradeCategory, GradeItem, LetterGradeScheme


def _dec(v, default="0"):
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal(default)


def _resolve_letter(course, pct: Decimal) -> str:
    scheme = LetterGradeScheme.objects.filter(course=course).order_by("id").first()
    if not scheme:
        return ""
    for band in scheme.bands or []:
        lo = _dec(band.get("min_pct"), "0")
        hi = _dec(band.get("max_pct"), "100")
        if lo <= pct <= hi:
            return str(band.get("letter") or "").strip()[:5]
    return ""


@transaction.atomic
def recalculate_enrollment_weighted_grade(enrollment: Enrollment):
    cats = (
        GradeCategory.objects.filter(course=enrollment.course)
        .prefetch_related(Prefetch("items", queryset=GradeItem.objects.order_by("id")))
        .order_by("order", "id")
    )
    category_scores = []
    for cat in cats:
        item_ids = [it.id for it in cat.items.all()]
        if not item_ids:
            continue
        grades = {
            g.grade_item_id: g
            for g in Grade.objects.filter(enrollment=enrollment, grade_item_id__in=item_ids).select_related("grade_item")
        }
        per_item_pcts = []
        for it in cat.items.all():
            g = grades.get(it.id)
            if not g or g.excused or g.points_earned is None:
                continue
            max_points = _dec(it.max_points, "0")
            if max_points <= 0:
                continue
            per_item_pcts.append((_dec(g.points_earned, "0") / max_points) * Decimal("100"))
        drop_n = int(cat.drop_lowest_n or 0)
        if drop_n > 0 and len(per_item_pcts) > drop_n:
            per_item_pcts = sorted(per_item_pcts)[drop_n:]
        if not per_item_pcts:
            continue
        score = sum(per_item_pcts) / Decimal(len(per_item_pcts))
        category_scores.append((score, _dec(cat.weight_pct, "0")))

    if not category_scores:
        enrollment.current_grade_pct = None
        enrollment.current_grade_letter = ""
        enrollment.save(update_fields=["current_grade_pct", "current_grade_letter"])
        return enrollment

    total_weight = sum(w for _, w in category_scores)
    if total_weight <= 0:
        total = sum(s for s, _ in category_scores) / Decimal(len(category_scores))
    else:
        total = sum((s * w) for s, w in category_scores) / total_weight
    total = total.quantize(Decimal("0.01"))
    enrollment.current_grade_pct = total
    enrollment.current_grade_letter = _resolve_letter(enrollment.course, total)
    enrollment.save(update_fields=["current_grade_pct", "current_grade_letter"])
    return enrollment


def recalculate_course_weighted_grades(course):
    qs = Enrollment.objects.filter(course=course, role="student").only("id")
    count = 0
    for enr in qs:
        recalculate_enrollment_weighted_grade(enr)
        count += 1
    return count
