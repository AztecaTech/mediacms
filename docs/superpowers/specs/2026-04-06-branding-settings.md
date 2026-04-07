# Branding Settings — Design Spec

**Date:** 2026-04-06
**Status:** Approved for implementation planning
**Scope:** Phase 1 (identity + logos) + Phase 2 (auth-page artwork)
**Deferred to later phases:** Phase 3 (color theming), Phase 4 (email template branding)

---

## 1. Problem

MediaCMS white-labeling currently requires editing Python settings files (`cms/settings.py`, `deploy/docker/local_settings.py`) and restarting containers. Operators of this fork need to change logos, portal name, footer text, and auth-page artwork without a code-edit-and-redeploy loop. A bundled SVG logo with legacy MediaCMS branding has already forced one workaround (`PORTAL_LOGO_*_SVG = ""` in `local_settings.py` to force PNG fallbacks), proving the settings-file approach is the wrong surface.

## 2. Goals

- Let an admin upload logos, favicon, and auth-page artwork from a web UI.
- Let an admin edit portal name, description, and footer text from a web UI.
- Changes take effect across all running containers (web, celery_worker, celery_beat) on next page load without restart.
- First deploy after merging must change nothing visually — new feature is opt-in, fields start empty and fall back to current `settings.py` values.
- No React rebuild required. The existing context-processor-to-site.html-to-window.MediaCMS pipeline already carries logo URLs and portal name to the React frontend; updating the upstream context values flows to the whole app for free.

## 3. Non-Goals

