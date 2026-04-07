"""Utilities for external video embedding: oEmbed fetching and URL-to-embed conversion."""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

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
        r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/|youtube\.com/live/)([a-zA-Z0-9_-]+)"
    ),
    "vimeo": re.compile(r"(?:https?://)?(?:www\.)?vimeo\.com/(\d+)"),
    "dailymotion": re.compile(r"(?:https?://)?(?:www\.)?dailymotion\.com/video/([a-zA-Z0-9]+)"),
    # file/d/, file/u/N/d/, drive/u/N/file/d/, open?id=, uc?id=
    "googledrive": re.compile(
        r"(?:https?://)?(?:www\.)?(?:drive|docs)\.google\.com(?:/a/[^/]+)?/"
        r"(?:(?:drive/(?:u/\d+/)?)?file/d/|file/(?:u/\d+/)?d/|open\?(?:[^#]*&)?id=|uc\?(?:[^#]*&)?id=)"
        r"([a-zA-Z0-9_-]+)"
    ),
}

# Progressive video file extensions (URL path); query strings are ignored for matching.
DIRECT_PROGRESSIVE_VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm", ".ogv")


def _url_path_lower(url):
    if not url or not isinstance(url, str):
        return ""
    parsed = urllib.parse.urlparse(url.strip())
    return (parsed.path or "").lower()


def is_direct_progressive_video_url(url):
    """True if URL path ends with a known progressive video extension."""
    path = _url_path_lower(url)
    return any(path.endswith(ext) for ext in DIRECT_PROGRESSIVE_VIDEO_EXTENSIONS)


def direct_progressive_video_mime_type(url):
    """Best-effort MIME type for Video.js source from URL path extension."""
    path = _url_path_lower(url)
    suffix_map = {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".ogv": "video/ogg",
    }
    for ext, mime in suffix_map.items():
        if path.endswith(ext):
            return mime
    return "video/mp4"


def resolve_source_type_for_url(url):
    """Classify a pasted video URL for Media.source_type.

    Order: known iframe platforms → external; direct file extension → direct;
    otherwise external (oEmbed / generic embed path).
    """
    if not url or not str(url).strip():
        return "external"
    u = str(url).strip()
    platform, _ = detect_platform(u)
    if platform:
        return "external"
    if is_direct_progressive_video_url(u):
        return "direct"
    return "external"


def suggested_title_from_direct_video_url(url):
    """Derive a human-readable title from the last path segment (strip extension)."""
    if not url or not isinstance(url, str):
        return None
    path = urllib.parse.urlparse(url.strip()).path
    segment = path.rstrip("/").split("/")[-1]
    if not segment:
        return None
    if "." in segment:
        segment = segment.rsplit(".", 1)[0]
    segment = segment.replace("_", " ").replace("-", " ").strip()
    return segment or None


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
    elif platform == "googledrive":
        return f"https://drive.google.com/file/d/{video_id}/preview"

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
    params = urllib.parse.urlencode(
        {
            "url": url,
            "format": "json",
            "maxwidth": max_width,
        }
    )
    request_url = f"{endpoint}?{params}"

    try:
        req = urllib.request.Request(request_url, headers={"User-Agent": "MediaCMS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as e:
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
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.warning("Thumbnail download failed for %s: %s", thumbnail_url, e)
        return None, None
