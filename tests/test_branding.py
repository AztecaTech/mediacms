"""Tests for branding singleton, admin, context, and templates."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.template.loader import render_to_string
from django.urls import reverse

from branding.admin import BrandingSettingsForm
from branding.models import BRANDING_CACHE_KEY, BrandingSettings
from files.context_processors import stuff


class BrandingSettingsSingletonTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)

    def test_fresh_load_returns_pk_1(self):
        BrandingSettings.objects.all().delete()
        obj = BrandingSettings.load()
        self.assertEqual(obj.pk, 1)
        self.assertEqual(BrandingSettings.objects.count(), 1)

    def test_second_create_does_not_add_row(self):
        BrandingSettings.load()
        second = BrandingSettings(portal_name="Second")
        second.save()
        self.assertEqual(BrandingSettings.objects.count(), 1)
        self.assertEqual(BrandingSettings.objects.first().portal_name, "Second")
        self.assertEqual(BrandingSettings.objects.first().pk, 1)

    def test_delete_is_noop(self):
        obj = BrandingSettings.load()
        obj.delete()
        self.assertEqual(BrandingSettings.objects.count(), 1)

    def test_save_invalidates_cache(self):
        obj = BrandingSettings.load()
        obj.portal_name = "Azteca"
        obj.save()
        self.assertIsNone(cache.get(BRANDING_CACHE_KEY))
        reloaded = BrandingSettings.load()
        self.assertEqual(reloaded.portal_name, "Azteca")

    def test_load_uses_cache(self):
        BrandingSettings.load()
        cached = cache.get(BRANDING_CACHE_KEY)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.pk, 1)


class BrandingSettingsAdminTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)
        user = get_user_model()
        self.admin = user.objects.create_superuser(
            username="branding_admin",
            email="branding_admin@example.com",
            password="pw",
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_changelist_redirects_to_singleton_change_form(self):
        url = reverse("admin:branding_brandingsettings_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/branding/brandingsettings/1/change/", response["Location"])

    def test_add_view_forbidden_when_row_exists(self):
        BrandingSettings.load()
        url = reverse("admin:branding_brandingsettings_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_delete_view_forbidden(self):
        BrandingSettings.load()
        url = reverse("admin:branding_brandingsettings_delete", args=(1,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class BrandingImageSizeTests(TestCase):
    MAX_BYTES = 2 * 1024 * 1024

    def _png_bytes(self, size):
        header = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        )
        return header + b"\x00" * max(0, size - len(header))

    def test_oversized_logo_rejected(self):
        oversized = SimpleUploadedFile(
            "huge.png",
            self._png_bytes(self.MAX_BYTES + 1),
            content_type="image/png",
        )
        form = BrandingSettingsForm(data={}, files={"logo_dark_mode": oversized})
        self.assertFalse(form.is_valid())
        self.assertIn("logo_dark_mode", form.errors)
        self.assertIn("2 MB", form.errors["logo_dark_mode"][0])

    def test_under_limit_logo_accepted(self):
        small = SimpleUploadedFile(
            "small.png",
            self._png_bytes(1024),
            content_type="image/png",
        )
        form = BrandingSettingsForm(data={}, files={"logo_dark_mode": small})
        form.is_valid()
        self.assertNotIn("logo_dark_mode", form.errors)


class BrandingContextProcessorTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)
        BrandingSettings.objects.all().delete()
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.get("/")
        request.LANGUAGE_CODE = "en"
        user = get_user_model()
        user_instance, _ = user.objects.get_or_create(username="ctxuser")
        request.user = user_instance
        return request

    @override_settings(
        PORTAL_NAME="FallbackCMS",
        PORTAL_DESCRIPTION="Fallback desc",
        SIDEBAR_FOOTER_TEXT="fallback footer",
    )
    def test_fallback_when_branding_row_empty(self):
        BrandingSettings.load()
        context = stuff(self._request())
        self.assertEqual(context["PORTAL_NAME"], "FallbackCMS")
        self.assertEqual(context["PORTAL_DESCRIPTION"], "Fallback desc")
        self.assertEqual(context["SIDEBAR_FOOTER_TEXT"], "fallback footer")
        self.assertEqual(context["BRANDING_FAVICON_URL"], "")
        self.assertEqual(context["BRANDING_LOGIN_HERO_URL"], "")
        self.assertEqual(context["BRANDING_REGISTER_HERO_URL"], "")
        self.assertEqual(context["BRANDING_NOT_FOUND_URL"], "")

    @override_settings(
        PORTAL_NAME="FallbackCMS",
        PORTAL_DESCRIPTION="Fallback desc",
        SIDEBAR_FOOTER_TEXT="fallback footer",
    )
    def test_text_fields_override_settings(self):
        obj = BrandingSettings.load()
        obj.portal_name = "Azteca Tax Systems Media"
        obj.portal_description = "Corporate video portal"
        obj.footer_text = "© Azteca Tax Systems"
        obj.save()
        context = stuff(self._request())
        self.assertEqual(context["PORTAL_NAME"], "Azteca Tax Systems Media")
        self.assertEqual(context["PORTAL_DESCRIPTION"], "Corporate video portal")
        self.assertEqual(context["SIDEBAR_FOOTER_TEXT"], "© Azteca Tax Systems")

    def test_logo_image_url_shadows_settings_and_clears_svg(self):
        obj = BrandingSettings.load()
        obj.logo_dark_mode = SimpleUploadedFile(
            "dark.png",
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 32,
            content_type="image/png",
        )
        obj.save()
        context = stuff(self._request())
        self.assertTrue(context["PORTAL_LOGO_DARK_PNG"].endswith(".png"))
        self.assertEqual(context["PORTAL_LOGO_DARK_SVG"], "")


class BrandingFaviconTemplateTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)

    def test_custom_favicon_url_used_when_set(self):
        html = render_to_string(
            "common/head-links.html",
            context={
                "BRANDING_FAVICON_URL": "/media/branding/custom.png",
                "LOAD_FROM_CDN": False,
                "RSS_URL": "/rss",
                "EXTRA_CSS_PATHS": [],
                "VERSION": "1.0.0",
            },
        )
        self.assertIn('href="/media/branding/custom.png"', html)
        self.assertNotIn("favicons/favicon-32x32.png", html)
        self.assertNotIn("favicons/favicon-16x16.png", html)
        self.assertNotIn('href="/static/favicons/favicon.ico"', html)

    def test_default_favicon_used_when_unset(self):
        html = render_to_string(
            "common/head-links.html",
            context={
                "BRANDING_FAVICON_URL": "",
                "LOAD_FROM_CDN": False,
                "RSS_URL": "/rss",
                "EXTRA_CSS_PATHS": [],
                "VERSION": "1.0.0",
            },
        )
        self.assertIn("favicons/favicon-32x32.png", html)
        self.assertIn("favicons/favicon-16x16.png", html)


class BrandingAuthHeroTests(TestCase):
    def test_login_template_includes_hero_when_url_set(self):
        html = render_to_string(
            "account/login.html",
            context={
                "BRANDING_LOGIN_HERO_URL": "/media/branding/login.png",
                "PORTAL_NAME": "Azteca",
                "signup_url": "/accounts/signup/",
                "redirect_field_name": "next",
                "redirect_field_value": "",
                "form": None,
            },
        )
        self.assertIn('class="auth-hero"', html)
        self.assertIn('src="/media/branding/login.png"', html)

    def test_login_template_omits_hero_when_url_blank(self):
        html = render_to_string(
            "account/login.html",
            context={
                "BRANDING_LOGIN_HERO_URL": "",
                "PORTAL_NAME": "Azteca",
                "signup_url": "/accounts/signup/",
                "redirect_field_name": "next",
                "redirect_field_value": "",
                "form": None,
            },
        )
        self.assertNotIn('class="auth-hero"', html)

    def test_signup_template_uses_register_hero(self):
        html = render_to_string(
            "account/signup.html",
            context={
                "BRANDING_REGISTER_HERO_URL": "/media/branding/signup.png",
                "PORTAL_NAME": "Azteca",
                "login_url": "/accounts/login/",
                "redirect_field_name": "next",
                "redirect_field_value": "",
                "form": None,
            },
        )
        self.assertIn('src="/media/branding/signup.png"', html)

    def test_password_reset_template_reuses_login_hero(self):
        html = render_to_string(
            "account/password_reset.html",
            context={
                "BRANDING_LOGIN_HERO_URL": "/media/branding/login.png",
                "PORTAL_NAME": "Azteca",
                "user": AnonymousUser(),
                "form": None,
            },
        )
        self.assertIn('src="/media/branding/login.png"', html)


class Branding404Tests(TestCase):
    def test_404_template_includes_image_when_url_set(self):
        html = render_to_string(
            "404.html",
            context={"BRANDING_NOT_FOUND_URL": "/media/branding/404.png", "PORTAL_NAME": "Azteca"},
        )
        self.assertIn('src="/media/branding/404.png"', html)

    def test_404_template_omits_image_when_url_blank(self):
        html = render_to_string(
            "404.html",
            context={"BRANDING_NOT_FOUND_URL": "", "PORTAL_NAME": "Azteca"},
        )
        self.assertNotIn('class="auth-hero"', html)


class BrandingEndToEndTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)
        self.client = Client()

    def test_login_page_renders_uploaded_hero(self):
        obj = BrandingSettings.load()
        obj.login_hero_image = SimpleUploadedFile(
            "hero.png",
            b"\x89PNG\r\n\x1a\n" + b"\x00" * 64,
            content_type="image/png",
        )
        obj.portal_name = "Azteca Tax Systems Media"
        obj.save()

        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "auth-hero")
        self.assertContains(response, "Azteca Tax Systems Media")
        self.assertContains(response, obj.login_hero_image.url)
