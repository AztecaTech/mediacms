# Branding Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let admins change logos, portal name, footer text, favicon, and auth-page artwork from `/admin/` without editing Python settings files or restarting containers.

**Architecture:** A new Django app `branding/` owns a singleton `BrandingSettings` model (always `pk=1`). Values overlay onto the existing `files/context_processors.py:stuff()` pipeline, so the whole app (including the React frontend, which reads `window.MediaCMS.site.*`) sees new values on next page load. Redis-backed cache keyed as `"branding_settings"` busts on save, propagating instantly across `web`, `celery_worker`, and `celery_beat`. First deploy changes nothing visually because every field is blank by default and falls back to current `settings.py` values.

**Tech Stack:** Django 4.x, Django admin, Django file storage (ImageField on local media volume), django_redis cache, pytest-django for tests.

**Spec:** `docs/superpowers/specs/2026-04-06-branding-settings.md`

---

## Conventions this plan follows

- **Test location:** `tests/test_branding.py` (project convention — all tests live at `tests/test_*.py`, matching `tests/test_external_video.py`).
- **Test runner:** `pytest` with `DJANGO_SETTINGS_MODULE=cms.settings` configured in `pytest.ini`. Run a single test with `pytest tests/test_branding.py::ClassName::method_name -v`.
- **Migrations:** `python manage.py makemigrations branding` and `python manage.py migrate branding`.
- **Commit messages:** short lowercase imperative, matching the repo's recent style (`a6882c9 categories`, `97ab7fa google drive support`).

---

## Task 1: Scaffold the `branding/` Django app

**Files:**
- Create: `branding/__init__.py`
- Create: `branding/apps.py`
- Create: `branding/models.py` (stub, to be filled in Task 2)
- Create: `branding/admin.py` (stub, to be filled in Task 4)
- Create: `branding/migrations/__init__.py`
- Modify: `cms/settings.py` (add to `INSTALLED_APPS`)

- [ ] **Step 1: Create empty `branding/__init__.py`**

File: `branding/__init__.py`
```python
```
(Empty file.)

- [ ] **Step 2: Create `branding/apps.py`**

File: `branding/apps.py`
```python
from django.apps import AppConfig


class BrandingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'branding'
    verbose_name = 'Branding'
```

- [ ] **Step 3: Create stub `branding/models.py`**

File: `branding/models.py`
```python
from django.db import models  # noqa: F401

# BrandingSettings is defined in Task 2.
```

- [ ] **Step 4: Create stub `branding/admin.py`**

File: `branding/admin.py`
```python
from django.contrib import admin  # noqa: F401

# BrandingSettingsAdmin is registered in Task 4.
```

- [ ] **Step 5: Create empty `branding/migrations/__init__.py`**

File: `branding/migrations/__init__.py`
```python
```
(Empty file.)

- [ ] **Step 6: Register the app in `cms/settings.py`**

Locate the `INSTALLED_APPS` list (starts around line 282). Add `"branding.apps.BrandingConfig"` immediately after `"files.apps.FilesConfig"` so branding sits with the other first-party MediaCMS apps.

Before:
```python
    "files.apps.FilesConfig",
    "users.apps.UsersConfig",
```

After:
```python
    "files.apps.FilesConfig",
    "branding.apps.BrandingConfig",
    "users.apps.UsersConfig",
```

- [ ] **Step 7: Run Django system check**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 8: Commit**

```bash
git add branding/__init__.py branding/apps.py branding/models.py branding/admin.py branding/migrations/__init__.py cms/settings.py
git commit -m "scaffold branding app"
```

---

## Task 2: Implement `BrandingSettings` singleton model

**Files:**
- Modify: `branding/models.py`
- Create: `tests/test_branding.py`
- Create: `branding/migrations/0001_initial.py` (generated)

- [ ] **Step 1: Write failing tests for the singleton model**

