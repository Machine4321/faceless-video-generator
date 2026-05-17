"""Tests for shadowvault.media - Pexels video fetching."""

import os
from unittest.mock import patch, MagicMock

import pytest

from shadowvault.media import (
    _pick_best_file,
    _search_pexels,
    _download_video,
    fetch_background_video,
    FALLBACK_KEYWORDS,
)
from shadowvault.models import MediaResult


# ---------------------------------------------------------------------------
# _pick_best_file
# ---------------------------------------------------------------------------

class TestPickBestFile:
    def test_picks_highest_quality_in_range(self):
        files = [
            {"link": "http://low.mp4", "width": 640, "height": 480},
            {"link": "http://mid.mp4", "width": 720, "height": 1280},
            {"link": "http://high.mp4", "width": 1080, "height": 1920},
        ]
        result = _pick_best_file(files)
        assert result == "http://high.mp4"

    def test_filters_by_min_max_width(self):
        files = [
            {"link": "http://tiny.mp4", "width": 320, "height": 240},
            {"link": "http://ok.mp4", "width": 720, "height": 1280},
            {"link": "http://huge.mp4", "width": 3840, "height": 2160},
        ]
        # 720 is in range, 3840 is not (>2000)
        result = _pick_best_file(files)
        assert result == "http://ok.mp4"

    def test_falls_back_to_above_min_width(self):
        files = [
            {"link": "http://tiny.mp4", "width": 320, "height": 240},
            {"link": "http://big.mp4", "width": 2500, "height": 1400},
        ]
        # 2500 is over MAX_WIDTH (2000) but >= MIN_WIDTH (720)
        result = _pick_best_file(files)
        assert result == "http://big.mp4"

    def test_returns_none_for_empty_list(self):
        assert _pick_best_file([]) is None

    def test_returns_none_all_too_small(self):
        files = [
            {"link": "http://tiny.mp4", "width": 320, "height": 240},
            {"link": "http://small.mp4", "width": 480, "height": 360},
        ]
        assert _pick_best_file(files) is None

    def test_handles_missing_width(self):
        files = [
            {"link": "http://no_w.mp4"},
            {"link": "http://ok.mp4", "width": 1080, "height": 1920},
        ]
        result = _pick_best_file(files)
        assert result == "http://ok.mp4"

    def test_handles_non_int_width(self):
        files = [
            {"link": "http://bad.mp4", "width": "sd", "height": 480},
            {"link": "http://ok.mp4", "width": 1080, "height": 1920},
        ]
        result = _pick_best_file(files)
        assert result == "http://ok.mp4"


# ---------------------------------------------------------------------------
# _search_pexels (mocked)
# ---------------------------------------------------------------------------

