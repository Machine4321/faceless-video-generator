"""
shadowvault/models.py
Shared dataclasses passed between pipeline stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentResult:
    """Output of Stage 1 (content.py)."""
    title: str
    script: str
    visual_search_keyword: str
    tags: str
    niche: str = "horror"
    hook: str = ""


@dataclass
class MediaResult:
    """Output of Stage 2 (media.py)."""
    video_path: str
    width: int = 0
    height: int = 0
    duration: float = 0.0
    source_url: str = ""
    is_fallback: bool = False


@dataclass
class AudioResult:
    """Output of Stage 3 (audio.py)."""
    audio_path: str
    duration: float = 0.0
    voice: str = "en-US-ChristopherNeural"


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
class PipelineRun:
    """Aggregates all stage results for a single pipeline execution."""
    run_id: int = 0
    niche: str = "horror"
    content: Optional[ContentResult] = None
    media: Optional[MediaResult] = None
    audio: Optional[AudioResult] = None
    video: Optional[VideoResult] = None
    upload: Optional[UploadResult] = None
    temp_files: list[str] = field(default_factory=list)