File: `tests/test_branding.py`
```python
"""Tests for the branding app (singleton BrandingSettings model + context overlay)."""

from django.core.cache import cache
from django.test import TestCase

from branding.models import BRANDING_CACHE_KEY, BrandingSettings


class BrandingSettingsSingletonTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)

    def test_fresh_load_returns_pk_1(self):
        """load() on a fresh DB creates and returns the row at pk=1."""
        BrandingSettings.objects.all().delete()
        obj = BrandingSettings.load()
        self.assertEqual(obj.pk, 1)
        self.assertEqual(BrandingSettings.objects.count(), 1)

    def test_second_create_does_not_add_row(self):
        """Creating a second instance still leaves exactly one row at pk=1."""
        BrandingSettings.load()
        second = BrandingSettings(portal_name="Second")
        second.save()
        self.assertEqual(BrandingSettings.objects.count(), 1)
        self.assertEqual(BrandingSettings.objects.first().portal_name, "Second")
        self.assertEqual(BrandingSettings.objects.first().pk, 1)

    def test_delete_is_noop(self):
        """Calling delete() on the singleton does not remove the row."""
        obj = BrandingSettings.load()
        obj.delete()
        self.assertEqual(BrandingSettings.objects.count(), 1)

    def test_save_invalidates_cache(self):
        """Modifying and saving the singleton purges the cache so load() returns fresh data."""
        obj = BrandingSettings.load()
        obj.portal_name = "Azteca"
        obj.save()
        self.assertIsNone(cache.get(BRANDING_CACHE_KEY))
        reloaded = BrandingSettings.load()
        self.assertEqual(reloaded.portal_name, "Azteca")

    def test_load_uses_cache(self):
        """Second load() call returns the cached instance without a new DB row lookup."""
        BrandingSettings.load()
        cached = cache.get(BRANDING_CACHE_KEY)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.pk, 1)
```

- [ ] **Step 2: Run tests and confirm they fail with ImportError**

Run: `pytest tests/test_branding.py -v`
Expected: `ImportError` (or `ModuleNotFoundError`) on `from branding.models import BRANDING_CACHE_KEY, BrandingSettings` — the symbols don't exist yet.

- [ ] **Step 3: Implement the `BrandingSettings` model**

Replace the entire contents of `branding/models.py`:
```python
"""Singleton model holding white-label branding settings editable from Django admin."""

from django.core.cache import cache
from django.db import models

BRANDING_CACHE_KEY = "branding_settings"


class BrandingSettings(models.Model):
    """Singleton row (pk=1) of admin-editable branding. Empty fields fall back to settings.py."""

    # --- Identity ---
    portal_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Shown in the browser tab, og:title meta, and sidebar header. "
                  "Leave blank to use settings.PORTAL_NAME.",
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

    # --- Logos (raster only; SVG is rejected for XSS safety) ---
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

    # --- Auth-page artwork ---
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
        # Force singleton: always row pk=1.
        self.pk = 1
        super().save(*args, **kwargs)
        # Invalidate the shared Redis cache so every container re-reads on next request.
        cache.delete(BRANDING_CACHE_KEY)

    def delete(self, *args, **kwargs):
        # Singleton: delete is a no-op. Never remove the row.
        return

    @classmethod
    def load(cls):
        """Return the singleton, creating it if missing, from shared Redis cache."""
        obj = cache.get(BRANDING_CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(BRANDING_CACHE_KEY, obj, timeout=None)
        return obj
```

- [ ] **Step 4: Generate the initial migration**

Run: `python manage.py makemigrations branding`
Expected output includes: `Migrations for 'branding': branding/migrations/0001_initial.py - Create model BrandingSettings`

- [ ] **Step 5: Apply the migration to the test DB implicitly via pytest**

Run: `pytest tests/test_branding.py -v`
Expected: all five tests in `BrandingSettingsSingletonTests` pass.

If any test fails on `test_save_invalidates_cache` with a stale cache read, confirm that `pytest.ini` does not set a non-local cache backend for tests — the default local-memory cache respects the same `cache.delete()` semantics as Redis.

- [ ] **Step 6: Commit**

```bash
git add branding/models.py branding/migrations/0001_initial.py tests/test_branding.py
git commit -m "branding singleton model + tests"
```

---

## Task 3: Seed the singleton row via data migration

The `BrandingSettings.load()` class method already handles first-boot via `get_or_create(pk=1)`. A data migration adds belt-and-braces: the row exists the moment migrations finish, so admin-page loads never race the "create on first read" code path.

**Files:**
- Create: `branding/migrations/0002_seed_singleton.py`

- [ ] **Step 1: Write the data migration**

File: `branding/migrations/0002_seed_singleton.py`
```python
from django.db import migrations


def create_singleton(apps, schema_editor):
    BrandingSettings = apps.get_model("branding", "BrandingSettings")
    BrandingSettings.objects.update_or_create(pk=1, defaults={})


def noop_reverse(apps, schema_editor):
    # Leave the row in place on rollback — removing it would cascade into deployed state.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("branding", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_singleton, noop_reverse),
    ]
```

- [ ] **Step 2: Apply migrations locally**

Run: `python manage.py migrate branding`
Expected output:
```
Operations to perform:
  Apply all migrations: branding
Running migrations:
  Applying branding.0002_seed_singleton... OK
```

