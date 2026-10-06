"""
shadowvault/metadata.py
Automated Metadata & Provenance Reporting Generator for YouTube Shorts & TikTok.

Generates companion .txt files alongside rendered MP4s containing:
1. YouTube Shorts Title, Description, Tags, Category, and Viral Title A/B options.
2. TikTok Caption, Hashtags, and Sound strategy.
3. Complete Provenance & Source Audit:
   - Story origin (Google News, Google Trends, Wikipedia, or editorial prompt)
   - Source publisher, published date, direct URL link
   - Scriptwriter & AI model details
   - Voice synthesis model, duration, and pacing
   - Scene-by-scene visual origins (Flux prompt, Pexels video, procedural 3D document)
   - Background score & procedural Foley SFX audit
"""

from __future__ import annotations

import datetime
import logging
import os
import re
from typing import Optional

from shadowvault.models import PipelineRun

logger = logging.getLogger(__name__)


def _generate_alternative_titles(title: str, niche: str) -> list[str]:
    """Generate 3 viral alternative hook titles for A/B testing."""
    clean_title = re.sub(r"\s*#\w+", "", title).strip()

    patterns = [
        f"The Untold Mystery of {clean_title} 👁️ #Shorts",
        f"What They Discovered Will Baffle You... ({clean_title})",
        f"DECLASSFIED: {clean_title} #TheShadowVault",
    ]
    return patterns


