"""
shadowvault/media.py
Stage 2 - Background video fetching from Pexels.

Strategy: search with keyword -> fallback chain -> stream download.
"""

from __future__ import annotations

import logging
import os
import random
from typing import Optional

import requests

from shadowvault.models import MediaResult

logger = logging.getLogger(__name__)

PEXELS_PER_PAGE: int = 80
MIN_WIDTH: int = 720
MAX_WIDTH: int = 2000
DOWNLOAD_CHUNK: int = 1024 * 512  # 512 KB

FALLBACK_KEYWORDS: list[str] = [
    "horror",
    "dark forest",
    "foggy",
    "abandoned",
    "dark ocean",
    "shadow",
    "creepy",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _search_pexels(keyword: str, api_key: str) -> list[dict]:
    url = (
        f"https://api.pexels.com/videos/search"
        f"?query={keyword}&orientation=portrait&per_page={PEXELS_PER_PAGE}"
    )
    headers = {"Authorization": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        videos: list[dict] = data.get("videos", [])
        logger.info("Pexels search '%s' returned %d results", keyword, len(videos))
        return videos
    except Exception as exc:
        logger.warning("Pexels search failed for '%s': %s", keyword, exc)
        return []


def _pick_best_file(video_files: list[dict]) -> Optional[str]:
    candidates = [
        f for f in video_files
        if isinstance(f.get("width"), int)
        and MIN_WIDTH <= f["width"] <= MAX_WIDTH
    ]
    if not candidates:
        candidates = [f for f in video_files if f.get("width", 0) >= MIN_WIDTH]
    if not candidates:
        return None

    candidates.sort(key=lambda f: f.get("width", 0) * f.get("height", 0), reverse=True)
    return candidates[0]["link"]


def _download_video(url: str, dest_path: str) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=DOWNLOAD_CHUNK):
                if chunk:
                    fh.write(chunk)
                    downloaded += len(chunk)
        logger.info("Downloaded %d / %d bytes -> %s", downloaded, total or downloaded, dest_path)
        return True
    except Exception as exc:
        logger.error("Video download failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_background_video(
    keyword: str,
    temp_dir: str | None = None,
    api_key: str | None = None,
) -> MediaResult:
    """
    Search Pexels for a portrait video, download it, return MediaResult.

    Falls back through keyword chain. Returns is_fallback=True if all fail.
    """
    if api_key is None:
        from shadowvault.config import get_config
        api_key = get_config().pexels_api_key

    if temp_dir is None:
        from shadowvault.config import get_config
        temp_dir = get_config().temp_dir
    os.makedirs(temp_dir, exist_ok=True)

    search_chain: list[str] = [keyword] + [
        kw for kw in FALLBACK_KEYWORDS if kw.lower() != keyword.lower()
    ]

    chosen_url: Optional[str] = None
    for search_kw in search_chain:
        videos = _search_pexels(search_kw, api_key)
        if not videos:
            continue

        video = random.choice(videos)
        file_url = _pick_best_file(video.get("video_files", []))
        if file_url:
            chosen_url = file_url
            logger.info("Selected video from keyword '%s'", search_kw)
            break

    if chosen_url is None:
        logger.error("All Pexels search strategies exhausted - returning fallback")
        return MediaResult(video_path="", is_fallback=True)

    dest_path = os.path.join(temp_dir, f"bg_{random.randint(10000, 99999)}.mp4")
    success = _download_video(chosen_url, dest_path)

    if not success:
        return MediaResult(video_path="", is_fallback=True, source_url=chosen_url)

    return MediaResult(video_path=dest_path, source_url=chosen_url, is_fallback=False)