- [ ] **Step 3: Verify the row exists**

Run:
```bash
python manage.py shell -c "from branding.models import BrandingSettings; print(BrandingSettings.objects.filter(pk=1).exists())"
```
Expected: `True`

- [ ] **Step 4: Commit**

```bash
git add branding/migrations/0002_seed_singleton.py
git commit -m "branding seed singleton row"
```

---

## Task 4: Register `BrandingSettingsAdmin` with singleton behavior

**Files:**
- Modify: `branding/admin.py`
- Modify: `tests/test_branding.py`

- [ ] **Step 1: Write failing admin tests**

Append to `tests/test_branding.py`:
```python
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse


class BrandingSettingsAdminTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="branding_admin",
            email="branding_admin@example.com",
            password="pw",
        )
        self.client = Client()
        self.client.force_login(self.admin)

    def test_changelist_redirects_to_singleton_change_form(self):
        """Hitting the admin list view should bounce straight to the edit page for pk=1."""
        url = reverse("admin:branding_brandingsettings_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/branding/brandingsettings/1/change/", response["Location"])

    def test_add_view_forbidden_when_row_exists(self):
        """The add page is hidden once the singleton exists."""
        BrandingSettings.load()  # ensure row exists
        url = reverse("admin:branding_brandingsettings_add")
        response = self.client.get(url)
        # Django admin returns 403 when has_add_permission is False.
        self.assertEqual(response.status_code, 403)

    def test_delete_view_forbidden(self):
        """The delete page is never accessible."""
        BrandingSettings.load()
        url = reverse("admin:branding_brandingsettings_delete", args=(1,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run and confirm failures**

Run: `pytest tests/test_branding.py::BrandingSettingsAdminTests -v`
Expected: failures on all three tests — URL `admin:branding_brandingsettings_changelist` either doesn't resolve or returns 200, not 302.

- [ ] **Step 3: Implement the admin class**

Replace the entire contents of `branding/admin.py`:
```python
"""Django admin registration for the singleton BrandingSettings model."""

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import BrandingSettings