def generate_metadata_text(run: PipelineRun) -> str:
    """Generate the full formatted metadata report as a string."""
    title = (run.content.title if run.content else "CLASSIFIED ARCHIVE FILE").strip()
    if not title.endswith("#Shorts") and "#shorts" not in title.lower():
        yt_title = f"{title} #Shorts"
    else:
        yt_title = title

    alt_titles = _generate_alternative_titles(title, run.niche)
    script = run.content.script if run.content else ""
    word_count = len(script.split()) if script else 0
    duration = run.video.duration if run.video else (run.audio.duration if run.audio else 0.0)

    # YouTube Description
    yt_desc = (
        f"{script[:220]}...\n\n"
        f"What do you believe actually happened? Drop your theory in the comments below. 👇\n\n"
        f"Subscribe to The Shadow Vault for declassified investigations, unsolved mysteries, and unbelievable true cases.\n\n"
        f"#Shorts #Mystery #Unexplained #TheShadowVault #History #Documentary #DidYouKnow"
    )

    # Tags
    base_tags = [
        "the shadow vault",
        "unexplained mystery",
        "strange anomaly",
        "deep space signal",
        "declassified files",
        "creepy facts",
        "investigative documentary",
        "true story",
        "viral shorts",
        "did you know",
        run.niche,
    ]
    if run.trend_topic and run.trend_topic.keywords:
        base_tags.extend(run.trend_topic.keywords[:4])
    yt_tags = ", ".join(dict.fromkeys(base_tags))

    # TikTok Caption
    first_sentence = script.split(".")[0] if script else title
    if len(first_sentence) > 90:
        first_sentence = first_sentence[:87] + "..."
    tt_caption = (
        f"Wait until the end... {first_sentence} 👁️📁 What do you think this was? "
        f"#shadowvault #mystery #unexplained #glitchinthematrix #fyp #creepyfacts #documentary"
    )

    # Source & Provenance information
    story_source = "Editorial Vault Archive"
    source_name = "The Shadow Vault Investigative Desk"
    source_url = "https://github.com/Machine4321/faceless-video-generator"
    pub_date = "Active Evergreen Archive"

    if run.trend_topic:
        if run.trend_topic.source == "google_news":
            story_source = "Google News Live Breaking RSS Scanner"
            source_name = run.trend_topic.source_name or "Verified News Outlet"
            source_url = run.trend_topic.source_url or "https://news.google.com"
            pub_date = run.trend_topic.published_date or "Recent"
        elif run.trend_topic.source == "google_trends":
            story_source = "Google Trends Daily Real-Time Search Feed"
            source_name = "Google Trends (US & Global Daily Traffic)"
            source_url = f"https://trends.google.com/trending?geo=US"
            pub_date = f"Trending Volume: {run.trend_topic.search_volume}"
        elif run.trend_topic.source == "wikipedia":
            story_source = "Wikimedia Foundation Historical Events API ('On This Day')"
            source_name = "Wikipedia Selected Anniversaries & Records"
            source_url = "https://en.wikipedia.org/wiki/Main_Page"
            pub_date = f"Historical Record: {run.trend_topic.search_volume}"

    voice_name = run.audio.voice if run.audio else "en-US-ChristopherNeural"
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build scene breakdown text
    scenes_text = []
    scenes = getattr(run.content, "scenes", [])
    scenes_media = getattr(run.media, "scenes_media", []) if run.media else []

    for i, sc in enumerate(scenes):
        m_info = scenes_media[i] if i < len(scenes_media) else {}
        s_format = m_info.get("format", getattr(sc, "visual_format", "auto"))
        s_desc = m_info.get("source_desc", f"Visual query: {sc.visual_query}")
        sfx = getattr(sc, "sfx_cue", "whoosh") or "whoosh"
        scenes_text.append(
            f"Scene #{sc.scene_id} [Format: {s_format.upper()} | SFX: {sfx}]\n"
            f"  • Narration : \"{sc.narration}\"\n"
            f"  • Sourcing  : {s_desc}\n"
        )
    scenes_block = "\n".join(scenes_text) if scenes_text else "  • Single background track with procedural dynamic kinetic effects."

    report = f"""================================================================================
🎬 THE SHADOW VAULT - VIDEO METADATA & FULL PROVENANCE AUDIT
================================================================================
Generated At : {now_str}
Run ID       : #{run.run_id}
Niche        : {run.niche}
Video File   : {os.path.basename(run.video.video_path) if run.video else f'FacelessVideo_{run.run_id}.mp4'}
Duration     : {duration:.2f} seconds
Resolution   : 1080x1920 (Vertical 9:16 - 60fps)

================================================================================
1. 📱 YOUTUBE SHORTS UPLOAD METADATA
================================================================================
PRIMARY TITLE:
{yt_title}

VIRAL ALTERNATIVE HOOK TITLES (A/B Test Variations):
1. {alt_titles[0]}
2. {alt_titles[1]}
3. {alt_titles[2]}

DESCRIPTION:
{yt_desc}

TAGS (Comma-Separated for Studio):
{yt_tags}

CATEGORY:
27 (Education / Science & Discovery) or 24 (Entertainment)

ALGORITHM SETTINGS:
- Shorts Remixing : Allow Video & Audio Remixing
- Made for Kids   : No (Not made for kids)
- Visibility      : Public (or Unlisted for initial inspection)
- Sound Strategy  : Original Audio (Narrator + Tension Pad + Foley SFX)

================================================================================
2. 🎵 TIKTOK UPLOAD METADATA
================================================================================
RECOMMENDED CAPTION (With Hook & Call-to-Action):
{tt_caption}

RECOMMENDED TIKTOK HASHTAGS:
#fyp #foryou #mystery #unexplained #glitchinthematrix #theshadowvault #didyouknow #creepyfacts #historymystery

TIKTOK SOUND STRATEGY:
Use the video's original audio track (Mastered Edge-TTS voiceover + Foley sound design).
Pro tip: Search for a trending eerie/suspense sound on TikTok, add it to your post,
and lower its volume to 3-5% while keeping the original sound at 100%. This triggers
the TikTok Sound Algorithm for additional organic viral push.

================================================================================
3. 🔍 COMPLETE PROVENANCE & SOURCE AUDIT
================================================================================
[STORY & INVESTIGATION ORIGIN]
- Story Engine     : {story_source}
- Source Publisher : {source_name}
- Origin Link / URL: {source_url}
- Date / Recency   : {pub_date}
- Scriptwriter AI  : Google Gemini 2.5 Flash (Viral Retention Prompt Engine)
- Story Hook       : "{getattr(run.content, 'hook', title)}"
- Word Count       : {word_count} words (~{int((word_count / max(duration, 1.0)) * 60)} WPM)

[VOICE & NARRATION SYNTHESIS]
- TTS Engine       : Microsoft Edge Neural TTS
- Voice Model      : {voice_name} (Documentary Investigator Tone)
- Speed & Pitch    : Rate +0% | Pitch +0Hz
- Subtitle System  : Kinetic Word-Level Timings with Zero-Flicker Gap-Bridging

[SCENE-BY-SCENE VISUAL ASSETS & PROMPTS]
{scenes_block}

[SOUND DESIGN & PROCEDURAL FOLEY SFX]
- Background Music : Cinematic Dark Tension Drone (Synthesized low-frequency pad, 12% vol)
- Scene Transition : Sub-bass impact swoosh & static frequency cut
- Foley Library    :
    * sfx/stamp_thud.wav   (Rubber stamp on classified document)
    * sfx/paper_slide.wav  (Physical archival paper slide on desk)
    * sfx/highlighter.wav  (Chisel-tip marker highlight swipe)
    * sfx/ticker.wav       (Mechanical counter click)
================================================================================
"""
    return report


