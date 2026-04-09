"""Persist `StudentRiskScore` from `AtRiskScoringManager` tiers."""

from __future__ import annotations

from decimal import Decimal

from learning.methods.at_risk_scoring import AtRiskScoringManager
from learning.models import StudentRiskScore


class StudentRiskScoreSyncManager:
    @classmethod
    def sync_all(cls, *, limit: int | None = None) -> int:
        mgr = AtRiskScoringManager()
        qs = mgr.base_queryset()
        n = 0
        for enr in qs.iterator(chunk_size=500):
            tier_res = mgr.tier_for(Decimal(enr.progress_pct or 0), enr.current_grade_pct)
            model_tier, score = cls._map_tier(tier_res.tier)
            StudentRiskScore.objects.update_or_create(
                enrollment=enr,
                defaults={
                    "tier": model_tier,
                    "score": score,
                    "factors": {"reasons": list(tier_res.reasons), "source_tier": tier_res.tier},
                },
            )
            n += 1
            if limit and n >= limit:
                break
        return n

    @staticmethod
    def _map_tier(raw: str) -> tuple[str, Decimal]:
        """Map scoring tier (none/low/medium/high) to StudentRiskScore fields."""
        if raw == "high":
            return StudentRiskScore.RiskTier.HIGH, Decimal("85")
        if raw == "medium":
            return StudentRiskScore.RiskTier.MEDIUM, Decimal("55")
        if raw == "low":
            return StudentRiskScore.RiskTier.LOW, Decimal("30")
        return StudentRiskScore.RiskTier.LOW, Decimal("5")
