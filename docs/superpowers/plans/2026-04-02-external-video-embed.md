# External Video Embed Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow admins to add external videos (YouTube, Vimeo, any oEmbed platform) to MediaCMS, using the existing RBAC system for access control, so users only see videos their account is authorized to view.

**Architecture:** Extend the existing `Media` model with `source_url`, `source_type`, and `embed_html` fields. External videos skip the entire encoding pipeline and render via iframe embeds on the frontend. A Celery task fetches metadata (thumbnail, title) via oEmbed. All existing RBAC, categories, permissions, and search work unchanged.

**Tech Stack:** Django 4.x, Django REST Framework, Celery, React.js, Video.js (bypassed for external), PostgreSQL

**Spec:** `docs/superpowers/specs/2026-04-02-external-video-embed-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `files/models/utils.py` | Add `SOURCE_TYPES` choices |
| Modify | `files/models/media.py` | Add fields, `is_external` property, guard pipeline methods |
| Create | `files/migrations/XXXX_add_external_video_fields.py` | Django migration (auto-generated) |
| Modify | `files/serializers.py` | Expose `source_url`, `source_type`, `embed_html` in API |
| Modify | `files/views/media.py` | Accept `source_url` in POST, skip file requirement |
| Modify | `files/admin.py` | Add external fields to MediaAdmin |
| Modify | `files/forms.py` | Add external video support to metadata form |
| Modify | `files/tasks.py` | Add `fetch_external_metadata` task |
| Create | `files/external_utils.py` | oEmbed fetching + URL-to-embed-URL conversion |
| Modify | `frontend/src/static/js/components/media-viewer/VideoViewer/index.js` | Render iframe for external videos |
| Create | `frontend/src/static/js/components/media-viewer/ExternalVideoEmbed.js` | Iframe embed component |
| Modify | `frontend/src/static/js/pages/MediaPage.js` | Pass source data to VideoViewer |
| Create | `tests/test_external_video.py` | Backend tests |

---

## Task 1: Add Source Type Choices to Utils

**Files:**
- Modify: `files/models/utils.py` (after line 22)

- [ ] **Step 1: Add SOURCE_TYPES to utils.py**

In `files/models/utils.py`, add the following after the `MEDIA_STATES` tuple (after line 22):

```python
# source type for Media - local upload or external embed
SOURCE_TYPES = (
    ("local", "Local"),
    ("external", "External"),
)
```

- [ ] **Step 2: Commit**

```bash
git add files/models/utils.py
git commit -m "feat: add SOURCE_TYPES choices for external video support"
```

---

## Task 2: Add External Video Fields to Media Model

**Files:**
- Modify: `files/models/media.py` (lines 26-34 imports, lines 92-97 fields, lines 241-306 save, lines 383-409 media_init, lines 1000-1014 post_save, lines 1042-1072 post_delete)

- [ ] **Step 1: Add import for SOURCE_TYPES**

In `files/models/media.py`, update the import from `.utils` (lines 27-34) to include `SOURCE_TYPES`:

```python
from .utils import (
    ENCODE_RESOLUTIONS_KEYS,
    MEDIA_ENCODING_STATUS,
    MEDIA_STATES,
    MEDIA_TYPES_SUPPORTED,
    SOURCE_TYPES,
    original_media_file_path,
    original_thumbnail_file_path,
)
```

- [ ] **Step 2: Make media_file optional and add new fields**

In `files/models/media.py`, change the `media_file` field (lines 92-97) to allow blank/null:

```python
    media_file = models.FileField(
        "media file",
        upload_to=original_media_file_path,
        max_length=500,
        blank=True,
        null=True,
        help_text="media file",
    )
```

Then, after the `media_info` field (line 99), add the new fields:

```python
    media_info = models.TextField(blank=True, help_text="extracted media metadata info")

    source_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL of external video (YouTube, Vimeo, etc.)",
    )

    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default="local",
        help_text="Whether media is a local upload or external embed",
    )

    embed_html = models.TextField(
        blank=True,
        default="",
        help_text="Cached oEmbed HTML for platforms without known embed URL patterns",
    )
```

- [ ] **Step 3: Add is_external property**

In the Media model class, after the `__str__` method (around line 226), add:

```python
    @property
    def is_external(self):
        return self.source_type == "external"
```

- [ ] **Step 4: Guard save() method for external videos**

In the `save()` method (line 241), the line `self.title = self.media_file.path.split("/")[-1]` will crash for external videos. Change lines 242-243 from:

```python
    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.media_file.path.split("/")[-1]
```

to:

```python
    def save(self, *args, **kwargs):
        if not self.title:
            if self.media_file:
                self.title = self.media_file.path.split("/")[-1]
            else:
                self.title = "Untitled"
```

Also, in the same `save()` method, the media_file change detection (lines 266-275) needs guarding. Change:

```python
            # check case where another media file was uploaded
            if self.media_file != self.__original_media_file:
                # set this otherwise gets to infinite loop
                self.__original_media_file = self.media_file
                from .. import tasks

                tasks.media_init.apply_async(args=[self.friendly_token], countdown=5)
```

to:

```python
            # check case where another media file was uploaded
            if self.media_file and self.media_file != self.__original_media_file:
                # set this otherwise gets to infinite loop
                self.__original_media_file = self.media_file
                from .. import tasks

                tasks.media_init.apply_async(args=[self.friendly_token], countdown=5)