@admin.register(BrandingSettings)
class BrandingSettingsAdmin(admin.ModelAdmin):
    """Singleton admin: skip the list, forbid add/delete, present fieldsets only."""

    fieldsets = (
        ("Identity", {
            "fields": ("portal_name", "portal_description", "footer_text"),
        }),
        ("Logos", {
            "fields": ("logo_dark_mode", "logo_light_mode", "favicon"),
            "description": "PNG, JPG, or WebP. Max 2 MB per image.",
        }),
        ("Auth pages", {
            "fields": ("login_hero_image", "register_hero_image", "not_found_image"),
            "description": "Optional imagery for the login, sign-up, password reset, and 404 pages.",
        }),
        ("Metadata", {
            "fields": ("updated_at",),
        }),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        # Allow only when the singleton row does not yet exist.
        return not BrandingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Skip the changelist entirely: jump straight to the edit form for pk=1.
        obj, _ = BrandingSettings.objects.get_or_create(pk=1)
        return HttpResponseRedirect(
            reverse("admin:branding_brandingsettings_change", args=(obj.pk,))
        )
```

- [ ] **Step 4: Run the admin tests and confirm they pass**

Run: `pytest tests/test_branding.py::BrandingSettingsAdminTests -v`
Expected: all three tests pass.

- [ ] **Step 5: Manual sanity check (optional but recommended)**

Start the dev server (`python manage.py runserver`) and visit `http://localhost:8000/admin/`. Under "Branding" you should see "Branding settings"; clicking it redirects to `/admin/branding/brandingsettings/1/change/`.

- [ ] **Step 6: Commit**

```bash
git add branding/admin.py tests/test_branding.py
git commit -m "branding admin registration"
```

---

## Task 5: Enforce 2 MB image size limit on all image fields

**Files:**
- Modify: `branding/admin.py`
- Modify: `tests/test_branding.py`

- [ ] **Step 1: Write failing test for the size limit**

Append to `tests/test_branding.py`:
```python
from django.core.files.uploadedfile import SimpleUploadedFile

from branding.admin import BrandingSettingsForm


class BrandingImageSizeTests(TestCase):
    MAX_BYTES = 2 * 1024 * 1024  # 2 MB

    def _png_bytes(self, size):
        # Minimal valid PNG header + padding up to `size` bytes.
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
        # May still be invalid for other field reasons, but not for size.
        form.is_valid()
        self.assertNotIn("logo_dark_mode", form.errors)
```

- [ ] **Step 2: Run test and confirm ImportError**

Run: `pytest tests/test_branding.py::BrandingImageSizeTests -v`
Expected: `ImportError` on `from branding.admin import BrandingSettingsForm` — symbol not defined yet.

- [ ] **Step 3: Add `BrandingSettingsForm` with size validation**

Replace the contents of `branding/admin.py` with:
```python
"""Django admin registration for the singleton BrandingSettings model."""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import BrandingSettings

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB

IMAGE_FIELD_NAMES = (
    "logo_dark_mode",
    "logo_light_mode",
    "favicon",
    "login_hero_image",
    "register_hero_image",
    "not_found_image",
)


class BrandingSettingsForm(forms.ModelForm):
    """Enforces a 2 MB max per uploaded image across every ImageField on the model."""

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
    """Singleton admin: skip the list, forbid add/delete, present fieldsets only."""

    form = BrandingSettingsForm

    fieldsets = (
        ("Identity", {
            "fields": ("portal_name", "portal_description", "footer_text"),
        }),
        ("Logos", {
            "fields": ("logo_dark_mode", "logo_light_mode", "favicon"),
            "description": "PNG, JPG, or WebP. Max 2 MB per image.",
        }),
        ("Auth pages", {
            "fields": ("login_hero_image", "register_hero_image", "not_found_image"),
            "description": "Optional imagery for the login, sign-up, password reset, and 404 pages.",
        }),
        ("Metadata", {
            "fields": ("updated_at",),
        }),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not BrandingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj, _ = BrandingSettings.objects.get_or_create(pk=1)
        return HttpResponseRedirect(
            reverse("admin:branding_brandingsettings_change", args=(obj.pk,))
        )
```

- [ ] **Step 4: Run tests and confirm they pass**

Run: `pytest tests/test_branding.py::BrandingImageSizeTests -v`
Expected: both tests pass.

Run the full branding test file to confirm no regression:
`pytest tests/test_branding.py -v`
Expected: all tests from Tasks 2, 4, and 5 pass.

- [ ] **Step 5: Commit**

```bash
git add branding/admin.py tests/test_branding.py
git commit -m "branding 2mb image size limit"
```

---

## Task 6: Overlay `BrandingSettings` values into the context processor

**Files:**
- Modify: `files/context_processors.py`
- Modify: `tests/test_branding.py`

- [ ] **Step 1: Write failing test for the overlay**

Append to `tests/test_branding.py`:
```python
from django.test import RequestFactory, override_settings

from files.context_processors import stuff


class BrandingContextProcessorTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)
        BrandingSettings.objects.all().delete()
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.get("/")
        # stuff() reads request.LANGUAGE_CODE; RequestFactory doesn't set it.
        request.LANGUAGE_CODE = "en"
        User = get_user_model()
        user, _ = User.objects.get_or_create(username="ctxuser")
        request.user = user
        return request

    @override_settings(
        PORTAL_NAME="FallbackCMS",
        PORTAL_DESCRIPTION="Fallback desc",
        SIDEBAR_FOOTER_TEXT="fallback footer",
    )
    def test_fallback_when_branding_row_empty(self):
        """An empty branding row falls back to settings.py values."""
        BrandingSettings.load()  # create blank singleton
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
        """Populated branding text fields shadow the settings.py defaults."""
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
        """When a raster logo is uploaded, context reports that URL and blanks the SVG key."""
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
```

- [ ] **Step 2: Run and confirm failures**

Run: `pytest tests/test_branding.py::BrandingContextProcessorTests -v`
Expected: failures because `stuff()` does not yet overlay `BrandingSettings.load()` values; `BRANDING_FAVICON_URL` and related keys are missing.

- [ ] **Step 3: Update `files/context_processors.py`**

Open `files/context_processors.py` and make two edits.

**Edit A:** Add the import at the top of the file alongside the existing imports.

Before (current top of file):
```python
from django.conf import settings

from cms.version import VERSION

from .frontend_translations import get_translation, get_translation_strings
from .methods import is_mediacms_editor, is_mediacms_manager
```

After:
```python
from django.conf import settings

from branding.models import BrandingSettings
from cms.version import VERSION

from .frontend_translations import get_translation, get_translation_strings
from .methods import is_mediacms_editor, is_mediacms_manager
```

**Edit B:** Inside `stuff()`, replace the block of lines that sets `PORTAL_NAME`, the four `PORTAL_LOGO_*` keys, `PORTAL_DESCRIPTION`, and `SIDEBAR_FOOTER_TEXT` with a branding-aware overlay. Leave every other line in `stuff()` unchanged.

Before (the block starting at the current line 14):
```python
    ret["PORTAL_NAME"] = settings.PORTAL_NAME

    ret["PORTAL_LOGO_DARK_SVG"] = getattr(settings, 'PORTAL_LOGO_DARK_SVG', "")
    ret["PORTAL_LOGO_DARK_PNG"] = getattr(settings, 'PORTAL_LOGO_DARK_PNG', "")
    ret["PORTAL_LOGO_LIGHT_SVG"] = getattr(settings, 'PORTAL_LOGO_LIGHT_SVG', "")
    ret["PORTAL_LOGO_LIGHT_PNG"] = getattr(settings, 'PORTAL_LOGO_LIGHT_PNG', "")
    ret["EXTRA_CSS_PATHS"] = getattr(settings, 'EXTRA_CSS_PATHS', [])
    ret["PORTAL_DESCRIPTION"] = settings.PORTAL_DESCRIPTION
```

After:
```python
    branding = BrandingSettings.load()

    ret["PORTAL_NAME"] = branding.portal_name or settings.PORTAL_NAME

    # Logos: branding-uploaded raster wins. When a raster is set, blank out the SVG
    # key so templates that prefer SVG fall through to the PNG path instead.
    if branding.logo_dark_mode:
        ret["PORTAL_LOGO_DARK_PNG"] = branding.logo_dark_mode.url
        ret["PORTAL_LOGO_DARK_SVG"] = ""
    else:
        ret["PORTAL_LOGO_DARK_PNG"] = getattr(settings, 'PORTAL_LOGO_DARK_PNG', "")
        ret["PORTAL_LOGO_DARK_SVG"] = getattr(settings, 'PORTAL_LOGO_DARK_SVG', "")

    if branding.logo_light_mode:
        ret["PORTAL_LOGO_LIGHT_PNG"] = branding.logo_light_mode.url
        ret["PORTAL_LOGO_LIGHT_SVG"] = ""
    else:
        ret["PORTAL_LOGO_LIGHT_PNG"] = getattr(settings, 'PORTAL_LOGO_LIGHT_PNG', "")
        ret["PORTAL_LOGO_LIGHT_SVG"] = getattr(settings, 'PORTAL_LOGO_LIGHT_SVG', "")

    ret["EXTRA_CSS_PATHS"] = getattr(settings, 'EXTRA_CSS_PATHS', [])
    ret["PORTAL_DESCRIPTION"] = branding.portal_description or settings.PORTAL_DESCRIPTION
```

**Edit C:** Further down in `stuff()`, replace the `SIDEBAR_FOOTER_TEXT` line with the branding-aware version. Leave every surrounding line unchanged.

Before:
```python
    ret["SIDEBAR_FOOTER_TEXT"] = settings.SIDEBAR_FOOTER_TEXT
```

After:
```python
    ret["SIDEBAR_FOOTER_TEXT"] = branding.footer_text or settings.SIDEBAR_FOOTER_TEXT
```

**Edit D:** Add the four new branding URL keys immediately before the `return ret` line at the bottom of `stuff()`.

Before:
```python
    if request.user.is_superuser:
        ret["DJANGO_ADMIN_URL"] = settings.DJANGO_ADMIN_URL

    return ret
```

After:
```python
    if request.user.is_superuser:
        ret["DJANGO_ADMIN_URL"] = settings.DJANGO_ADMIN_URL

    ret["BRANDING_FAVICON_URL"] = branding.favicon.url if branding.favicon else ""
    ret["BRANDING_LOGIN_HERO_URL"] = branding.login_hero_image.url if branding.login_hero_image else ""
    ret["BRANDING_REGISTER_HERO_URL"] = branding.register_hero_image.url if branding.register_hero_image else ""
    ret["BRANDING_NOT_FOUND_URL"] = branding.not_found_image.url if branding.not_found_image else ""

    return ret
```

- [ ] **Step 4: Run tests and confirm they pass**

Run: `pytest tests/test_branding.py::BrandingContextProcessorTests -v`
Expected: all three tests pass.

Run: `pytest tests/test_branding.py -v`
Expected: every test in the file passes.

- [ ] **Step 5: Commit**

```bash
git add files/context_processors.py tests/test_branding.py
git commit -m "branding context processor overlay"
```

---

## Task 7: Favicon override in `templates/common/head-links.html`

**Files:**
- Modify: `templates/common/head-links.html`
- Modify: `tests/test_branding.py`

- [ ] **Step 1: Write failing test for favicon conditional**

Append to `tests/test_branding.py`:
```python
from django.template.loader import render_to_string


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
```

- [ ] **Step 2: Run and confirm failures**

Run: `pytest tests/test_branding.py::BrandingFaviconTemplateTests -v`
Expected: `test_custom_favicon_url_used_when_set` fails — the template currently always renders the static favicons, so `/media/branding/custom.png` is never in the output.

- [ ] **Step 3: Edit `templates/common/head-links.html`**

Open the file. Find the current lines 3, 4, and 7 (the three browser-favicon `<link>` tags). Wrap all three in a conditional, leaving the `apple-touch-icon`, `manifest`, `mask-icon`, and other tags untouched.

Before (lines 2-7):
```django
		<link rel="apple-touch-icon" sizes="180x180" href="{% static "favicons/apple-touch-icon.png" %}">
		<link rel="icon" type="image/png" sizes="32x32" href="{% static "favicons/favicon-32x32.png" %}">
		<link rel="icon" type="image/png" sizes="16x16" href="{% static "favicons/favicon-16x16.png" %}">
		<link rel="manifest" href="{% static "favicons/site.webmanifest" %}">
		<link rel="mask-icon" href="{% static "favicons/safari-pinned-tab.svg" %}" color="#009933">
		<link rel="shortcut icon" href="{% static "favicons/favicon.ico" %}">
```

After:
```django
		<link rel="apple-touch-icon" sizes="180x180" href="{% static "favicons/apple-touch-icon.png" %}">
		{% if BRANDING_FAVICON_URL %}
		<link rel="icon" type="image/png" sizes="32x32" href="{{ BRANDING_FAVICON_URL }}">
		<link rel="icon" type="image/png" sizes="16x16" href="{{ BRANDING_FAVICON_URL }}">
		<link rel="shortcut icon" href="{{ BRANDING_FAVICON_URL }}">
		{% else %}
		<link rel="icon" type="image/png" sizes="32x32" href="{% static "favicons/favicon-32x32.png" %}">
		<link rel="icon" type="image/png" sizes="16x16" href="{% static "favicons/favicon-16x16.png" %}">
		<link rel="shortcut icon" href="{% static "favicons/favicon.ico" %}">
		{% endif %}
		<link rel="manifest" href="{% static "favicons/site.webmanifest" %}">
		<link rel="mask-icon" href="{% static "favicons/safari-pinned-tab.svg" %}" color="#009933">
```

- [ ] **Step 4: Run tests and confirm they pass**

Run: `pytest tests/test_branding.py::BrandingFaviconTemplateTests -v`
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add templates/common/head-links.html tests/test_branding.py
git commit -m "branding favicon override"
```

---

## Task 8: Auth-page hero on login / signup / password reset

**Files:**
- Modify: `templates/account/login.html`
- Modify: `templates/account/signup.html`
- Modify: `templates/account/password_reset.html`
- Modify: `tests/test_branding.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_branding.py`:
```python
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
        from django.contrib.auth.models import AnonymousUser
        html = render_to_string(
            "account/password_reset.html",
            context={
                "BRANDING_LOGIN_HERO_URL": "/media/branding/login.png",
                "PORTAL_NAME": "Azteca",
                # AnonymousUser avoids triggering {% include "already_logged_in.html" %}
                "user": AnonymousUser(),
                "form": None,
            },
        )
        self.assertIn('src="/media/branding/login.png"', html)
```

- [ ] **Step 2: Run and confirm failures**

Run: `pytest tests/test_branding.py::BrandingAuthHeroTests -v`
Expected: all four tests fail — the templates don't include any `auth-hero` markup yet.

- [ ] **Step 3: Edit `templates/account/login.html`**

Find the `{% block innercontent %}` block and insert the hero `<div>` inside `user-action-form-inner`, directly before the `<h1>Sign In</h1>` line.

Before:
```django
{% block innercontent %}
<div class="user-action-form-wrap">
    <div class="user-action-form-inner">

		<h1>Sign In</h1>
```

After:
```django
{% block innercontent %}
<div class="user-action-form-wrap">
    <div class="user-action-form-inner">

		{% if BRANDING_LOGIN_HERO_URL %}
		<div class="auth-hero"><img src="{{ BRANDING_LOGIN_HERO_URL }}" alt="{{ PORTAL_NAME }}"></div>
		{% endif %}

		<h1>Sign In</h1>
```

- [ ] **Step 4: Edit `templates/account/signup.html`**

Same pattern, keyed on `BRANDING_REGISTER_HERO_URL`.

Before:
```django
{% block innercontent %}
<div class="user-action-form-wrap">
    <div class="user-action-form-inner">

		<h1>Sign Up</h1>
```

After:
```django
{% block innercontent %}
<div class="user-action-form-wrap">
    <div class="user-action-form-inner">

		{% if BRANDING_REGISTER_HERO_URL %}
		<div class="auth-hero"><img src="{{ BRANDING_REGISTER_HERO_URL }}" alt="{{ PORTAL_NAME }}"></div>
		{% endif %}

		<h1>Sign Up</h1>
```

- [ ] **Step 5: Edit `templates/account/password_reset.html`**

Reuse the login hero URL.

Before:
```django
{% block innercontent %}
<div class="user-action-form-wrap">
    <div class="user-action-form-inner">

    <h1>{% trans "Password Reset" %}</h1>
```

After:
```django
{% block innercontent %}
<div class="user-action-form-wrap">
    <div class="user-action-form-inner">

    {% if BRANDING_LOGIN_HERO_URL %}
    <div class="auth-hero"><img src="{{ BRANDING_LOGIN_HERO_URL }}" alt="{{ PORTAL_NAME }}"></div>
    {% endif %}

    <h1>{% trans "Password Reset" %}</h1>
```

- [ ] **Step 6: Run tests and confirm they pass**

Run: `pytest tests/test_branding.py::BrandingAuthHeroTests -v`
Expected: all four tests pass.

- [ ] **Step 7: Commit**

```bash
git add templates/account/login.html templates/account/signup.html templates/account/password_reset.html tests/test_branding.py
git commit -m "branding auth page hero images"
```

---

## Task 9: Branded 404 page image

**Files:**
- Modify: `templates/404.html`
- Modify: `tests/test_branding.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_branding.py`:
```python
class Branding404Tests(TestCase):
    def test_404_template_includes_image_when_url_set(self):
        html = render_to_string(
            "404.html",
            context={
                "BRANDING_NOT_FOUND_URL": "/media/branding/404.png",
                "PORTAL_NAME": "Azteca",
            },
        )
        self.assertIn('src="/media/branding/404.png"', html)

    def test_404_template_omits_image_when_url_blank(self):
        html = render_to_string(
            "404.html",
            context={
                "BRANDING_NOT_FOUND_URL": "",
                "PORTAL_NAME": "Azteca",
            },
        )
        self.assertNotIn('class="auth-hero"', html)
```

- [ ] **Step 2: Run and confirm failure**

Run: `pytest tests/test_branding.py::Branding404Tests -v`
Expected: `test_404_template_includes_image_when_url_set` fails; current `404.html` only contains the "you are lost!" paragraph.

- [ ] **Step 3: Edit `templates/404.html`**

Before:
```django
{% extends "base.html" %}

{% block headtitle %} - error{% endblock headtitle %}

{% block innercontent %}
	<p>you are lost!</p>
{% endblock %}
```

After:
```django
{% extends "base.html" %}

{% block headtitle %} - error{% endblock headtitle %}

{% block innercontent %}
	{% if BRANDING_NOT_FOUND_URL %}
	<div class="auth-hero"><img src="{{ BRANDING_NOT_FOUND_URL }}" alt="{{ PORTAL_NAME }}"></div>
	{% endif %}
	<p>you are lost!</p>
{% endblock %}
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `pytest tests/test_branding.py::Branding404Tests -v`
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add templates/404.html tests/test_branding.py
git commit -m "branding 404 page image"
```

---

## Task 10: Add `.auth-hero` CSS rule

**Files:**
- Modify: `static/css/_extra.css`

- [ ] **Step 1: Append the rule**

Open `static/css/_extra.css`. The file currently ends with a `body { ... }` block and two blank lines. Append the new rule at the bottom of the file.

Before (last lines of file):
```css
  @media screen and (min-width: 2200px) {
      --default-item-width: 342px !important;
      --default-max-item-width: 342px !important;
      --default-item-margin-right-width: 17px !important;
      --default-item-margin-bottom-width: 27px !important;
  }
}



