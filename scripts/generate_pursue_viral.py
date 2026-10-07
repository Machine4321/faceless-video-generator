"""
scripts/generate_pursue_viral.py
Master generator for the 2026 PURSUE Tranche 6 declassified files viral video.
Engineered for maximum 25s retention, seamless infinite loop,
Hollywood-mastered voiceover, high-contrast hook banner, and verified visual assets.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import shutil
import sys
import subprocess

from shadowvault.config import get_config
from shadowvault.models import ContentResult, ScenePlan
from shadowvault import media as media_stage
from shadowvault import audio as audio_stage
from shadowvault import video as video_stage
from shadowvault.utils.file_manager import cleanup_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pursue_viral_master")


async def main():
    cfg = get_config()
    run_id = random.randint(10000, 99999)
    temp_dir = cfg.temp_dir
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(cfg.output_folder, exist_ok=True)

    title = "WAR.GOV JUST LEAKED TRANCHE 6: PROJECT PURSUE"
    hook_header = "WAR.GOV JUST LEAKED TRANCHE 6"
    hook_category = "2026 DECLASSIFIED"
    tags = "#shorts #mystery #uap #declassified #pentagon #pursue #conspiracy #truecrime #fyp #viral"

    scenes = [
        ScenePlan(
            scene_id=1,
            narration="The United States government just unsealed Tranche Six of project PURSUE.",
            visual_query="TOP SECRET PENTAGON TRANCHE 6 UNSEALED MEMORANDUM DECLASSIFIED",
            sfx_cue="impact",
            visual_format="dossier",
        ),
        ScenePlan(
            scene_id=2,
            narration="Declassified radar records confirm metallic plasma orbs moving at Mach 3 with zero heat signature.",
            visual_query="MILITARY RADAR TELEMETRY MACH 3 TARGET LOCK",
            sfx_cue="radar_ping",
            visual_format="radar",
        ),
        ScenePlan(
            scene_id=3,
            narration="FBI files reveal fighter pilots suffered total instrument blackout and electromagnetic radiation burns.",
            visual_query="cinematic military fighter jet cockpit night flir infrared screen blinking warning red cockpit instruments failure",
            sfx_cue="whoosh",
            visual_format="ai_image",
        ),
        ScenePlan(
            scene_id=4,
            narration="Over two thousand pages of evidence describe unacknowledged subterranean facilities.",
            visual_query="2000 pages declassified evidence",
            sfx_cue="ticker",
            visual_format="counter",
        ),
        ScenePlan(
            scene_id=5,
            narration="Which leaves the Pentagon with only one unanswered record...",
            visual_query="cinematic dark metallic glowing sphere floating over military base security gate ominous dramatic lighting",
            sfx_cue="suspense_drone",
            visual_format="ai_image",
        ),
    ]

    full_script = " ".join(s.narration for s in scenes)

    content = ContentResult(
        title=title,
        script=full_script,
        visual_search_keyword="pentagon declassified uap military",
        tags=tags,
        niche="glitches",
        hook=scenes[0].narration,
        hook_header=hook_header,
        hook_category=hook_category,
        scenes=scenes,
    )

    logger.info("=== STEP 1: SCRIPT & HOOK ARCHITECTURE ===")
    logger.info("Title       : %s", content.title)
    logger.info("Hook Banner : [%s] %s", content.hook_category, content.hook_header)
    logger.info("Word Count  : %d words (~24-26s)", len(full_script.split()))
    logger.info("Full Script : %s", full_script)

    temp_files: list[str] = []

    # Step 2: Sourcing visual media with Vision Critic validation
    logger.info("=== STEP 2: SOURCING HIGH-RES VISUAL MEDIA ===")
    media = media_stage.fetch_multi_scene_media(
        content.scenes,
        primary_query="military radar classified uap document",
    )
    for sc in getattr(media, "scenes_media", []):
        if sc.get("path"):
            temp_files.append(sc["path"])
            logger.info("Scene %d [%s] -> %s (%s)", sc.get("scene_id"), sc.get("visual_format"), sc.get("path"), sc.get("source_desc", "")[:60])

    # Step 3: TTS Audio Synthesis with Edge-TTS & Hollywood Mastering
    logger.info("=== STEP 3: TTS AUDIO SYNTHESIS & HOLLYWOOD MASTERING ===")
    audio = await audio_stage.generate_audio_async(
        text=content.script,
        voice="en-US-BrianMultilingualNeural",
        rate="+8%",
        master=True,
    )
    if audio.audio_path:
        temp_files.append(audio.audio_path)
    logger.info("Mastered audio ready: %s (Duration: %.2fs)", audio.audio_path, audio.duration)

    # Step 4: Composing Master Video
    logger.info("=== STEP 4: COMPOSING MASTER VIDEO ===")
    loop = asyncio.get_running_loop()
    video = await loop.run_in_executor(
        None,
        lambda: video_stage.compose_video(
            media=media,
            audio=audio,
            script=content.script,
            title=content.title,
            watermark_handle=None,
            enable_sfx=True,
            hook_header=content.hook_header,
            hook_category=content.hook_category,
        ),
    )
    logger.info("Master video rendered: %s (Duration: %.2fs)", video.video_path, video.duration)

    # Step 5: Extract Frames for Inspection
    out_dir = cfg.output_folder
    f1 = os.path.join(out_dir, "pursue_frame_1s.jpg")
    f5 = os.path.join(out_dir, "pursue_frame_5s.jpg")
    f11 = os.path.join(out_dir, "pursue_frame_11s.jpg")
    f17 = os.path.join(out_dir, "pursue_frame_17s.jpg")
    f23 = os.path.join(out_dir, "pursue_frame_23s.jpg")

    for ss, dest in [("00:00:01.000", f1), ("00:00:05.000", f5), ("00:00:11.000", f11), ("00:00:17.000", f17), ("00:00:23.000", f23)]:
        cmd = ["ffmpeg", "-y", "-ss", ss, "-i", video.video_path, "-vframes", "1", dest]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info("Extracted inspection frames to %s", out_dir)

    # Step 6: Create TikTok Upload Guide & Metadata
    drive_dir = r"G:\My Drive\tiktok"
    os.makedirs(drive_dir, exist_ok=True)

    dest_video_name = "2026_DECLASSIFIED_WAR_GOV_PURSUE_TRANCHE_6.mp4"
    dest_video_path = os.path.join(drive_dir, dest_video_name)
    shutil.copy2(video.video_path, dest_video_path)
    logger.info("Copied video to Google Drive: %s", dest_video_path)

    # Copy Hook Preview
    shutil.copy2(f1, os.path.join(drive_dir, "2026_PURSUE_TRANCHE_6_HOOK_PREVIEW.jpg"))

    # Write TikTok upload info
    info_text = f"""================================================================================
