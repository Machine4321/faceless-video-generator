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
import re
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
                    # Try high-res alternatives first
                    candidates = [
                        re.sub(r"~(thumb|small)\.jpg$", "~large.jpg", img_url),
                        re.sub(r"~(thumb|small)\.jpg$", "~medium.jpg", img_url),
                        img_url,
                    ]
                    for cand_url in candidates:
                        try:
                            img_resp = requests.get(cand_url, timeout=15)
                            if img_resp.status_code == 200 and len(img_resp.content) > 10_000:
                                with open(dest_path, "wb") as f:
                                    f.write(img_resp.content)
                                title = item.get("data", [{}])[0].get("title", search_term)
                                logger.info("Fetched authentic NASA archive photograph: %s", title)
                                return title
                        except Exception:
                            continue
    except Exception as exc:
        logger.debug("NASA archive search skipped/failed for '%s': %s", query, exc)
    return None


def _fetch_wikimedia_archive_image(query: str, dest_path: str) -> Optional[str]:
    """Fetch authentic public-domain historical evidence/photo from Wikimedia Commons."""
    try:
        clean_terms = [w for w in re.findall(r"\b[A-Za-z]{4,}\b", query) if w.lower() not in {"dark", "eerie", "shot", "view", "wide", "photograph", "macro", "close", "scene", "room", "vintage", "archival"}]
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
            # Sort pages strictly by search relevance index
            sorted_pages = sorted(pages.values(), key=lambda x: x.get("index", 999))
            for p in sorted_pages:
                page_title = p.get("title", "").lower()
                # Ensure the page title genuinely matches the key search terms with whole-word boundaries
                if clean_terms:
                    matches = [bool(re.search(rf"\b{re.escape(term.lower())}\b", page_title)) for term in clean_terms]
                    if not any(matches):
                        continue
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