- Color / accent / dark-palette theming (Phase 3, separate spec).
- Email template branding — password reset / signup verification mails (Phase 4, separate spec).
- SVG logo uploads (rejected: user-uploaded SVG is an XSS vector; PNG/JPG/WebP only).
- A React-based settings page with live preview (rejected: 5–10× the effort of the Django admin form for the same functional outcome).
- About-page editable text (MediaCMS already has a `Page` model with an admin for editable static pages; don't duplicate it).

## 4. Surface Decision

**Django admin (`/admin/`) hosts the Branding Settings UI.** Same login surface operators already use for categories and users. Django's `ModelAdmin` provides file-upload widgets, form validation, and permission handling for free. The alternative — a React "Manage" page — was considered and rejected as too expensive for a settings page touched rarely.

The model is a **singleton**: exactly one row, always `pk=1`, never deleted, never duplicated. The admin changelist is skipped entirely; clicking "Branding settings" in the admin sidebar jumps straight to the edit form for the single row.

## 5. Data Model

A new Django app `branding/` houses a single model. Lives at the repo root as a top-level app, not nested inside `files/` (`files/models/` is already crowded and this is not file-domain logic).

```python
# branding/models.py
from django.core.cache import cache
from django.db import models

BRANDING_CACHE_KEY = "branding_settings"

class BrandingSettings(models.Model):
    # --- Identity (Phase 1) ---
    portal_name        = models.CharField(max_length=120, blank=True)
    portal_description = models.CharField(max_length=300, blank=True)
    footer_text        = models.TextField(blank=True)

    # --- Logos (Phase 1) ---
    logo_dark_mode  = models.ImageField(upload_to="branding/", blank=True)  # shown on dark backgrounds
    logo_light_mode = models.ImageField(upload_to="branding/", blank=True)  # shown on light backgrounds
    favicon         = models.ImageField(upload_to="branding/", blank=True)  # PNG, browsers handle it

    # --- Auth-page artwork (Phase 2) ---
    login_hero_image    = models.ImageField(upload_to="branding/", blank=True)
    register_hero_image = models.ImageField(upload_to="branding/", blank=True)
    not_found_image     = models.ImageField(upload_to="branding/", blank=True)  # 404 page

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branding settings"
        verbose_name_plural = "Branding settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # force singleton
        super().save(*args, **kwargs)
        cache.delete(BRANDING_CACHE_KEY)  # invalidate read cache

    def delete(self, *args, **kwargs):
        pass  # singleton — never deletable

    @classmethod
    def load(cls):
        obj = cache.get(BRANDING_CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(BRANDING_CACHE_KEY, obj, timeout=None)
        return obj
```

### Design decisions

1. **Every field is `blank=True`.** An empty field means "fall back to whatever `settings.py` has". Day-of-deploy, nothing visually changes until an admin uploads something. Zero risk of breaking existing deployments.
2. **No SVG uploads.** Accepting user-uploaded SVG opens an XSS vector (SVG can embed `<script>` tags; Django doesn't sanitize). Locking to PNG/JPG/WebP avoids needing a sanitizer dependency. A 2000px-wide PNG looks crisp everywhere.
3. **Cache-invalidation on save.** The cache backend is Redis (`django_redis`), shared by every container. Admin saves take effect instantly across `web`, `celery_worker`, and `celery_beat` without restart. Without this, every page load would hit the DB; with it, it's one query per save.
4. **No `loading_logo` field.** MediaCMS has no splash screen, only CSS spinners. YAGNI.
5. **No `about_text` field.** The existing `Page` model already supports editable static pages.

## 6. Admin Registration

```python
# branding/admin.py
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import BrandingSettings

@admin.register(BrandingSettings)
class BrandingSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identity",   {"fields": ("portal_name", "portal_description", "footer_text")}),
        ("Logos",      {"fields": ("logo_dark_mode", "logo_light_mode", "favicon")}),
        ("Auth pages", {"fields": ("login_hero_image", "register_hero_image", "not_found_image")}),
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

Result in the Django admin sidebar: a new "Branding" section appears alongside "Media" and "Users". Clicking "Branding settings" drops the admin straight into the edit form — no list, no add button, no delete button.

## 7. Read Path — Context Processor Overlay

`files/context_processors.py:stuff()` already injects `PORTAL_NAME`, `PORTAL_LOGO_*`, and `SIDEBAR_FOOTER_TEXT` into every Django template context. Modify that function to overlay values from `BrandingSettings.load()` on top of the `settings.py` defaults:

```python
# files/context_processors.py — modified section
from branding.models import BrandingSettings

def stuff(request):
    ret = {...}  # all existing keys assembled by the current implementation — unchanged

    branding = BrandingSettings.load()  # cached singleton, ~0 cost after first call

    ret["PORTAL_NAME"]         = branding.portal_name        or settings.PORTAL_NAME
    ret["PORTAL_DESCRIPTION"]  = branding.portal_description or settings.PORTAL_DESCRIPTION
    ret["SIDEBAR_FOOTER_TEXT"] = branding.footer_text        or settings.SIDEBAR_FOOTER_TEXT

    # Logos: branding image wins, else fall back to settings.py paths.
    # When a branding raster logo is set, SVG keys are blanked so templates prefer the raster.
    ret["PORTAL_LOGO_DARK_PNG"]  = branding.logo_dark_mode.url  if branding.logo_dark_mode  else getattr(settings, "PORTAL_LOGO_DARK_PNG", "")
    ret["PORTAL_LOGO_LIGHT_PNG"] = branding.logo_light_mode.url if branding.logo_light_mode else getattr(settings, "PORTAL_LOGO_LIGHT_PNG", "")
    ret["PORTAL_LOGO_DARK_SVG"]  = "" if branding.logo_dark_mode  else getattr(settings, "PORTAL_LOGO_DARK_SVG", "")
    ret["PORTAL_LOGO_LIGHT_SVG"] = "" if branding.logo_light_mode else getattr(settings, "PORTAL_LOGO_LIGHT_SVG", "")

    # New keys for favicon and auth-page artwork
    ret["BRANDING_FAVICON_URL"]       = branding.favicon.url             if branding.favicon             else ""
    ret["BRANDING_LOGIN_HERO_URL"]    = branding.login_hero_image.url    if branding.login_hero_image    else ""
    ret["BRANDING_REGISTER_HERO_URL"] = branding.register_hero_image.url if branding.register_hero_image else ""
    ret["BRANDING_NOT_FOUND_URL"]     = branding.not_found_image.url     if branding.not_found_image     else ""

    return ret
```

**Cross-container propagation:** `BrandingSettings.save()` calls `cache.delete("branding_settings")`. Because the cache backend is Redis (shared by `web` + `celery_worker` + `celery_beat`), the next page load on any container re-fetches the row and re-caches. No restarts, no cold-cache hot spots.

## 8. Template Integration

Four surgical template edits. None of them get rewritten.

### 8a. Favicon override — `templates/common/head-links.html`

Wrap the three browser-favicon `<link>` tags in a conditional. If `BRANDING_FAVICON_URL` is set, all three point at the uploaded file; otherwise the existing static defaults render unchanged.

```django
{% if BRANDING_FAVICON_URL %}
    <link rel="icon" type="image/png" sizes="32x32" href="{{ BRANDING_FAVICON_URL }}">
    <link rel="icon" type="image/png" sizes="16x16" href="{{ BRANDING_FAVICON_URL }}">
    <link rel="shortcut icon" href="{{ BRANDING_FAVICON_URL }}">
{% else %}
    <link rel="icon" type="image/png" sizes="32x32" href="{% static "favicons/favicon-32x32.png" %}">
    <link rel="icon" type="image/png" sizes="16x16" href="{% static "favicons/favicon-16x16.png" %}">
    <link rel="shortcut icon" href="{% static "favicons/favicon.ico" %}">
{% endif %}
```

The `apple-touch-icon` and web manifest tags stay on bundled defaults — browsers don't reach for them on desktop and the iOS use-case is rare for this deployment. Can be added to a later phase if needed.

### 8b. Auth-page hero images

Three templates get an optional hero image block prepended to their `innercontent`:

| Template                                 | URL key                      |
| ---------------------------------------- | ---------------------------- |
| `templates/account/login.html`           | `BRANDING_LOGIN_HERO_URL`    |
| `templates/account/signup.html`          | `BRANDING_REGISTER_HERO_URL` |
| `templates/account/password_reset.html`  | `BRANDING_LOGIN_HERO_URL`    |

Password reset reuses the login hero by design — same surface, same visual context, one fewer image for admins to upload.

```django
{% if BRANDING_LOGIN_HERO_URL %}
<div class="auth-hero"><img src="{{ BRANDING_LOGIN_HERO_URL }}" alt="{{ PORTAL_NAME }}"></div>
{% endif %}
```

Plus a CSS rule in `static/css/_extra.css` (operator-owned, no SCSS rebuild):

```css
.auth-hero img { max-width: 240px; margin: 0 auto 24px; display: block; }
```

### 8c. 404 page — `templates/404.html`

Same conditional pattern using `BRANDING_NOT_FOUND_URL`.

### 8d. No change to `templates/config/installation/site.html`

This is the highest-leverage finding. That file already reads `{{ PORTAL_LOGO_* }}` and `{{ PORTAL_NAME }}` from context to populate `window.MediaCMS.site`. Since the context processor now returns the new branding values, the React frontend picks them up automatically. **Phase 1 covers the entire React app for free with zero React code changes.**

## 9. Storage, Migration, Fallback

**File storage.** Standard `ImageField` with `upload_to="branding/"`. Files land at `media_files/branding/*.png` inside the `mediacms_media` Docker volume — already persistent in `docker-compose.dokploy.yml`. Served by the same nginx + Django pipeline that serves user-uploaded videos. Zero new infrastructure.

**Migrations.**
1. `0001_initial.py` — auto-generated, creates the `branding_brandingsettings` table.
2. `0002_seed_singleton.py` — data migration, creates row `pk=1` with all blank fields. Guarantees `BrandingSettings.load()` always returns a row, never errors.

Both idempotent and reversible. Run by the existing `migrations` service in `docker-compose.dokploy.yml` on every deploy — no operator action needed.

**Fallback behavior (safety net).**

| Branding field state | Context value resolves to |
| -------------------- | ------------------------- |
| empty                | `settings.PORTAL_NAME` (or equivalent) |
| populated            | branding model value      |

The first deploy after merging this feature changes nothing visually. Operators upgrade safely, then start uploading on their own schedule.

**Cache key.** `"branding_settings"` (single key, infinite TTL, busted on `save()`). Lives in the existing Redis at `redis://redis:6379/1`. No new cache config.

## 10. File Map

### New files (8)

| Path                                         | Purpose |
| -------------------------------------------- | ------- |
| `branding/__init__.py`                       | empty |
| `branding/apps.py`                           | `BrandingConfig` — standard Django app config |
| `branding/models.py`                         | `BrandingSettings` model (Section 5) |
| `branding/admin.py`                          | `BrandingSettingsAdmin` (Section 6) |
| `branding/migrations/__init__.py`            | empty |
| `branding/migrations/0001_initial.py`        | auto-generated by `makemigrations` |
| `branding/migrations/0002_seed_singleton.py` | data migration creating `pk=1` row |
| `branding/tests.py`                          | unit tests (see Section 11) |

### Modified files (8)

| Path                                    | Change                                                                                 | Risk    |
| --------------------------------------- | -------------------------------------------------------------------------------------- | ------- |
| `cms/settings.py`                       | Add `"branding"` to `INSTALLED_APPS`                                                   | trivial |
| `files/context_processors.py`           | Overlay `BrandingSettings.load()` values onto existing keys + add 4 new keys           | low — additive, empty row → current behavior |
| `templates/common/head-links.html`      | Wrap 3 favicon `<link>` tags in `{% if BRANDING_FAVICON_URL %}` conditional            | trivial |
| `templates/account/login.html`          | Prepend optional `<div class="auth-hero">` block                                       | trivial |
| `templates/account/signup.html`         | Same                                                                                   | trivial |
| `templates/account/password_reset.html` | Same (reuses `BRANDING_LOGIN_HERO_URL`)                                                | trivial |
| `templates/404.html`                    | Same with `BRANDING_NOT_FOUND_URL`                                                     | trivial |
| `static/css/_extra.css`                 | Append `.auth-hero` rule (~1 line)                                                     | trivial |

### Files deliberately NOT touched

- **No React/SCSS rebuild.** `templates/config/installation/site.html` already reads the same context keys we're updating; the React app sees new values for free.
- **No `cms/settings.py` default removal.** `PORTAL_NAME`, `PORTAL_LOGO_*`, `SIDEBAR_FOOTER_TEXT` become the fallback, not the source of truth. Fully backwards compatible.
- **No `deploy/docker/local_settings.py` changes.** Operators keep existing overrides; admin uploads take precedence when set.
- **No `docker-compose.dokploy.yml` changes.** Reuses the existing `mediacms_media` volume and Redis cache.
- **No new `requirements.txt` entries.** Uses only Django stdlib and already-installed packages.

## 11. Tests

All in `branding/tests.py`. Target is confidence the feature works, not 100% coverage of Django's own behaviors.

| Test | What it proves |
| ---- | -------------- |
| `test_singleton_enforced`             | Calling `BrandingSettings.objects.create()` twice leaves exactly one row at `pk=1`. |
| `test_delete_is_noop`                 | `obj.delete()` does not remove the row. |
| `test_cache_invalidation_on_save`     | Modifying a field, calling `save()`, then `load()` returns the new value without a manual cache bust. |
| `test_context_processor_fallback`     | Empty branding row → `stuff()` returns `settings.PORTAL_NAME`. |
| `test_context_processor_override`     | Populated `branding.portal_name` → `stuff()` returns the branding value. |
| `test_admin_singleton_redirect`       | `GET /admin/branding/brandingsettings/` returns 302 to the change form for `pk=1`. |

## 12. Rollout & End-to-End Flow

After deploy, an admin logs into `/admin/`, clicks "Branding settings", and sees one form with three sections (Identity, Logos, Auth pages). They upload logo PNGs, a favicon, and a login hero image; fill in `Portal name = "Azteca Tax Systems Media"`; click Save.

Within one page reload, every container shows the new branding:
- Sidebar logo (light + dark mode variants)
- Browser tab title and favicon
- `og:title` meta tag (from `PORTAL_NAME`)
- Footer text
- Login / signup / password-reset hero image
- 404 page artwork
- `window.MediaCMS.site.*` values in the React app

No container restart, no code edit, no redeploy.

Email branding (Phase 4) and color theming (Phase 3) remain on the roadmap as separate brainstorms.

## 13. Open Risks

- **Image size limits.** Django's default `ImageField` has no size cap. An admin uploading a 50 MB PNG would land it in the media volume and serve it on every page. **Mitigation:** add a `clean_*()` method on the admin form rejecting files over 2 MB. Deferred to implementation plan; flagged here so it doesn't get forgotten.
- **Redis downtime.** If Redis is unreachable, `cache.get()` fails and `load()` falls through to a DB query on every request. This is the same failure mode every other cache-backed lookup in the app has; not unique to this feature.
- **Singleton race on first load.** Two concurrent requests on a fresh DB could both call `get_or_create(pk=1)`. Django's `get_or_create` handles this atomically via `IntegrityError` retry, so the outcome is still one row. No action needed.