```

After:
```css
  @media screen and (min-width: 2200px) {
      --default-item-width: 342px !important;
      --default-max-item-width: 342px !important;
      --default-item-margin-right-width: 17px !important;
      --default-item-margin-bottom-width: 27px !important;
  }
}

.auth-hero {
  text-align: center;
  margin-bottom: 24px;
}

.auth-hero img {
  max-width: 240px;
  height: auto;
  display: inline-block;
}
```

- [ ] **Step 2: Visual smoke check (optional)**

Start the dev server and visit `/accounts/login/` after uploading a login hero image via the admin. The image should appear centered above the "Sign In" heading, capped at 240 px wide.

- [ ] **Step 3: Commit**

```bash
git add static/css/_extra.css
git commit -m "branding auth hero css"
```

---

## Task 11: End-to-end smoke test

This task verifies that every layer — model, context processor, template, view — hangs together when a branding row is populated.

**Files:**
- Modify: `tests/test_branding.py`

- [ ] **Step 1: Write the end-to-end test**

Append to `tests/test_branding.py`:
```python
class BrandingEndToEndTests(TestCase):
    def setUp(self):
        cache.delete(BRANDING_CACHE_KEY)
        self.client = Client()

    def test_login_page_renders_uploaded_hero(self):
        """Uploading a login hero via the model surfaces on a real login-page render."""
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

    def test_home_page_reflects_portal_name(self):
        obj = BrandingSettings.load()
        obj.portal_name = "Azteca Tax Systems Media"
        obj.save()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Azteca Tax Systems Media")
