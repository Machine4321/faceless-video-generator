"""Tests for shadowvault.video - video composition and PIL rendering."""

import os
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from shadowvault.video import (
    _load_font,
    _render_subtitle_frame,
    _render_watermark_frame,
    _build_subtitle_clips,
    _mix_audio,
    compose_video,
)
from shadowvault.models import AudioResult, MediaResult, VideoResult


# ---------------------------------------------------------------------------
# _load_font
# ---------------------------------------------------------------------------

class TestLoadFont:
    def test_loads_some_font(self):
        """Should return a font object (either Arial or PIL default)."""
        font = _load_font(40, bold=False)
        assert font is not None

    def test_loads_bold_font(self):
        font = _load_font(80, bold=True)
        assert font is not None

    def test_different_sizes(self):
        small = _load_font(20)
        large = _load_font(80)
        assert small is not None
        assert large is not None


# ---------------------------------------------------------------------------
# _render_subtitle_frame
# ---------------------------------------------------------------------------

class TestRenderSubtitleFrame:
    def test_returns_rgba_array(self):
        frame = _render_subtitle_frame("HELLO WORLD", 1080, 480)
        assert isinstance(frame, np.ndarray)
        assert frame.shape[2] == 4  # RGBA
        assert frame.shape[0] == 480
        assert frame.shape[1] == 1080

    def test_custom_dimensions(self):
        frame = _render_subtitle_frame("TEST", 800, 300)
        assert frame.shape == (300, 800, 4)

    def test_long_text_wraps(self):
        frame = _render_subtitle_frame("THIS IS A VERY LONG TEXT THAT SHOULD WRAP", 1080, 480)
        assert frame.shape == (480, 1080, 4)

    def test_empty_text(self):
        frame = _render_subtitle_frame("", 1080, 480)
        assert frame.shape == (480, 1080, 4)

    def test_custom_colors(self):
        frame = _render_subtitle_frame(
            "TEST", 1080, 480,
            font_color=(255, 0, 0),
            stroke_color=(255, 255, 255),
            bg_color=(0, 0, 0, 200),
        )
        assert frame.shape == (480, 1080, 4)

    def test_has_non_transparent_pixels(self):
        """Rendered text should produce some non-transparent pixels."""
        frame = _render_subtitle_frame("VISIBLE TEXT", 1080, 480)
        alpha_channel = frame[:, :, 3]
        assert alpha_channel.max() > 0


# ---------------------------------------------------------------------------
# _render_watermark_frame
# ---------------------------------------------------------------------------

class TestRenderWatermarkFrame:
    def test_returns_full_frame_size(self):
        frame = _render_watermark_frame(1080, 1920)
        assert frame.shape == (1920, 1080, 4)

    def test_custom_handle(self):
        frame = _render_watermark_frame(1080, 1920, handle="@TestChannel")
        assert frame.shape == (1920, 1080, 4)

    def test_has_non_transparent_pixels(self):
        frame = _render_watermark_frame(1080, 1920)
        alpha_channel = frame[:, :, 3]
        assert alpha_channel.max() > 0

    def test_custom_position(self):
        frame = _render_watermark_frame(1080, 1920, position_y=100)
        assert frame.shape == (1920, 1080, 4)


# ---------------------------------------------------------------------------
# _build_subtitle_clips
# ---------------------------------------------------------------------------

class TestBuildSubtitleClips:
    def test_creates_correct_number_of_clips(self):
        # 12 words / 4 words per chunk = 3 chunks
        script = "one two three four five six seven eight nine ten eleven twelve"
        clips = _build_subtitle_clips(script, audio_duration=6.0, output_width=1080)
        assert len(clips) == 3

    def test_empty_script_returns_empty(self):
        clips = _build_subtitle_clips("", audio_duration=5.0, output_width=1080)
        assert clips == []

    def test_single_word(self):
        clips = _build_subtitle_clips("hello", audio_duration=3.0, output_width=1080)
        assert len(clips) == 1

    def test_custom_words_per_chunk(self):
        script = "a b c d e f"
        clips = _build_subtitle_clips(
            script, audio_duration=6.0, output_width=1080, words_per_chunk=2
        )
        assert len(clips) == 3

    def test_clips_cover_audio_duration(self):
        script = "word " * 16  # 4 chunks of 4 words
        clips = _build_subtitle_clips(script, audio_duration=10.0, output_width=1080)
        assert len(clips) == 4
        # Last clip should end near audio_duration
        last_clip = clips[-1]
        end_time = last_clip.start + last_clip.duration
        assert end_time <= 10.0


