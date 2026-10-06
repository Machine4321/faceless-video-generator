"""
shadowvault/image_gen.py
AI Image Generation Engine for 100% unique cinematic scenes.

Generates custom 9:16 vertical photorealistic visuals tailored to each exact script sentence.
Uses high-performance Flux models with cinematic 35mm lighting and color science.
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from typing import Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 35

CINEMATIC_SUFFIX = (
    "cinematic 35mm film still, photorealistic documentary, dark moody atmospheric lighting, "
    "sharp focus, ultra detailed, depth of field, 8k resolution, no text, no captions"
)


def generate_ai_image(
    prompt: str,
    dest_path: str,
    width: int = 768,
    height: int = 1344,
    timeout: int = DEFAULT_TIMEOUT,
) -> bool:
    """
    Generate a 100% unique cinematic portrait image for a scene using Flux.
    Returns True if successfully downloaded and validated, False otherwise.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    clean_prompt = prompt.strip()
    if not clean_prompt:
        clean_prompt = "mysterious cinematic crime documentary scene"

    full_prompt = f"{clean_prompt}, {CINEMATIC_SUFFIX}"
    encoded = urllib.parse.quote(full_prompt)

    # Use Flux endpoint
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux"

    try:
        logger.info("Generating AI visual: %r ...", clean_prompt[:60])
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200 and len(resp.content) > 10_000:
            with open(dest_path, "wb") as f:
                f.write(resp.content)

            # Validate with PIL that it is a valid image
            with Image.open(dest_path) as img:
                img.verify()

            logger.info("AI Image generated successfully -> %s (%d bytes)", dest_path, len(resp.content))
            return True
        else:
            logger.warning("AI image generation returned status %d (size=%d)", resp.status_code, len(resp.content))
            return False
    except Exception as exc:
        logger.warning("AI image generation failed (%s) - will fallback gracefully", exc)
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return False
