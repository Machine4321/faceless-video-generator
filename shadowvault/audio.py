"""
shadowvault/audio.py
Stage 3 - TTS audio generation via Edge-TTS.

Exposes both async and sync wrappers.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random

import edge_tts
from moviepy.editor import AudioFileClip

from shadowvault.models import AudioResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _synthesise(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: str,
) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    logger.info("TTS saved to %s (voice=%s)", output_path, voice)


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
        }
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
    Generate TTS audio asynchronously.

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
            await _synthesise(text, voice, rate, pitch, output_path)
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        return AudioResult(audio_path="", duration=0.0, voice=voice)

    duration = _measure_duration(output_path)
    logger.info("Audio duration: %.2fs", duration)

    return AudioResult(audio_path=output_path, duration=duration, voice=voice)


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
