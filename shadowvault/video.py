"""
shadowvault/video.py
Stage 4 - Video Composition.

PIL-based text rendering (no ImageMagick dependency).
Assembles background video + voice-over + subtitles + watermark + optional music.
Output: 1080x1920 (9:16) MP4.
"""

from __future__ import annotations

import logging
import os
import random
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    vfx,
)

from shadowvault.models import AudioResult, MediaResult, VideoResult
from shadowvault.utils.text_utils import chunk_words

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PIL rendering helpers
# ---------------------------------------------------------------------------

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["arialbd.ttf", r"C:\Windows\Fonts\arialbd.ttf"] if bold
        else ["arial.ttf", r"C:\Windows\Fonts\arial.ttf"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue
    logger.warning("Arial font not found - using PIL default")
    return ImageFont.load_default()


def _render_subtitle_frame(
    text: str,
    canvas_w: int,
    canvas_h: int,
    font_size: int = 80,
    font_color: tuple = (255, 221, 0),
    stroke_color: tuple = (0, 0, 0),
    stroke_width: int = 4,
    bg_color: tuple = (0, 0, 0, 160),
) -> np.ndarray:
    """Render a single subtitle chunk to a numpy RGBA array."""
    import textwrap

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size, bold=True)

    wrapped = textwrap.fill(text, width=14)
    bbox = draw.textbbox((0, 0), wrapped, font=font, stroke_width=stroke_width)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad_x, pad_y = 30, 20
    box_x0 = (canvas_w - text_w) // 2 - pad_x
    box_y0 = (canvas_h - text_h) // 2 - pad_y
    box_x1 = (canvas_w + text_w) // 2 + pad_x
    box_y1 = (canvas_h + text_h) // 2 + pad_y

    draw.rectangle([box_x0, box_y0, box_x1, box_y1], fill=bg_color)
    draw.multiline_text(
        (canvas_w // 2, canvas_h // 2),
        wrapped,
        font=font,
        fill=font_color,
        anchor="mm",
        align="center",
        stroke_width=stroke_width,
        stroke_fill=stroke_color,
    )
    return np.array(img)


def _render_watermark_frame(
    width: int,
    height: int,
    handle: str = "@The_ShadowVaultOfficial",
    font_size: int = 38,
    font_color: tuple = (255, 255, 255, 160),
    position_y: int = 1800,
) -> np.ndarray:
    """Render channel watermark to numpy RGBA array."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size, bold=False)
    draw.text(
        (width // 2, position_y),
        handle,
        font=font,
        fill=font_color,
        anchor="mm",
    )
    return np.array(img)


# ---------------------------------------------------------------------------
# Subtitle clip builder
# ---------------------------------------------------------------------------

def _build_subtitle_clips(
    script: str,
    audio_duration: float,
    output_width: int,
    words_per_chunk: int = 4,
    sub_canvas_h: int = 480,
    sub_position_y: int = 820,
) -> list[ImageClip]:
    chunks = chunk_words(script, words_per_chunk)
    if not chunks:
        return []

    usable_duration = max(audio_duration - 0.5, audio_duration * 0.95)
    chunk_dur = usable_duration / len(chunks)

    clips: list[ImageClip] = []
    for idx, chunk in enumerate(chunks):
        try:
            frame = _render_subtitle_frame(chunk.upper(), output_width, sub_canvas_h)
            clip = (
                ImageClip(frame)
                .set_start(idx * chunk_dur)
                .set_duration(chunk_dur)
                .set_position(("center", sub_position_y))
            )
            clips.append(clip)
        except Exception as exc:
            logger.warning("Failed to render subtitle chunk %d: %s", idx, exc)

    return clips


# ---------------------------------------------------------------------------
# Audio mixer
# ---------------------------------------------------------------------------

def _mix_audio(
    voice_clip: AudioFileClip,
    total_duration: float,
    music_folder: str,
    bg_music_volume: float,
) -> CompositeAudioClip | AudioFileClip:
    if not music_folder or not os.path.isdir(music_folder):
        return voice_clip

    music_files = [
        f for f in os.listdir(music_folder)
        if f.lower().endswith((".mp3", ".wav", ".ogg"))
    ]
    if not music_files:
        return voice_clip

    music_path = os.path.join(music_folder, random.choice(music_files))
    try:
        music_clip = AudioFileClip(music_path).volumex(bg_music_volume)
        if music_clip.duration < total_duration:
            music_clip = music_clip.audio_loop(duration=total_duration)
        music_clip = music_clip.subclip(0, total_duration)
        logger.info("Mixed background music: %s", os.path.basename(music_path))
        return CompositeAudioClip([voice_clip, music_clip])
    except Exception as exc:
        logger.warning("Music mixing failed (%s) - voice only", exc)
        return voice_clip


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_video(
    media: MediaResult,
    audio: AudioResult,
    script: str,
    title: str,
    output_folder: str | None = None,
    music_folder: str | None = None,
    fps: int | None = None,
    codec: str | None = None,
    preset: str | None = None,
    bg_music_volume: float | None = None,
    trail_seconds: float | None = None,
    output_width: int | None = None,
    output_height: int | None = None,
    ffmpeg_path: str | None = None,
) -> VideoResult:
    """
    Compose the final YouTube Short from all fetched assets.

    All settings loaded from config if not explicitly provided.
    """
    from shadowvault.config import get_config
    cfg = get_config()

    output_folder = output_folder or cfg.output_folder
    music_folder = music_folder or cfg.music_folder
    fps = fps if fps is not None else cfg.fps
    codec = codec or cfg.codec
    preset = preset or cfg.preset
    bg_music_volume = bg_music_volume if bg_music_volume is not None else cfg.bg_music_volume
    trail_seconds = trail_seconds if trail_seconds is not None else cfg.trail_seconds
    output_width = output_width if output_width is not None else cfg.output_width
    output_height = output_height if output_height is not None else cfg.output_height
    ffmpeg_path = ffmpeg_path or cfg.ffmpeg_path

    # Configure ffmpeg path if specified
    if ffmpeg_path:
        from moviepy.config import change_settings
        change_settings({"FFMPEG_BINARY": ffmpeg_path})

    os.makedirs(output_folder, exist_ok=True)

    vid_id = random.randint(10000, 99999)
    output_path = os.path.join(output_folder, f"ShadowVault_{vid_id}.mp4")

    # 1. Background video
    total_duration = audio.duration + trail_seconds

    if media.video_path and os.path.isfile(media.video_path):
        logger.info("Loading background video: %s", media.video_path)
        bg = VideoFileClip(media.video_path)

        if bg.h < output_height:
            bg = bg.resize(height=output_height)
        if bg.w > output_width:
            x1 = (bg.w - output_width) / 2
            bg = bg.crop(x1=x1, width=output_width, height=output_height)
        if bg.duration < total_duration:
            bg = vfx.loop(bg, duration=total_duration)
        bg = bg.subclip(0, total_duration)
    else:
        logger.warning("No background video - using black ColorClip")
        bg = ColorClip(
            size=(output_width, output_height),
            color=(0, 0, 0),
            duration=total_duration,
        )

    # 2. Voice-over audio
    if not audio.audio_path or not os.path.isfile(audio.audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio.audio_path}")

    voice_clip = AudioFileClip(audio.audio_path)

    # 3. Mix with background music
    final_audio = _mix_audio(voice_clip, total_duration, music_folder, bg_music_volume)
    bg = bg.set_audio(final_audio)

    # 4. Subtitle overlays
    subtitle_clips = _build_subtitle_clips(script, audio.duration, output_width)
    logger.info("Created %d subtitle chunks", len(subtitle_clips))

    # 5. Watermark
    overlay_clips: list = subtitle_clips
    try:
        wm_frame = _render_watermark_frame(output_width, output_height)
        watermark_clip = (
            ImageClip(wm_frame)
            .set_duration(total_duration)
            .set_position((0, 0))
        )
        overlay_clips = subtitle_clips + [watermark_clip]
    except Exception as exc:
        logger.warning("Watermark creation failed: %s", exc)

    # 6. Compose & render
    final = CompositeVideoClip([bg] + overlay_clips)

    logger.info(
        "Rendering -> %s  (%.1fs, %dx%d, fps=%d, preset=%s)",
        output_path, total_duration, output_width, output_height, fps, preset,
    )

    final.write_videofile(
        output_path,
        fps=fps,
        codec=codec,
        audio_codec=cfg.audio_codec,
        preset=preset,
        threads=4,
        logger=None,
    )

    # Cleanup MoviePy handles
    try:
        bg.close()
        voice_clip.close()
        final.close()
    except Exception:
        pass

    logger.info("Render complete: %s", output_path)

    return VideoResult(
        video_path=output_path,
        duration=total_duration,
        width=output_width,
        height=output_height,
    )
