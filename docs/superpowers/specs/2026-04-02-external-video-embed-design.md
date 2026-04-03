# External Video Embed Support — Design Spec

## Overview

Add support for embedding videos from external platforms (YouTube, Vimeo, any oEmbed-compatible platform) into MediaCMS, while using the existing RBAC and permission system for access control.

**Goal:** Use MediaCMS as an access-controlled video portal where videos are hosted externally but users only see content their account has access to (via RBAC groups and categories).

## Approach

Extend the existing `Media` model with two new fields (`source_url`, `source_type`). External videos are treated as regular Media entries — they participate in the same RBAC, categories, permissions, search, and listings as local uploads. The encoding pipeline is skipped entirely for external videos.

---

## 1. Data Model Changes

### New fields on `Media` model (`files/models/media.py`)

```python
source_url = models.URLField(
    max_length=500, blank=True, null=True,
    help_text="URL of external video (YouTube, Vimeo, etc.)"
)
source_type = models.CharField(
    max_length=20, blank=True, default="local",
    choices=[("local", "Local"), ("external", "External")]
)
embed_html = models.TextField(
    blank=True, default="",
    help_text="Cached oEmbed HTML for platforms that don't have known embed URL patterns"
)
```

### Behavior changes

- `media_file` becomes optional (`blank=True`) when `source_type == "external"`
- `encoding_status` is set to `"success"` immediately for external videos (required for listings)
- `media_type` is set to `"video"` for external entries
- A helper property `is_external` on the model: `return self.source_type == "external"`
- `allow_download` is forced to `False` for external videos

### What stays the same

Categories, RBAC groups, tags, MediaPermission, state, is_reviewed — all work unchanged.

---

## 2. Backend Logic — Pipeline Bypass

When `source_type == "external"`, the following are **skipped**:

- `media_init()` — no file type detection, no FFmpeg probe, no encoding
- `set_media_type()` — hardcoded to `"video"`
- `set_thumbnail()` — no frame extraction
- `encode()` / `chunkize_media()` — no transcoding
- `create_hls()` — no HLS generation
- `produce_sprite_from_video()` — no sprite sheet
- File deletion on `post_delete` — no local files to clean up

### What still runs

- `save()` — friendly_token generation, state assignment, listable check, search vector update
- `post_save` signal — user media count update, category count update, notifications
- All permission checks (RBAC, MediaPermission, state)

### oEmbed Metadata Fetching

A new Celery task `fetch_external_metadata`:

1. Calls the platform's oEmbed endpoint (e.g., `https://www.youtube.com/oembed?url=...`)
2. Extracts thumbnail URL, title (if not provided), and duration (if available)
3. Downloads the thumbnail image and saves it to the Media's `poster`/`thumbnail` fields
4. Falls back gracefully if oEmbed isn't supported — admin can upload thumbnail manually

---

## 3. Frontend — Video Playback

### API response changes (`SingleMediaSerializer`)

- New field `source_url` — the external URL (only for external videos)
- New field `source_type` — `"local"` or `"external"`
- `encodings_info` and `hls_info` return empty for external videos

### Player logic (`VideoViewer`)

When `source_type == "external"`:

- Render an **iframe embed** instead of the Video.js player
- Derive iframe `src` from `source_url` using URL-to-embed transformation:
  - YouTube: `https://www.youtube.com/watch?v=ABC` -> `https://www.youtube.com/embed/ABC`
  - Vimeo: `https://vimeo.com/123` -> `https://player.vimeo.com/video/123`
  - Other platforms: use the `html` field from the oEmbed response (cached at creation time)
- For unsupported platforms, fall back to a direct link
- The iframe is wrapped in the same page layout — title, description, comments, categories render normally

### What stays the same

- Page URL structure (`/view?v=friendly_token`)
- All metadata display (title, description, tags, categories)
- Comments, likes, views counter
- Listings/search results — external videos appear alongside local videos with fetched thumbnails

---

## 4. Admin & Upload Workflows

### Django Admin

- Add `source_url` and `source_type` to the Media admin form
- `media_file` is not required when `source_type == "external"`
- All existing fields work: category, tags, state, permissions

### Upload Page (frontend)

- Add a toggle/tab: **"Upload File"** (existing) vs **"Add External Video"** (new)
- External video form fields:
  - **URL** (required) — paste the video link
  - **Title** (optional) — auto-populated from oEmbed if left blank
  - **Description** (optional)
  - **Category** (optional) — assign to RBAC categories for access control
  - **Thumbnail** (optional) — auto-fetched, with manual upload override

### API endpoint

- Extend `POST /api/v1/media` to accept `source_url` instead of a file
- Validation: one of `source_url` or `media_file` must be present (not both, not neither)

### Typical admin workflow

1. Create RBAC Group "Sales Team" -> assign categories "Q2 Training", "Company Events"
2. Add users to the group as members
3. Upload page -> "Add External Video" -> paste YouTube URL -> assign to "Q2 Training"
4. Sales team members log in -> see only videos in their assigned categories

---

## 5. Validation & Edge Cases

### Input validation

- `source_url` must be a valid URL (Django `URLField`)
- Cannot have both `media_file` and `source_url`
- Cannot have neither — at least one must be present
- `source_type` is auto-set based on which field is provided

### Edge cases

- **oEmbed fails** (private video, unsupported platform): Media is created, thumbnail uploaded manually, embed falls back to oEmbed `html` or direct link
- **External video deleted on platform**: Platform's own "video unavailable" message shows in the iframe
- **Download button**: Hidden for external videos
- **Encoding status page**: Shows "N/A" or skips encoding section for external videos
- **Search**: Works via title, description, tags — same as local videos
- **`DO_NOT_TRANSCODE_VIDEO` setting**: Irrelevant for external videos

### Out of scope

- No video downloading/re-hosting
- No syncing if external video metadata changes later
- No bulk import from YouTube channels or playlists
- No new permission model — existing RBAC used as-is

---

## Key Files to Modify

| Component | File |
|-----------|------|
| Media model | `files/models/media.py` |
| Model choices | `files/models/utils.py` |
| Serializers | `files/serializers.py` |
| API views | `files/views/media.py` |
| Celery tasks | `files/tasks.py` |
| Django admin | `files/admin.py` |
| Upload forms | `files/forms.py`, `uploader/views.py` |
| Frontend player | `frontend/src/static/js/components/media-viewer/VideoViewer/` |
| Upload page | `templates/cms/add-media.html` (Django); `frontend/config/templates/htmlBodySnippetAddMediaPage.ejs` (SPA dev) |
| Post-save signal | `files/models/media.py` (signal handlers) |
| Post-delete signal | `files/models/media.py` (file cleanup) |
| Migration | `files/migrations/` (new migration for model fields) |
