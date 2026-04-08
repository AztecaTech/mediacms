from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("branding", "0002_seed_singleton"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePromoSlide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "image",
                    models.ImageField(
                        help_text="Wide image works best (e.g. 1200×400). PNG, JPG, or WebP. Max 2 MB.",
                        upload_to="branding/home_promo/",
                    ),
                ),
                (
                    "link_url",
                    models.URLField(
                        blank=True,
                        help_text="Optional: entire slide becomes a link (opens in same tab).",
                        max_length=500,
                    ),
                ),
                (
                    "alt_text",
                    models.CharField(
                        blank=True,
                        help_text="Short description for screen readers (recommended).",
                        max_length=200,
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Lower numbers appear first.",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Home promo slide",
                "verbose_name_plural": "Home promo slides",
                "ordering": ("sort_order", "id"),
            },
        ),
    ]
