"""Tests for shadowvault.audio - TTS generation."""

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from shadowvault.audio import (
    _measure_duration,
    generate_audio_async,
    generate_audio,
)
from shadowvault.models import AudioResult


def _make_mock_config(tmp_path):
    mock_cfg = MagicMock()
    mock_cfg.tts_voice = "en-US-ChristopherNeural"
    mock_cfg.tts_rate = "-6%"
    mock_cfg.tts_pitch = "-5Hz"
    mock_cfg.temp_dir = str(tmp_path)
    return mock_cfg


# ---------------------------------------------------------------------------
# _measure_duration
# ---------------------------------------------------------------------------

class TestMeasureDuration:
    @patch("shadowvault.audio.AudioFileClip")
    def test_returns_duration(self, mock_clip_cls):
        mock_clip = MagicMock()
        mock_clip.duration = 5.5
        mock_clip_cls.return_value = mock_clip

        result = _measure_duration("/tmp/voice.mp3")
        assert result == 5.5
        mock_clip.close.assert_called_once()

    @patch("shadowvault.audio.AudioFileClip")
    def test_returns_zero_on_error(self, mock_clip_cls):
        mock_clip_cls.side_effect = Exception("bad file")
        result = _measure_duration("/tmp/nonexistent.mp3")
        assert result == 0.0


# ---------------------------------------------------------------------------
# generate_audio_async
# ---------------------------------------------------------------------------

class TestGenerateAudioAsync:
    @patch("shadowvault.audio._measure_duration", return_value=8.5)
    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    @pytest.mark.asyncio
    async def test_successful_generation(self, mock_get_cfg, mock_synth, mock_dur, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        result = await generate_audio_async("Hello world test text")
        assert isinstance(result, AudioResult)
        assert result.duration == 8.5
        assert result.voice == "en-US-ChristopherNeural"
        assert result.audio_path.endswith(".mp3")
        mock_synth.assert_called_once()

    @patch("shadowvault.audio._measure_duration", return_value=3.0)
    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    @pytest.mark.asyncio
    async def test_custom_voice(self, mock_get_cfg, mock_synth, mock_dur, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        result = await generate_audio_async("Test text", voice="en-GB-RyanNeural")
        assert result.voice == "en-GB-RyanNeural"

    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    @pytest.mark.asyncio
    async def test_synthesis_failure_returns_empty(self, mock_get_cfg, mock_synth, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        mock_synth.side_effect = Exception("TTS service down")
        result = await generate_audio_async("Test text")
        assert result.audio_path == ""
        assert result.duration == 0.0

    @patch("shadowvault.audio._measure_duration", return_value=5.0)
    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    @pytest.mark.asyncio
    async def test_creates_temp_dir(self, mock_get_cfg, mock_synth, mock_dur, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        new_dir = str(tmp_path / "new_audio_dir")
        result = await generate_audio_async("Test text", temp_dir=new_dir)
        assert os.path.isdir(new_dir)

    @patch("shadowvault.audio._measure_duration", return_value=5.0)
    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    @pytest.mark.asyncio
    async def test_custom_rate_and_pitch(self, mock_get_cfg, mock_synth, mock_dur, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        await generate_audio_async("Test", rate="+10%", pitch="+3Hz")
        call_args = mock_synth.call_args[0]
        assert call_args[2] == "+10%"  # rate
        assert call_args[3] == "+3Hz"  # pitch

    @patch("shadowvault.audio._measure_duration", return_value=7.0)
    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    @pytest.mark.asyncio
    async def test_uses_config_defaults(self, mock_get_cfg, mock_synth, mock_dur, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        result = await generate_audio_async("Test defaults")
        assert result.voice == "en-US-ChristopherNeural"
        call_args = mock_synth.call_args[0]
        assert call_args[1] == "en-US-ChristopherNeural"  # voice
        assert call_args[2] == "-6%"   # rate from config
        assert call_args[3] == "-5Hz"  # pitch from config


# ---------------------------------------------------------------------------
# generate_audio (sync wrapper)
# ---------------------------------------------------------------------------

class TestGenerateAudioSync:
    @patch("shadowvault.audio._measure_duration", return_value=4.0)
    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    def test_sync_wrapper_works(self, mock_get_cfg, mock_synth, mock_dur, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        result = generate_audio("Test sync wrapper")
        assert isinstance(result, AudioResult)
        assert result.duration == 4.0

    @patch("shadowvault.audio._synthesise", new_callable=AsyncMock)
    @patch("shadowvault.config.get_config")
    def test_sync_wrapper_failure(self, mock_get_cfg, mock_synth, tmp_path):
        mock_get_cfg.return_value = _make_mock_config(tmp_path)
        mock_synth.side_effect = Exception("fail")
        result = generate_audio("Test")
        assert result.audio_path == ""
        assert result.duration == 0.0


# ---------------------------------------------------------------------------
# apply_hollywood_mastering
# ---------------------------------------------------------------------------

class TestApplyHollywoodMastering:
    def test_missing_input_returns_input(self):
        from shadowvault.audio import apply_hollywood_mastering
        res = apply_hollywood_mastering("nonexistent_file.mp3")
        assert res == "nonexistent_file.mp3"

    @patch("subprocess.run")
    def test_successful_mastering(self, mock_run, tmp_path):
        from shadowvault.audio import apply_hollywood_mastering
        inp = tmp_path / "voice.mp3"
        inp.write_bytes(b"dummy audio data" * 100)
        out = tmp_path / "voice_mastered.mp3"
        out.write_bytes(b"mastered audio data" * 100)

        res = apply_hollywood_mastering(str(inp), str(out))
        assert res == str(out)
        mock_run.assert_called_once()