```

- [ ] **Step 5: Guard media_init() for external videos**

Change `media_init()` (lines 383-409) from:

```python
    def media_init(self):
        """Normally this is called when a media is uploaded
        Performs all related tasks, as check for media type,
        video duration, encode
        """
        self.set_media_type()
        from ..methods import is_media_allowed_type

        if not is_media_allowed_type(self):
            helpers.rm_file(self.media_file.path)
            if self.state == "public":
                self.state = "unlisted"
                self.save(update_fields=["state"])
            return False

        if self.media_type == "video":
            self.set_thumbnail(force=True)
            if settings.DO_NOT_TRANSCODE_VIDEO:
                self.encoding_status = "success"
                self.save()
                self.produce_sprite_from_video()
            else:
                self.produce_sprite_from_video()
                self.encode()
        elif self.media_type == "image":
            self.set_thumbnail(force=True)
        return True
```

to:

```python
    def media_init(self):
        """Normally this is called when a media is uploaded
        Performs all related tasks, as check for media type,
        video duration, encode
        """
        if self.is_external:
            # External videos skip the entire encoding pipeline
            self.media_type = "video"
            self.encoding_status = "success"
            self.save(update_fields=["media_type", "encoding_status"])
            from ..tasks import fetch_external_metadata
            fetch_external_metadata.delay(self.friendly_token)
            return True

        self.set_media_type()
        from ..methods import is_media_allowed_type

        if not is_media_allowed_type(self):
            helpers.rm_file(self.media_file.path)
            if self.state == "public":
                self.state = "unlisted"
                self.save(update_fields=["state"])
            return False

        if self.media_type == "video":
            self.set_thumbnail(force=True)
            if settings.DO_NOT_TRANSCODE_VIDEO:
                self.encoding_status = "success"
                self.save()
                self.produce_sprite_from_video()
            else:
                self.produce_sprite_from_video()
                self.encode()
        elif self.media_type == "image":
            self.set_thumbnail(force=True)
        return True
```

- [ ] **Step 6: Guard post_save signal for external videos**

In the `media_save` signal handler (lines 1000-1028), the `media_init()` call on line 1013 is fine — it will hit our early return. No change needed here.

However, in the `post_delete` signal (lines 1042-1072), guard the file deletions. Change lines 1048-1062 from:

```python
    if instance.media_file:
        helpers.rm_file(instance.media_file.path)
```

This is already guarded by the `if instance.media_file:` check, so no change is needed — the existing guard works because `media_file` will be falsy (None/empty) for external videos.

Verify: check that all other file references in `post_delete` also have guards. Lines 1050-1062 all check `if instance.thumbnail:`, `if instance.poster:`, etc. — these are all safe.

- [ ] **Step 7: Guard the original_media_url property**

Find the `original_media_url` property in the Media model (around line 655-660). It accesses `self.media_file.path`. Change:

```python
        return helpers.url_from_path(self.media_file.path)
```

to:

```python
        if self.is_external:
            return self.source_url
        return helpers.url_from_path(self.media_file.path)
```

Also find the `encodings_info` property (around line 680-695). It references `self.media_file.path`. Guard it:

Find lines like:
```python
            ret['0-original'] = {"h264": {"url": helpers.url_from_path(self.media_file.path), "status": "success", "progress": 100}}
```

Wrap with:
```python
        if self.is_external:
            return {}
```

Add this at the very top of the `encodings_info` property, before any other logic.

- [ ] **Step 8: Commit**

```bash
git add files/models/media.py
git commit -m "feat: add external video fields and pipeline guards to Media model"
```

---

## Task 3: Generate and Apply Database Migration

**Files:**
- Create: `files/migrations/XXXX_add_external_video_fields.py` (auto-generated)

- [ ] **Step 1: Generate migration**

```bash
cd /c/Users/Ivan/Documents/GitHub/mediacms
python manage.py makemigrations files --name add_external_video_fields
```

Expected: Migration file created showing addition of `source_url`, `source_type`, `embed_html` fields and `media_file` becoming nullable.

- [ ] **Step 2: Review the migration**

Read the generated migration file and verify it contains:
- `AddField` for `source_url` (URLField, blank=True, null=True)
- `AddField` for `source_type` (CharField, default="local")
- `AddField` for `embed_html` (TextField, blank=True, default="")
- `AlterField` for `media_file` (blank=True, null=True)

- [ ] **Step 3: Apply migration**

```bash
python manage.py migrate files
```

Expected: `Applying files.XXXX_add_external_video_fields... OK`

- [ ] **Step 4: Commit**

```bash
git add files/migrations/
git commit -m "feat: add migration for external video fields"
```

---

## Task 4: Create oEmbed Utility Module

**Files:**
- Create: `files/external_utils.py`

- [ ] **Step 1: Create the external_utils.py file**

Create `files/external_utils.py` with the following content:

```python
"""Utilities for external video embedding: oEmbed fetching and URL-to-embed conversion."""

import json
import logging
import re
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)

# Known oEmbed endpoints for popular platforms
OEMBED_ENDPOINTS = {
    "youtube": "https://www.youtube.com/oembed",
    "vimeo": "https://vimeo.com/api/oembed.json",
    "dailymotion": "https://www.dailymotion.com/services/oembed",
}

