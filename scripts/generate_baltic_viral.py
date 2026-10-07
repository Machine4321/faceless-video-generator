"""
scripts/generate_baltic_viral.py
Master generator for the 2026 Baltic Sea Anomaly viral video.
Engineered for maximum 25s retention, infinite loop structure,
high-contrast hook banner, and verified cinematic visual assets.
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
from shadowvault.models import ContentResult, ScenePlan, PipelineRun
from shadowvault import media as media_stage
from shadowvault import audio as audio_stage
from shadowvault import video as video_stage
from shadowvault.utils.file_manager import cleanup_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("baltic_viral_master")


async def main():
    cfg = get_config()
    run_id = random.randint(10000, 99999)
    temp_dir = cfg.temp_dir
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(cfg.output_folder, exist_ok=True)

    title = "2026 DECLASSIFIED: THE BALTIC SEA ANOMALY"
    hook_header = "BALTIC SEA ANOMALY 90M DOWN"
    hook_category = "2026 DECLASSIFIED"
    tags = "#shorts #mystery #balticsea #unexplained #ocean #anomaly #declassified #deepsea #fyp #viral"

    scenes = [
        ScenePlan(
            scene_id=1,
            narration="Deep beneath the Baltic Sea, sonar just detected an object that should not exist.",
            visual_query="cinematic 35mm archival underwater photograph of massive circular stone structure on dark murky Baltic seabed, glowing sonar scan beam, high contrast dramatic lighting",
            sfx_cue="impact",
            visual_format="ai_image",
        ),
        ScenePlan(
            scene_id=2,
            narration="Ninety meters down between Sweden and Finland, lies an artificial sixty-meter circular disk.",
            visual_query="BALTIC SEABED SONAR 55N 19E TARGET LOCK",
            sfx_cue="radar_ping",
            visual_format="radar",
        ),
        ScenePlan(
            scene_id=3,
            narration="Robotic drones revealed smooth ninety-degree corridors and staircase formations carved into the stone.",
            visual_query="underwater ROV robotic submarine with bright headlights illuminating 90-degree right-angle stone corridor on ocean floor, murky cold water",
            sfx_cue="whoosh",
            visual_format="ai_image",
        ),
        ScenePlan(
            scene_id=4,
            narration="Within two hundred meters, all compasses spin out of control and electronic signals completely die.",
            visual_query="TOP SECRET NAVAL EXPEDITION REPORT ELECTROMAGNETIC BLACKOUT BALTIC ANOMALY",
            sfx_cue="stamp_thud",
            visual_format="dossier",
        ),
        ScenePlan(
            scene_id=5,
            narration="New 2026 sub-bottom sonar confirmed the sixty-meter disk is not bedrock, but rests directly on top of sediment.",
            visual_query="60 meters diameter recorded object",
            sfx_cue="ticker",
            visual_format="counter",
        ),
        ScenePlan(
            scene_id=6,
            narration="Which leaves researchers with only one terrifying reality...",
            visual_query="cinematic macro shot of spinning brass compass needle underwater near dark glowing monolith, extreme depth of field",
            sfx_cue="suspense_drone",
            visual_format="ai_image",
        ),
    ]

    full_script = " ".join(s.narration for s in scenes)

    content = ContentResult(
        title=title,
        script=full_script,
        visual_search_keyword="baltic sea underwater anomaly",
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
    logger.info("Word Count  : %d words (~25-27s)", len(full_script.split()))
    logger.info("Full Script : %s", full_script)

    temp_files: list[str] = []

    # Step 2: Sourcing visual media with Vision Critic validation
    logger.info("=== STEP 2: SOURCING HIGH-RES VISUAL MEDIA ===")
    media = media_stage.fetch_multi_scene_media(
        content.scenes,
        primary_query="baltic sea deep ocean sonar anomaly",
    )
    for sc in getattr(media, "scenes_media", []):
        if sc.get("path"):
            temp_files.append(sc["path"])
            logger.info("Scene %d [%s] -> %s (%s)", sc.get("scene_id"), sc.get("visual_format"), sc.get("path"), sc.get("source_desc", "")[:60])

    # Step 3: TTS Audio Synthesis with Edge-TTS (Brian, +8% rate)
    logger.info("=== STEP 3: TTS AUDIO SYNTHESIS ===")
    audio = await audio_stage.generate_audio_async(
        text=content.script,
        voice="en-US-BrianMultilingualNeural",
        rate="+8%",
    )
    if audio.audio_path:
        temp_files.append(audio.audio_path)
    logger.info("Audio synthesized: %s (Duration: %.2fs)", audio.audio_path, audio.duration)

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
    f1 = os.path.join(out_dir, "baltic_frame_1s.jpg")
    f4 = os.path.join(out_dir, "baltic_frame_4s.jpg")
    f8 = os.path.join(out_dir, "baltic_frame_8s.jpg")
    f15 = os.path.join(out_dir, "baltic_frame_15s.jpg")
    f22 = os.path.join(out_dir, "baltic_frame_22s.jpg")

    for ss, dest in [("00:00:01.000", f1), ("00:00:04.000", f4), ("00:00:08.500", f8), ("00:00:15.000", f15), ("00:00:22.000", f22)]:
        cmd = ["ffmpeg", "-y", "-ss", ss, "-i", video.video_path, "-vframes", "1", dest]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info("Extracted inspection frames to %s", out_dir)

    # Step 6: Create TikTok Upload Guide & Metadata
    drive_dir = r"G:\My Drive\tiktok"
    os.makedirs(drive_dir, exist_ok=True)

    dest_video_name = "2026_DECLASSIFIED_THE_BALTIC_SEA_ANOMALY.mp4"
    dest_video_path = os.path.join(drive_dir, dest_video_name)
    shutil.copy2(video.video_path, dest_video_path)
    logger.info("Copied video to Google Drive: %s", dest_video_path)

    # Copy Hook Preview
    shutil.copy2(f1, os.path.join(drive_dir, "2026_BALTIC_ANOMALY_HOOK_PREVIEW.jpg"))

    # Write TikTok upload info
    info_text = f"""================================================================================