class TestSearchPexels:
    @patch("shadowvault.media.requests.get")
    def test_successful_search(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "videos": [
                {"id": 1, "video_files": [{"link": "http://v.mp4", "width": 1080}]}
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _search_pexels("horror", "fake-key")
        assert len(result) == 1
        assert result[0]["id"] == 1

    @patch("shadowvault.media.requests.get")
    def test_empty_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"videos": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _search_pexels("nonexistent_keyword", "fake-key")
        assert result == []

    @patch("shadowvault.media.requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = ConnectionError("Network down")
        result = _search_pexels("horror", "fake-key")
        assert result == []

    @patch("shadowvault.media.requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
        mock_get.return_value = mock_resp

        result = _search_pexels("horror", "fake-key")
        assert result == []

    @patch("shadowvault.media.requests.get")
    def test_sends_correct_headers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"videos": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _search_pexels("test", "my-api-key")
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "my-api-key"

    @patch("shadowvault.media.requests.get")
    def test_uses_portrait_orientation(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"videos": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _search_pexels("dark", "key")
        url = mock_get.call_args[0][0]
        assert "orientation=portrait" in url


# ---------------------------------------------------------------------------
# _download_video (mocked)
# ---------------------------------------------------------------------------

class TestDownloadVideo:
    @patch("shadowvault.media.requests.get")
    def test_successful_download(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.headers = {"content-length": "100"}
        mock_resp.iter_content.return_value = [b"video_data_chunk"]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        dest = str(tmp_path / "bg.mp4")
        result = _download_video("http://example.com/video.mp4", dest)
        assert result is True
        assert os.path.isfile(dest)
        with open(dest, "rb") as f:
            assert f.read() == b"video_data_chunk"

    @patch("shadowvault.media.requests.get")
    def test_download_failure(self, mock_get, tmp_path):
        mock_get.side_effect = ConnectionError("fail")
        dest = str(tmp_path / "bg.mp4")
        result = _download_video("http://example.com/video.mp4", dest)
        assert result is False

    @patch("shadowvault.media.requests.get")
    def test_http_error_during_download(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404")
        mock_get.return_value = mock_resp

        dest = str(tmp_path / "bg.mp4")
        result = _download_video("http://example.com/video.mp4", dest)
        assert result is False


# ---------------------------------------------------------------------------
# fetch_background_video (integration with mocks)
# ---------------------------------------------------------------------------

class TestFetchBackgroundVideo:
    @patch("shadowvault.media._download_video")
    @patch("shadowvault.media._search_pexels")
    def test_successful_fetch(self, mock_search, mock_download, tmp_path):
        mock_search.return_value = [
            {"video_files": [{"link": "http://v.mp4", "width": 1080, "height": 1920}]}
        ]
        mock_download.return_value = True

        result = fetch_background_video("horror", temp_dir=str(tmp_path), api_key="key")
        assert isinstance(result, MediaResult)
        assert result.is_fallback is False
        assert result.source_url == "http://v.mp4"

    @patch("shadowvault.media._search_pexels")
    def test_all_searches_fail_returns_fallback(self, mock_search, tmp_path):
        mock_search.return_value = []

        result = fetch_background_video("horror", temp_dir=str(tmp_path), api_key="key")
        assert result.is_fallback is True
        assert result.video_path == ""

    @patch("shadowvault.media._download_video")
    @patch("shadowvault.media._search_pexels")
    def test_download_fails_returns_fallback(self, mock_search, mock_download, tmp_path):
        mock_search.return_value = [
            {"video_files": [{"link": "http://v.mp4", "width": 1080, "height": 1920}]}
        ]
        mock_download.return_value = False

        result = fetch_background_video("horror", temp_dir=str(tmp_path), api_key="key")
        assert result.is_fallback is True

    @patch("shadowvault.media._download_video")
    @patch("shadowvault.media._search_pexels")
    def test_fallback_keyword_chain(self, mock_search, mock_download, tmp_path):
        # First keyword fails, second succeeds
        mock_search.side_effect = [
            [],  # primary keyword fails
            [{"video_files": [{"link": "http://fallback.mp4", "width": 1080, "height": 1920}]}],
        ]
        mock_download.return_value = True

        result = fetch_background_video("weird_keyword", temp_dir=str(tmp_path), api_key="key")
        assert result.is_fallback is False
        assert mock_search.call_count == 2

    @patch("shadowvault.media._download_video")
    @patch("shadowvault.media._search_pexels")
    def test_creates_temp_dir(self, mock_search, mock_download, tmp_path):
        target_dir = str(tmp_path / "new_temp")
        mock_search.return_value = []
        fetch_background_video("horror", temp_dir=target_dir, api_key="key")
        assert os.path.isdir(target_dir)

    @patch("shadowvault.media._download_video")
    @patch("shadowvault.media._search_pexels")
    def test_skips_duplicate_fallback_keyword(self, mock_search, mock_download, tmp_path):
        """If primary keyword matches a fallback keyword, it shouldn't be searched twice."""
        mock_search.return_value = []
        fetch_background_video("horror", temp_dir=str(tmp_path), api_key="key")
        # "horror" is both primary and first fallback - should appear once
        called_keywords = [call[0][0] for call in mock_search.call_args_list]
        assert called_keywords.count("horror") == 1

    @patch("shadowvault.media._download_video")
    @patch("shadowvault.media._search_pexels")
    def test_no_suitable_file_tries_next(self, mock_search, mock_download, tmp_path):
        """If video files are all too small, try the next keyword."""
        mock_search.side_effect = [
            [{"video_files": [{"link": "http://tiny.mp4", "width": 100, "height": 100}]}],
            [{"video_files": [{"link": "http://ok.mp4", "width": 1080, "height": 1920}]}],
        ]
        mock_download.return_value = True

        result = fetch_background_video("tiny_stuff", temp_dir=str(tmp_path), api_key="key")
        assert result.is_fallback is False
