from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BrandingSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "portal_name",
                    models.CharField(
                        blank=True,
                        help_text="Shown in the browser tab, og:title meta, and sidebar header. Leave blank to use settings.PORTAL_NAME.",
                        max_length=120,
                    ),
                ),
                (
                    "portal_description",
                    models.CharField(
                        blank=True,
                        help_text="Shown in the meta description tag. Leave blank to use settings.PORTAL_DESCRIPTION.",
                        max_length=300,
                    ),
                ),
                (
                    "footer_text",
                    models.TextField(
                        blank=True,
                        help_text="Shown in the sidebar footer. Leave blank to use settings.SIDEBAR_FOOTER_TEXT.",
                    ),
                ),
                (
                    "logo_dark_mode",
                    models.ImageField(
                        blank=True,
                        help_text="Logo shown on dark backgrounds. PNG/JPG/WebP only. Max 2 MB.",
                        upload_to="branding/",
                    ),
                ),
                (
                    "logo_light_mode",
                    models.ImageField(
                        blank=True,
                        help_text="Logo shown on light backgrounds. PNG/JPG/WebP only. Max 2 MB.",
                        upload_to="branding/",
                    ),
                ),
                (
                    "favicon",
                    models.ImageField(
                        blank=True,
                        help_text="Browser tab icon, PNG. Max 2 MB.",
                        upload_to="branding/",
                    ),
                ),
                (
                    "login_hero_image",
                    models.ImageField(
                        blank=True,
                        help_text="Hero image on the login and password-reset pages. Max 2 MB.",
                        upload_to="branding/",
                    ),
                ),
                (
                    "register_hero_image",
                    models.ImageField(
                        blank=True,
                        help_text="Hero image on the sign-up page. Max 2 MB.",
                        upload_to="branding/",
                    ),
                ),
                (
                    "not_found_image",
                    models.ImageField(
                        blank=True,
                        help_text="Artwork shown on the 404 page. Max 2 MB.",
                        upload_to="branding/",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Branding settings", "verbose_name_plural": "Branding settings"},
        ),
    ]
