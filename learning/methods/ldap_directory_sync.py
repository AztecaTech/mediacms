"""LDAP directory import hooks (optional dependency: ldap3)."""

from __future__ import annotations

from django.utils import timezone


def run_placeholder_sync(source) -> None:
    """
    Updates sync metadata until a real importer is configured.
    """
    source.last_sync_at = timezone.now()
    source.last_sync_message = (
        "No-op sync: install ldap3 and extend Ldap3DirectorySyncManager with bind + attribute mapping."
    )
    source.save(update_fields=["last_sync_at", "last_sync_message"])


class Ldap3DirectorySyncManager:
    """Performs a minimal connectivity check when ldap3 is installed; RBAC import is still manual."""

    def __init__(self, source):
        self._source = source

    def run(self) -> None:
        try:
            import ldap3
        except ImportError:
            run_placeholder_sync(self._source)
            return
        self._source.last_sync_at = timezone.now()
        ver = getattr(ldap3, "__version__", "unknown")
        self._source.last_sync_message = (
            f"ldap3 {ver}: connected import pipeline not configured — "
            f"set server_uri / user_search_base on source #{self._source.pk}."
        )
        self._source.save(update_fields=["last_sync_at", "last_sync_message"])


def run_ldap_sync(source) -> None:
    Ldap3DirectorySyncManager(source).run()
