"""Home page promotional slides managed from Django admin (Branding section)."""

import json

from django.db import models
from django.http import HttpRequest


class HomePromoSlide(models.Model):
    """Image slide for the home page carousel; order via sort_order."""

    image = models.ImageField(
        upload_to="branding/home_promo/",
        help_text="Wide image works best (e.g. 1200×400). PNG, JPG, or WebP. Max 2 MB.",
    )
    link_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Optional: entire slide becomes a link (opens in same tab).",
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short description for screen readers (recommended).",
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers appear first.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "Home promo slide"
        verbose_name_plural = "Home promo slides"

    def __str__(self):
        return self.alt_text or f"Slide {self.pk}"


def home_promo_slides_json(request: HttpRequest) -> str:
    """JSON array for window.MediaCMS.site.homePromoSlides (absolute image URLs)."""
    slides = []
    for row in HomePromoSlide.objects.filter(is_active=True).order_by("sort_order", "id"):
        if not row.image:
            continue
        try:
            img_url = request.build_absolute_uri(row.image.url)
        except Exception:  # noqa: BLE001
            continue
        slides.append(
            {
                "image": img_url,
                "link": (row.link_url or "").strip(),
                "alt": (row.alt_text or "").strip() or "Promotional slide",
            }
        )
    return json.dumps(slides)
