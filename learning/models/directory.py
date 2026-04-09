from django.db import models


class LdapDirectorySource(models.Model):
    """Stored connection profile for future LDAP / AD directory sync (sync logic is pluggable)."""

    name = models.CharField(max_length=120, unique=True)
    server_uri = models.CharField(max_length=512, help_text="e.g. ldap://ldap.example.org:389")
    bind_dn = models.CharField(max_length=512, blank=True)
    bind_password = models.CharField(
        max_length=256,
        blank=True,
        help_text="Stored as plain text for now; use env/secret injection at deploy time.",
    )
    user_search_base = models.CharField(max_length=512)
    user_search_filter = models.CharField(
        max_length=512,
        blank=True,
        help_text="Optional; default (objectClass=person) used when empty.",
    )
    enabled = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
