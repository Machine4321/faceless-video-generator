"""Tests for shadowvault.models dataclasses."""

from shadowvault.models import (
    ContentResult,
    MediaResult,
    AudioResult,
    VideoResult,
    UploadResult,
    PipelineRun,
)


def test_content_result_defaults():
    cr = ContentResult(
        title="TEST TITLE",
        script="Test script text.",
        visual_search_keyword="horror",
        tags="#shorts #horror",
    )
    assert cr.niche == "horror"
    assert cr.hook == ""


def test_content_result_all_fields():
    cr = ContentResult(
        title="TITLE",
        script="Script.",
        visual_search_keyword="dark",
        tags="#tags",
        niche="motivation",
        hook="Nobody will tell you.",
    )
    assert cr.niche == "motivation"
    assert cr.hook == "Nobody will tell you."


def test_media_result_defaults():
    mr = MediaResult(video_path="/tmp/bg.mp4")
    assert mr.width == 0
    assert mr.height == 0
    assert mr.duration == 0.0
    assert mr.source_url == ""
    assert mr.is_fallback is False


def test_media_result_fallback():
    mr = MediaResult(video_path="", is_fallback=True)
    assert mr.is_fallback is True


def test_audio_result_defaults():
    ar = AudioResult(audio_path="/tmp/voice.mp3")
    assert ar.duration == 0.0
    assert ar.voice == "en-US-ChristopherNeural"


def test_video_result_defaults():
    vr = VideoResult(video_path="/tmp/out.mp4")
    assert vr.width == 1080
    assert vr.height == 1920
    assert vr.duration == 0.0


def test_upload_result_success():
    ur = UploadResult(
        success=True,
        video_id="abc123",
        youtube_url="https://www.youtube.com/shorts/abc123",
    )
    assert ur.success is True
    assert ur.video_id == "abc123"
    assert ur.error_message == ""


def test_upload_result_failure():
    ur = UploadResult(success=False, error_message="Auth failed")
    assert ur.success is False
    assert ur.video_id == ""


def test_pipeline_run_defaults():
    pr = PipelineRun()
    assert pr.run_id == 0
    assert pr.niche == "horror"
    assert pr.content is None
    assert pr.temp_files == []


def test_pipeline_run_temp_files_isolated():
    """Each PipelineRun should have its own temp_files list."""
    pr1 = PipelineRun()
    pr2 = PipelineRun()
    pr1.temp_files.append("file1.mp4")
    assert pr2.temp_files == []
