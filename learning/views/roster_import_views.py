"""Instructor roster CSV import (multipart upload)."""

from django.shortcuts import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.roster_csv_import import RosterCsvImportError, RosterCsvImportManager
from learning.models import Course
from learning.permissions import is_course_instructor


class CourseRosterCsvImportView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
        course = get_object_or_404(Course, slug=slug)
        if not is_course_instructor(request.user, course):
            return Response({"detail": "Forbidden"}, status=403)

        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Missing multipart field `file`."}, status=400)

        raw = upload.read()
        try:
            decoded = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"detail": "File must be UTF-8 encoded."}, status=400)

        try:
            summary = RosterCsvImportManager(course, request.user).run(decoded)
        except RosterCsvImportError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(
            {
                "created": summary.created,
                "updated": summary.updated,
                "failed": summary.failed,
                "rows": summary.rows,
            }
        )
