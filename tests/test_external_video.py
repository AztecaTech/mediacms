"""Tests for external video embedding support."""

import json
from unittest.mock import MagicMock, patch

import urllib.error

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from files.external_utils import detect_platform, fetch_oembed, get_embed_url
from files.models import Category, Media
from files.tests import create_account

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

    def test_google_drive_file_view_url(self):
        platform, video_id = detect_platform(
            "https://drive.google.com/file/d/1abcXYZ_09/view?usp=sharing"
        )
        self.assertEqual(platform, "googledrive")
        self.assertEqual(video_id, "1abcXYZ_09")

    def test_google_drive_open_id_url(self):
        platform, video_id = detect_platform("https://drive.google.com/open?id=1OpenIdTest_-abc")
        self.assertEqual(platform, "googledrive")
        self.assertEqual(video_id, "1OpenIdTest_-abc")

    def test_google_drive_file_u0_d_url(self):
        platform, video_id = detect_platform(
            "https://drive.google.com/file/u/0/d/1MultiAccountPath/view?usp=sharing"
        )
        self.assertEqual(platform, "googledrive")
        self.assertEqual(video_id, "1MultiAccountPath")

    def test_google_drive_drive_u0_file_d_url(self):
        platform, video_id = detect_platform(
            "https://drive.google.com/drive/u/0/file/d/1NestedDrivePath/view"
        )
        self.assertEqual(platform, "googledrive")
        self.assertEqual(video_id, "1NestedDrivePath")

    def test_google_drive_uc_export_url(self):
        platform, video_id = detect_platform(
            "https://drive.google.com/uc?export=download&id=1UcExportId"
        )
        self.assertEqual(platform, "googledrive")
        self.assertEqual(video_id, "1UcExportId")

    def test_google_workspace_docs_file_d_url(self):
        platform, video_id = detect_platform(
            "https://docs.google.com/a/example.org/file/d/1WorkspaceFile/view"
        )
        self.assertEqual(platform, "googledrive")
        self.assertEqual(video_id, "1WorkspaceFile")

    def test_google_docs_file_d_url(self):
        platform, video_id = detect_platform("https://docs.google.com/file/d/1DocLegacyId/view")
        self.assertEqual(platform, "googledrive")
        self.assertEqual(video_id, "1DocLegacyId")

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

    def test_google_drive_embed(self):
        result = get_embed_url("https://drive.google.com/file/d/1TestFileId_x/view")
        self.assertEqual(result, "https://drive.google.com/file/d/1TestFileId_x/preview")

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
        media = Media.objects.create(
            source_type="external",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test External Video",
            user=self.user,
            allow_download=True,
        )
        media.refresh_from_db()
        self.assertFalse(media.allow_download)

    def test_external_media_encodings_info_empty(self):
        media = Media.objects.create(
            source_type="external",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Test External Video",
            user=self.user,
        )
        self.assertEqual(media.encodings_info, {})

    def test_external_media_title_defaults(self):
        media = Media(source_type="external", source_url="https://youtube.com/watch?v=abc", user=self.user)
        media.save()
        self.assertEqual(media.title, "Untitled")


class FetchOembedTests(TestCase):
    """Tests for oEmbed fetching (mocked HTTP)."""

    @patch("files.external_utils.urllib.request.urlopen")
    def test_fetch_youtube_oembed(self, mock_urlopen):
        inner = MagicMock()
        inner.read.return_value = json.dumps(
            {
                "title": "Test Video",
                "thumbnail_url": "https://img.youtube.com/vi/abc/hqdefault.jpg",
                "html": '<iframe src="https://www.youtube.com/embed/abc"></iframe>',
            }
        ).encode("utf-8")
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = inner
        mock_cm.__exit__.return_value = None
        mock_urlopen.return_value = mock_cm

        result = fetch_oembed("https://www.youtube.com/watch?v=abc")
        self.assertEqual(result["title"], "Test Video")
        self.assertIn("thumbnail_url", result)

    @patch("files.external_utils.urllib.request.urlopen")
    def test_fetch_oembed_failure_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Network error")
        result = fetch_oembed("https://www.youtube.com/watch?v=abc")
        self.assertEqual(result, {})


class ExternalMediaAPITests(TestCase):
    """POST /api/v1/media with source_url, categories, session auth."""

    def setUp(self):
        self.password = "ext-api-test-pass"
        self.user = create_account(password=self.password)
        self.category = Category.objects.create(
            title="External API Category",
            user=self.user,
            is_global=True,
            is_rbac_category=False,
        )

    def test_post_external_source_url_returns_201(self):
        client = Client()
        self.assertTrue(client.login(username=self.user.username, password=self.password))
        response = client.post(
            "/api/v1/media",
            {
                "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "API external title",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data.get("source_type"), "external")
        media = Media.objects.get(friendly_token=data["friendly_token"])
        self.assertTrue(media.is_external)
        self.assertEqual(media.source_url, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_post_external_with_allowed_category(self):
        client = Client()
        self.assertTrue(client.login(username=self.user.username, password=self.password))
        response = client.post(
            "/api/v1/media",
            [
                ("source_url", "https://youtu.be/jNQXAC9IVRw"),
                ("title", "With category"),
                ("category_uids", self.category.uid),
            ],
        )
        self.assertEqual(response.status_code, 201)
        media = Media.objects.get(title="With category")
        self.assertIn(self.category, media.category.all())

    def test_post_external_rejects_unknown_category_uid(self):
        client = Client()
        self.assertTrue(client.login(username=self.user.username, password=self.password))
        response = client.post(
            "/api/v1/media",
            {
                "source_url": "https://youtu.be/jNQXAC9IVRw",
                "title": "Bad category",
                "category_uids": "00000000-0000-0000-0000-000000000001",
            },
        )
        self.assertEqual(response.status_code, 400)