📱 TIKTOK & SHORTS UPLOAD INFO - THE SHADOW VAULT
================================================================================
Video Title   : {title}
Video File    : {dest_video_name}
Duration      : {video.duration:.1f} seconds (Optimal 25s viral sweet spot)
Niche         : Deep Sea Anomalies & Declassified Secrets
Date          : 2026-10-07

================================================================================
1. 🎵 TIKTOK POST DETAILS
================================================================================
CAPTION (Kopioi suoraan TikTokin kuvaukseen):
Wait until the end... Deep beneath the Baltic Sea, 2026 sonar just confirmed what this 60-meter disk actually is 👁️🌊 What do you believe is down there? #shadowvault #balticsea #unexplained #deepsea #oceanmystery #anomaly #declassified #fyp #foryou #mindblowing

HASHTAGIT:
#fyp #foryou #shadowvault #balticsea #deepsea #oceanmystery #anomaly #declassified #glitchinthematrix #didyouknow #viral

ÄÄNISTRATEGIA (TikTok Sound Boost):
1. Pidä videon oma ääni 100%:ssa (elokuvamainen kertoja, sub-bass startle ja taktinen tutkaääni).
2. Etsi TikTokista jokin suosittu "creepy / deep sea / suspense" trendiääni, valitse se ja säädä sen voimakkuudeksi 3-5%.
3. Tämä yhdistää videon heti TikTokin ääni-algoritmiin ja nostaa FYP-jakelua!

================================================================================
2. 🧠 RETENTION & INFINITE LOOP TEKNIIKKA TÄSSÄ VIDEOSSA
================================================================================
1. Kesto (~25s): 25 sekunnin videolla jokainen 18 sekuntia katsonut tuottaa huikean ~75% retention!
2. Infinite Loop: Videon viimeinen lause ("Which leaves researchers with only one terrifying reality...")
   jatkuu saumattomasti ilman katkoa ensimmäiseen lauseeseen ("Deep beneath the Baltic Sea...").
   -> Katsoja katsoo videon huomaamattaan kahdesti, mikä nostaa watch timen yli 100%:iin!
3. Visual Attention Hook Banner: Yläkolmanneksen [● 2026 DECLASSIFIED] badge ja hehkuva [BALTIC SEA ANOMALY 90M DOWN]
   pysäyttää selaajan sormen heti alle 0.4 sekunnissa ilman ääntäkin.
4. Kinetic Punch-Zoom: Ensimmäinen sekunti tekee aggressiivisen eteenpäin-zoomauksen pimeään Itämeren syvyyteen.
5. Acoustic Startle: Tasan 0.0s käynnistyy matalataajuinen sub-bass isku.
================================================================================
"""
    info_path = os.path.join(drive_dir, "2026_BALTIC_ANOMALY_TIKTOK_INFO.txt")
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(info_text)

    # Also save in output/
    with open(os.path.join(out_dir, "2026_BALTIC_ANOMALY_TIKTOK_INFO.txt"), "w", encoding="utf-8") as f:
        f.write(info_text)

    logger.info("Upload info guide written to Google Drive: %s", info_path)
    cleanup_files(temp_files)
    logger.info("SUCCESS! Full run completed.")


if __name__ == "__main__":
    asyncio.run(main())