# Regex patterns to identify platforms from URLs
PLATFORM_PATTERNS = {
    "youtube": re.compile(
        r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]+)"
    ),
    "vimeo": re.compile(
        r"(?:https?://)?(?:www\.)?vimeo\.com/(\d+)"
    ),
    "dailymotion": re.compile(
        r"(?:https?://)?(?:www\.)?dailymotion\.com/video/([a-zA-Z0-9]+)"
    ),
}


def detect_platform(url):
    """Detect which platform a URL belongs to.

    Returns (platform_name, video_id) or (None, None).
    """
    for platform, pattern in PLATFORM_PATTERNS.items():
        match = pattern.search(url)
        if match:
            return platform, match.group(1)
    return None, None


def get_embed_url(url):
    """Convert a video URL to its embeddable iframe URL.

    Returns the embed URL string, or None if the platform is not recognized.
    """
    platform, video_id = detect_platform(url)

    if platform == "youtube":
        return f"https://www.youtube.com/embed/{video_id}"
    elif platform == "vimeo":
        return f"https://player.vimeo.com/video/{video_id}"
    elif platform == "dailymotion":
        return f"https://www.dailymotion.com/embed/video/{video_id}"

    return None


def fetch_oembed(url, max_width=720):
    """Fetch oEmbed metadata for a URL.

    Tries known platform endpoints first, then falls back to a generic
    oEmbed discovery approach.

    Returns a dict with keys like: title, thumbnail_url, html, duration,
    author_name, provider_name. Returns empty dict on failure.
    """
    platform, _ = detect_platform(url)

    # Try known endpoint first
    if platform and platform in OEMBED_ENDPOINTS:
        endpoint = OEMBED_ENDPOINTS[platform]
        result = _fetch_oembed_from_endpoint(endpoint, url, max_width)
        if result:
            return result

    # Try generic oEmbed discovery via noembed.com (supports many platforms)
    result = _fetch_oembed_from_endpoint("https://noembed.com/embed", url, max_width)
    if result:
        return result

    return {}


