"""Singleton model holding white-label branding settings editable from Django admin."""

from django.core.cache import cache
from django.db import models

BRANDING_CACHE_KEY = "branding_settings"


class BrandingSettings(models.Model):
    """Singleton row (pk=1) of admin-editable branding. Empty fields fall back to settings.py."""

    portal_name = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Shown in the browser tab, og:title meta, and sidebar header. "
            "Leave blank to use settings.PORTAL_NAME."
        ),
    )
    portal_description = models.CharField(
        max_length=300,
        blank=True,
        help_text="Shown in the meta description tag. Leave blank to use settings.PORTAL_DESCRIPTION.",
    )
    footer_text = models.TextField(
        blank=True,
        help_text="Shown in the sidebar footer. Leave blank to use settings.SIDEBAR_FOOTER_TEXT.",
    )
    logo_dark_mode = models.ImageField(
        upload_to="branding/",
        blank=True,
        help_text="Logo shown on dark backgrounds. PNG/JPG/WebP only. Max 2 MB.",
    )
    logo_light_mode = models.ImageField(
        upload_to="branding/",
        blank=True,
        help_text="Logo shown on light backgrounds. PNG/JPG/WebP only. Max 2 MB.",
    )
    favicon = models.ImageField(
        upload_to="branding/",
        blank=True,
        help_text="Browser tab icon, PNG. Max 2 MB.",
    )
    login_hero_image = models.ImageField(
        upload_to="branding/",
        blank=True,
        help_text="Hero image on the login and password-reset pages. Max 2 MB.",
    )
    register_hero_image = models.ImageField(
        upload_to="branding/",
        blank=True,
        help_text="Hero image on the sign-up page. Max 2 MB.",
    )
    not_found_image = models.ImageField(
        upload_to="branding/",
        blank=True,
        help_text="Artwork shown on the 404 page. Max 2 MB.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branding settings"
        verbose_name_plural = "Branding settings"

    def __str__(self):
        return "Branding settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(BRANDING_CACHE_KEY)

    def delete(self, *args, **kwargs):
        return

    @classmethod
    def load(cls):
        obj = cache.get(BRANDING_CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(BRANDING_CACHE_KEY, obj, timeout=None)
        return obj


from .home_promo import HomePromoSlide  # noqa: E402,F401
