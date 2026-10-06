"""
shadowvault/audio.py
Stage 3 - TTS audio generation via Edge-TTS & ElevenLabs with word-level boundary synchronization.

Exposes both async and sync wrappers.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
from typing import Optional

import edge_tts
from moviepy.editor import AudioFileClip

from shadowvault.models import AudioResult, WordTiming

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_estimated_word_timings(text: str, duration: float) -> list[WordTiming]:
    """Fallback word-level alignment based on syllable/character length distribution."""
    clean_words = [re.sub(r"[^\w']", "", w) for w in text.split()]
    raw_words = text.split()
    if not raw_words or duration <= 0:
        return []

    weights = [max(1, len(w)) for w in raw_words]
    total_weight = sum(weights)
    timings: list[WordTiming] = []
    curr = 0.0

    for idx, (raw_w, weight) in enumerate(zip(raw_words, weights)):
        w_dur = (weight / total_weight) * duration
        # Add slight pause weighting after punctuation
        has_punct = raw_w.endswith((".", "!", "?", ",", ":", ";"))
        pad = 0.05 if has_punct else 0.0
        timings.append(
            WordTiming(
                word=raw_w,
                start=round(curr, 3),
                end=round(min(duration, curr + w_dur + pad), 3),
            )
        )
        curr += w_dur

    return timings


async def _synthesise(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: str,
) -> list[WordTiming]:
    """
    Synthesise speech with Edge-TTS using WordBoundary streaming.
    Saves audio file and returns exact word timings.
    Includes clean text normalization and fallback voices for 100% reliability.
    """
    clean_text = text.replace("—", ", ").replace("–", ", ").replace('"', '').strip()
    voices_to_try = [voice]
    for alt_voice in ["en-US-ChristopherNeural", "en-US-GuyNeural", "en-US-BrianNeural"]:
        if alt_voice not in voices_to_try:
            voices_to_try.append(alt_voice)

    last_exc = None
    for v_candidate in voices_to_try:
        try:
            communicate = edge_tts.Communicate(
                clean_text,
                v_candidate,
                rate=rate,
                pitch=pitch,
                boundary="WordBoundary",
            )
            word_timings: list[WordTiming] = []
            has_audio = False

            with open(output_path, "wb") as f:
                async for chunk in communicate.stream():
                    chunk_type = chunk.get("type")
                    if chunk_type == "audio":
                        data = chunk.get("data", b"")
                        if data:
                            f.write(data)
                            has_audio = True
                    elif chunk_type == "WordBoundary":
                        word = chunk.get("text", "").strip()
                        if word:
                            offset_sec = chunk.get("offset", 0) / 10_000_000.0
                            dur_sec = chunk.get("duration", 0) / 10_000_000.0
                            word_timings.append(
                                WordTiming(
                                    word=word,
                                    start=round(offset_sec, 3),
                                    end=round(offset_sec + dur_sec, 3),
                                )
                            )
            if has_audio and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info("TTS saved to %s (voice=%s, words=%d)", output_path, v_candidate, len(word_timings))
                return word_timings
        except Exception as exc:
            last_exc = exc
            logger.warning("Edge-TTS attempt with voice %s failed (%s) - trying fallback voice", v_candidate, exc)

    if last_exc:
        raise last_exc
    return []


async def _synthesise_elevenlabs(
    text: str,
    voice_id: str,
    api_key: str,
    output_path: str,
) -> None:
    import aiohttp
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key,
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }
    logger.info("Calling ElevenLabs API for TTS synthesis (voice_id=%s)", voice_id)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status != 200:
                err_text = await response.text()
                raise RuntimeError(f"ElevenLabs API failed with status {response.status}: {err_text}")
            with open(output_path, "wb") as f:
                while True:
                    chunk = await response.content.read(4096)
                    if not chunk:
                        break
                    f.write(chunk)
    logger.info("ElevenLabs TTS saved to %s", output_path)


def _measure_duration(audio_path: str) -> float:
    try:
        clip = AudioFileClip(audio_path)
        dur = clip.duration
        clip.close()
        return dur
    except Exception as exc:
        logger.warning("Could not measure audio duration: %s", exc)
        return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_audio_async(
    text: str,
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
    temp_dir: str | None = None,
) -> AudioResult:
    """
    Generate TTS audio asynchronously with word-level synchronization.

    Parameters loaded from config if not provided.
    """
    from shadowvault.config import get_config
    cfg = get_config()

    if cfg.tts_provider == "elevenlabs":
        voice = voice or cfg.elevenlabs_voice_id
    else:
        voice = voice or cfg.tts_voice

    rate = rate or cfg.tts_rate
    pitch = pitch or cfg.tts_pitch
    temp_dir = temp_dir or cfg.temp_dir

    os.makedirs(temp_dir, exist_ok=True)
    output_path = os.path.join(temp_dir, f"voice_{random.randint(10000, 99999)}.mp3")

    word_timings: list[WordTiming] = []
    try:
        if cfg.tts_provider == "elevenlabs":
            if not cfg.elevenlabs_api_key:
                raise ValueError("ELEVENLABS_API_KEY is not set in config/env")
            logger.info("Generating TTS via ElevenLabs | voice_id=%s len=%d chars", voice, len(text))
            await _synthesise_elevenlabs(text, voice, cfg.elevenlabs_api_key, output_path)
        else:
            logger.info(
                "Generating TTS via Edge-TTS | voice=%s rate=%s pitch=%s len=%d chars",
                voice, rate, pitch, len(text),
            )
            res = await _synthesise(text, voice, rate, pitch, output_path)
            if isinstance(res, list):
                word_timings = res
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        return AudioResult(audio_path="", duration=0.0, voice=voice)

    duration = _measure_duration(output_path)
    logger.info("Audio duration: %.2fs", duration)

    if not word_timings and duration > 0:
        word_timings = _generate_estimated_word_timings(text, duration)

    return AudioResult(
        audio_path=output_path,
        duration=duration,
        voice=voice,
        word_timings=word_timings,
    )


def generate_audio(
    text: str,
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
    temp_dir: str | None = None,
) -> AudioResult:
    """Synchronous wrapper around generate_audio_async."""
    return asyncio.run(
        generate_audio_async(
            text=text, voice=voice, rate=rate, pitch=pitch, temp_dir=temp_dir,
        )
    )