def write_metadata_file(run: PipelineRun, output_dir: Optional[str] = None) -> str:
    """
    Write the metadata report to a .txt file alongside the video.
    Returns the absolute path to the generated file.
    """
    if output_dir is None:
        from shadowvault.config import get_config
        try:
            output_dir = get_config().output_dir
        except Exception:
            output_dir = "output"

    os.makedirs(output_dir, exist_ok=True)

    if run.video and run.video.video_path:
        base_name = os.path.splitext(os.path.basename(run.video.video_path))[0]
    else:
        base_name = f"FacelessVideo_{run.run_id}"

    filename = f"{base_name}_metadata.txt"
    dest_path = os.path.join(output_dir, filename)

    content = generate_metadata_text(run)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

    run.metadata_path = dest_path
    logger.info("Generated video metadata & source report at %s", dest_path)
    return dest_path


def print_metadata_summary(run: PipelineRun) -> None:
    """Print an attractive summary of the metadata directly to stdout/console safely across all OSes."""
    import sys
    title = run.content.title if run.content else "Faceless Video"
    summary_lines = [
        "",
        "=" * 65,
        "[METADATA] VIDEO & PROVENANCE SUMMARY",
        "=" * 65,
        f"Video File    : {os.path.basename(run.video.video_path) if run.video else 'N/A'}",
        f"Metadata File : {run.metadata_path or 'N/A'}",
        f"Niche         : {run.niche.upper()}",
        f"YouTube Title : {title} #Shorts",
    ]
    if run.trend_topic:
        summary_lines.append(f"Story Source  : {run.trend_topic.source_name or run.trend_topic.source}")
        if run.trend_topic.source_url:
            summary_lines.append(f"Source URL    : {run.trend_topic.source_url[:70]}...")
        if run.trend_topic.published_date:
            summary_lines.append(f"Published Date: {run.trend_topic.published_date}")
    summary_lines.append(f"Voice Actor   : {run.audio.voice if run.audio else 'en-US-ChristopherNeural'}")
    if run.media and run.media.scenes_media:
        summary_lines.append(f"Visual Scenes : {len(run.media.scenes_media)} scenes sourced (Flux AI, 3D Docs, Pexels)")
    summary_lines.extend(["=" * 65, ""])

    output = "\n".join(summary_lines)
    try:
        print(output)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "ascii"
        print(output.encode(encoding, errors="replace").decode(encoding))
