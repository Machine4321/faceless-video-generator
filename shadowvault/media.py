"""
shadowvault/media.py
Stage 2 - Multi-Scene Background Video & High-Res Visual Asset Fetching from Pexels.

Supports:
- Multi-scene concurrent asset sourcing (video & photo)
- Ken-Burns-ready high-res portrait photography fallback
- Robust retry & fallback chains
- Procedural cinematic backdrop generation when offline
"""

from __future__ import annotations

import logging
import os
import random
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFilter

from shadowvault.models import MediaResult, ScenePlan

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
        logger.info("Pexels video search '%s' returned %d results", keyword, len(videos))
        return videos
    except Exception as exc:
        logger.warning("Pexels video search failed for '%s': %s", keyword, exc)
        return []


def _search_pexels_photos(keyword: str, api_key: str) -> list[dict]:
    url = (
        f"https://api.pexels.com/v1/search"
        f"?query={keyword}&orientation=portrait&per_page={PEXELS_PER_PAGE}"
    )
    headers = {"Authorization": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        photos: list[dict] = data.get("photos", [])
        logger.info("Pexels photo search '%s' returned %d results", keyword, len(photos))
        return photos
    except Exception as exc:
        logger.warning("Pexels photo search failed for '%s': %s", keyword, exc)
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


def _fetch_nasa_archive_image(query: str, dest_path: str) -> Optional[str]:
    """Fetch authentic high-res space/astronomy photograph from NASA open archive."""
    try:
        # Simplify query to 2-3 key nouns for optimal archive recall
        clean_terms = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", query) if w.lower() not in {"dark", "eerie", "shot", "view", "wide", "photograph", "macro"}]
        search_term = " ".join(clean_terms[:3]) if clean_terms else query
        url = f"https://images-api.nasa.gov/search?q={requests.utils.quote(search_term)}&media_type=image"
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            items = resp.json().get("collection", {}).get("items", [])
            for item in items[:4]:
                links = item.get("links", [])
                if links and "href" in links[0]:
                    img_url = links[0]["href"]
                    # Prefer high-res medium/large if available
                    img_url_hr = img_url.replace("~thumb.jpg", "~medium.jpg")
                    img_resp = requests.get(img_url_hr, timeout=15)
                    if img_resp.status_code != 200 or len(img_resp.content) < 10_000:
                        img_resp = requests.get(img_url, timeout=15)
                    if img_resp.status_code == 200 and len(img_resp.content) > 10_000:
                        with open(dest_path, "wb") as f:
                            f.write(img_resp.content)
                        title = item.get("data", [{}])[0].get("title", search_term)
                        logger.info("Fetched authentic NASA archive photograph: %s", title)
                        return title
    except Exception as exc:
        logger.debug("NASA archive search skipped/failed for '%s': %s", query, exc)
    return None


def _fetch_wikimedia_archive_image(query: str, dest_path: str) -> Optional[str]:
    """Fetch authentic public-domain historical evidence/photo from Wikimedia Commons."""
    try:
        clean_terms = [w for w in re.findall(r"\b[A-Za-z]{3,}\b", query) if w.lower() not in {"dark", "eerie", "shot", "view", "wide", "photograph", "macro"}]
        search_term = " ".join(clean_terms[:3]) if clean_terms else query
        url = (
            f"https://en.wikipedia.org/w/api.php"
            f"?action=query&format=json&prop=pageimages&pithumbsize=1080"
            f"&generator=search&gsrsearch={requests.utils.quote(search_term)}&gsrlimit=3"
        )
        headers = {"User-Agent": "ShadowVaultInvestigator/1.0 (contact@machine4321.dev)"}
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for pid, p in pages.items():
                thumb = p.get("thumbnail", {}).get("source")
                if thumb:
                    img_resp = requests.get(thumb, headers=headers, timeout=15)
                    if img_resp.status_code == 200 and len(img_resp.content) > 10_000:
                        with open(dest_path, "wb") as f:
                            f.write(img_resp.content)
                        title = p.get("title", search_term)
                        logger.info("Fetched authentic Wikimedia archive photograph: %s", title)
                        return title
    except Exception as exc:
        logger.debug("Wikimedia archive search skipped/failed for '%s': %s", query, exc)
    return None


def _create_procedural_backdrop(
    scene_id: int,
    dest_path: str,
    width: int = 1080,
    height: int = 1920,
) -> str:
    """Generate a clean dark cinematic gradient backdrop for offline / fallback scenes."""
    img = Image.new("RGB", (width, height), (15, 17, 24))
    draw = ImageDraw.Draw(img)

    # Ambient deep gradients based on scene_id
    colors = [
        ((25, 20, 35), (8, 9, 14)),
        ((15, 28, 38), (5, 10, 16)),
        ((35, 18, 18), (12, 6, 6)),
        ((20, 32, 22), (6, 12, 8)),
        ((32, 26, 12), (12, 10, 4)),
    ]
    c_top, c_bot = colors[scene_id % len(colors)]

    for y in range(height):
        ratio = y / float(height)
        r = int(c_top[0] * (1 - ratio) + c_bot[0] * ratio)
        g = int(c_top[1] * (1 - ratio) + c_bot[1] * ratio)
        b = int(c_top[2] * (1 - ratio) + c_bot[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Add dark vignette shadow around edges
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([0, 0, width, height], fill=(0, 0, 0, 80))
    ov_draw.ellipse([100, 200, width - 100, height - 200], fill=(0, 0, 0, 0))
    overlay = overlay.filter(ImageFilter.GaussianBlur(120))
    img.paste(overlay, (0, 0), overlay)

    img.save(dest_path, "JPEG", quality=90)
    return dest_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_scene_media(
    scene: ScenePlan,
    temp_dir: str,
    api_key: str | None = None,
) -> dict:
    """
    Fetch best media (documentary graphic, AI image, Pexels video, or photo) for a scene.
    Returns dict: {'scene_id': int, 'path': str, 'type': 'video'|'image'}
    """
    if api_key is None:
        from shadowvault.config import get_config
        try:
            api_key = get_config().pexels_api_key
        except Exception:
            api_key = ""

    os.makedirs(temp_dir, exist_ok=True)
    query = scene.visual_query or "cinematic mystery"

    # Explicit offline / mock test mode
    if api_key == "":
        dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_procedural.jpg")
        _create_procedural_backdrop(scene.scene_id, dest)
        return {
            "scene_id": scene.scene_id,
            "path": dest,
            "type": "image",
            "format": "procedural",
            "source_desc": "Procedural Dark Cinema Backdrop (Pillow)",
        }

    import re
    vformat = getattr(scene, "visual_format", "auto")
    text_lower = (scene.narration or "").lower()

    # Intelligent format selection when format is 'auto'
    if vformat == "auto":
        if scene.scene_id == 1 and any(w in text_lower for w in ["sentenced", "arrest", "breaking", "heist", "stole", "found", "shocking", "discovered", "death", "police"]):
            vformat = "newspaper"
        elif any(w in text_lower for w in ["fbi", "police", "cia", "secret", "confidential", "classified", "investigation", "dossier", "surveillance", "evidence"]):
            vformat = "dossier"
        elif any(w in text_lower for w in ["million", "billion", "dollars", "cash", "$", "worth", "stolen"]) and re.search(r"(\$[\d,]+|\b\d+\s*(?:million|billion)\b)", scene.narration, re.I):
            vformat = "counter"
        else:
            vformat = "ai_image"

    # 1. Documentary Evidence Graphic: Newspaper Clipping (with highlighter effect)
    if vformat == "newspaper":
        try:
            from shadowvault.graphics import render_newspaper_frame
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_news_{random.randint(1000, 9999)}.jpg")
            render_newspaper_frame(headline=scene.narration, dest_path=dest)
            logger.info("Generated Vox-style newspaper graphic for scene %d", scene.scene_id)
            return {
                "scene_id": scene.scene_id,
                "path": dest,
                "type": "image",
                "format": "newspaper",
                "source_desc": f"Procedural Archival Newspaper (Pillow 3D Desk, Headline: '{scene.narration[:60]}...')",
            }
        except Exception as exc:
            logger.warning("Newspaper graphic generation failed: %s", exc)

    # 2. Documentary Evidence Graphic: Classified Dossier (red stamp + redaction bars)
    if vformat == "dossier":
        try:
            from shadowvault.graphics import render_classified_dossier
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_dossier_{random.randint(1000, 9999)}.jpg")
            render_classified_dossier(title=scene.visual_query, body_text=scene.narration, dest_path=dest)
            logger.info("Generated classified FBI dossier for scene %d", scene.scene_id)
            return {
                "scene_id": scene.scene_id,
                "path": dest,
                "type": "image",
                "format": "dossier",
                "source_desc": f"Procedural Classified Dossier (Pillow 3D Desk, Stamp: TOP SECRET, Query: '{scene.visual_query}')",
            }
        except Exception as exc:
            logger.warning("Classified dossier generation failed: %s", exc)

    # 3. Documentary Graphic: Animated Stat Counter Video (Rising Number Ticker)
    if vformat == "counter":
        try:
            from shadowvault.graphics import parse_stat_from_narration, render_animated_counter_video
            target_val, prefix, suffix, label = parse_stat_from_narration(scene.narration)
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_counter_{random.randint(1000, 9999)}.mp4")
            dur = max(getattr(scene, "duration", 0.0) or 4.0, 5.0)
            render_animated_counter_video(
                target_value=target_val,
                prefix=prefix,
                suffix=suffix,
                stat_label=label,
                dest_path=dest,
                duration=dur,
            )
            val_str = f"{prefix}{target_val:,} {suffix}".strip()
            logger.info("Generated animated stat counter video for scene %d (%s: %s)", scene.scene_id, label, val_str)
            return {
                "scene_id": scene.scene_id,
                "path": dest,
                "type": "video",
                "format": "counter",
                "source_desc": f"Animated Stat Counter Video (Pillow/FFmpeg, Value: {val_str}, Label: '{label}')",
            }
        except Exception as exc:
            logger.warning("Animated stat counter video generation failed: %s", exc)
            try:
                from shadowvault.graphics import render_stat_counter_card
                dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_counter_{random.randint(1000, 9999)}.jpg")
                render_stat_counter_card(stat_value=val_str if "val_str" in locals() else "$100M", stat_label=label if "label" in locals() else "DOCUMENTED RECORD", dest_path=dest)
                return {
                    "scene_id": scene.scene_id,
                    "path": dest,
                    "type": "image",
                    "format": "counter",
                    "source_desc": f"Static Stat Card Fallback (Value: {val_str if 'val_str' in locals() else '$100M'})",
                }
            except Exception:
                pass

    # 4. Documentary Graphic: Military / Scientific Radar Scope
    if vformat == "radar":
        try:
            from shadowvault.graphics import render_radar_scope_frame
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_radar_{random.randint(1000, 9999)}.jpg")
            render_radar_scope_frame(target_name=scene.visual_query or "ANOMALOUS PULSE", dest_path=dest)
            logger.info("Generated military/scientific radar scope for scene %d", scene.scene_id)
            return {
                "scene_id": scene.scene_id,
                "path": dest,
                "type": "image",
                "format": "radar",
                "source_desc": f"Procedural Military Radar Scope (CRT Phosphor, Target: '{scene.visual_query}')",
            }
        except Exception as exc:
            logger.warning("Radar scope graphic generation failed: %s", exc)

    # 5. Authentic Open Archive Photographs (NASA & Wikimedia Commons)
    if vformat in {"ai_image", "photo", "auto"}:
        # Check NASA for space/astronomy/planets/probes/signals
        space_keywords = ["space", "nasa", "probe", "venus", "mars", "telescope", "astronomy", "signal", "planet", "galaxy", "satellite", "orbit", "meteor", "dust", "cosmic"]
        if any(w in query.lower() or w in text_lower for w in space_keywords):
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_nasa_{random.randint(1000, 9999)}.jpg")
            nasa_title = _fetch_nasa_archive_image(query, dest)
            if nasa_title:
                return {
                    "scene_id": scene.scene_id,
                    "path": dest,
                    "type": "image",
                    "format": "photo",
                    "source_desc": f"NASA Official Archive Photograph ('{nasa_title}')",
                }

        # Check Wikimedia Commons for historical cases/heists/crimes/dossiers
        history_keywords = ["heist", "fbi", "cia", "vault", "diamond", "robbery", "stole", "investigation", "case", "signal", "wow", "plague", "conspiracy", "secret", "archive"]
        if any(w in query.lower() or w in text_lower for w in history_keywords):
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_wiki_{random.randint(1000, 9999)}.jpg")
            wiki_title = _fetch_wikimedia_archive_image(query, dest)
            if wiki_title:
                return {
                    "scene_id": scene.scene_id,
                    "path": dest,
                    "type": "image",
                    "format": "photo",
                    "source_desc": f"Wikimedia Commons Historical Evidence ('{wiki_title}')",
                }

    # 6. Custom 100% Unique AI Visual (Flux)
    if vformat in {"ai_image", "auto"}:
        try:
            from shadowvault.image_gen import generate_ai_image
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_ai_{random.randint(1000, 9999)}.jpg")
            if generate_ai_image(prompt=scene.visual_query, dest_path=dest):
                return {
                    "scene_id": scene.scene_id,
                    "path": dest,
                    "type": "image",
                    "format": "ai_image",
                    "prompt": scene.visual_query,
                    "source_desc": f"Pollinations Flux AI Image (Prompt: '{scene.visual_query}')",
                }
        except Exception as exc:
            logger.warning("AI image generation call failed: %s", exc)

    # 7. High-Resolution Portrait DSLR Photography from Pexels (for Ken Burns smooth motion)
    if api_key and api_key != "fake-key" and not api_key.startswith("test"):
        clean_q = re.sub(r"\b(astronaut|actor|man|woman|person|people|posing|costume|walking away|silhouette)\b", "dark atmospheric", query, flags=re.I).strip()
        search_queries = [clean_q]
        words = clean_q.split()
        if len(words) > 2:
            search_queries.append(" ".join(words[:2]))
        search_queries.append("dark cinematic texture vertical")

        # Prioritize 4K/8K DSLR photos over stock videos with actors
        for sq in search_queries:
            photos = _search_pexels_photos(sq, api_key)
            if photos:
                photo_url = photos[0].get("src", {}).get("large2x") or photos[0].get("src", {}).get("portrait")
                if photo_url:
                    dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_{random.randint(1000, 9999)}.jpg")
                    if _download_video(photo_url, dest):
                        return {
                            "scene_id": scene.scene_id,
                            "path": dest,
                            "type": "image",
                            "format": "photo",
                            "source_desc": f"Pexels High-Res Photo (Query: '{sq}')",
                        }

        # 8. Pexels Video (only for atmospheric textures if photo not found)
        for sq in search_queries:
            videos = _search_pexels(sq, api_key)
            if videos:
                best_link = _pick_best_file(videos[0].get("video_files", []))
                if best_link:
                    dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_{random.randint(1000, 9999)}.mp4")
                    if _download_video(best_link, dest):
                        return {
                            "scene_id": scene.scene_id,
                            "path": dest,
                            "type": "video",
                            "format": "video",
                            "source_desc": f"Pexels Atmospheric B-Roll (Query: '{sq}', URL: {best_link[:60]}...)",
                        }

    # 9. Procedural cinematic backdrop fallback (only when completely offline or all APIs fail)
    dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_procedural.jpg")
    _create_procedural_backdrop(scene.scene_id, dest)
    return {
        "scene_id": scene.scene_id,
        "path": dest,
        "type": "image",
        "format": "procedural",
        "source_desc": "Procedural Dark Cinema Backdrop (Pillow Fallback)",
    }


def fetch_multi_scene_media(
    scenes: list[ScenePlan],
    temp_dir: str | None = None,
    api_key: str | None = None,
) -> MediaResult:
    """
    Fetch media assets for all scenes in a script.
    Populates MediaResult.scenes_media and sets primary video_path.
    """
    if temp_dir is None:
        from shadowvault.config import get_config
        temp_dir = get_config().temp_dir
    os.makedirs(temp_dir, exist_ok=True)

    scenes_media: list[dict] = []
    primary_path = ""
    is_fallback = False

    for scene in scenes:
        item = fetch_scene_media(scene, temp_dir, api_key=api_key)
        scenes_media.append(item)
        if not primary_path:
            primary_path = item["path"]

    return MediaResult(
        video_path=primary_path,
        source_url="multi_scene_pexels",
        is_fallback=is_fallback,
        scenes_media=scenes_media,
    )


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