```

- [ ] **Step 2: Run the end-to-end tests**

Run: `pytest tests/test_branding.py::BrandingEndToEndTests -v`
Expected: both tests pass.

If `test_home_page_reflects_portal_name` fails because the home route is behind auth or returns a non-200 status on a bare DB, drop it — the login-page test is the load-bearing one. Keeping only the auth-page test is acceptable.

- [ ] **Step 3: Run the entire branding test file**

Run: `pytest tests/test_branding.py -v`
Expected: every test from Tasks 2, 4, 5, 6, 7, 8, 9, and 11 passes.

- [ ] **Step 4: Run the broader test suite to catch regressions**

Run: `pytest -x`
Expected: the whole suite passes. If a pre-existing test was already failing before this feature, note it and move on — the branding work must not cause new failures.

- [ ] **Step 5: Commit**

```bash
git add tests/test_branding.py
git commit -m "branding end to end tests"
```

---

## Task 12: Deployment verification checklist (manual, pre-merge)

This is a non-code task. Run through it once before merging the branch to `main`.

- [ ] **Step 1: Verify the initial deploy is a no-op**

On a staging container (or local docker stack), pull the branch and run migrations. Confirm:
- The admin sidebar has a new "Branding" section.
- Clicking "Branding settings" lands on the edit form (no changelist, no add button, no delete button).
- Every visible page (`/`, `/accounts/login/`, `/accounts/signup/`, a 404) looks identical to before the branch — because all branding fields are blank.

- [ ] **Step 2: Verify uploads take effect without restart**

In the admin: fill in portal name, upload PNG logos, upload a favicon and a login hero, save. Open a new tab and visit `/` and `/accounts/login/`. Confirm:
- Portal name updated in the browser tab and sidebar.
- Favicon updated in the tab icon.
- Login hero visible.
- No container restart was needed.

- [ ] **Step 3: Verify cross-container propagation**

`docker compose restart` is NOT required. Open the `web` and `celery_worker` logs; no errors. Save a branding change, reload any page served by `web`, confirm the change is visible — proving Redis cache invalidation is working.

- [ ] **Step 4: Verify fallback still works**

Blank every branding field in the admin and save. Confirm the portal reverts to the current `settings.py` values (including whatever is in `deploy/docker/local_settings.py`). No error pages.

---

## Notes for the implementing engineer

- **Tests import from `branding.models` directly.** That's intentional — the scaffold in Task 1 creates the stub module, and Task 2 tests fail on `ImportError` first. Don't skip the empty stub in Task 1.
- **`cache.delete()` in `setUp`.** Every test class that touches `BrandingSettings.load()` must clear `BRANDING_CACHE_KEY` in `setUp`, otherwise a cached instance from a prior test leaks across cases. The pattern is in every test class in this plan.
- **`SimpleUploadedFile` for image fields.** Django's `ImageField` uses Pillow to verify the file is actually an image; the bytes in the examples are a minimal valid PNG header. Don't shortcut this to `b"..."` literals or the field validation will reject the upload.
- **`render_to_string` context keys.** The template tests mock out just the variables each template actually references. If you add a new variable to a template later, the corresponding test will fail with `VariableDoesNotExist` — add the missing key to the test context.
- **Don't add `"branding"` to `admin_customizations/apps.py:apps_to_hide`.** That list is for apps we want *hidden* from the admin sidebar. Branding should be visible; the default sort-order of 999 drops it to the bottom, which is fine.
- **Don't touch `templates/config/installation/site.html`.** The whole point of this architecture is that the React frontend picks up branding via the context processor automatically. Modifying that file would double-wire the data and risk inconsistency.
- **Don't modify `deploy/docker/local_settings.py`.** Operators' existing overrides still work; admin uploads take precedence only when populated. Preserving that file untouched is part of the backwards-compatibility contract.
