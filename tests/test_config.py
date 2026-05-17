"""Tests for shadowvault.config."""

import os
import pytest

from shadowvault.config import load_config, reset_config, Config


@pytest.fixture(autouse=True)
def _clean_config():
    """Reset the config singleton before each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def _set_required_env(monkeypatch):
    """Set the minimum required env vars."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("PEXELS_API_KEY", "test-pexels-key")


def test_missing_gemini_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        load_config()


def test_missing_pexels_key_raises(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="PEXELS_API_KEY"):
        load_config()


def test_valid_config_loads(monkeypatch, _set_required_env):
    cfg = load_config()
    assert cfg.gemini_api_key == "test-gemini-key"
    assert cfg.pexels_api_key == "test-pexels-key"


def test_default_values(monkeypatch, _set_required_env):
    cfg = load_config()
    assert cfg.tts_voice == "en-US-ChristopherNeural"
    assert cfg.fps == 24
    assert cfg.output_width == 1080
    assert cfg.output_height == 1920
    assert cfg.bg_music_volume == 0.12
    assert cfg.max_videos_per_day == 5


def test_custom_env_values(monkeypatch, _set_required_env):
    monkeypatch.setenv("TTS_VOICE", "en-GB-RyanNeural")
    monkeypatch.setenv("FPS", "30")
    monkeypatch.setenv("BG_MUSIC_VOLUME", "0.2")
    cfg = load_config()
    assert cfg.tts_voice == "en-GB-RyanNeural"
    assert cfg.fps == 30
    assert cfg.bg_music_volume == 0.2


def test_config_is_frozen(monkeypatch, _set_required_env):
    cfg = load_config()
    with pytest.raises(AttributeError):
        cfg.gemini_api_key = "new-key"


def test_optional_pixabay_key(monkeypatch, _set_required_env):
    cfg = load_config()
    assert cfg.pixabay_api_key == ""

    monkeypatch.setenv("PIXABAY_API_KEY", "pixabay-test")
    reset_config()
    cfg2 = load_config()
    assert cfg2.pixabay_api_key == "pixabay-test"


def test_get_config_singleton(monkeypatch, _set_required_env):
    from shadowvault.config import get_config
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2


def test_reset_config_clears_singleton(monkeypatch, _set_required_env):
    from shadowvault.config import get_config
    cfg1 = get_config()
    reset_config()
    cfg2 = get_config()
    # After reset, a new instance is created (may be equal but not same object)
    assert cfg1 is not cfg2


def test_path_resolution_relative(monkeypatch, _set_required_env):
    """Relative paths should be resolved against PROJECT_ROOT."""
    cfg = load_config()
    # Default music_folder is "music" relative to project root
    assert os.path.isabs(cfg.music_folder)
    assert cfg.music_folder.endswith("music")


def test_path_resolution_absolute(monkeypatch, _set_required_env):
    """Absolute paths should be kept as-is."""
    abs_path = os.path.abspath("/tmp/custom_music")
    monkeypatch.setenv("MUSIC_FOLDER", abs_path)
    cfg = load_config()
    assert cfg.music_folder == abs_path


def test_all_path_fields_are_absolute(monkeypatch, _set_required_env):
    cfg = load_config()
    for field in ["music_folder", "output_folder", "temp_dir", "log_dir",
                   "archive_folder", "client_secrets_file", "token_pickle_file"]:
        path = getattr(cfg, field)
        assert os.path.isabs(path), f"{field} is not absolute: {path}"


def test_int_env_var_parsing(monkeypatch, _set_required_env):
    monkeypatch.setenv("MAX_VIDEOS_PER_DAY", "10")
    monkeypatch.setenv("INTER_VIDEO_DELAY_MIN", "3600")
    cfg = load_config()
    assert cfg.max_videos_per_day == 10
    assert cfg.inter_video_delay_min == 3600


def test_float_env_var_parsing(monkeypatch, _set_required_env):
    monkeypatch.setenv("TRAIL_SECONDS", "2.5")
    cfg = load_config()
    assert cfg.trail_seconds == 2.5


def test_gemini_model_default(monkeypatch, _set_required_env):
    cfg = load_config()
    assert cfg.gemini_model == "gemini-2.0-flash"


def test_gemini_model_custom(monkeypatch, _set_required_env):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-pro")
    cfg = load_config()
    assert cfg.gemini_model == "gemini-1.5-pro"
