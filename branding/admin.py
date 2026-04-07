"""Django admin registration for the singleton BrandingSettings model."""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import BrandingSettings

MAX_IMAGE_BYTES = 2 * 1024 * 1024
IMAGE_FIELD_NAMES = (
    "logo_dark_mode",
    "logo_light_mode",
    "favicon",
    "login_hero_image",
    "register_hero_image",
    "not_found_image",
)


class BrandingSettingsForm(forms.ModelForm):
    class Meta:
        model = BrandingSettings
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        for field_name in IMAGE_FIELD_NAMES:
            uploaded = cleaned.get(field_name)
            if uploaded and hasattr(uploaded, "size") and uploaded.size > MAX_IMAGE_BYTES:
                self.add_error(
                    field_name,
                    ValidationError(
                        "File exceeds the 2 MB limit. "
                        f"Uploaded {uploaded.size / (1024 * 1024):.1f} MB."
                    ),
                )
        return cleaned


@admin.register(BrandingSettings)
class BrandingSettingsAdmin(admin.ModelAdmin):
    form = BrandingSettingsForm
    fieldsets = (
        ("Identity", {"fields": ("portal_name", "portal_description", "footer_text")}),
        (
            "Logos",
            {
                "fields": ("logo_dark_mode", "logo_light_mode", "favicon"),
                "description": "PNG, JPG, or WebP. Max 2 MB per image.",
            },
        ),
        (
            "Auth pages",
            {
                "fields": ("login_hero_image", "register_hero_image", "not_found_image"),
                "description": "Optional imagery for the login, sign-up, password reset, and 404 pages.",
            },
        ),
        ("Metadata", {"fields": ("updated_at",)}),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not BrandingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj, _ = BrandingSettings.objects.get_or_create(pk=1)
        return HttpResponseRedirect(reverse("admin:branding_brandingsettings_change", args=(obj.pk,)))
