"""Course roster search for @mention autocomplete (active members + instructors)."""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.mention_notifications import active_course_member_user_ids
from learning.models import Course
from learning.permissions import is_active_course_member


class CourseMemberSearchView(APIView):
    def get(self, request, slug):
        course = get_object_or_404(Course, slug=slug)
        if not request.user.is_authenticated or not is_active_course_member(request.user, course):
            return Response({"detail": "Forbidden"}, status=403)
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 1:
            return Response({"results": []})
        try:
            limit = min(int(request.query_params.get("limit") or 15), 50)
        except ValueError:
            limit = 15
        allowed = active_course_member_user_ids(course)
        User = get_user_model()
        qs = User.objects.filter(pk__in=allowed).filter(
            Q(username__icontains=q) | Q(name__icontains=q) | Q(email__icontains=q)
        ).order_by("username")[:limit]
        results = [
            {
                "id": u.id,
                "username": getattr(u, "username", str(u.pk)),
                "name": getattr(u, "name", "") or "",
            }
            for u in qs
        ]
        return Response({"results": results})
