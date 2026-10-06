"""
shadowvault/pipeline.py
Pipeline orchestrator - chains all five stages.

Provides:
  - run_once()          : single video (async)
  - run_pipeline_loop() : continuous automation
  - main()              : CLI entry point
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import re
import sys
from typing import Optional

from shadowvault.models import PipelineRun
from shadowvault import content as content_stage
from shadowvault import media as media_stage
from shadowvault import audio as audio_stage
from shadowvault import video as video_stage
from shadowvault.upload import YouTubeUploader
from shadowvault.utils.file_manager import cleanup_files

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Single-run pipeline (async)
# ---------------------------------------------------------------------------

async def run_once(
    niche: str = "facts",
    length: str = "short",
    upload: bool = True,
    privacy: str = "public",
    uploader: Optional[YouTubeUploader] = None,
    run_id: Optional[int] = None,
    trend: bool = False,
    topic: Optional[str] = None,
    no_sfx: bool = False,
    watermark: Optional[str] = None,
) -> PipelineRun:
    """
    Execute one full pipeline run.

    Parameters
    ----------
    niche     : "horror" | "motivation" | "facts" | "heists" | "glitches" | "business" | "dark_psychology"
    length    : "short" | "long"
    upload    : whether to upload to YouTube
    privacy   : "public" | "unlisted" | "private"
    uploader  : pre-authenticated YouTubeUploader (created if None)
    run_id    : integer identifier (random if None)
    trend     : whether to scan live internet trends (Google Trends/Wikipedia)
    topic     : custom topic override
    no_sfx    : whether to disable sound effect transitions
    watermark : custom channel watermark handle (empty by default)
    """
    if run_id is None:
        run_id = random.randint(10_000, 99_999)

    run = PipelineRun(run_id=run_id, niche=niche)
    logger.info("=" * 60)
    logger.info("PIPELINE RUN #%d | niche=%s length=%s trend=%s", run_id, niche, length, trend)
    logger.info("=" * 60)

    try:
        # Stage 0: Viral Trend Discovery (if enabled)
        trend_topic = None
        if trend:
            logger.info("[0/5] Scanning hottest viral trends ...")
            from shadowvault.trend_scanner import get_hottest_viral_topic
            trend_topic = get_hottest_viral_topic(preferred_niche=niche if niche != "facts" else None)
            run.trend_topic = trend_topic
            logger.info("[0/5] Viral trend selected: %r [%s] from %s", trend_topic.title, trend_topic.suggested_niche, trend_topic.source)
            niche = trend_topic.suggested_niche or niche
            run.niche = niche

        # Stage 1: Content generation
        logger.info("[1/5] Generating content ...")
        chosen_topic = trend_topic if trend_topic is not None else topic
        if chosen_topic:
            run.content = content_stage.generate_content(niche=niche, length=length, topic=chosen_topic)
        else:
            run.content = content_stage.generate_content(niche=niche, length=length)
        logger.info("[1/5] Done | title=%r | keyword=%s | scenes=%d",
                     run.content.title, run.content.visual_search_keyword, len(run.content.scenes))

        # Stage 2: Background visual sourcing
        logger.info("[2/5] Sourcing visual media ...")
        if getattr(run.content, "scenes", None) and len(run.content.scenes) > 1:
            primary = run.content.visual_search_keyword
            if chosen_topic:
                topic_str = chosen_topic.title if hasattr(chosen_topic, "title") else str(chosen_topic)
                stop_and_jargon = {
                    "the", "a", "an", "that", "this", "these", "those", "and", "or", "in", "on", "at",
                    "to", "for", "of", "with", "by", "from", "yes", "no", "heres", "why", "there",
                    "has", "been", "an", "uptick", "high", "profile", "highprofile", "shocking",
                    "look", "other", "famous", "what", "did", "top", "biggest", "after"
                }
                topic_words = [w for w in re.sub(r"[^\w\s]", "", topic_str).split() if w.lower() not in stop_and_jargon]
                if len(topic_words) >= 2:
                    primary = " ".join(topic_words[:2])
                elif topic_words:
                    primary = topic_words[0]
            if niche == "heists" and primary.lower() in {"art", "heist", "heists", "art heists"}:
                primary = "art museum gallery"
            run.media = media_stage.fetch_multi_scene_media(
                run.content.scenes,
                primary_query=primary,
            )
            for sc in getattr(run.media, "scenes_media", []):
                if sc.get("path"):
                    run.temp_files.append(sc["path"])
        else:
            run.media = media_stage.fetch_background_video(
                keyword=run.content.visual_search_keyword,
            )
            if run.media.video_path:
                run.temp_files.append(run.media.video_path)
        logger.info("[2/5] Done | fallback=%s", run.media.is_fallback)

        # Stage 3: Audio generation (async)
        logger.info("[3/5] Generating TTS audio ...")
        run.audio = await audio_stage.generate_audio_async(
            text=run.content.script,
        )
        if run.audio.audio_path:
            run.temp_files.append(run.audio.audio_path)
        if not run.audio.audio_path:
            raise RuntimeError("TTS stage returned empty audio path")
        logger.info("[3/5] Done | duration=%.2fs", run.audio.duration)

        # Stage 4: Video composition (sync, run in executor)
        logger.info("[4/5] Composing video ...")
        loop = asyncio.get_running_loop()
        run.video = await loop.run_in_executor(
            None,
            lambda: video_stage.compose_video(
                media=run.media,
                audio=run.audio,
                script=run.content.script,
                title=run.content.title,
                watermark_handle=watermark,
                enable_sfx=(not no_sfx),
            ),
        )
        logger.info("[4/5] Done | output=%s", run.video.video_path)

        # Stage 5: YouTube upload
        if upload:
            logger.info("[5/5] Uploading to YouTube (privacy=%s) ...", privacy)
            if uploader is None:
                uploader = YouTubeUploader()
            run.upload = uploader.upload(
                video=run.video,
                content=run.content,
                privacy=privacy,
            )
            if run.upload.success:
                logger.info("[5/5] Done | url=%s", run.upload.youtube_url)
            else:
                logger.error("[5/5] Upload failed: %s", run.upload.error_message)
        else:
            logger.info("[5/5] Skipped (--no-upload) | video at %s", run.video.video_path)

        # Stage 6: Metadata and Provenance Report
        try:
            from shadowvault.config import get_config
            out_dir = get_config().output_dir
        except Exception:
            out_dir = "output"

        try:
            from shadowvault.metadata import write_metadata_file, print_metadata_summary
            write_metadata_file(run, output_dir=out_dir)
            print_metadata_summary(run)
        except Exception as meta_exc:
            logger.warning("Failed to generate metadata report file: %s", meta_exc)

    except Exception as exc:
        logger.error("Pipeline run #%d failed: %s", run_id, exc, exc_info=True)

    finally:
        deleted = cleanup_files(run.temp_files)
        logger.info("Cleaned up %d temp files for run #%d", deleted, run_id)

    return run


# ---------------------------------------------------------------------------
# Continuous automation loop
# ---------------------------------------------------------------------------

async def run_pipeline_loop(
    niche: str = "horror",
    length: str = "short",
    privacy: str = "public",
) -> None:
    """
    Run the pipeline continuously with daily cap and random delays.
    Press Ctrl-C to stop.
    """
    from shadowvault.config import get_config
    cfg = get_config()

    max_per_day = cfg.max_videos_per_day
    delay_min = cfg.inter_video_delay_min
    delay_max = cfg.inter_video_delay_max

    uploader = YouTubeUploader()
    if not uploader.authenticate():
        logger.error("YouTube authentication failed - aborting loop")
        return

    videos_today: int = 0

    logger.info("SHADOW VAULT AUTOMATION LOOP STARTED")
    logger.info("  niche=%s  length=%s  privacy=%s  max/day=%d", niche, length, privacy, max_per_day)

    while True:
        if videos_today >= max_per_day:
            logger.info("Daily cap reached (%d/%d). Sleeping 24h ...", videos_today, max_per_day)
            await asyncio.sleep(86_400)
            videos_today = 0
            continue

        run = await run_once(
            niche=niche,
            length=length,
            upload=True,
            privacy=privacy,
            uploader=uploader,
        )

        if run.upload and run.upload.success:
            videos_today += 1
            logger.info("Videos today: %d/%d | %s", videos_today, max_per_day, run.upload.youtube_url)
        else:
            logger.warning("Upload did not succeed for run #%d", run.run_id)

        delay = random.randint(delay_min, delay_max)
        logger.info("Sleeping %.1f hours before next video ...", delay / 3600)
        await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point: `shadowvault --mode once --niche horror`"""
    parser = argparse.ArgumentParser(
        description="Shadowvault - YouTube Shorts Automation Pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["once", "loop"],
        default="once",
        help="'once' = single video, 'loop' = continuous automation",
    )
    parser.add_argument(
        "--niche",
        choices=["horror", "motivation", "facts", "heists", "glitches", "business", "dark_psychology"],
        default="horror",
        help="Content niche",
    )
    parser.add_argument(
        "--length",
        choices=["short", "long"],
        default="long",
        help="Script length (default: long, 45-55s minidocumentary)",
    )
    parser.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="public",
        help="YouTube privacy status",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Render video but do not upload to YouTube",
    )
    parser.add_argument(
        "--trend",
        action="store_true",
        help="Scan and use the hottest live viral trend from Google Trends / Wikipedia",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Generate a video on a custom topic or headline",
    )
    parser.add_argument(
        "--no-sfx",
        action="store_true",
        help="Disable sound effect transitions (whooshes, impacts)",
    )
    parser.add_argument(
        "--watermark",
        type=str,
        default="",
        help="Custom channel watermark handle (omitted by default)",
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive mode: select category or type custom topic",
    )

    args = parser.parse_args()

    # Initialize logging and config
    from shadowvault.logging_config import setup_logging
    setup_logging()

    if getattr(args, "interactive", False):
        print()
        print("=" * 60)
        print("🏛️  THE SHADOW VAULT - INTERACTIVE EPISODE CREATOR")
        print("=" * 60)
        print("Select category / focus for today's video:")
        print("  [1] Heists & Impossible Crimes (heists)")
        print("  [2] Classified Archives & Government Secrets (dark_psychology)")
        print("  [3] Unexplained Mysteries & Anomalies (glitches)")
        print("  [4] Horror & Dark Historical Events (horror)")
        print("  [5] Today's Top Filtered Viral Trend (live Google Trends)")
        print("  [6] Custom Topic (type your own story/case)")
        choice = input("\nEnter choice [1-6, default=1]: ").strip() or "1"

        if choice == "1":
            chosen_niche = "heists"
            use_trend = True
            custom_topic = None
        elif choice == "2":
            chosen_niche = "dark_psychology"
            use_trend = True
            custom_topic = None
        elif choice == "3":
            chosen_niche = "glitches"
            use_trend = True
            custom_topic = None
        elif choice == "4":
            chosen_niche = "horror"
            use_trend = True
            custom_topic = None
        elif choice == "5":
            chosen_niche = "facts"
            use_trend = True
            custom_topic = None
        elif choice == "6":
            chosen_niche = "facts"
            use_trend = False
            custom_topic = input("Enter custom topic / case name: ").strip()
        else:
            chosen_niche = "heists"
            use_trend = True
            custom_topic = None

        result = asyncio.run(
            run_once(
                niche=chosen_niche,
                length=args.length,
                upload=not args.no_upload,
                privacy=args.privacy,
                trend=use_trend,
                topic=custom_topic,
                no_sfx=args.no_sfx,
                watermark=args.watermark,
            )
        )
    elif args.mode == "loop":
        asyncio.run(
            run_pipeline_loop(
                niche=args.niche,
                length=args.length,
                privacy=args.privacy,
            )
        )
    else:
        result = asyncio.run(
            run_once(
                niche=args.niche,
                length=args.length,
                upload=not args.no_upload,
                privacy=args.privacy,
                trend=args.trend,
                topic=args.topic,
                no_sfx=args.no_sfx,
                watermark=args.watermark,
            )
        )
        print()
        print("=" * 50)
        print(f"Run ID   : {result.run_id}")
        if result.content:
            print(f"Title    : {result.content.title}")
        if result.video:
            print(f"Video    : {result.video.video_path}")
        if result.metadata_path:
            print(f"Metadata : {result.metadata_path}")
        if result.upload:
            if result.upload.success:
                print(f"YouTube  : {result.upload.youtube_url}")
            else:
                print(f"Upload   : FAILED - {result.upload.error_message}")
        print("=" * 50)


if __name__ == "__main__":
    main()
