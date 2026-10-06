"""
shadowvault/content.py
Stage 1 - Viral Content Generation via Google Gemini with Multi-Scene Planning.

Supports niches:
- heists          : Legendary robberies, scams, and masterminds.
- glitches        : Bizarre anomalies and glitches in history.
- business        : Ruthless corporate moves and marketing genius.
- dark_psychology : Mind games, FBI interrogation tricks, psychological paradoxes.
- horror          : Chilling true mysteries and forbidden archives.
- motivation      : Relentless discipline and high-energy drive.
- facts           : Unbelievable scientific and historical truths.

Falls back gracefully to rich multi-scene presets when API is unavailable.
"""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any

from shadowvault.models import ContentResult, ScenePlan, TrendingTopic
from shadowvault.utils.text_utils import clean_text, strip_json_fences

logger = logging.getLogger(__name__)

# Word-count targets per length
WORD_COUNTS: dict[str, int] = {
    "short": 65,
    "long": 130,
}

# ---------------------------------------------------------------------------
# Niche configuration & Multi-Scene Fallbacks
# ---------------------------------------------------------------------------

NICHE_CONFIG: dict[str, dict[str, Any]] = {
    "heists": {
        "hooks": [
            "He stole $100M from a vault... using only an apple and hairspray.",
            "This man sold the Eiffel Tower twice, and police never caught him.",
            "The greatest diamond heist in history was solved because of a sandwich.",
            "He robbed 20 banks without holding a single weapon.",
        ],
        "style": (
            "You are a master viral storyteller for YouTube Shorts and TikTok. "
            "Write fast-paced, high-stakes heist and scam breakdowns. "
            "Focus on the unbelievable flaw in security, the clever trick, and the absurd detail that exposed them."
        ),
        "fallback": ContentResult(
            title="THE $100M DIAMOND HEIST SOLVED BY A SANDWICH",
            script=(
                "In 2003, an Italian thief bypassed ten layers of vault security in Antwerp to steal one hundred million dollars in diamonds. "
                "He used hairspray to blind heat sensors and magnetic tape to trick infrared beams. "
                "The vault was impenetrable, yet he left without triggering a single alarm. "
                "Detectives were completely baffled until they searched the highway nearby. "
                "His accomplice had discarded a half-eaten salami sandwich with his DNA on the crust. "
                "One hundred million dollars vanished forever, all undone by a single bite."
            ),
            visual_search_keyword="diamonds vault heist",
            tags="#shorts #heist #truestory #crime #mystery #history #viral",
            niche="heists",
            hook="The greatest diamond heist in history was solved because of a sandwich.",
            scenes=[
                ScenePlan(1, "In 2003, an Italian thief bypassed ten layers of vault security in Antwerp to steal one hundred million dollars in diamonds.", "bank vault security dark diamonds", "impact"),
                ScenePlan(2, "He used hairspray to blind heat sensors and magnetic tape to trick infrared beams.", "laser alarm security camera cinematic", "whoosh"),
                ScenePlan(3, "The vault was impenetrable, yet he left without triggering a single alarm.", "dark vault door open empty safe", "whoosh"),
                ScenePlan(4, "Detectives were completely baffled until they searched the highway nearby.", "police investigation flashing lights crime scene", "glitch"),
                ScenePlan(5, "His accomplice had discarded a half-eaten salami sandwich with his DNA on the crust.", "dna evidence forensics laboratory macro", "whoosh"),
                ScenePlan(6, "One hundred million dollars vanished forever, all undone by a single bite.", "cash falling dark luxury slow motion", "cash"),
            ],
        ),
    },
    "glitches": {
        "hooks": [
            "In 1518, an entire city started dancing until they dropped dead.",
            "In World War Two, the US military deployed an army made entirely of rubber.",
            "An island remained on world maps for 120 years before anyone realized it didn't exist.",
        ],
        "style": (
            "You are a creator exploring surreal, unbelievable historical glitches and anomalies. "
            "Keep the delivery punchy, authoritative, and gripping."
        ),
        "fallback": ContentResult(
            title="THE HISTORICAL GLITCH NOBODY CAN EXPLAIN",
            script=(
                "In July 1518, a woman stepped into a town square in France and began violently dancing. "
                "Within days, hundreds of people joined her, unable to stop. "
                "Doctors prescribed more dancing, claiming it would cure the fever. "
                "Dozens died of exhaustion and heart attacks right in front of onlookers. "
                "To this day, modern science cannot fully explain the dancing plague."
            ),
            visual_search_keyword="ancient city fog mystery",
            tags="#shorts #history #glitches #mystery #creepyfacts #viral",
            niche="glitches",
            hook="In 1518, an entire city started dancing until they dropped dead.",
            scenes=[
                ScenePlan(1, "In July 1518, a woman stepped into a town square in France and began violently dancing.", "medieval town cobblestone dramatic fog", "impact"),
                ScenePlan(2, "Within days, hundreds of people joined her, unable to stop.", "crowd mysterious movement shadows silhouette", "whoosh"),
                ScenePlan(3, "Doctors prescribed more dancing, claiming it would cure the fever.", "old parchment medical vintage archival", "whoosh"),
                ScenePlan(4, "Dozens died of exhaustion and heart attacks right in front of onlookers.", "dramatic dark hospital vintage horror", "heartbeat"),
                ScenePlan(5, "To this day, modern science cannot fully explain the dancing plague.", "ancient dusty library old books candle", "glitch"),
            ],
        ),
    },
    "business": {
        "hooks": [
            "Red Bull conquered the world by filling trash cans with empty cans.",
            "Blockbuster laughed Netflix out of the boardroom in 2000.",
            "Ferrari insulted a tractor mechanic, accidentally creating Lamborghini.",
        ],
        "style": (
            "You are a viral business and psychology analyst. "
            "Expose the counter-intuitive power moves and brutal rivalries that built billion-dollar empires."
        ),
        "fallback": ContentResult(
            title="HOW RED BULL TRICKED THE ENTIRE WORLD",
            script=(
                "When Red Bull first launched, absolutely nobody wanted to drink it. "
                "Competitors had millions in advertising, while Red Bull was on the brink of bankruptcy. "
                "So the founder did something insane: he filled London trash cans with empty Red Bull cans. "
                "People saw overflowing bins outside nightclubs and assumed everyone was drinking it. "
                "Demand exploded overnight. Today, Red Bull sells over twelve billion cans a year."
            ),
            visual_search_keyword="nightclub luxury city neon",
            tags="#shorts #business #marketing #money #success #wealth #billionaire",
            niche="business",
            hook="Red Bull conquered the world by filling trash cans with empty cans.",
            scenes=[
                ScenePlan(1, "When Red Bull first launched, absolutely nobody wanted to drink it.", "empty street night rain dramatic", "impact"),
                ScenePlan(2, "Competitors had millions in advertising, while Red Bull was on the brink of bankruptcy.", "corporate boardroom glass skyscraper", "whoosh"),
                ScenePlan(3, "So the founder did something insane: he filled London trash cans with empty Red Bull cans.", "nightclub neon lights crowd city party", "whoosh"),
                ScenePlan(4, "People saw overflowing bins outside nightclubs and assumed everyone was drinking it.", "busy street pedestrians urban time lapse", "cash"),
                ScenePlan(5, "Demand exploded overnight. Today, Red Bull sells over twelve billion cans a year.", "sports car speed champion race luxury", "cash"),
            ],
        ),
    },
    "dark_psychology": {
        "hooks": [
            "If someone insults you, pause and whisper this single sentence.",
            "FBI interrogators use this 3-second silence to make anyone confess.",
            "The smartest people pretend to be naive for this one reason.",
        ],
        "style": (
            "You are a psychological profiler. Deliver punchy, intense psychological insights "
            "that make the viewer feel like they are learning a classified interrogation secret."
        ),
        "fallback": ContentResult(
            title="THE 3-SECOND FBI TRICK THAT EXPOSES LIARS",
            script=(
                "When an FBI interrogator suspects someone is lying, they never argue. "
                "Instead, they repeat the suspect's last three words as a question, then maintain complete silence. "
                "Silence creates immense psychological discomfort in the human brain. "
                "To fill the void, the liar will over-explain, giving away details they never intended to share. "
                "Never fear the silence. Use it."
            ),
            visual_search_keyword="interrogation room shadow dark",
            tags="#shorts #psychology #mindset #fbi #bodylanguage #darkpsychology #manipulation",
            niche="dark_psychology",
            hook="FBI interrogators use this 3-second silence to make anyone confess.",
            scenes=[
                ScenePlan(1, "When an FBI interrogator suspects someone is lying, they never argue.", "interrogation room dim lamp silhouette", "impact"),
                ScenePlan(2, "Instead, they repeat the suspect's last three words as a question, then maintain complete silence.", "close up intense eyes stare dramatic", "heartbeat"),
                ScenePlan(3, "Silence creates immense psychological discomfort in the human brain.", "brain nervous system pulses abstract", "whoosh"),
                ScenePlan(4, "To fill the void, the liar will over-explain, giving away details they never intended to share.", "whisper microphone audio soundwave", "glitch"),
                ScenePlan(5, "Never fear the silence. Use it.", "confident businessman shadow silhouette walking", "impact"),
            ],
        ),
    },
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
            scenes=[
                ScenePlan(1, "Don't look behind you. The shadows in your room shift when you blink.", "dark bedroom shadows moving creepy", "impact"),
                ScenePlan(2, "Three people reported seeing a figure standing in the corner of their bedroom for weeks before they disappeared.", "shadow figure hallway dark silhouette", "heartbeat"),
                ScenePlan(3, "Authorities found their homes perfectly clean. No signs of struggle.", "police crime scene empty room dust", "whoosh"),
                ScenePlan(4, "Just one detail that matched every case: every mirror in the house had been turned to face the wall.", "mirror reflection dark fog horror", "glitch"),
            ],
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
            scenes=[
                ScenePlan(1, "Nobody will tell you this. Discipline is not something you feel.", "athlete running dark morning mist", "impact"),
                ScenePlan(2, "It is something you build, brick by brick, on the days you least want to show up.", "heavy weights gym intense workout chalk", "whoosh"),
                ScenePlan(3, "Every person you admire was once sitting exactly where you are right now.", "businessman looking city view window sunrise", "whoosh"),
                ScenePlan(4, "The only difference between them and you is that they chose to start.", "mountain summit climber reaching top clouds", "whoosh"),
                ScenePlan(5, "Today is your day to start.", "fire spark blazing dark cinematic", "impact"),
            ],
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
            scenes=[
                ScenePlan(1, "You were never taught this in school.", "vintage classroom dusty chalkboard mysterious", "impact"),
                ScenePlan(2, "The human brain cannot distinguish between a vivid memory and a real event.", "brain glowing synapses neural network 3d", "whoosh"),
                ScenePlan(3, "Every memory you have has been silently rewritten each time you recalled it.", "photograph burning disappearing into ashes slow motion", "whoosh"),
                ScenePlan(4, "The person you think you were five years ago?", "person looking into dark water reflection distorted", "glitch"),
                ScenePlan(5, "That version of you was quietly edited out of your own mind.", "cosmic space stars eye zoom galaxy", "impact"),
            ],
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
1. Write a viral short-form script that starts with: "{hook}"
   Target total length: ~{word_count} words.
   Story rules:
   - First sentence is the explosive hook (already given).
   - In-media-res pacing (no slow introductions).
   - Build relentless tension or curiosity with every sentence.
   - Deliver an unexpected twist or punchline at the end.
   - Break the script into 5 to 7 sequential scenes (each scene 1-2 punchy sentences).
   - For each scene, provide a highly specific portrait stock footage search query and an optional SFX cue.

2. Write a short, ALL-CAPS clickbait title (under 10 words).
3. Provide one primary English keyword for fallback background video.
4. Provide 8-12 viral hashtags.

RESPOND ONLY with valid JSON in this exact structure (no markdown fences):
{{
  "title": "ALL-CAPS VIRAL TITLE",
  "script": "Full narrative text...",
  "visual_search": "primary_keyword",
  "tags": "#shorts #topic #viral",
  "scenes": [
    {{
      "scene_id": 1,
      "narration": "First sentence matching the hook...",
      "visual_query": "specific search phrase for pexels",
      "sfx_cue": "impact"
    }}
}}"""


def _build_trend_prompt(topic: str, summary: str, length: str = "short") -> str:
    word_count = WORD_COUNTS.get(length, WORD_COUNTS["short"])
    return f"""\
You are an elite viral documentary director (MagnatesMedia, Vox, Johnny Harris level).
Your videos achieve 95%+ watch-time retention and millions of shares because you eliminate all fluff and structure every second with psychological hooks.

VIRAL TOPIC / INVESTIGATION:
Topic: {topic}
Context & Details: {summary}

RETENTION RULES (MANDATORY):
1. THE 1.5-SECOND PATTERN INTERRUPT:
   - First sentence MUST start in-media-res with an unbelievable revelation, conflict, or classified leak (under 12 words).
   - NEVER start with: "Did you know", "Imagine", "In this video", "Have you heard".
2. MAXIMUM VISUAL CONTRAST (Multi-Format Diversity):
   - Scene 1: "ai_image" (Ultra-cinematic 35mm film still setting the dark scene)
   - Scene 2: "dossier" (Classified evidence / government memo with redacted details)
   - Scene 3: "counter" (Shocking number, money amount, casualty count, or year)
   - Scene 4: "newspaper" (Mass media coverage / explosive public headline)
   - Scene 5: "video" or "ai_image" (The chilling conclusion / unanswered question)
3. RELENTLESS PACING & LOOP:
   - Keep total narration tight (~{word_count} words).
   - Every sentence must advance the mystery.
   - The final sentence must leave the viewer in shock or loop back seamlessly to the first sentence.

RESPOND ONLY with valid JSON in this exact structure (no markdown fences):
{{
  "title": "ALL-CAPS VIRAL THRILLER TITLE",
  "script": "Full narrative script...",
  "visual_search": "primary_fallback_keyword",
  "tags": "#shorts #trending #viral #mystery",
  "scenes": [
    {{
      "scene_id": 1,
      "narration": "First sentence matching the hook...",
      "visual_query": "35mm cinematic photograph of ...",
      "visual_format": "ai_image",
      "sfx_cue": "impact"
    }},
    {{
      "scene_id": 2,
      "narration": "Second sentence revealing the secret document...",
      "visual_query": "classified memo details",
      "visual_format": "dossier",
      "sfx_cue": "paper_slide"
    }},
    {{
      "scene_id": 3,
      "narration": "Third sentence giving the unbelievable number...",
      "visual_query": "financial records",
      "visual_format": "counter",
      "sfx_cue": "ticker"
    }},
    {{
      "scene_id": 4,
      "narration": "Fourth sentence showing the media reaction...",
      "visual_query": "breaking news scandal",
      "visual_format": "newspaper",
      "sfx_cue": "highlighter"
    }},
    {{
      "scene_id": 5,
      "narration": "Final sentence delivering the punchline or cliffhanger...",
      "visual_query": "dark eerie silhouette walking away",
      "visual_format": "video",
      "sfx_cue": "whoosh"
    }}
  ]
}}"""


def _split_into_scenes(script: str, default_keyword: str) -> list[ScenePlan]:
    """Helper to auto-split a plain script into 4-6 sequential scenes if scenes not provided."""
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return [ScenePlan(1, script, default_keyword, "impact")]

    scenes: list[ScenePlan] = []
    for idx, sentence in enumerate(sentences, start=1):
        cue = "impact" if idx == 1 else ("whoosh" if idx < len(sentences) else "impact")
        words = [re.sub(r"[^\w]", "", w).lower() for w in sentence.split()]
        filtered = [w for w in words if len(w) > 4 and w not in {"there", "their", "about", "would", "could", "should", "every", "before"}]
        query = " ".join(filtered[:3]) if filtered else default_keyword
        vformat = "newspaper" if idx == 1 else ("dossier" if idx == 3 else "ai_image")
        scenes.append(
            ScenePlan(
                scene_id=idx,
                narration=sentence,
                visual_query=query,
                sfx_cue=cue,
                visual_format=vformat,
            )
        )
    return scenes


def _parse_response(raw: str, niche: str, hook: str) -> ContentResult:
    """Parse Gemini JSON response into a ContentResult."""
    clean = strip_json_fences(raw)
    data = json.loads(clean)

    required = {"title", "script", "visual_search", "tags"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Gemini response missing keys: {missing}")

    title = clean_text(data["title"])
    script = clean_text(data["script"])
    visual_search = clean_text(data["visual_search"]).split()[0]
    tags = clean_text(data["tags"])

    # Parse multi-scene plan if provided by model
    scenes: list[ScenePlan] = []
    raw_scenes = data.get("scenes")
    if isinstance(raw_scenes, list) and len(raw_scenes) >= 2:
        for idx, item in enumerate(raw_scenes, start=1):
            if isinstance(item, dict) and "narration" in item:
                scenes.append(
                    ScenePlan(
                        scene_id=item.get("scene_id", idx),
                        narration=clean_text(item["narration"]),
                        visual_query=clean_text(item.get("visual_query", visual_search)),
                        sfx_cue=item.get("sfx_cue") or ("whoosh" if idx > 1 else "impact"),
                        visual_format=item.get("visual_format", "auto"),
                    )
                )

    if not scenes:
        scenes = _split_into_scenes(script, visual_search)

    return ContentResult(
        title=title,
        script=script,
        visual_search_keyword=visual_search,
        tags=tags,
        niche=niche,
        hook=hook,
        scenes=scenes,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_content(
    niche: str = DEFAULT_NICHE,
    length: str = "short",
    api_key: str | None = None,
    model: str | None = None,
    topic: str | TrendingTopic | None = None,
) -> ContentResult:
    """
    Generate a short-form video script via Google Gemini.

    Parameters
    ----------
    niche   : "heists", "glitches", "business", "dark_psychology", "horror", "motivation", or "facts"
    length  : "short" (~65 words) or "long" (~130 words)
    api_key : Gemini API key (loaded from config if None)
    model   : Gemini model name (loaded from config if None)
    topic   : Optional viral trending topic string or TrendingTopic instance

    Returns
    -------
    ContentResult. Falls back to rich multi-scene content on API failure.
    """
    if api_key is None or model is None:
        from shadowvault.config import get_config
        cfg = get_config()
        api_key = api_key or cfg.gemini_api_key
        model = model or cfg.gemini_model

    if topic is not None:
        if isinstance(topic, TrendingTopic):
            topic_title = topic.title
            topic_summary = topic.summary
            niche = topic.suggested_niche or niche
        else:
            topic_title = str(topic)
            topic_summary = str(topic)
        hook = topic_title
        prompt = _build_trend_prompt(topic_title, topic_summary, length)
        logger.info("Generating trend-focused content | topic=%r niche=%s length=%s", topic_title, niche, length)
    else:
        niche = niche if niche in NICHE_CONFIG else DEFAULT_NICHE
        hook = _pick_hook(niche)
        prompt = _build_prompt(niche, hook, length)
        logger.info("Generating content | niche=%s length=%s", niche, length)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        raw_text: str = response.text
        logger.debug("Gemini raw response: %s", raw_text[:200])

        result = _parse_response(raw_text, niche, hook)
        logger.info("Content generated: title=%r (scenes=%d)", result.title, len(result.scenes))
        return result

    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned invalid JSON (%s) - using fallback", exc)
    except Exception as exc:
        logger.warning("Gemini API error (%s) - using fallback", exc)

    if topic is not None:
        # Dynamic fallback for trend topics
        clean_kw = " ".join([w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", topic_title)][:2]) or "mystery"
        scenes = [
            ScenePlan(1, f"Did you hear what just happened with {topic_title}?", f"{clean_kw} dark", "impact"),
            ScenePlan(2, f"{topic_summary}", f"{clean_kw} dramatic", "whoosh"),
            ScenePlan(3, "Experts are still scrambling to explain the full impact.", "investigation dark", "whoosh"),
            ScenePlan(4, "This completely changes everything we thought we knew.", "neon mysterious cinematic", "glitch"),
            ScenePlan(5, "What do you think is really going on here?", "space night question", "impact"),
        ]
        return ContentResult(
            title=f"THE TRUTH ABOUT {topic_title.upper()[:40]}",
            script=" ".join(s.narration for s in scenes),
            visual_search_keyword=clean_kw,
            tags=f"#shorts #{clean_kw} #trending #viral",
            niche=niche,
            hook=scenes[0].narration,
            scenes=scenes,
        )

    fallback = NICHE_CONFIG[niche]["fallback"]
    logger.info("Using fallback content for niche=%s (scenes=%d)", niche, len(fallback.scenes))
    return fallback
