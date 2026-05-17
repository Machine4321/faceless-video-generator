"""Tests for shadowvault.upload - YouTubeUploader."""

import os
from unittest.mock import patch, MagicMock

import pytest

from shadowvault.upload import YouTubeUploader, DEFAULT_TAGS
from shadowvault.models import VideoResult, ContentResult, UploadResult


@pytest.fixture
def mock_config(tmp_path):
    cfg = MagicMock()
    cfg.client_secrets_file = str(tmp_path / "client_secrets.json")
    cfg.token_pickle_file = str(tmp_path / "token.pickle")
    cfg.archive_folder = str(tmp_path / "archive")
    return cfg


@pytest.fixture
def uploader(mock_config):
    with patch("shadowvault.config.get_config", return_value=mock_config):
        return YouTubeUploader(
            client_secrets=mock_config.client_secrets_file,
            token_file=mock_config.token_pickle_file,
            archive_folder=mock_config.archive_folder,
        )


@pytest.fixture
def sample_video(tmp_path):
    path = str(tmp_path / "video.mp4")
    with open(path, "wb") as f:
        f.write(b"fake video data")
    return VideoResult(video_path=path, duration=10.0)


@pytest.fixture
def sample_content():
    return ContentResult(
        title="TEST TITLE",
        script="Test script content.",
        visual_search_keyword="horror",
        tags="#shorts #horror #scary #fyp",
        niche="horror",
        hook="Test hook.",
    )


# ---------------------------------------------------------------------------
# YouTubeUploader.__init__
# ---------------------------------------------------------------------------

class TestUploaderInit:
    def test_default_init(self, mock_config):
        with patch("shadowvault.config.get_config", return_value=mock_config):
            u = YouTubeUploader()
        assert u.client_secrets == mock_config.client_secrets_file
        assert u._service is None

    def test_custom_paths(self, mock_config):
        with patch("shadowvault.config.get_config", return_value=mock_config):
            u = YouTubeUploader(
                client_secrets="/custom/secrets.json",
                token_file="/custom/token.pickle",
                archive_folder="/custom/archive",
            )
        assert u.client_secrets == "/custom/secrets.json"


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