📱 TIKTOK & SHORTS UPLOAD INFO - THE SHADOW VAULT
================================================================================
Video Title   : {title}
Video File    : {dest_video_name}
Duration      : {video.duration:.1f} seconds (Ultra-viral ~25s retention length)
Niche         : 2026 Declassified Files & Military Anomalies
Date          : 2026-10-07

================================================================================
1. 🎵 TIKTOK POST DETAILS
================================================================================
CAPTION (Kopioi suoraan TikTokin kuvaukseen):
Wait until the end... The US government just unsealed Tranche 6 on war.gov and pilots are officially coming forward 👁️📁 Did you check the leaked documents yet? #shadowvault #declassified #pursue #pentagon #uap #mystery #unexplained #foryou #fyp #mindblowing

HASHTAGIT:
#fyp #foryou #shadowvault #declassified #pentagon #uap #pursue #mystery #unexplained #governmentsecrets #viral

ÄÄNISTRATEGIA (TikTok Sound Boost):
1. Videon oma ääni on nyt HOLLYWOOD-MASTEROITU (matalataajuinen 120Hz rintaresonanssi, dynaaminen kompressio ja -14 LUFS normalisointi). Pidä se 100%:ssa.
2. Etsi TikTokista jokin suosittu "creepy / military / dark suspense" trendiääni, valitse se ja säädä sen volyymi 3-5%:iin.
3. Tämä yhdistää videon heti TikTokin trendaavaan ääneen ja antaa algoritmisen FYP-boostin!

================================================================================
2. 🧠 RETENTION & INFINITE LOOP TEKNIIKKA TÄSSÄ VIDEOSSA
================================================================================
1. Kesto (~{video.duration:.1f}s): Lyhyt, armoton 25 sekunnin kesto, jossa EI OLE sekuntiakaan taustoitusta.
2. Hollywood Vocal Mastering: Kertojaääni leikattu 75Hz alapuolelta, buustattu 120Hz lämpöä ja 3.5kHz puhe-erottuvuutta sekä ajettu ammattimaisen kompressorin läpi.
3. Infinite Loop: Viimeinen lause ("Which leaves the Pentagon with only one unanswered record...")
   yhdistyy saumattomasti ilman katkoa ensimmäiseen lauseeseen ("The United States government just unsealed Tranche Six...").
   -> Tuottaa yli 100% katseluajan!
4. Visual Attention Hook Banner: Yläosan punainen [● 2026 DECLASSIFIED] pill badge ja sähkökeltaisella hehkuva
   [WAR.GOV JUST LEAKED TRANCHE 6] pysäyttää selaajan silmät 0.1 sekunnissa.
================================================================================
"""
    info_path = os.path.join(drive_dir, "2026_PURSUE_TRANCHE_6_TIKTOK_INFO.txt")
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(info_text)

    # Also save in output/
    with open(os.path.join(out_dir, "2026_PURSUE_TRANCHE_6_TIKTOK_INFO.txt"), "w", encoding="utf-8") as f:
        f.write(info_text)

    logger.info("Upload info guide written to Google Drive: %s", info_path)
    cleanup_files(temp_files)
    logger.info("SUCCESS! Full run completed.")


if __name__ == "__main__":
    asyncio.run(main())
