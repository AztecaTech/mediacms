"""
Minimal Phase-7 integration endpoints.
"""

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class LtiJwksView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        keys = getattr(settings, "LMS_LTI_JWKS_KEYS", [])
        if not isinstance(keys, list):
            keys = []
        return Response({"keys": keys})