# ---------------------------------------------------------------------------
# _mix_audio
# ---------------------------------------------------------------------------

class TestMixAudio:
    def test_returns_voice_if_no_music_folder(self):
        voice_clip = MagicMock()
        result = _mix_audio(voice_clip, 10.0, "", 0.12)
        assert result is voice_clip

    def test_returns_voice_if_folder_missing(self):
        voice_clip = MagicMock()
        result = _mix_audio(voice_clip, 10.0, "/nonexistent/path", 0.12)
        assert result is voice_clip

    def test_returns_voice_if_no_music_files(self, tmp_path):
        music_dir = str(tmp_path / "empty_music")
        os.makedirs(music_dir)
        voice_clip = MagicMock()
        result = _mix_audio(voice_clip, 10.0, music_dir, 0.12)
        assert result is voice_clip

    @patch("shadowvault.video.CompositeAudioClip")
    @patch("shadowvault.video.AudioFileClip")
    def test_mixes_with_music(self, mock_audio_cls, mock_composite, tmp_path):
        # Create a fake music file
        music_dir = str(tmp_path / "music")
        os.makedirs(music_dir)
        (tmp_path / "music" / "track.mp3").write_text("fake")

        mock_music = MagicMock()
        mock_music.duration = 60.0  # longer than total_duration, no loop needed
        mock_music.volumex.return_value = mock_music
        mock_music.subclip.return_value = mock_music
        mock_audio_cls.return_value = mock_music

        mock_result = MagicMock()
        mock_composite.return_value = mock_result

        voice_clip = MagicMock()
        result = _mix_audio(voice_clip, 10.0, music_dir, 0.12)
        mock_composite.assert_called_once()
        assert result is mock_result

    @patch("shadowvault.video.AudioFileClip")
    def test_music_error_returns_voice_only(self, mock_audio_cls, tmp_path):
        music_dir = str(tmp_path / "music")
        os.makedirs(music_dir)
        (tmp_path / "music" / "track.mp3").write_text("fake")

        mock_audio_cls.side_effect = Exception("bad audio")
        voice_clip = MagicMock()
        result = _mix_audio(voice_clip, 10.0, music_dir, 0.12)
        assert result is voice_clip


# ---------------------------------------------------------------------------
# compose_video (integration with heavy mocking)
# ---------------------------------------------------------------------------

