"""
shadowvault/utils/sfx_generator.py
Procedural studio-quality sound effects generator using numpy and wave.

Generates royalty-free, zero-dependency sound effects for transitions and impact:
- whoosh.wav    : Fast cinematic swoosh for scene cuts
- impact.wav    : Deep cinematic sub-bass impact for plot reveals
- cash.wav      : Crisp cash-register / bell chime for money and numbers
- glitch.wav    : Digital glitch / tension buzz
- heartbeat.wav : Low-frequency suspense heartbeat
"""

from __future__ import annotations

import logging
import math
import os
import struct
import wave
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100


def _save_wav(filename: str, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Save normalized numpy float array (-1.0 to 1.0) as 16-bit PCM WAV."""
    audio = np.clip(audio, -1.0, 1.0)
    int_audio = (audio * 32767).astype(np.int16)

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(int_audio.tobytes())


def generate_whoosh(duration: float = 0.45) -> np.ndarray:
    """Generate a clean cinematic whoosh / swoosh using shaped noise and pitch sweep."""
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # Bell envelope centered at 45% of duration
    peak = duration * 0.45
    env = np.exp(-((t - peak) ** 2) / (2 * (0.12 ** 2)))

    # Noise base
    noise = np.random.uniform(-1, 1, n_samples)

    # Modulating sweep (sine sweep 180Hz -> 850Hz -> 120Hz)
    freq = 180 + 670 * np.sin(np.pi * t / duration)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    tone = np.sin(phase)

    audio = (0.65 * noise + 0.35 * tone) * env
    # Smooth fade out at edges
    fade_len = int(SAMPLE_RATE * 0.02)
    audio[:fade_len] *= np.linspace(0, 1, fade_len)
    audio[-fade_len:] *= np.linspace(1, 0, fade_len)

    max_val = np.max(np.abs(audio)) or 1.0
    return audio / max_val * 0.85


def generate_impact(duration: float = 1.2) -> np.ndarray:
    """Generate a deep cinematic sub-bass impact / boom."""
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # Pitch drops rapidly from 120Hz down to 35Hz
    freq = 35 + 85 * np.exp(-t * 8)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sub = np.sin(phase)

    # Initial transient click/hit (first 25ms)
    hit_samples = int(SAMPLE_RATE * 0.025)
    hit_noise = np.zeros(n_samples)
    hit_noise[:hit_samples] = np.random.uniform(-1, 1, hit_samples) * np.linspace(1, 0, hit_samples)

    # Exponential decay envelope
    decay = np.exp(-t * 3.2)
    audio = (sub * 0.85 + hit_noise * 0.15) * decay

    max_val = np.max(np.abs(audio)) or 1.0
    return audio / max_val * 0.95


def generate_cash(duration: float = 0.55) -> np.ndarray:
    """Generate a crisp chime / cash register tone."""
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # Dual ringing bells (2400 Hz and 3180 Hz)
    f1, f2 = 2400.0, 3180.0
    chime = 0.6 * np.sin(2 * np.pi * f1 * t) + 0.4 * np.sin(2 * np.pi * f2 * t)

    # Quick secondary tick at 0.08s
    tick_delay = int(SAMPLE_RATE * 0.07)
    tick = np.zeros(n_samples)
    if tick_delay < n_samples:
        t_rem = t[tick_delay:]
        tick[tick_delay:] = 0.5 * np.sin(2 * np.pi * 3800 * (t_rem - t_rem[0])) * np.exp(-(t_rem - t_rem[0]) * 15)

    decay = np.exp(-t * 7.5)
    audio = chime * decay + tick

    max_val = np.max(np.abs(audio)) or 1.0
    return audio / max_val * 0.85


def generate_glitch(duration: float = 0.35) -> np.ndarray:
    """Generate a digital glitch / static tape sound."""
    n_samples = int(SAMPLE_RATE * duration)
    audio = np.random.uniform(-1, 1, n_samples)

    # Stutter modulation
    mod = np.sin(2 * np.pi * 40 * np.linspace(0, duration, n_samples))
    mod = np.where(mod > 0.2, 1.0, 0.05)
    audio *= mod

    # Low bit-depth crush emulation
    audio = np.round(audio * 8) / 8.0

    max_val = np.max(np.abs(audio)) or 1.0
    return audio / max_val * 0.75


def generate_heartbeat(duration: float = 0.85) -> np.ndarray:
    """Generate a suspenseful double-thump heartbeat."""
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    audio = np.zeros(n_samples)

    # First thump (lub) at t = 0
    t1 = t[t < 0.35]
    thump1 = np.sin(2 * np.pi * 55 * t1) * np.exp(-t1 * 14)
    audio[:len(t1)] += thump1 * 0.9

    # Second thump (dub) at t = 0.22s
    start2 = int(SAMPLE_RATE * 0.22)
    end2 = min(n_samples, start2 + int(SAMPLE_RATE * 0.35))
    t2 = np.linspace(0, 0.35, end2 - start2, endpoint=False)
    thump2 = np.sin(2 * np.pi * 48 * t2) * np.exp(-t2 * 16)
    audio[start2:end2] += thump2 * 0.7

    max_val = np.max(np.abs(audio)) or 1.0
    return audio / max_val * 0.9


def ensure_default_sfx(sfx_dir: str) -> dict[str, str]:
    """
    Ensure all standard sound effects exist in sfx_dir.
    Generates missing WAV files procedurally. Returns dict mapping sfx_name -> filepath.
    """
    os.makedirs(sfx_dir, exist_ok=True)
    generators = {
        "whoosh": generate_whoosh,
        "impact": generate_impact,
        "cash": generate_cash,
        "glitch": generate_glitch,
        "heartbeat": generate_heartbeat,
    }

    sfx_paths: dict[str, str] = {}
    for name, gen_fn in generators.items():
        path = os.path.join(sfx_dir, f"{name}.wav")
        if not os.path.isfile(path) or os.path.getsize(path) < 100:
            logger.info("Generating procedural SFX: %s -> %s", name, path)
            audio = gen_fn()
            _save_wav(path, audio)
        sfx_paths[name] = path

    return sfx_paths
