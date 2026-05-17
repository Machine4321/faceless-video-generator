"""
shadowvault/config.py
Configuration loader - reads .env into a frozen dataclass.

Usage:
    from shadowvault.config import cfg
    print(cfg.gemini_api_key)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Project root = directory containing pyproject.toml
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None:
        return default
    return int(val)


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    if val is None:
        return default
    return float(val)


def _resolve_path(raw: str, default: str) -> str:
    """Resolve a path relative to PROJECT_ROOT if not absolute."""
    p = raw or default
    path = Path(p)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)


@dataclass(frozen=True)
class Config:
    # --- Required API keys ---
    gemini_api_key: str
    pexels_api_key: str

    # --- Optional API keys ---
    pixabay_api_key: str = ""
    elevenlabs_api_key: str = ""

    # --- TTS ---
    tts_provider: str = "edge"  # "edge" or "elevenlabs"
    tts_voice: str = "en-US-ChristopherNeural"
    tts_rate: str = "-6%"
    tts_pitch: str = "-5Hz"
    elevenlabs_voice_id: str = "pNInz6obpgq5paNsJ7vm"

    # --- Gemini ---
    gemini_model: str = "gemini-2.0-flash"

    # --- Video ---
    output_width: int = 1080
    output_height: int = 1920
    fps: int = 24
    codec: str = "libx264"
    audio_codec: str = "aac"
    preset: str = "ultrafast"
    bg_music_volume: float = 0.12
    trail_seconds: float = 1.5

    # --- Paths ---
    music_folder: str = ""
    output_folder: str = ""
    temp_dir: str = ""
    log_dir: str = ""
    archive_folder: str = ""

    # --- YouTube OAuth ---
    client_secrets_file: str = ""
    token_pickle_file: str = ""

    # --- Pipeline ---
    max_videos_per_day: int = 5
    inter_video_delay_min: int = 14_400
    inter_video_delay_max: int = 21_600

    # --- FFmpeg ---
    ffmpeg_path: str = ""


def _validate(config: Config) -> None:
    """Validate that required keys are present."""
    errors: list[str] = []
    if not config.gemini_api_key:
        errors.append("GEMINI_API_KEY is required")
    if not config.pexels_api_key:
        errors.append("PEXELS_API_KEY is required")
    if errors:
        for e in errors:
            print(f"[CONFIG ERROR] {e}", file=sys.stderr)
        raise ValueError(f"Missing required config: {', '.join(errors)}")


def load_config() -> Config:
    """Load configuration from environment variables and validate."""
    config = Config(
        gemini_api_key=_env("GEMINI_API_KEY"),
        pexels_api_key=_env("PEXELS_API_KEY"),
        pixabay_api_key=_env("PIXABAY_API_KEY"),
        elevenlabs_api_key=_env("ELEVENLABS_API_KEY"),
        tts_provider=_env("TTS_PROVIDER", "edge"),
        tts_voice=_env("TTS_VOICE", "en-US-ChristopherNeural"),
        tts_rate=_env("TTS_RATE", "-6%"),
        tts_pitch=_env("TTS_PITCH", "-5Hz"),
        elevenlabs_voice_id=_env("ELEVENLABS_VOICE_ID", "pNInz6obpgq5paNsJ7vm"),
        gemini_model=_env("GEMINI_MODEL", "gemini-2.0-flash"),
        output_width=_env_int("OUTPUT_WIDTH", 1080),
        output_height=_env_int("OUTPUT_HEIGHT", 1920),
        fps=_env_int("FPS", 24),
        codec=_env("CODEC", "libx264"),
        audio_codec=_env("AUDIO_CODEC", "aac"),
        preset=_env("PRESET", "ultrafast"),
        bg_music_volume=_env_float("BG_MUSIC_VOLUME", 0.12),
        trail_seconds=_env_float("TRAIL_SECONDS", 1.5),
        music_folder=_resolve_path(_env("MUSIC_FOLDER"), "music"),
        output_folder=_resolve_path(_env("OUTPUT_FOLDER"), "output"),
        temp_dir=_resolve_path(_env("TEMP_DIR"), "temp"),
        log_dir=_resolve_path(_env("LOG_DIR"), "logs"),
        archive_folder=_resolve_path(_env("ARCHIVE_FOLDER"), "uploaded_archive"),
        client_secrets_file=_resolve_path(_env("CLIENT_SECRETS_FILE"), "client_secrets.json"),
        token_pickle_file=_resolve_path(_env("TOKEN_PICKLE_FILE"), "token.pickle"),
        max_videos_per_day=_env_int("MAX_VIDEOS_PER_DAY", 5),
        inter_video_delay_min=_env_int("INTER_VIDEO_DELAY_MIN", 14_400),
        inter_video_delay_max=_env_int("INTER_VIDEO_DELAY_MAX", 21_600),
        ffmpeg_path=_env("FFMPEG_PATH"),
    )
    _validate(config)
    return config


# Module-level singleton - import as `from shadowvault.config import cfg`
# Deferred: only created when actually accessed, so tests can set env vars first.
_cfg: Config | None = None


def get_config() -> Config:
    """Get or create the singleton Config instance."""
    global _cfg
    if _cfg is None:
        _cfg = load_config()
    return _cfg


def reset_config() -> None:
    """Reset the singleton (useful for testing)."""
    global _cfg
    _cfg = None
