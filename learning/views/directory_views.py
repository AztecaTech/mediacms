"""Manager API for LDAP directory source profiles (sync is placeholder until ldap3 wiring)."""

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.methods.ldap_directory_sync import run_ldap_sync
from learning.models import LdapDirectorySource


def _require_manager(request):
    return request.user.is_authenticated and getattr(request.user, "is_manager", False)


def _serialize_source(obj: LdapDirectorySource) -> dict:
    return {
        "id": obj.id,
        "name": obj.name,
        "server_uri": obj.server_uri,
        "user_search_base": obj.user_search_base,
        "enabled": obj.enabled,
        "last_sync_at": obj.last_sync_at.isoformat() if obj.last_sync_at else None,
        "last_sync_message": obj.last_sync_message or "",
    }


class LdapDirectorySourceListView(APIView):
    def get(self, request):
        if not _require_manager(request):
            return Response({"detail": "Forbidden"}, status=403)
        rows = LdapDirectorySource.objects.order_by("name")
        return Response([_serialize_source(s) for s in rows])


class LdapDirectorySourceSyncView(APIView):
    def post(self, request, pk):
        if not _require_manager(request):
            return Response({"detail": "Forbidden"}, status=403)
        source = get_object_or_404(LdapDirectorySource, pk=pk)
        run_ldap_sync(source)
        source.refresh_from_db()
        return Response(_serialize_source(source))
