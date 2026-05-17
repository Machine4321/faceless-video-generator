"""
shadowvault/content.py
Stage 1 - Content Generation via Google Gemini.

Supports niches: horror, motivation, facts.
Falls back to hardcoded content when the API is unavailable.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any

from shadowvault.models import ContentResult
from shadowvault.utils.text_utils import clean_text, strip_json_fences

logger = logging.getLogger(__name__)

# Word-count targets per length
WORD_COUNTS: dict[str, int] = {
    "short": 65,
    "long": 130,
}

# ---------------------------------------------------------------------------
# Niche configuration
# ---------------------------------------------------------------------------

NICHE_CONFIG: dict[str, dict[str, Any]] = {
    "horror": {
        "hooks": [
            "This is a true story that will keep you awake.",
            "Scientists cannot explain this phenomenon.",
            "Never search for this website on the dark web.",
            "If you hear this sound at night, do not open your eyes.",
            "This is the most disturbing fact about the ocean.",
            "People who visited this place never came back.",
            "Start with a forbidden fact that 'they' don't want us to know.",
            "Start with a direct threat or warning to the viewer.",
            "Start with a terrifying question about the viewer's current surroundings.",
            "Start with a bone-chilling 'true' archive record summary.",
        ],
        "style": (
            "You are a viral horror content creator for YouTube Shorts and TikTok. "
            "Write terrifying, mystery-driven scripts with escalating tension and a "
            "shocking final line. Never break the fourth wall with meta-commentary."
        ),
        "fallback": ContentResult(
            title="THEY ARE WATCHING YOU RIGHT NOW",
            script=(
                "Don't look behind you. The shadows in your room shift when you blink. "
                "Three people reported seeing a figure standing in the corner of their "
                "bedroom for weeks before they disappeared. Authorities found their homes "
                "perfectly clean. No signs of struggle. Just one detail that matched every "
                "case: every mirror in the house had been turned to face the wall."
            ),
            visual_search_keyword="horror",
            tags="#shorts #horror #scary #mystery #creepypasta #fyp #viral #darkfacts",
            niche="horror",
            hook="Don't look behind you.",
        ),
    },
    "motivation": {
        "hooks": [
            "Nobody will tell you this, but here is the truth.",
            "The most successful people on earth share one secret.",
            "If you feel lost right now, watch this.",
            "One habit separates winners from everyone else.",
            "Most people waste the first hour of their day. Here is why that matters.",
        ],
        "style": (
            "You are a high-energy motivational content creator. "
            "Write punchy, direct scripts that challenge the viewer and end with a "
            "powerful call to action. Use second-person ('you') throughout."
        ),
        "fallback": ContentResult(
            title="THE ONE HABIT THAT WILL CHANGE YOUR LIFE",
            script=(
                "Nobody will tell you this. Discipline is not something you feel. "
                "It is something you build, brick by brick, on the days you least want "
                "to show up. Every person you admire was once sitting exactly where "
                "you are right now. The only difference between them and you is that "
                "they chose to start. Today is your day to start."
            ),
            visual_search_keyword="sunrise gym workout",
            tags="#shorts #motivation #mindset #success #fyp #viral",
            niche="motivation",
            hook="Nobody will tell you this.",
        ),
    },
    "facts": {
        "hooks": [
            "You were never taught this in school.",
            "This fact will completely change how you see the world.",
            "Scientists discovered something that defies all logic.",
            "The government tried to hide this for decades.",
            "This happens to every human being, but nobody talks about it.",
        ],
        "style": (
            "You are a fact-based content creator focused on mind-blowing, "
            "counter-intuitive, or deeply unsettling true facts. "
            "Keep the tone authoritative and the pacing fast. End with a twist."
        ),
        "fallback": ContentResult(
            title="THE FACT THEY DON'T WANT YOU TO KNOW",
            script=(
                "You were never taught this in school. The human brain cannot "
                "distinguish between a vivid memory and a real event. Every memory "
                "you have has been silently rewritten each time you recalled it. "
                "The person you think you were five years ago? That version of you "
                "was quietly edited out of your own mind."
            ),
            visual_search_keyword="human brain neuron",
            tags="#shorts #facts #mindblown #science #fyp #viral #didyouknow",
            niche="facts",
            hook="You were never taught this in school.",
        ),
    },
}

DEFAULT_NICHE: str = "horror"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pick_hook(niche: str) -> str:
    cfg = NICHE_CONFIG.get(niche, NICHE_CONFIG[DEFAULT_NICHE])
    return random.choice(cfg["hooks"])


def _build_prompt(niche: str, hook: str, length: str = "short") -> str:
    cfg = NICHE_CONFIG.get(niche, NICHE_CONFIG[DEFAULT_NICHE])
    word_count = WORD_COUNTS.get(length, WORD_COUNTS["short"])

    return f"""\
{cfg['style']}

TASK:
1. Write a script that starts with: "{hook}"
   The script must be approximately {word_count} words.
   Story structure rules:
   - First sentence is a powerful hook (already given above).
   - Build tension continuously.
   - Keep the reveal hidden until the very last sentence.
   - The final sentence must be the most impactful line.
   - Do NOT summarize or add "THE END" or any meta-commentary.

2. Write a short, ALL-CAPS clickbait title (under 10 words).
3. Provide exactly ONE English keyword for a background video (e.g. "foggy forest").
4. Provide 10-15 viral hashtags for the niche.

RESPOND ONLY with valid JSON in this exact structure (no markdown fences):
{{
  "title": "...",
  "script": "...",
  "visual_search": "...",
  "tags": "..."
}}"""


def _parse_response(raw: str, niche: str, hook: str) -> ContentResult:
    """Parse Gemini JSON response into a ContentResult."""
    clean = strip_json_fences(raw)
    data = json.loads(clean)

    required = {"title", "script", "visual_search", "tags"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Gemini response missing keys: {missing}")

    return ContentResult(
        title=clean_text(data["title"]),
        script=clean_text(data["script"]),
        visual_search_keyword=clean_text(data["visual_search"]).split()[0],
        tags=clean_text(data["tags"]),
        niche=niche,
        hook=hook,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_content(
    niche: str = DEFAULT_NICHE,
    length: str = "short",
    api_key: str | None = None,
    model: str | None = None,
) -> ContentResult:
    """
    Generate a short-form video script via Google Gemini.

    Parameters
    ----------
    niche   : "horror", "motivation", or "facts"
    length  : "short" (~65 words) or "long" (~130 words)
    api_key : Gemini API key (loaded from config if None)
    model   : Gemini model name (loaded from config if None)

    Returns
    -------
    ContentResult. Falls back to hardcoded content on API failure.
    """
    if api_key is None or model is None:
        from shadowvault.config import get_config
        cfg = get_config()
        api_key = api_key or cfg.gemini_api_key
        model = model or cfg.gemini_model

    niche = niche if niche in NICHE_CONFIG else DEFAULT_NICHE
    hook = _pick_hook(niche)

    logger.info("Generating content | niche=%s length=%s", niche, length)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(niche, hook, length)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        raw_text: str = response.text
        logger.debug("Gemini raw response: %s", raw_text[:200])

        result = _parse_response(raw_text, niche, hook)
        logger.info("Content generated: title=%r", result.title)
        return result

    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned invalid JSON (%s) - using fallback", exc)
    except Exception as exc:
        logger.warning("Gemini API error (%s) - using fallback", exc)

    fallback = NICHE_CONFIG[niche]["fallback"]
    logger.info("Using fallback content for niche=%s", niche)
    return fallback
