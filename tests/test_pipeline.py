"""Tests for shadowvault.pipeline - orchestrator and CLI."""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from shadowvault.pipeline import run_once, main
from shadowvault.models import (
    ContentResult, MediaResult, AudioResult, VideoResult, UploadResult, PipelineRun,
)


# ---------------------------------------------------------------------------
# run_once
# ---------------------------------------------------------------------------

class TestRunOnce:
    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.video_stage.compose_video")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_full_pipeline_no_upload(
        self, mock_content, mock_media, mock_audio, mock_video, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="TEST", script="Script text here", visual_search_keyword="horror",
            tags="#shorts", niche="horror", hook="Hook.",
        )
        mock_media.return_value = MediaResult(video_path="/tmp/bg.mp4")
        mock_audio.return_value = AudioResult(audio_path="/tmp/voice.mp3", duration=5.0)
        mock_video.return_value = VideoResult(video_path="/tmp/out.mp4", duration=6.5)

        result = await run_once(niche="horror", upload=False, run_id=12345)

        assert isinstance(result, PipelineRun)
        assert result.run_id == 12345
        assert result.content.title == "TEST"
        assert result.media.video_path == "/tmp/bg.mp4"
        assert result.audio.duration == 5.0
        assert result.video.video_path == "/tmp/out.mp4"
        assert result.upload is None

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.video_stage.compose_video")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_pipeline_with_upload(
        self, mock_content, mock_media, mock_audio, mock_video, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="T", script="S", visual_search_keyword="h", tags="#t", niche="horror",
        )
        mock_media.return_value = MediaResult(video_path="/tmp/bg.mp4")
        mock_audio.return_value = AudioResult(audio_path="/tmp/voice.mp3", duration=5.0)
        mock_video.return_value = VideoResult(video_path="/tmp/out.mp4", duration=6.5)

        mock_uploader = MagicMock()
        mock_uploader.upload.return_value = UploadResult(
            success=True, video_id="abc", youtube_url="https://youtube.com/shorts/abc"
        )

        result = await run_once(upload=True, privacy="unlisted", uploader=mock_uploader)
        assert result.upload.success is True
        assert result.upload.video_id == "abc"
        mock_uploader.upload.assert_called_once()

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_pipeline_handles_content_error(self, mock_content, mock_cleanup):
        mock_content.side_effect = Exception("Gemini down")
        result = await run_once(upload=False)
        assert isinstance(result, PipelineRun)
        assert result.content is None

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_pipeline_handles_audio_failure(
        self, mock_content, mock_media, mock_audio, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="T", script="S", visual_search_keyword="h", tags="#t",
        )
        mock_media.return_value = MediaResult(video_path="/tmp/bg.mp4")
        mock_audio.return_value = AudioResult(audio_path="", duration=0.0)

        result = await run_once(upload=False)
        assert result.video is None  # Should fail at audio validation

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.video_stage.compose_video")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_cleanup_always_called(
        self, mock_content, mock_media, mock_audio, mock_video, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="T", script="S", visual_search_keyword="h", tags="#t",
        )
        mock_media.return_value = MediaResult(video_path="/tmp/bg.mp4")
        mock_audio.return_value = AudioResult(audio_path="/tmp/v.mp3", duration=5.0)
        mock_video.return_value = VideoResult(video_path="/tmp/out.mp4")

        await run_once(upload=False)
        mock_cleanup.assert_called_once()

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_cleanup_called_on_error(self, mock_content, mock_cleanup):
        mock_content.side_effect = Exception("boom")
        await run_once(upload=False)
        mock_cleanup.assert_called_once()

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.video_stage.compose_video")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_temp_files_tracked(
        self, mock_content, mock_media, mock_audio, mock_video, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="T", script="S", visual_search_keyword="h", tags="#t",
        )
        mock_media.return_value = MediaResult(video_path="/tmp/bg.mp4")
        mock_audio.return_value = AudioResult(audio_path="/tmp/voice.mp3", duration=5.0)
        mock_video.return_value = VideoResult(video_path="/tmp/out.mp4")

        result = await run_once(upload=False)
        assert "/tmp/bg.mp4" in result.temp_files
        assert "/tmp/voice.mp3" in result.temp_files

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.video_stage.compose_video")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_random_run_id_when_not_specified(
        self, mock_content, mock_media, mock_audio, mock_video, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="T", script="S", visual_search_keyword="h", tags="#t",
        )
        mock_media.return_value = MediaResult(video_path="")
        mock_audio.return_value = AudioResult(audio_path="/tmp/v.mp3", duration=5.0)
        mock_video.return_value = VideoResult(video_path="/tmp/out.mp4")

        result = await run_once(upload=False)
        assert 10_000 <= result.run_id <= 99_999

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.video_stage.compose_video")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_upload_failed(
        self, mock_content, mock_media, mock_audio, mock_video, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="T", script="S", visual_search_keyword="h", tags="#t",
        )
        mock_media.return_value = MediaResult(video_path="/tmp/bg.mp4")
        mock_audio.return_value = AudioResult(audio_path="/tmp/v.mp3", duration=5.0)
        mock_video.return_value = VideoResult(video_path="/tmp/out.mp4")

        mock_uploader = MagicMock()
        mock_uploader.upload.return_value = UploadResult(
            success=False, error_message="quota exceeded"
        )
        result = await run_once(upload=True, uploader=mock_uploader)
        assert result.upload.success is False

    @patch("shadowvault.pipeline.cleanup_files")
    @patch("shadowvault.pipeline.video_stage.compose_video")
    @patch("shadowvault.pipeline.audio_stage.generate_audio_async", new_callable=AsyncMock)
    @patch("shadowvault.pipeline.media_stage.fetch_background_video")
    @patch("shadowvault.pipeline.content_stage.generate_content")
    @pytest.mark.asyncio
    async def test_motivation_niche(
        self, mock_content, mock_media, mock_audio, mock_video, mock_cleanup
    ):
        mock_content.return_value = ContentResult(
            title="M", script="S", visual_search_keyword="gym", tags="#t", niche="motivation",
        )
        mock_media.return_value = MediaResult(video_path="/tmp/bg.mp4")
        mock_audio.return_value = AudioResult(audio_path="/tmp/v.mp3", duration=5.0)
        mock_video.return_value = VideoResult(video_path="/tmp/out.mp4")

        result = await run_once(niche="motivation", upload=False)
        assert result.niche == "motivation"
        mock_content.assert_called_once_with(niche="motivation", length="short")