class TestComposeVideo:
    def _make_mock_config(self, tmp_path):
        mock_cfg = MagicMock()
        mock_cfg.output_folder = str(tmp_path / "output")
        mock_cfg.music_folder = ""
        mock_cfg.fps = 24
        mock_cfg.codec = "libx264"
        mock_cfg.audio_codec = "aac"
        mock_cfg.preset = "ultrafast"
        mock_cfg.bg_music_volume = 0.12
        mock_cfg.trail_seconds = 1.5
        mock_cfg.output_width = 1080
        mock_cfg.output_height = 1920
        mock_cfg.ffmpeg_path = ""
        return mock_cfg

    @patch("shadowvault.video.CompositeVideoClip")
    @patch("shadowvault.video.AudioFileClip")
    @patch("shadowvault.video.ColorClip")
    @patch("shadowvault.config.get_config")
    def test_compose_with_fallback_black_bg(
        self, mock_get_cfg, mock_color, mock_audio, mock_composite, tmp_path
    ):
        mock_get_cfg.return_value = self._make_mock_config(tmp_path)

        # Setup mocks
        mock_bg = MagicMock()
        mock_bg.set_audio.return_value = mock_bg
        mock_color.return_value = mock_bg

        mock_voice = MagicMock()
        mock_voice.duration = 5.0
        mock_audio.return_value = mock_voice

        mock_final = MagicMock()
        mock_composite.return_value = mock_final

        # Create dummy audio file
        audio_path = str(tmp_path / "voice.mp3")
        with open(audio_path, "w") as f:
            f.write("fake")

        media = MediaResult(video_path="", is_fallback=True)
        audio = AudioResult(audio_path=audio_path, duration=5.0)

        result = compose_video(
            media=media,
            audio=audio,
            script="Test script with some words",
            title="Test Title",
        )

        assert isinstance(result, VideoResult)
        assert result.width == 1080
        assert result.height == 1920
        mock_color.assert_called_once()  # Black ColorClip used
        mock_final.write_videofile.assert_called_once()

    @patch("shadowvault.config.get_config")
    def test_compose_raises_on_missing_audio(self, mock_get_cfg, tmp_path):
        mock_get_cfg.return_value = self._make_mock_config(tmp_path)

        media = MediaResult(video_path="", is_fallback=True)
        audio = AudioResult(audio_path="", duration=0.0)

        with pytest.raises(FileNotFoundError):
            compose_video(
                media=media,
                audio=audio,
                script="Test",
                title="Test",
            )

    @patch("shadowvault.video.CompositeVideoClip")
    @patch("shadowvault.video.AudioFileClip")
    @patch("shadowvault.video.VideoFileClip")
    @patch("shadowvault.config.get_config")
    def test_compose_with_real_video_bg(
        self, mock_get_cfg, mock_vfc, mock_afc, mock_composite, tmp_path
    ):
        mock_get_cfg.return_value = self._make_mock_config(tmp_path)

        # Mock background video
        mock_bg = MagicMock()
        mock_bg.h = 1920
        mock_bg.w = 1080
        mock_bg.duration = 30.0
        mock_bg.subclip.return_value = mock_bg
        mock_bg.set_audio.return_value = mock_bg
        mock_vfc.return_value = mock_bg

        # Mock audio
        mock_voice = MagicMock()
        mock_voice.duration = 5.0
        mock_afc.return_value = mock_voice

        mock_final = MagicMock()
        mock_composite.return_value = mock_final

        # Create dummy files
        video_path = str(tmp_path / "bg.mp4")
        audio_path = str(tmp_path / "voice.mp3")
        with open(video_path, "w") as f:
            f.write("fake")
        with open(audio_path, "w") as f:
            f.write("fake")

        media = MediaResult(video_path=video_path)
        audio = AudioResult(audio_path=audio_path, duration=5.0)

        result = compose_video(
            media=media,
            audio=audio,
            script="Test script text here",
            title="Test",
        )

        assert isinstance(result, VideoResult)
        mock_vfc.assert_called_once_with(video_path)

    @patch("shadowvault.video.CompositeVideoClip")
    @patch("shadowvault.video.AudioFileClip")
    @patch("shadowvault.video.ColorClip")
    @patch("shadowvault.config.get_config")
    def test_compose_creates_output_dir(
        self, mock_get_cfg, mock_color, mock_audio, mock_composite, tmp_path
    ):
        mock_get_cfg.return_value = self._make_mock_config(tmp_path)

        mock_bg = MagicMock()
        mock_bg.set_audio.return_value = mock_bg
        mock_color.return_value = mock_bg

        mock_voice = MagicMock()
        mock_voice.duration = 3.0
        mock_audio.return_value = mock_voice

        mock_final = MagicMock()
        mock_composite.return_value = mock_final

        audio_path = str(tmp_path / "voice.mp3")
        with open(audio_path, "w") as f:
            f.write("fake")

        media = MediaResult(video_path="", is_fallback=True)
        audio = AudioResult(audio_path=audio_path, duration=3.0)

        output_dir = str(tmp_path / "new_output")
        compose_video(
            media=media, audio=audio,
            script="Test", title="Test",
            output_folder=output_dir,
        )
        assert os.path.isdir(output_dir)


class TestHookBannerClip:
    def test_build_hook_banner_clip_returns_clip(self):
        from shadowvault.video import _build_hook_banner_clip
        from moviepy.editor import ImageClip

        clip = _build_hook_banner_clip(
            hook_header="THE $100M APPLE HEIST 🍏🔒",
            hook_category="CLASSIFIED CASE",
            duration=3.5,
            output_width=1080,
            output_height=1920,
        )
        assert clip is not None
        assert isinstance(clip, ImageClip)
        assert clip.start == 0.0
        assert clip.duration == 3.5

    def test_build_hook_banner_clip_empty_returns_none(self):
        from shadowvault.video import _build_hook_banner_clip

        assert _build_hook_banner_clip("") is None
        assert _build_hook_banner_clip("   ") is None