def _extract_clean_search_terms(query: str, narration: str = "") -> list[str]:
    """
    Extract meaningful subject queries for stock media / image retrieval,
    stripping camera jargon, lens details, and prompt filler words
    so search engines (Pexels, Pollinations) receive high-relevance subject terms.
    """
    camera_noise = {
        "35mm", "photo", "photograph", "photography", "photographer", "camera", "lens",
        "macro", "close", "closeup", "ultra", "detailed", "realistic", "cinematic",
        "hd", "4k", "8k", "dslr", "film", "still", "view", "wide", "angle", "setting",
        "background", "wallpaper", "portrait", "vertical", "texture", "archival", "vintage",
        "grainy", "eerie", "dark", "atmospheric", "shadow", "floor", "room", "style", "format",
        "dynamic", "action", "shot", "video", "footage", "clip", "ready", "scene",
        "up", "look", "looking", "capture", "capturing", "perspective", "a", "an",
        "the", "of", "in", "on", "at", "to", "by", "from", "as", "into", "is", "it",
        "he", "she", "they", "was", "were", "this", "that", "him", "her", "his",
        "with", "and", "for", "showing", "featuring", "under", "about", "could", "would",
        # Abstract journalistic buzzwords and adjectives that break stock media retrieval:
        "highprofile", "high-profile", "high", "profile", "uptick", "crisis", "shocking",
        "unbelievable", "mysterious", "secret", "truth", "viral", "epic", "insane",
        "crazy", "bizarre", "real", "why", "heres", "there", "has", "been", "yes", "no",
        "overview", "look", "report", "news", "trend", "trending"
    }

    q_words = [w for w in re.findall(r"\b[A-Za-z0-9'-]+\b", query) if w.lower() not in camera_noise]
    n_words = [w for w in re.findall(r"\b[A-Za-z0-9'-]+\b", narration) if w.lower() not in camera_noise]

    queries: list[str] = []
    if len(q_words) >= 3:
        queries.append(" ".join(q_words[:3]))
    if len(q_words) >= 2:
        queries.append(" ".join(q_words[:2]))
    if q_words:
        queries.append(q_words[0])

    if len(n_words) >= 2:
        nq = " ".join(n_words[:2])
        if nq not in queries:
            queries.append(nq)
    if n_words and n_words[0] not in queries:
        queries.append(n_words[0])

    if not queries:
        clean_fallback = [w for w in re.findall(r"\b[A-Za-z0-9'-]+\b", query) if w.lower() not in {"the", "a", "an", "this", "that"}]
        queries = [clean_fallback[0]] if clean_fallback else ["viral subject"]
    return queries


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_scene_media(
    scene: ScenePlan,
    temp_dir: str,
    api_key: str | None = None,
    context_image_path: str | None = None,
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
    critic_key = "fake-key" if (api_key and (api_key == "fake-key" or "mock" in api_key.lower() or api_key.startswith("test"))) else None

    # Explicit offline / mock test mode
    if api_key == "":
        dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_procedural.jpg")
        _create_procedural_backdrop(scene.scene_id, dest)
        return {
            "scene_id": scene.scene_id,
            "path": dest,
            "type": "image",
            "format": "procedural",
            "visual_format": "procedural",
            "narration": scene.narration,
            "source_desc": "Procedural Dark Cinema Backdrop (Pillow)",
        }

    vformat = getattr(scene, "visual_format", "auto")
    text_lower = (scene.narration or "").lower()

    # Intelligent format selection when format is 'auto'
    if vformat == "auto":
        vformat = "ai_image"

    # Guard: Dossier format should ONLY be used for classified intelligence/crime
    if vformat == "dossier":
        dossier_keywords = ["fbi", "cia", "classified", "secret", "confidential", "investigation", "memo", "case file", "dossier", "agent", "heist", "police", "top secret"]
        if not any(w in query.lower() or w in text_lower for w in dossier_keywords):
            vformat = "newspaper" if any(w in text_lower for w in ["record", "rule", "headline", "news", "official", "judges", "competition"]) else "ai_image"

    # Guard: Radar format should ONLY be used for actual signals/radio/astronomy/radar
    if vformat == "radar":
        radar_keywords = ["radar", "signal", "radio", "telescope", "mhz", "ghz", "frequency", "satellite", "space", "astronomy", "pulsar", "telemetry"]
        if not any(w in query.lower() or w in text_lower for w in radar_keywords):
            vformat = "ai_image"

    # 1. Documentary Evidence Graphic: Newspaper Clipping (with embedded subject photo & highlighter effect)
    if vformat == "newspaper":
        try:
            from shadowvault.graphics import render_newspaper_frame
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_news_{random.randint(1000, 9999)}.jpg")
            render_newspaper_frame(headline=scene.narration, photo_path=context_image_path, dest_path=dest)
            logger.info("Generated Vox-style broadsheet newspaper graphic for scene %d (photo=%s)", scene.scene_id, bool(context_image_path))
            return {
                "scene_id": scene.scene_id,
                "path": dest,
                "type": "image",
                "format": "newspaper",
                "visual_format": "newspaper",
                "narration": scene.narration,
                "source_desc": f"Procedural Archival Broadsheet (Pillow 3D Desk, Headline: '{scene.narration[:60]}...')",
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
                "visual_format": "dossier",
                "narration": scene.narration,
                "source_desc": f"Procedural Classified Dossier (Pillow 3D Desk, Stamp: TOP SECRET, Query: '{scene.visual_query}')",
            }
        except Exception as exc:
            logger.warning("Classified dossier generation failed: %s", exc)

    # 3. Documentary Graphic: Animated Stat Counter Video (Rising Number Ticker with Blurred Backdrop & EQ)
    if vformat == "counter":
        try:
            from shadowvault.graphics import parse_stat_from_narration, render_animated_counter_video
            target_val, prefix, suffix, label = parse_stat_from_narration(scene.narration, fallback_query=scene.visual_query)
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_counter_{random.randint(1000, 9999)}.mp4")
            dur = max(getattr(scene, "duration", 0.0) or 4.0, 5.0)
            render_animated_counter_video(
                target_value=target_val,
                prefix=prefix,
                suffix=suffix,
                stat_label=label,
                dest_path=dest,
                duration=dur,
                bg_image_path=context_image_path,
            )
            val_str = f"{prefix}{target_val:,} {suffix}".strip()
            logger.info("Generated animated stat counter video for scene %d (%s: %s | bg=%s)", scene.scene_id, label, val_str, bool(context_image_path))
            return {
                "scene_id": scene.scene_id,
                "path": dest,
                "type": "video",
                "format": "counter",
                "visual_format": "counter",
                "narration": scene.narration,
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

        # Check Wikimedia Commons ONLY for verified specific historical entities/cases
        history_entities = ["gardner museum", "isabella stewart", "rembrandt", "vermeer", "mona lisa", "green vault", "antwerp diamond", "wow signal", "dancing plague", "operation midnight climax", "mk ultra"]
        if any(w in query.lower() or w in text_lower for w in history_entities):
            dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_wiki_{random.randint(1000, 9999)}.jpg")
            wiki_title = _fetch_wikimedia_archive_image(query, dest)
            if wiki_title:
                from shadowvault.vision_critic import verify_image_relevance
                passed, score, reason = verify_image_relevance(dest, scene.narration, scene.visual_query, api_key=critic_key)
                if passed:
                    return {
                        "scene_id": scene.scene_id,
                        "path": dest,
                        "type": "image",
                        "format": "photo",
                        "source_desc": f"Wikimedia Commons Historical Evidence ('{wiki_title}')",
                    }
                else:
                    logger.info("Vision Critic rejected Wikimedia image %s (score=%d): %s", dest, score, reason)
                    if os.path.exists(dest):
                        try:
                            os.remove(dest)
                        except Exception:
                            pass

    # 6. Custom 100% Unique AI Visual (Flux)
    if vformat in {"ai_image", "auto", "photo"}:
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

    # 7. High-Resolution Portrait Photography from Pexels (Vision-Critic verified)
    if api_key and api_key != "fake-key" and not api_key.startswith("test"):
        search_queries = _extract_clean_search_terms(query, scene.narration)

        # Prioritize high-res portrait photography
        for sq in search_queries:
            photos = _search_pexels_photos(sq, api_key)
            if photos:
                for cand_idx in range(min(len(photos), 3)):
                    pick_idx = (scene.scene_id - 1 + cand_idx) % len(photos)
                    photo = photos[pick_idx]
                    photo_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("portrait")
                    if photo_url:
                        dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_{random.randint(1000, 9999)}.jpg")
                        if _download_video(photo_url, dest):
                            from shadowvault.vision_critic import verify_image_relevance
                            passed, score, reason = verify_image_relevance(dest, scene.narration, scene.visual_query, api_key=critic_key)
                            if passed:
                                return {
                                    "scene_id": scene.scene_id,
                                    "path": dest,
                                    "type": "image",
                                    "format": "photo",
                                    "source_desc": f"Pexels High-Res Photo (Query: '{sq}', Alt: '{photo.get('alt', '')[:50]}')",
                                }
                            else:
                                logger.info("Vision Critic rejected Pexels photo %s (score=%d): %s", dest, score, reason)
                                if os.path.exists(dest):
                                    try:
                                        os.remove(dest)
                                    except Exception:
                                        pass

        # 8. High-Resolution Video from Pexels
        for sq in search_queries:
            videos = _search_pexels(sq, api_key)
            if videos:
                pick_vidx = (scene.scene_id - 1) % len(videos)
                best_link = _pick_best_file(videos[pick_vidx].get("video_files", []))
                if best_link:
                    dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_{random.randint(1000, 9999)}.mp4")
                    if _download_video(best_link, dest):
                        return {
                            "scene_id": scene.scene_id,
                            "path": dest,
                            "type": "video",
                            "format": "video",
                            "source_desc": f"Pexels Video Footage (Query: '{sq}', URL: {best_link[:60]}...)",
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
    primary_query: str | None = None,
) -> MediaResult:
    """
    Fetch media assets for all scenes in a script with Character/Subject Series Anchoring:
    - Finds a unified photoshoot series on Pexels (same photographer) for the core subject/character
      so the subject (e.g. Jack Russell terrier, athlete, car) remains 100% consistent across all scenes!
    - Generates documentary graphics (newspaper, counter, dossier, radar) when appropriate for the scene
    - Falls back gracefully to single-scene fetch if no character series is needed or found.
    """
    if temp_dir is None:
        from shadowvault.config import get_config
        temp_dir = get_config().temp_dir
    os.makedirs(temp_dir, exist_ok=True)

    if api_key is None:
        from shadowvault.config import get_config
        try:
            api_key = get_config().pexels_api_key
        except Exception:
            api_key = ""

    critic_key = "fake-key" if (api_key and (api_key == "fake-key" or "mock" in api_key.lower() or api_key.startswith("test"))) else None

    # Offline / Mock test mode
    if not api_key or api_key == "fake-key" or api_key.startswith("test"):
        scenes_media = []
        for sc in scenes:
            it = fetch_scene_media(sc, temp_dir, api_key=api_key)
            it["narration"] = sc.narration
            it["visual_format"] = getattr(sc, "visual_format", "auto")
            scenes_media.append(it)
        return MediaResult(
            video_path=scenes_media[0]["path"] if scenes_media else "",
            source_url="multi_scene_offline",
            is_fallback=False,
            scenes_media=scenes_media,
        )

    # 1. Discover Character / Subject Anchor Series on Pexels
    anchor_photos: list[dict] = []
    anchor_photographer: str = ""
    anchor_query: str = ""

    # Build prioritized candidate subject queries
    candidates: list[str] = []

    # Priority A: Check if a specific animal breed or distinct subject is named in scenes or primary_query
    known_distinct_subjects = [
        "jack russell terrier", "jack russell", "golden retriever", "dalmatian", "german shepherd",
        "border collie", "corgi", "poodle", "husky", "chihuahua", "french bulldog", "labrador",
        "beagle", "rottweiler", "pitbull", "boxer", "dachshund", "shiba inu", "pug",
        "dog dancing", "dancing dog", "salsa dog", "dog", "puppy", "dogs",
        "tabby cat", "persian cat", "siamese cat", "black cat", "cat", "kitten",
        "formula 1 car", "supercar", "sports car", "fighter jet", "space shuttle",
        # Settings, Art & Crime physical subjects
        "art museum gallery", "art museum", "museum gallery", "art gallery", "museum vault",
        "bank vault", "diamond vault", "framed oil painting", "framed painting", "oil painting",
        "security camera cctv", "empty picture frame",
    ]
    all_text = " ".join([primary_query or ""] + [f"{sc.visual_query} {sc.narration}" for sc in scenes]).lower()
    for ds in known_distinct_subjects:
        if ds in all_text and ds not in candidates:
            candidates.append(ds)

    # Priority B: Primary query clean terms (strip stopwords)
    if primary_query:
        for t in _extract_clean_search_terms(primary_query):
            if t.lower() not in {"the", "a", "an", "viral subject"} and t not in candidates:
                candidates.append(t)

    # Priority C: Clean terms from character/visual scenes
    for sc in scenes:
        if sc.visual_format in {"ai_image", "photo", "video", "auto"} and sc.visual_query:
            for term in _extract_clean_search_terms(sc.visual_query, sc.narration):
                if term.lower() not in {"the", "a", "an", "viral subject"} and term not in candidates:
                    candidates.append(term)

    # Search Pexels to locate a photographer with a multi-shot series
    from collections import Counter
    for cand_q in candidates[:6]:
        # Expand single-word ambiguous art terms to concrete gallery searches
        if cand_q.lower() == "art":
            cand_q = "art museum gallery"
        photos = _search_pexels_photos(cand_q, api_key)
        if not photos:
            continue
        counts = Counter(p.get("photographer") for p in photos if p.get("photographer"))
        if counts:
            top_photographer, count = counts.most_common(1)[0]
            if count >= 2:
                anchor_photographer = top_photographer
                anchor_photos = [p for p in photos if p.get("photographer") == top_photographer]
                anchor_query = cand_q
                logger.info(
                    "Locked Character Anchor Series: '%s' by photographer '%s' (%d photos in series)",
                    anchor_query, anchor_photographer, len(anchor_photos)
                )
                break

    # 2. Allocate media per scene
    scenes_media: list[dict] = []
    series_idx = 0
    primary_path = ""
    last_character_photo: str | None = None

    for scene in scenes:
        vformat = getattr(scene, "visual_format", "auto")
        text_lower = (scene.narration or "").lower()

        # Intelligent format resolution if 'auto'
        if vformat == "auto":
            if any(w in text_lower for w in ["bpm", "beats per minute", "points", "million", "billion", "dollars", "cash", "$"]) and re.search(r"(\$[\d,]+|\b\d+\s*(?:bpm|beats|points|million|billion|mph|km/h|percent|%)\b)", scene.narration, re.I):
                vformat = "counter"
                scene.visual_format = "counter"
            elif any(w in text_lower for w in ["breaking", "headline", "newspaper", "record headline", "front page"]):
                vformat = "newspaper"
                scene.visual_format = "newspaper"

        # Documentary graphics take precedence for their specific purpose
        if vformat in {"newspaper", "dossier", "counter", "radar"}:
            item = fetch_scene_media(scene, temp_dir, api_key=api_key, context_image_path=last_character_photo)
            item["narration"] = scene.narration
            item["visual_format"] = vformat
            scenes_media.append(item)
            if not primary_path:
                primary_path = item["path"]
            continue

        # For visual scenes: use character anchor series if available, suitable, and verified
        used_series_item = False
        # Do not override custom AI images with stock photos unless an explicit continuous character/animal series is active
        allow_series = any(
            k in anchor_query.lower() for k in ["dog", "puppy", "cat", "car", "terrier", "athlete", "supercar", "jet", "shuttle", "dancer"]
        )
        if allow_series and anchor_photos and series_idx < len(anchor_photos):
            photo = anchor_photos[series_idx]
            photo_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("portrait") or photo.get("src", {}).get("original")
            if photo_url:
                dest = os.path.join(temp_dir, f"scene_{scene.scene_id}_series_{photo.get('id')}.jpg")
                if _download_video(photo_url, dest):
                    from shadowvault.vision_critic import verify_image_relevance
                    passed, score, reason = verify_image_relevance(dest, scene.narration, scene.visual_query, api_key=critic_key)
                    if passed:
                        series_idx += 1
                        last_character_photo = dest
                        alt_desc = (photo.get("alt") or "").strip()
                        logger.info("Scene %d assigned from Character Series (%s - Photo %d, score=%d)", scene.scene_id, anchor_photographer, series_idx, score)
                        scenes_media.append({
                            "scene_id": scene.scene_id,
                            "path": dest,
                            "type": "image",
                            "format": "photo",
                            "visual_format": "photo",
                            "narration": scene.narration,
                            "source_desc": f"Pexels Character Series ({anchor_photographer}, Subject: '{anchor_query}', Alt: '{alt_desc[:50]}')",
                        })
                        used_series_item = True
                        if not primary_path:
                            primary_path = dest
                    else:
                        logger.info("Vision Critic rejected Character Series photo for scene %d (score=%d): %s", scene.scene_id, score, reason)
                        if os.path.exists(dest):
                            try:
                                os.remove(dest)
                            except Exception:
                                pass

        if not used_series_item:
            # Fall back to standard scene-specific search
            item = fetch_scene_media(scene, temp_dir, api_key=api_key, context_image_path=last_character_photo)
            item["narration"] = scene.narration
            item["visual_format"] = getattr(scene, "visual_format", "auto")
            scenes_media.append(item)
            if not primary_path:
                primary_path = item["path"]

    return MediaResult(
        video_path=primary_path,
        source_url="multi_scene_pexels",
        is_fallback=False,
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