# ---------------------------------------------------------------------------
# main (CLI entry point)
# ---------------------------------------------------------------------------

class TestMain:
    @patch("shadowvault.pipeline.asyncio.run")
    @patch("shadowvault.logging_config.setup_logging")
    def test_once_mode_no_upload(self, mock_logging, mock_run, monkeypatch):
        mock_run.return_value = PipelineRun(run_id=1)
        monkeypatch.setattr(
            "sys.argv", ["shadowvault", "--mode", "once", "--niche", "horror", "--no-upload"]
        )
        main()
        mock_run.assert_called_once()

    @patch("shadowvault.pipeline.asyncio.run")
    @patch("shadowvault.logging_config.setup_logging")
    def test_loop_mode(self, mock_logging, mock_run, monkeypatch):
        monkeypatch.setattr("sys.argv", ["shadowvault", "--mode", "loop", "--niche", "facts"])
        main()
        mock_run.assert_called_once()

    @patch("shadowvault.pipeline.asyncio.run")
    @patch("shadowvault.logging_config.setup_logging")
    def test_default_mode_is_once(self, mock_logging, mock_run, monkeypatch):
        mock_run.return_value = PipelineRun(run_id=1)
        monkeypatch.setattr("sys.argv", ["shadowvault", "--no-upload"])
        main()
        mock_run.assert_called_once()

    @patch("shadowvault.pipeline.asyncio.run")
    @patch("shadowvault.logging_config.setup_logging")
    def test_all_niches_accepted(self, mock_logging, mock_run, monkeypatch):
        for niche in ["horror", "motivation", "facts"]:
            mock_run.return_value = PipelineRun(run_id=1)
            monkeypatch.setattr(
                "sys.argv", ["shadowvault", "--niche", niche, "--no-upload"]
            )
            main()
