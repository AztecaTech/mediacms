"""Heuristics for learner at-risk signals (org / manager dashboards)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Q

from learning.models import Enrollment, EnrollmentRole, EnrollmentStatus


@dataclass(frozen=True)
class AtRiskTierResult:
    tier: str
    reasons: tuple[str, ...]


class AtRiskScoringManager:
    """
    Assigns coarse tiers from progress and recorded course grade.
    Tiers: none < low < medium < high (severity increases).
    """

    def __init__(
        self,
        *,
        progress_high: Decimal = Decimal("15"),
        progress_medium: Decimal = Decimal("25"),
        progress_low: Decimal = Decimal("40"),
        grade_high: Decimal = Decimal("50"),
        grade_medium: Decimal = Decimal("60"),
        grade_low: Decimal = Decimal("70"),
    ):
        self._progress_high = progress_high
        self._progress_medium = progress_medium
        self._progress_low = progress_low
        self._grade_high = grade_high
        self._grade_medium = grade_medium
        self._grade_low = grade_low

    def tier_for(self, progress_pct: Decimal, grade_pct: Decimal | None) -> AtRiskTierResult:
        reasons: list[str] = []
        tier_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
        tier = "none"

        def bump(new_tier: str, reason: str) -> None:
            nonlocal tier
            if tier_order[new_tier] > tier_order[tier]:
                tier = new_tier
            reasons.append(reason)

        p = progress_pct or Decimal("0")
        if p < self._progress_high:
            bump("high", "progress_below_15_pct")
        elif p < self._progress_medium:
            bump("medium", "progress_below_25_pct")
        elif p < self._progress_low:
            bump("low", "progress_below_40_pct")

        if grade_pct is not None:
            g = grade_pct
            if g < self._grade_high:
                bump("high", "grade_below_50_pct")
            elif g < self._grade_medium:
                bump("medium", "grade_below_60_pct")
            elif g < self._grade_low:
                bump("low", "grade_below_70_pct")

        return AtRiskTierResult(tier=tier, reasons=tuple(dict.fromkeys(reasons)))

    def base_queryset(self):
        return Enrollment.objects.filter(
            role=EnrollmentRole.STUDENT,
            status=EnrollmentStatus.ACTIVE,
        ).select_related("user", "course")

    def filter_at_least_tier(self, qs, min_tier: str):
        """DB prefilter to shrink rows before Python tiering (approximate OR of signals)."""
        tier_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
        if tier_order.get(min_tier, 0) <= 0:
            return qs

        q = Q(progress_pct__lt=self._progress_low)
        q |= Q(current_grade_pct__lt=self._grade_low, current_grade_pct__isnull=False)
        if min_tier in ("medium", "high"):
            q |= Q(progress_pct__lt=self._progress_medium)
            q |= Q(current_grade_pct__lt=self._grade_medium, current_grade_pct__isnull=False)
        if min_tier == "high":
            q |= Q(progress_pct__lt=self._progress_high)
            q |= Q(current_grade_pct__lt=self._grade_high, current_grade_pct__isnull=False)
        return qs.filter(q)