def _fetch_oembed_from_endpoint(endpoint, url, max_width):
    """Fetch oEmbed JSON from a specific endpoint.

    Returns parsed JSON dict or None on failure.
    """
    params = urllib.parse.urlencode({
        "url": url,
        "format": "json",
        "maxwidth": max_width,
    })
    request_url = f"{endpoint}?{params}"

    try:
        req = urllib.request.Request(request_url, headers={"User-Agent": "MediaCMS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        logger.warning("oEmbed fetch failed for %s from %s: %s", url, endpoint, e)
        return None


def download_thumbnail(thumbnail_url):
    """Download a thumbnail image from a URL.

    Returns (image_bytes, content_type) or (None, None) on failure.
    """
    try:
        req = urllib.request.Request(thumbnail_url, headers={"User-Agent": "MediaCMS/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "image/jpeg")
            image_data = response.read()
            return image_data, content_type
    except (urllib.error.URLError, TimeoutError) as e:
        logger.warning("Thumbnail download failed for %s: %s", thumbnail_url, e)
        return None, None
```

- [ ] **Step 2: Commit**

```bash
git add files/external_utils.py
git commit -m "feat: add oEmbed utility module for external video metadata"
```

---

## Task 5: Add Celery Task for External Metadata Fetching

**Files:**
- Modify: `files/tasks.py` (add new task after the `media_init` task around line 637)

- [ ] **Step 1: Add the fetch_external_metadata task**

In `files/tasks.py`, add the following import near the top imports (around line 31, with the other `from .helpers` imports):

```python
from .external_utils import fetch_oembed, download_thumbnail, get_embed_url
```

Then add the new task after the `media_init` task (after line 637):

```python
@task(name="fetch_external_metadata", queue="short_tasks")
def fetch_external_metadata(friendly_token):
    """Fetch metadata from oEmbed for external videos.

    Populates title (if empty), thumbnail, poster, embed_html, and duration.
    """
    try:
        media = Media.objects.get(friendly_token=friendly_token)
    except Media.DoesNotExist:
        logger.info("fetch_external_metadata: media not found for %s", friendly_token)
        return False

    if not media.is_external or not media.source_url:
        return False

    # Fetch oEmbed data
    oembed_data = fetch_oembed(media.source_url)

    update_fields = []

    # Set title from oEmbed if not already set
    if (not media.title or media.title == "Untitled") and oembed_data.get("title"):
        media.title = oembed_data["title"][:100]
        update_fields.append("title")

    # Set duration if available (some providers return this)
    if oembed_data.get("duration") and not media.duration:
        media.duration = int(oembed_data["duration"])
        update_fields.append("duration")

    # Cache embed HTML for platforms without known embed URL patterns
    embed_url = get_embed_url(media.source_url)
    if not embed_url and oembed_data.get("html"):
        media.embed_html = oembed_data["html"]
        update_fields.append("embed_html")

    # Download and save thumbnail
    thumbnail_url = oembed_data.get("thumbnail_url")
    if thumbnail_url:
        image_data, content_type = download_thumbnail(thumbnail_url)
        if image_data:
            ext = "jpg" if "jpeg" in (content_type or "") or "jpg" in (content_type or "") else "jpg"
            filename = f"{media.uid.hex}_external.{ext}"
            from django.core.files.base import ContentFile
            try:
                media.thumbnail.save(filename, ContentFile(image_data), save=False)
                update_fields.append("thumbnail")
                media.poster.save(filename, ContentFile(image_data), save=False)
                update_fields.append("poster")
            except Exception as e:
                logger.warning("Failed to save thumbnail for %s: %s", friendly_token, e)

    if update_fields:
        media.save(update_fields=update_fields)

    # Update search vector with new title
    media.update_search_vector()

    return True
```

- [ ] **Step 2: Commit**

```bash
git add files/tasks.py
git commit -m "feat: add fetch_external_metadata Celery task for oEmbed"
```

---

## Task 6: Update Serializers to Expose External Fields

**Files:**
- Modify: `files/serializers.py` (lines 38-82 MediaSerializer, lines 101-177 SingleMediaSerializer)

- [ ] **Step 1: Add fields to MediaSerializer**

In `files/serializers.py`, in the `MediaSerializer` class `Meta.fields` tuple (lines 55-82), add `"source_type"` after `"media_type"`:

```python
        fields = (
            "friendly_token",
            "url",
            "api_url",
            "user",
            "title",
            "description",
            "add_date",
            "views",
            "media_type",
            "source_type",
            "state",
            "duration",
            "thumbnail_url",
            "is_reviewed",
            "preview_url",
            "author_name",
            "author_profile",
            "author_thumbnail",
            "encoding_status",
            "views",
            "likes",
            "dislikes",
            "reported_times",
            "featured",
            "user_featured",
            "size",
            # "category",
        )
```

Also add `"source_type"` to `read_only_fields`:

```python
        read_only_fields = (
            "friendly_token",
            "user",
            "add_date",
            "media_type",
            "source_type",
            "state",
            "duration",
            "encoding_status",
            "views",
            "likes",
            "dislikes",
            "reported_times",
            "size",
            "is_reviewed",
            "featured",
        )
```

- [ ] **Step 2: Add fields to SingleMediaSerializer**

In the `SingleMediaSerializer` class `Meta.fields` tuple (lines 134-177), add `"source_url"`, `"source_type"`, and `"embed_html"` after `"is_shared"`:

```python
        fields = (
            "url",
            "user",
            "title",
            "description",
            "add_date",
            "edit_date",
            "media_type",
            "state",
            "is_shared",
            "source_url",
            "source_type",
            "embed_html",
            "duration",
            "thumbnail_url",
            "poster_url",
            "thumbnail_time",
            "url",
            "sprites_url",
            "preview_url",
            "author_name",
            "author_profile",
            "author_thumbnail",
            "encodings_info",
            "encoding_status",
            "views",
            "likes",
            "dislikes",
            "reported_times",
            "user_featured",
            "original_media_url",
            "size",
            "video_height",
            "enable_comments",
            "categories_info",
            "is_reviewed",
            "edit_url",
            "tags_info",
            "hls_info",
            "license",
            "subtitles_info",
            "chapter_data",
            "ratings_info",
            "add_subtitle_url",
            "allow_download",
            "slideshow_items",
        )
```

Also add `"source_type"` and `"source_url"` to `read_only_fields`:

```python
        read_only_fields = (
            "friendly_token",
            "user",
            "add_date",
            "views",
            "media_type",
            "source_type",
            "source_url",
            "state",
            "duration",
            "encoding_status",
            "views",
            "likes",
            "dislikes",
            "reported_times",
            "size",
            "video_height",
            "is_reviewed",
        )
```

- [ ] **Step 3: Commit**

```bash
git add files/serializers.py
git commit -m "feat: expose source_url, source_type, embed_html in API serializers"
```

---

## Task 7: Update API View to Accept External Video URLs

**Files:**
- Modify: `files/views/media.py` (lines 258-277, the POST method of MediaList)

- [ ] **Step 1: Update the POST method**

In `files/views/media.py`, replace the `post` method (lines 258-277) with:

```python
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(name="media_file", in_=openapi.IN_FORM, type=openapi.TYPE_FILE, required=False, description="media_file"),
            openapi.Parameter(name="source_url", in_=openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, description="External video URL (YouTube, Vimeo, etc.)"),
            openapi.Parameter(name="description", in_=openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, description="description"),
            openapi.Parameter(name="title", in_=openapi.IN_FORM, type=openapi.TYPE_STRING, required=False, description="title"),
        ],
        tags=['Media'],
        operation_summary='Add new Media',
        operation_description='Adds a new media. Provide either media_file (upload) or source_url (external video), not both.',
        responses={201: openapi.Response('response description', MediaSerializer), 400: 'bad request', 401: 'unauthorized'},
    )
    def post(self, request, format=None):
        # Add new media — either file upload or external URL
        source_url = request.data.get("source_url")
        media_file = request.data.get("media_file")

        if source_url and media_file:
            return Response(
                {"detail": "Provide either media_file or source_url, not both."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not source_url and not media_file:
            return Response(
                {"detail": "Provide either media_file or source_url."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MediaSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            if source_url:
                # External video
                from ..external_utils import get_embed_url
                embed_url = get_embed_url(source_url)
                serializer.save(
                    user=request.user,
                    source_url=source_url,
                    source_type="external",
                    media_type="video",
                    encoding_status="success",
                )
            else:
                # Local file upload
                serializer.save(user=request.user, media_file=media_file)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

**Extension (design spec §4 — upload workflow):** The implemented `POST` also accepts optional **`category_uids`** (repeated form keys or JSON list string) and optional **`uploaded_poster`** (image file), validated with `categories_queryset_for_uploading_user` and `parse_category_uids_from_request` in `files/methods.py`. Responses use a fresh `MediaSerializer` after M2M/poster updates.

- [ ] **Step 2: Commit**

```bash
git add files/views/media.py files/methods.py
git commit -m "feat: accept source_url in media API for external videos"
```

---

## Task 8: Update Django Admin for External Videos

**Files:**
- Modify: `files/admin.py` (lines 33-60, MediaAdmin class)

- [ ] **Step 1: Update MediaAdmin**

In `files/admin.py`, replace the `MediaAdmin` class (lines 33-60) with:

```python
class ExternalMediaForm(forms.ModelForm):
    """Custom form for Media admin that makes media_file optional for external videos."""

    class Meta:
        model = Media
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        source_url = cleaned_data.get('source_url')
        media_file = cleaned_data.get('media_file')

        if source_url and media_file:
            raise ValidationError("Provide either a media file or an external source URL, not both.")

        if not source_url and not media_file:
            # Check if this is an existing object that already has a media_file
            if not (self.instance and self.instance.pk and self.instance.media_file):
                raise ValidationError("Provide either a media file or an external source URL.")

        # Auto-set source_type
        if source_url:
            cleaned_data['source_type'] = 'external'
        elif not self.instance.pk or not self.instance.source_url:
            cleaned_data['source_type'] = 'local'

        return cleaned_data


class MediaAdmin(admin.ModelAdmin):
    form = ExternalMediaForm
    search_fields = ["title"]
    list_display = [
        "title",
        "user",
        "add_date",
        "media_type",
        "source_type",
        "duration",
        "state",
        "is_reviewed",
        "encoding_status",
        "featured",
        "get_comments_count",
    ]
    list_filter = ["state", "is_reviewed", "encoding_status", "featured", "category", "source_type"]
    ordering = ("-add_date",)
    readonly_fields = ("user", "tags", "category", "channel")

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'media_file', 'user')
        }),
        ('External Video', {
            'fields': ('source_url', 'source_type', 'embed_html'),
            'classes': ('collapse',),
            'description': 'For embedding videos from YouTube, Vimeo, etc. Provide a source URL instead of uploading a file.',
        }),
        ('Status & Visibility', {
            'fields': ('state', 'is_reviewed', 'encoding_status', 'featured', 'allow_download', 'enable_comments'),
        }),
        ('Metadata', {
            'fields': ('tags', 'category', 'channel', 'license'),
        }),
    )

    def get_comments_count(self, obj):
        return obj.comments.count()

    @admin.action(description="Generate missing encoding(s)", permissions=["change"])
    def generate_missing_encodings(modeladmin, request, queryset):
        for m in queryset:
            if not m.is_external:
                m.encode(force=False)

    actions = [generate_missing_encodings]
    get_comments_count.short_description = "Comments count"
```

- [ ] **Step 2: Commit**

```bash
git add files/admin.py
git commit -m "feat: add external video fields to Django admin with validation"
```

---

## Task 9: Create ExternalVideoEmbed Frontend Component

**Files:**
- Create: `frontend/src/static/js/components/media-viewer/ExternalVideoEmbed.js`

- [ ] **Step 1: Create the component**

Create `frontend/src/static/js/components/media-viewer/ExternalVideoEmbed.js`:

```jsx
import React from 'react';
import PropTypes from 'prop-types';

// Known platform URL-to-embed transformations
function getEmbedUrl(sourceUrl) {
    if (!sourceUrl) return null;

    // YouTube: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/shorts/ID
    const ytMatch = sourceUrl.match(
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)/
    );
    if (ytMatch) {
        return `https://www.youtube.com/embed/${ytMatch[1]}`;
    }

    // Vimeo: vimeo.com/ID
    const vimeoMatch = sourceUrl.match(/vimeo\.com\/(\d+)/);
    if (vimeoMatch) {
        return `https://player.vimeo.com/video/${vimeoMatch[1]}`;
    }

    // Dailymotion: dailymotion.com/video/ID
    const dmMatch = sourceUrl.match(/dailymotion\.com\/video\/([a-zA-Z0-9]+)/);
    if (dmMatch) {
        return `https://www.dailymotion.com/embed/video/${dmMatch[1]}`;
    }

    return null;
}

export default function ExternalVideoEmbed({ sourceUrl, embedHtml, containerStyles }) {
    // Try known platform embed URL first
    const embedUrl = getEmbedUrl(sourceUrl);

    if (embedUrl) {
        return (
            <div className="player-container external-video-container" style={containerStyles}>
                <div className="player-container-inner" style={{ position: 'relative', paddingBottom: '56.25%', height: 0, overflow: 'hidden' }}>
                    <iframe
                        src={embedUrl}
                        style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                        title="External video"
                    />
                </div>
            </div>
        );
    }

    // Fall back to cached oEmbed HTML
    if (embedHtml) {
        return (
            <div
                className="player-container external-video-container"
                style={containerStyles}
                dangerouslySetInnerHTML={{ __html: embedHtml }}
            />
        );
    }

    // Last resort: link to the video
    return (
        <div className="player-container external-video-container" style={containerStyles}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px' }}>
                <a href={sourceUrl} target="_blank" rel="noopener noreferrer" style={{ fontSize: '1.2em' }}>
                    Open video in new tab
                </a>
            </div>
        </div>
    );
}

ExternalVideoEmbed.propTypes = {
    sourceUrl: PropTypes.string.isRequired,
    embedHtml: PropTypes.string,
    containerStyles: PropTypes.object,
};

ExternalVideoEmbed.defaultProps = {
    embedHtml: '',
    containerStyles: {},
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/static/js/components/media-viewer/ExternalVideoEmbed.js
git commit -m "feat: add ExternalVideoEmbed React component for iframe playback"
```

---

## Task 10: Update VideoViewer to Handle External Videos

**Files:**
- Modify: `frontend/src/static/js/components/media-viewer/VideoViewer/index.js` (lines 36-457)

- [ ] **Step 1: Import ExternalVideoEmbed**

At the top of `VideoViewer/index.js`, add the import after line 14:

```javascript
import ExternalVideoEmbed from '../ExternalVideoEmbed';
```

- [ ] **Step 2: Add external video check in constructor**

In the constructor (lines 37-50), after `this.videoSources = [];` (line 44), add an early return for external videos:

```javascript
        this.videoSources = [];

        // External videos use iframe embed, skip Video.js setup entirely
        if (this.props.data.source_type === 'external') {
            this.state.displayPlayer = true;
            this.isExternal = true;
            return;
        }
        this.isExternal = false;

        filterVideoEncoding(this.props.data.encoding_status);
```

This replaces the existing line 46 (`filterVideoEncoding(this.props.data.encoding_status);`). The `filterVideoEncoding` call and everything after it in the constructor should only run for local videos.

- [ ] **Step 3: Update render method**

In the `render()` method (line 346), add an external video branch at the very top of the method, before any existing logic:

Change the render method to start with:

```javascript
    render() {
        // External video: render iframe embed instead of Video.js
        if (this.isExternal) {
            return (
                <ExternalVideoEmbed
                    sourceUrl={this.props.data.source_url}
                    embedHtml={this.props.data.embed_html}
                    containerStyles={this.props.containerStyles}
                />
            );
        }

        let nextLink = null;
        let previousLink = null;
        // ... rest of existing render method unchanged
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/static/js/components/media-viewer/VideoViewer/index.js
git commit -m "feat: render ExternalVideoEmbed for external videos in VideoViewer"
```

---

## Task 11: Update MediaPage to Pass Source Data

**Files:**
- Modify: `frontend/src/static/js/pages/MediaPage.js` (lines 45-62)

- [ ] **Step 1: Update viewerContainerContent**

The `MediaPage.viewerContainerContent` (line 46) passes `mediaData` to `VideoViewer`. Since `mediaData` comes from the API response and our serializer now includes `source_url`, `source_type`, and `embed_html`, this data will automatically flow through to `VideoViewer` via `this.props.data`.

No change needed here — the data flows through `mediaData` automatically.

Verify by reading `MediaPage.js` line 51:
```javascript
<SiteConsumer>{(site) => <VideoViewer data={mediaData} siteUrl={site.url} inEmbed={!1} />}</SiteConsumer>
```

`mediaData` is `MediaPageStore.get('media-data')` which is the full API response from `SingleMediaSerializer`. Since we added `source_url`, `source_type`, and `embed_html` to that serializer, they'll be in `mediaData` automatically.

- [ ] **Step 2: Mark complete — no code change needed**

This task confirms the data flow is correct. No commit needed.

---

## Task 12: Update Upload Page with External Video Tab

**Files (as implemented in MediaCMS):**
- Modify: `templates/cms/add-media.html` — primary Django upload view (`upload_media`)
- Modify: `files/views/pages.py` — pass `external_upload_categories` for the category multiselect
- Modify: `frontend/config/templates/htmlBodySnippetAddMediaPage.ejs` — SPA dev upload page (loads categories via `GET /api/v1/categories`)

NOTE: The upload page uses the Fine Uploader library for chunked uploads. The external video form POSTs as `multipart/form-data` to `/api/v1/media` (supports optional `category_uids` and `uploaded_poster`).

- [ ] **Step 1: Locate the upload UI section**

The Fine Uploader integration lives in `templates/cms/add-media.html` (production) and `htmlBodySnippetAddMediaPage.ejs` (frontend bundle).

- [ ] **Step 2: Add external video form**

Add a tabbed interface with an "External Video" section containing:
- URL input field (required)
- Title input field (optional)  
- Description textarea (optional)
- Category select dropdown (optional)
- Thumbnail file input (optional, for manual override)
- Submit button

On submit, POST to `/api/v1/media` with `FormData`: `source_url`, optional `title`, `description`, repeated `category_uids`, optional file `uploaded_poster`. Use `X-CSRFToken` and session cookies (`credentials: 'same-origin'`). On success, redirect to `data.url`.

The key points are:
1. Toggle between "Upload file" and "External video" modes
2. External flow uses `fetch` + `FormData`, not Fine Uploader
3. On success, redirect to the new media page

- [ ] **Step 3: Commit**

```bash
git add templates/cms/add-media.html files/views/pages.py frontend/config/templates/htmlBodySnippetAddMediaPage.ejs
git commit -m "feat: add external video form to upload pages"
```

---

## Task 13: Hide Download Button for External Videos

**Files:**
- Modify: `files/models/media.py` (in the `save()` method)

- [ ] **Step 1: Force allow_download=False for external videos**

In the `save()` method of the Media model, just before the `super().save()` call (line 306), add:

```python
        # External videos cannot be downloaded
        if self.is_external:
            self.allow_download = False
```

So it reads:

```python
        # External videos cannot be downloaded
        if self.is_external:
            self.allow_download = False

        super(Media, self).save(*args, **kwargs)
```

- [ ] **Step 2: Commit**

```bash
git add files/models/media.py
git commit -m "feat: force allow_download=False for external videos"
```

---

## Task 14: Guard Remaining Media Model Methods

**Files:**
- Modify: `files/models/media.py` (various properties that access media_file.path)

- [ ] **Step 1: Guard set_thumbnail method**

Find the `set_thumbnail` method in the Media model. Add at the top:

```python
    def set_thumbnail(self, force=False):
        if self.is_external:
            return False
        # ... rest of existing method
```

- [ ] **Step 2: Guard produce_sprite_from_video method**

Find the `produce_sprite_from_video` method. Add at the top:

```python
    def produce_sprite_from_video(self):
        if self.is_external:
            return False
        # ... rest of existing method
```

- [ ] **Step 3: Guard encode method**

Find the `encode` method. Add at the top:

```python
    def encode(self, force=True):
        if self.is_external:
            return False
        # ... rest of existing method
```

- [ ] **Step 4: Guard the hls_info property**

Find the `hls_info` property. Add at the top:

```python
    @property
    def hls_info(self):
        if self.is_external:
            return {}
        # ... rest of existing method
```

- [ ] **Step 5: Guard preview_url property**

Find the `preview_url` property. If it accesses `media_file.path`, add a guard:

```python
    @property
    def preview_url(self):
        if self.is_external:
            return ""
        # ... rest of existing method
```

- [ ] **Step 6: Commit**

```bash
git add files/models/media.py
git commit -m "feat: guard all media_file-dependent methods for external videos"
```

---

## Task 15: Write Backend Tests

**Files:**
- Create: `tests/test_external_video.py`

- [ ] **Step 1: Create the test file**

Create `tests/test_external_video.py`:

```python
"""Tests for external video embedding support."""

import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from files.models import Media
from files.external_utils import detect_platform, get_embed_url, fetch_oembed

User = get_user_model()


class DetectPlatformTests(TestCase):
    """Tests for URL platform detection."""

    def test_youtube_watch_url(self):
        platform, video_id = detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(platform, "youtube")
        self.assertEqual(video_id, "dQw4w9WgXcQ")

    def test_youtube_short_url(self):
        platform, video_id = detect_platform("https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(platform, "youtube")
        self.assertEqual(video_id, "dQw4w9WgXcQ")

    def test_youtube_shorts_url(self):
        platform, video_id = detect_platform("https://youtube.com/shorts/dQw4w9WgXcQ")
        self.assertEqual(platform, "youtube")
        self.assertEqual(video_id, "dQw4w9WgXcQ")

    def test_vimeo_url(self):
        platform, video_id = detect_platform("https://vimeo.com/123456789")
        self.assertEqual(platform, "vimeo")
        self.assertEqual(video_id, "123456789")

    def test_dailymotion_url(self):
        platform, video_id = detect_platform("https://www.dailymotion.com/video/x7zzrmj")
        self.assertEqual(platform, "dailymotion")
        self.assertEqual(video_id, "x7zzrmj")

    def test_unknown_url(self):
        platform, video_id = detect_platform("https://example.com/video/123")
        self.assertIsNone(platform)
        self.assertIsNone(video_id)


class GetEmbedUrlTests(TestCase):
    """Tests for URL-to-embed-URL conversion."""

    def test_youtube_embed(self):
        result = get_embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(result, "https://www.youtube.com/embed/dQw4w9WgXcQ")

    def test_vimeo_embed(self):
        result = get_embed_url("https://vimeo.com/123456789")
        self.assertEqual(result, "https://player.vimeo.com/video/123456789")

    def test_dailymotion_embed(self):
        result = get_embed_url("https://www.dailymotion.com/video/x7zzrmj")
        self.assertEqual(result, "https://www.dailymotion.com/embed/video/x7zzrmj")

    def test_unknown_returns_none(self):
        result = get_embed_url("https://example.com/video/123")
        self.assertIsNone(result)


class ExternalMediaModelTests(TestCase):
    """Tests for external video Media model behavior."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_is_external_property(self):
        media = Media(source_type="external", source_url="https://youtube.com/watch?v=abc", user=self.user)
        self.assertTrue(media.is_external)

    def test_is_not_external_for_local(self):
        media = Media(source_type="local", user=self.user)
        self.assertFalse(media.is_external)

    def test_external_media_encoding_status_set_to_success(self):
        """External videos should have encoding_status=success after media_init."""
        media = Media.objects.create(
            source_type="external",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test External Video",
            user=self.user,
        )
        media.refresh_from_db()
        self.assertEqual(media.encoding_status, "success")
        self.assertEqual(media.media_type, "video")

    def test_external_media_allow_download_false(self):
        """External videos should have allow_download=False."""
        media = Media.objects.create(
            source_type="external",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test External Video",
            user=self.user,
        )
        media.refresh_from_db()
        self.assertFalse(media.allow_download)

    def test_external_media_encodings_info_empty(self):
        """External videos should return empty encodings_info."""
        media = Media.objects.create(
            source_type="external",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test External Video",
            user=self.user,
        )
        self.assertEqual(media.encodings_info, {})

    def test_external_media_title_defaults(self):
        """External video with no title should get 'Untitled'."""
        media = Media(source_type="external", source_url="https://youtube.com/watch?v=abc", user=self.user)
        media.save()
        self.assertEqual(media.title, "Untitled")


class FetchOembedTests(TestCase):
    """Tests for oEmbed fetching (mocked HTTP)."""

    @patch('files.external_utils.urllib.request.urlopen')
    def test_fetch_youtube_oembed(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "title": "Test Video",
            "thumbnail_url": "https://img.youtube.com/vi/abc/hqdefault.jpg",
            "html": '<iframe src="https://www.youtube.com/embed/abc"></iframe>',
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = fetch_oembed("https://www.youtube.com/watch?v=abc")
        self.assertEqual(result["title"], "Test Video")
        self.assertIn("thumbnail_url", result)

    @patch('files.external_utils.urllib.request.urlopen')
    def test_fetch_oembed_failure_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Network error")
        result = fetch_oembed("https://www.youtube.com/watch?v=abc")
        self.assertEqual(result, {})
```

- [ ] **Step 2: Run the tests**

```bash
cd /c/Users/Ivan/Documents/GitHub/mediacms
python manage.py test tests.test_external_video -v 2
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_external_video.py
git commit -m "test: add tests for external video embedding support"
```

---

## Task 16: Build Frontend and Verify

**Files:**
- No new files — build and test existing changes

- [ ] **Step 1: Build the frontend**

```bash
cd /c/Users/Ivan/Documents/GitHub/mediacms/frontend
npm run build
```

Expected: Build succeeds with no errors. There may be warnings — those are acceptable.

- [ ] **Step 2: Verify no import errors**

Check the build output for any errors related to `ExternalVideoEmbed` import or the modified `VideoViewer`.

- [ ] **Step 3: Commit build artifacts if applicable**

If the project commits built files:

```bash
git add frontend/dist/ static/
git commit -m "build: compile frontend with external video embed support"
```

---

## Task 17: End-to-End Verification Checklist

This task is a manual verification checklist. Run the Django dev server and test each scenario.

**Code audit (pre-flight):** `MediaAdmin` now makes **User** editable on add and defaults `user` to the logged-in staff user if left blank, so admin “Add media” works for external entries. Download on the media page is gated by `allow_download` in `ViewerInfoTitleBanner` / `ViewerInfo` (external media forces `allow_download=False` in `Media.save`). JSON `POST /api/v1/media` is valid because `MediaList` includes `JSONParser` and DRF enables `TokenAuthentication`. **Step 6** requires a running **Celery worker** (and broker); `fetch_external_metadata` is queued from `media_init()` for external media.

- [ ] **Step 1: Start the server**

```bash
cd /c/Users/Ivan/Documents/GitHub/mediacms
python manage.py runserver
```

(Optional for Step 6: start Celery worker in another terminal.)

- [ ] **Step 2: Test via Django Admin**

1. Go to `/admin/files/media/add/`
2. Expand the "External Video" section
3. Enter a YouTube URL in `source_url` (e.g., `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
4. `source_type` is set automatically to **External** when `source_url` is set (you can still set it explicitly)
5. Enter a title; choose **User** if not the default (defaults to you when saved)
6. Leave **media file** empty
7. Save
8. Verify: encoding_status is "success", media_type is "video"
9. Verify: the media appears in listings (if state/public + reviewed + listable rules allow)

- [ ] **Step 3: Test video playback**

1. Navigate to the media page (click "View on site" in admin)
2. Verify: YouTube video is embedded via iframe, not Video.js
3. Verify: Video plays correctly
4. Verify: Download button is not shown

- [ ] **Step 4: Test API endpoint**

Use a real API token from a user allowed to upload (`CAN_ADD_MEDIA`, limits, etc.):

```bash
curl -X POST http://localhost:8000/api/v1/media \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -d "{\"source_url\": \"https://vimeo.com/123456789\", \"title\": \"Test Vimeo\"}"
```

Or session auth from the browser (e.g. upload page / devtools) with `multipart/form-data` and `X-CSRFToken`.

Verify: Returns **201** with JSON including `"source_type": "external"`.

- [ ] **Step 5: Test RBAC access control**

1. Create an RBAC group in admin
2. Assign a category to the group
3. Put the external video in that category using a path your site actually supports: e.g. **Add external video** category multiselect on `add-media`, **`POST /api/v1/media/user/bulk_actions`** with `add_to_category` / `category_uids`, or the **Publish media** / edit UI if it sets categories. (Default `MediaAdmin` keeps **category** / **tags** read-only on the change form, so you typically do not assign them there.)
4. Add a test user as a member
5. Log in as the test user
6. Verify: the video is visible where RBAC allows
7. Log in as a different user (not in the group)
8. Verify: the video is NOT visible (if category is RBAC-controlled and portal rules hide it)

- [ ] **Step 6: Test oEmbed metadata fetching**

1. Add an external video with no title (admin or API)
2. Wait for the Celery task to complete (check Celery logs)
3. Verify: title was auto-populated from oEmbed (or remains **Untitled** if oEmbed failed — still valid)
4. Verify: thumbnail/poster were saved when oEmbed returned `thumbnail_url`

- [ ] **Step 7: Final commit**

If any fixes were needed during verification:

```bash
git add -A
git commit -m "fix: address issues found during external video e2e testing"
```
