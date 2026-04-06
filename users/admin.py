from django.conf import settings
from django.contrib import admin

from rbac.models import RBACMembership

from .models import User


class RBACMembershipInline(admin.TabularInline):
    model = RBACMembership
    extra = 1
    fields = ('rbac_group', 'role')
    verbose_name = 'RBAC Group Membership'
    verbose_name_plural = 'RBAC Group Memberships'


class UserAdmin(admin.ModelAdmin):
    search_fields = ["email", "username", "name"]
    exclude = ["user_permissions", "title", "password", "groups", "last_login", "is_featured", "location", "first_name", "last_name", "media_count", "date_joined", "is_active", "is_approved"]
    list_display = [
        "username",
        "name",
        "email",
        "logo",
        "date_added",
        "is_superuser",
        "is_editor",
        "is_manager",
        "media_count",
    ]
    list_filter = ["is_superuser", "is_editor", "is_manager"]
    ordering = ("-date_added",)
    inlines = []

    if settings.USERS_NEEDS_TO_BE_APPROVED:
        list_display.append("is_approved")
        list_filter.append("is_approved")
        exclude.remove("is_approved")

    if getattr(settings, 'USE_RBAC', False):
        inlines.append(RBACMembershipInline)


admin.site.register(User, UserAdmin)
