"""Manager-facing at-risk enrollment listing (intervention workflows)."""

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.at_risk_scoring import AtRiskScoringManager
from learning.models import AnalyticsEvent, Enrollment


class OrgAtRiskEnrollmentsView(APIView):
    """
    Lists active student enrollments with heuristic at-risk tiers.
    Query: min_tier=low|medium|high (default low), limit=1..200 (default 50).
    """

    def get(self, request):
        if not request.user.is_authenticated or not getattr(request.user, "is_manager", False):
            return Response({"detail": "Forbidden"}, status=403)

        min_tier = (request.query_params.get("min_tier") or "low").strip().lower()
        if min_tier not in ("low", "medium", "high"):
            return Response({"detail": "min_tier must be low, medium, or high."}, status=400)

        try:
            limit = int(request.query_params.get("limit") or 50)
        except ValueError:
            return Response({"detail": "limit must be an integer."}, status=400)
        limit = max(1, min(limit, 200))

        scorer = AtRiskScoringManager()
        qs = scorer.filter_at_least_tier(scorer.base_queryset(), min_tier).order_by(
            "course__slug", "user__username", "id"
        )

        tier_floor = {"low": 1, "medium": 2, "high": 3}
        floor = tier_floor[min_tier]
        tier_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}

        rows = []
        for enr in qs[: limit * 3]:
            if len(rows) >= limit:
                break
            result = scorer.tier_for(enr.progress_pct, enr.current_grade_pct)
            if tier_rank[result.tier] < floor:
                continue
            u = enr.user
            rows.append(
                {
                    "enrollment_id": enr.id,
                    "user_id": enr.user_id,
                    "username": getattr(u, "username", str(enr.user_id)),
                    "course_slug": enr.course.slug,
                    "course_title": enr.course.title,
                    "progress_pct": str(enr.progress_pct),
                    "current_grade_pct": str(enr.current_grade_pct)
                    if enr.current_grade_pct is not None
                    else None,
                    "current_grade_letter": enr.current_grade_letter or "",
                    "at_risk_tier": result.tier,
                    "at_risk_reasons": list(result.reasons),
                }
            )

        return Response(
            {
                "min_tier": min_tier,
                "limit": limit,
                "count": len(rows),
                "enrollments": rows,
            }
        )


class OrgInterventionNoteView(APIView):
    """Records a manager note against an enrollment (analytics trail for follow-ups)."""

    def post(self, request):
        if not request.user.is_authenticated or not getattr(request.user, "is_manager", False):
            return Response({"detail": "Forbidden"}, status=403)

        try:
            enrollment_id = int(request.data.get("enrollment_id"))
        except (TypeError, ValueError):
            return Response({"detail": "enrollment_id is required and must be an integer."}, status=400)

        note = (request.data.get("note") or "").strip()
        if not note:
            return Response({"detail": "note is required."}, status=400)
        if len(note) > 2000:
            return Response({"detail": "note must be at most 2000 characters."}, status=400)

        enr = get_object_or_404(Enrollment.objects.select_related("course"), pk=enrollment_id)
        ev = AnalyticsEvent.objects.create(
            type="manager_intervention_note",
            user=request.user,
            course=enr.course,
            metadata={
                "enrollment_id": enr.id,
                "target_user_id": enr.user_id,
                "note": note,
            },
        )
        return Response({"id": ev.id, "enrollment_id": enr.id}, status=201)
