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
    niche: str = "horror",
    length: str = "short",
    upload: bool = True,
    privacy: str = "public",
    uploader: Optional[YouTubeUploader] = None,
    run_id: Optional[int] = None,
) -> PipelineRun:
    """
    Execute one full pipeline run.

    Parameters
    ----------
    niche    : "horror" | "motivation" | "facts"
    length   : "short" | "long"
    upload   : whether to upload to YouTube
    privacy  : "public" | "unlisted" | "private"
    uploader : pre-authenticated YouTubeUploader (created if None)
    run_id   : integer identifier (random if None)
    """
    if run_id is None:
        run_id = random.randint(10_000, 99_999)

    run = PipelineRun(run_id=run_id, niche=niche)
    logger.info("=" * 60)
    logger.info("PIPELINE RUN #%d | niche=%s length=%s", run_id, niche, length)
    logger.info("=" * 60)

    try:
        # Stage 1: Content generation
        logger.info("[1/5] Generating content ...")
        run.content = content_stage.generate_content(niche=niche, length=length)
        logger.info("[1/5] Done | title=%r | keyword=%s",
                     run.content.title, run.content.visual_search_keyword)

        # Stage 2: Background video fetch
        logger.info("[2/5] Fetching background video ...")
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
        choices=["horror", "motivation", "facts"],
        default="horror",
        help="Content niche",
    )
    parser.add_argument(
        "--length",
        choices=["short", "long"],
        default="short",
        help="Script length",
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

    args = parser.parse_args()

    # Initialize logging and config
    from shadowvault.logging_config import setup_logging
    setup_logging()

    if args.mode == "loop":
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
            )
        )
        print()
        print("=" * 50)
        print(f"Run ID   : {result.run_id}")
        if result.content:
            print(f"Title    : {result.content.title}")
        if result.video:
            print(f"Video    : {result.video.video_path}")
        if result.upload:
            if result.upload.success:
                print(f"YouTube  : {result.upload.youtube_url}")
            else:
                print(f"Upload   : FAILED - {result.upload.error_message}")
        print("=" * 50)


if __name__ == "__main__":
    main()