class TestCredentials:
    def test_load_nonexistent_returns_none(self, uploader):
        creds = uploader._load_credentials()
        assert creds is None


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_valid_existing_token(self, uploader):
        fake_creds = MagicMock()
        fake_creds.valid = True

        with patch.object(uploader, "_load_credentials", return_value=fake_creds), \
             patch("shadowvault.upload.build") as mock_build:
            mock_build.return_value = MagicMock()
            result = uploader.authenticate()
        assert result is True
        assert uploader._service is not None

    def test_expired_token_refresh(self, uploader):
        fake_creds = MagicMock()
        fake_creds.valid = False
        fake_creds.expired = True
        fake_creds.refresh_token = "fake_refresh"

        with patch.object(uploader, "_load_credentials", return_value=fake_creds), \
             patch.object(uploader, "_save_credentials"), \
             patch("shadowvault.upload.build") as mock_build, \
             patch("shadowvault.upload.Request"):
            mock_build.return_value = MagicMock()
            result = uploader.authenticate()
        assert result is True

    def test_no_token_no_secrets_fails(self, uploader):
        result = uploader.authenticate()
        assert result is False

    def test_no_token_with_secrets_triggers_flow(self, uploader):
        # Create client secrets file
        with open(uploader.client_secrets, "w") as f:
            f.write("{}")

        with patch.object(uploader, "_load_credentials", return_value=None), \
             patch.object(uploader, "_save_credentials"), \
             patch("shadowvault.upload.InstalledAppFlow") as mock_flow_cls, \
             patch("shadowvault.upload.build") as mock_build:
            mock_flow = MagicMock()
            mock_flow.run_local_server.return_value = MagicMock(valid=True)
            mock_flow_cls.from_client_secrets_file.return_value = mock_flow
            mock_build.return_value = MagicMock()
            result = uploader.authenticate()
        assert result is True
        mock_flow.run_local_server.assert_called_once()

    def test_refresh_failure_no_secrets_fails(self, uploader):
        fake_creds = MagicMock()
        fake_creds.valid = False
        fake_creds.expired = True
        fake_creds.refresh_token = "token"
        fake_creds.refresh.side_effect = Exception("refresh failed")

        with patch.object(uploader, "_load_credentials", return_value=fake_creds):
            result = uploader.authenticate()
        assert result is False

    def test_build_failure(self, uploader):
        fake_creds = MagicMock()
        fake_creds.valid = True

        with patch.object(uploader, "_load_credentials", return_value=fake_creds), \
             patch("shadowvault.upload.build") as mock_build:
            mock_build.side_effect = Exception("build failed")
            result = uploader.authenticate()
        assert result is False

    def test_oauth_flow_failure(self, uploader):
        with open(uploader.client_secrets, "w") as f:
            f.write("{}")

        with patch.object(uploader, "_load_credentials", return_value=None), \
             patch("shadowvault.upload.InstalledAppFlow") as mock_flow_cls:
            mock_flow_cls.from_client_secrets_file.side_effect = Exception("flow error")
            result = uploader.authenticate()
        assert result is False


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_missing_video_file(self, uploader, sample_content):
        video = VideoResult(video_path="/nonexistent.mp4")
        result = uploader.upload(video, sample_content)
        assert result.success is False
        assert "not found" in result.error_message

    def test_auth_failure(self, uploader, sample_video, sample_content):
        result = uploader.upload(sample_video, sample_content)
        assert result.success is False

    def test_successful_upload(self, uploader, sample_video, sample_content):
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_request.next_chunk.return_value = (None, {"id": "abc123"})
        mock_service.videos.return_value.insert.return_value = mock_request
        uploader._service = mock_service

        result = uploader.upload(sample_video, sample_content, privacy="unlisted")
        assert result.success is True
        assert result.video_id == "abc123"
        assert "abc123" in result.youtube_url

    def test_upload_with_progress(self, uploader, sample_video, sample_content):
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_status = MagicMock()
        mock_status.progress.return_value = 0.5
        mock_request.next_chunk.side_effect = [
            (mock_status, None),
            (None, {"id": "xyz789"}),
        ]
        mock_service.videos.return_value.insert.return_value = mock_request
        uploader._service = mock_service

        result = uploader.upload(sample_video, sample_content)
        assert result.success is True
        assert result.video_id == "xyz789"

    def test_upload_failure(self, uploader, sample_video, sample_content):
        mock_service = MagicMock()
        mock_service.videos.return_value.insert.side_effect = Exception("API error")
        uploader._service = mock_service

        result = uploader.upload(sample_video, sample_content)
        assert result.success is False
        assert "API error" in result.error_message

    def test_upload_archives_file(self, uploader, sample_video, sample_content):
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_request.next_chunk.return_value = (None, {"id": "arc1"})
        mock_service.videos.return_value.insert.return_value = mock_request
        uploader._service = mock_service

        result = uploader.upload(sample_video, sample_content)
        assert result.success is True

    def test_upload_tag_parsing(self, uploader, sample_video, sample_content):
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_request.next_chunk.return_value = (None, {"id": "t1"})
        mock_service.videos.return_value.insert.return_value = mock_request
        uploader._service = mock_service

        uploader.upload(sample_video, sample_content, extra_tags=["custom_tag"])
        call_args = mock_service.videos().insert.call_args
        body = call_args[1]["body"]
        assert "custom_tag" in body["snippet"]["tags"]

    def test_privacy_options(self, uploader, sample_video, sample_content):
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_request.next_chunk.return_value = (None, {"id": "p1"})
        mock_service.videos.return_value.insert.return_value = mock_request
        uploader._service = mock_service

        for privacy in ["public", "unlisted", "private"]:
            uploader.upload(sample_video, sample_content, privacy=privacy)
            call_args = mock_service.videos().insert.call_args
            body = call_args[1]["body"]
            assert body["status"]["privacyStatus"] == privacy

    def test_title_truncated_to_100(self, uploader, sample_video):
        long_content = ContentResult(
            title="A" * 200,
            script="S",
            visual_search_keyword="h",
            tags="#t",
        )
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_request.next_chunk.return_value = (None, {"id": "tr1"})
        mock_service.videos.return_value.insert.return_value = mock_request
        uploader._service = mock_service

        uploader.upload(sample_video, long_content)
        call_args = mock_service.videos().insert.call_args
        body = call_args[1]["body"]
        assert len(body["snippet"]["title"]) == 100
