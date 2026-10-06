"""
shadowvault/models.py
Shared dataclasses passed between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WordTiming:
    """Word-level timing event for kinetic subtitles."""
    word: str
    start: float  # seconds
    end: float    # seconds


@dataclass
class ScenePlan:
    """Individual visual/narration scene within a video."""
    scene_id: int
    narration: str
    visual_query: str
    sfx_cue: Optional[str] = None  # e.g. "whoosh", "impact", "cash", "glitch"
    duration: float = 0.0          # Measured or estimated duration in seconds
    visual_path: Optional[str] = None
    visual_type: str = "video"     # "video" or "image"
    visual_format: str = "auto"    # "auto", "ai_image", "newspaper", "dossier", "counter", "video"
    caption_highlight_words: list[str] = field(default_factory=list)


@dataclass
class ContentResult:
    """Output of Stage 1 (content.py)."""
    title: str
    script: str
    visual_search_keyword: str
    tags: str
    niche: str = "horror"
    hook: str = ""
    scenes: list[ScenePlan] = field(default_factory=list)


@dataclass
class MediaResult:
    """Output of Stage 2 (media.py)."""
    video_path: str
    width: int = 0
    height: int = 0
    duration: float = 0.0
    source_url: str = ""
    is_fallback: bool = False
    scenes_media: list[dict] = field(default_factory=list)


@dataclass
class AudioResult:
    """Output of Stage 3 (audio.py)."""
    audio_path: str
    duration: float = 0.0
    voice: str = "en-US-ChristopherNeural"
    word_timings: list[WordTiming] = field(default_factory=list)


@dataclass
class VideoResult:
    """Output of Stage 4 (video.py)."""
    video_path: str
    duration: float = 0.0
    width: int = 1080
    height: int = 1920


@dataclass
class UploadResult:
    """Output of Stage 5 (upload.py)."""
    success: bool
    video_id: str = ""
    youtube_url: str = ""
    archived_path: str = ""
    error_message: str = ""


@dataclass
class TrendingTopic:
    """A hot viral topic discovered from real-time internet trends."""
    title: str
    summary: str
    source: str = "google_trends"  # "google_trends", "reddit", "wikipedia", "hackernews"
    search_volume: str = ""
    suggested_niche: str = "facts"  # "facts", "glitches", "heists", "business", "horror"
    keywords: list[str] = field(default_factory=list)
    source_url: str = ""
    source_name: str = ""
    published_date: str = ""


@dataclass
class PipelineRun:
    """Aggregates all stage results for a single pipeline execution."""
    run_id: int = 0
    niche: str = "horror"
    trend_topic: Optional[TrendingTopic] = None
    content: Optional[ContentResult] = None
    media: Optional[MediaResult] = None
    audio: Optional[AudioResult] = None
    video: Optional[VideoResult] = None
    upload: Optional[UploadResult] = None
    metadata_path: str = ""
    temp_files: list[str] = field(default_factory=list)


