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
            title="THE 72-SECOND SIGNAL FROM DEEP UNCHARTED SPACE",
            script=(
                "On August 15, 1977, a radio telescope in Ohio intercepted an artificial signal from deep space. "
                "It was thirty times louder than cosmic background noise. "
                "The frequency was locked exactly to 1,420 megahertz, the hydrogen line. "
                "Astronomer Jerry Ehman circled the code on a printout and scribbled 'Wow!'. "
                "The signal broadcast continuously for seventy-two seconds. "
                "Every satellite and military transmitter was ruled out. "
                "For forty-nine years, telescopes have watched that exact coordinate. "
                "The signal has never returned."
            ),
            visual_search_keyword="radio telescope deep space",
            tags="#shorts #history #glitches #mystery #astronomy #viral",
            niche="glitches",
            hook="On August 15, 1977, a radio telescope in Ohio intercepted an artificial signal from deep space.",
            scenes=[
                ScenePlan(1, "On August 15, 1977, a radio telescope intercepted an artificial signal from deep space.", "35mm archival photograph of Big Ear radio telescope at night", "impact", visual_format="ai_image"),
                ScenePlan(2, "It was thirty times louder than cosmic background noise.", "oscilloscope green frequency pulse telemetry", "radar_ping", visual_format="radar"),
                ScenePlan(3, "The frequency was locked to 1,420 megahertz.", "frequency 1420 mhz hydrogen line", "ticker", visual_format="counter"),
                ScenePlan(4, "Astronomer Jerry Ehman circled the code and scribbled 'Wow!'.", "vintage dot matrix computer printout circled in red ink", "paper_slide", visual_format="dossier"),
                ScenePlan(5, "The signal broadcast continuously for seventy-two seconds.", "72 seconds duration record", "ticker", visual_format="counter"),
                ScenePlan(6, "Breaking headlines ignited global speculation overnight.", "astronomy breaking news discovery headline", "highlighter", visual_format="newspaper"),
                ScenePlan(7, "Every satellite and military transmitter was completely ruled out.", "classified intelligence transmission report", "stamp_thud", visual_format="dossier"),
                ScenePlan(8, "For forty-nine years, telescopes have watched that exact coordinate.", "deep space radio telescope dish pointing at stars night", "whoosh", visual_format="ai_image"),
                ScenePlan(9, "The signal has never returned.", "dark cosmic void deep galaxy infinite loop", "impact", visual_format="ai_image"),
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
    is_long = length == "long"
    target_dur = "~45-55 seconds spoken" if is_long else "~22-26 seconds spoken"
    num_scenes = "13 to 17" if is_long else "8 to 11"

    arc_instruction = (
        "4-ACT DOCUMENTARY NARRATIVE ARC:\n"
        "   - Act 1 (Hook & Impossible Stakes, scenes 1-3): Cold open fact, impenetrable setting.\n"
        "   - Act 2 (The Tactical Flaw & Quantifiable Stakes, scenes 4-7): The secret vulnerability and record numbers (use 'counter' scene with exact value).\n"
        "   - Act 3 (The Second-by-Second Execution, scenes 8-12): Tension-filled execution, alarms bypassed, loot seized (use 'dossier' or 'ai_image').\n"
        "   - Act 4 (The Shocking Climax & Loop, scenes 13-16): Breaking front page ('newspaper'), chilling revelation/clue, and loop back to the opening hook."
        if is_long else
        "FAST 2-ACT RHYTHM:\n"
        "   - In-media-res pacing (no slow introductions or filler).\n"
        "   - Build relentless tension and end with a chilling twist or seamless loop back to the hook."
    )

    return f"""\
{cfg['style']}

TASK:
1. Write a viral short-form investigative script that starts with: "{hook}"
   Target total length: ~{word_count} words ({target_dur}).
   RETENTION & STORY RULES:
   - First sentence is the explosive hook (already given).
   {arc_instruction}
   - DOUBLE THE VISUAL RHYTHM: Divide the story into {num_scenes} sequential micro-scenes (each cut 4-8 words, ~1.8-2.5 seconds).
   - Use high-contrast documentary formats across scenes: "ai_image", "radar", "dossier", "counter", "newspaper".
   - NO generic stock actors or AI clichés.

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
      "visual_query": "cinematic 35mm archival photograph of ...",
      "visual_format": "ai_image",
      "sfx_cue": "impact"
    }},
    {{
      "scene_id": 2,
      "narration": "Second fast micro-scene...",
      "visual_query": "radar frequency monitor",
      "visual_format": "radar",
      "sfx_cue": "radar_ping"
    }}
  ]
}}"""


def _build_trend_prompt(topic: str, summary: str, length: str = "short") -> str:
    word_count = WORD_COUNTS.get(length, WORD_COUNTS["short"])
    is_long = length == "long"
    target_dur = "~45-55 seconds spoken" if is_long else "~22-26 seconds spoken"
    num_scenes = "13 to 17" if is_long else "8 to 11"

    arc_instruction = (
        "4-ACT DOCUMENTARY NARRATIVE ARC:\n"
        "   - Act 1 (Hook & Impossible Stakes, scenes 1-3): Cold open fact, impenetrable setting.\n"
        "   - Act 2 (The Tactical Flaw & Quantifiable Stakes, scenes 4-7): The secret vulnerability and record numbers (use 'counter' scene with exact value).\n"
        "   - Act 3 (The Second-by-Second Execution, scenes 8-12): Tension-filled execution, alarms bypassed, loot seized (use 'dossier' or 'ai_image').\n"
        "   - Act 4 (The Shocking Climax & Loop, scenes 13-16): Breaking front page ('newspaper'), chilling revelation/clue, and loop back to the opening hook."
        if is_long else
        "FAST 2-ACT RHYTHM:\n"
        "   - In-media-res pacing (no slow introductions or filler).\n"
        "   - Build relentless tension and end with a chilling twist or seamless loop back to the hook."
    )

    return f"""\
You are an elite viral documentary director (MagnatesMedia, Vox, Johnny Harris, Lemmino level).
Your videos achieve 95%+ watch-time retention and millions of shares because you eliminate all generic AI fluff and structure every single second with rapid visual cuts and verifiable facts.

VIRAL TOPIC: {topic}
CONTEXT & DETAILS: {summary}

MANDATORY JOURNALISTIC & RETENTION RULES:
1. ZERO AI CLICHÉS (STRICTLY BANNED):
   - NEVER use: "Did you know", "Imagine", "they don't want you to know", "fed a lie", "leaving us to wonder", "shocking secret", "unravel the mystery".
   - Write like a top-tier investigative journalist: cite exact years, exact locations, exact names, exact frequencies/tempos/stats, and verified records.
2. CRITICAL TOPIC RELEVANCE & VISUAL SYNCHRONIZATION:
   - The topic is: "{topic}". EVERY SINGLE SCENE must directly portray and describe this specific subject.
   - Do NOT hallucinate dark crime archives, space telescopes, or laboratories unless the topic is literally about space or laboratories!
   - If the topic is about an animal, dance, sport, music, or event (e.g. "{topic}"), EVERY visual query MUST explicitly focus on that physical subject.
   - Format selection rules:
     * "ai_image": Ultra-detailed cinematic photograph depicting the exact action of {topic}.
     * "photo": Archival or high-resolution photography of {topic}.
     * "video": Motion footage of {topic}.
     * "counter": Use when narrating a quantifiable metric or record. CRITICAL: When visual_format is "counter", the narration MUST speak the exact number and unit (e.g. "$500 million", "180 beats per minute", "13 masterpieces", "81 minutes").
     * "newspaper": Use for breaking news, competition headline, or public sensation about {topic}.
     * "dossier": ONLY if {topic} involves classified intelligence or crime. Otherwise use "ai_image" or "photo".
     * "radar": ONLY if {topic} involves radio frequencies, astronomy, or radar telemetry. Otherwise use "ai_image" or "photo".
3. DOUBLED VISUAL RHYTHM ({num_scenes} FAST-PACED MICRO-SCENES):
   - Modern viewers drop off if a scene holds longer than 2.5 seconds.
   - Break the script into {num_scenes} sequential micro-scenes (each scene is one punchy clause of 4 to 8 words, lasting ~1.8 to 2.5 seconds).
4. RELENTLESS PACING & SEAMLESS LOOP:
   - Total narration: ~{word_count} words ({target_dur}).
   - The cold open starts immediately in-media-res with an unbelievable recorded fact.
   {arc_instruction}
   - The final sentence delivers a bone-chilling twist or connects back seamlessly to the first sentence for infinite loop retention.
5. TRUE CRIME & HEISTS MANDATE (WHEN TOPIC INVOLVES HEISTS, ROBBERIES, THEFT, ART, OR INVESTIGATIONS):
   - ZERO ABSTRACT FLUFF: Never talk about generic museum security procedures, guard checklists, or abstract statistics.
   - GROUND IMMEDIATELY IN A LEGENDARY SPECIFIC CASE:
     * For art heists: Anchor immediately on the $500,000,000 Isabella Stewart Gardner Museum heist in Boston (two thieves disguised as police officers walked in at 1:24 AM, handcuffed guards with duct tape in the basement, cut 13 priceless masterpieces including Rembrandt and Vermeer out of their gilded frames in 81 minutes, and vanished forever; for 34 years the empty frames still hang on the gallery walls, and a $10M FBI bounty remains unclaimed).
     * Reveal the dark underworld secret: high-profile masterpieces can NEVER be sold on the open market—they become shadow underworld currency and collateral traded between international drug cartels and syndicates.
   - MANDATORY EXACT NUMBERS IN COUNTER SCENE: If using "counter", state the exact dollar value (e.g. "$500 million", "$100 million") or exact count (e.g. "13 masterpieces stolen", "81 minutes").
6. PHYSICAL NOUNS FOR VISUAL QUERIES (CRITICAL):
   - "visual_search" and EVERY "visual_query" MUST consist of CONCRETE, PHYSICAL NOUNS (e.g. "art museum gallery", "framed classical oil painting", "empty picture frame hanging on museum wall", "bank vault steel door", "police investigation tape", "museum security camera").
   - NEVER use abstract adjectives or journalistic buzzwords: "high-profile", "highprofile", "uptick", "shocking", "unbelievable", "mysterious", "secret", "crisis". Search engines cannot search abstract adjectives and will return fashion models or curtains. ONLY use concrete physical nouns!

RESPOND ONLY with valid JSON in this exact structure (no markdown fences):
{{
  "title": "ALL-CAPS VIRAL THRILLER TITLE",
  "script": "Full narrative script...",
  "visual_search": "primary concrete physical subject noun directly describing {topic}",
  "tags": "#shorts #trending #viral #mystery",
  "scenes": [
    {{
      "scene_id": 1,
      "narration": "First punchy hook introducing {topic}...",
      "visual_query": "cinematic vibrant photograph of {topic}...",
      "visual_format": "ai_image",
      "sfx_cue": "impact"
    }},
    {{
      "scene_id": 2,
      "narration": "Second sentence showing the subject in action...",
      "visual_query": "dynamic action shot of {topic} in movement...",
      "visual_format": "ai_image",
      "sfx_cue": "whoosh"
    }},
    {{
      "scene_id": 3,
      "narration": "Exact measurement or shocking record: reaching 180 beats per minute...",
      "visual_query": "high energy visual of {topic} matching the stat...",
      "visual_format": "counter",
      "sfx_cue": "ticker"
    }},
    {{
      "scene_id": 4,
      "narration": "Close up detail or technique of {topic}...",
      "visual_query": "macro close up of {topic}...",
      "visual_format": "ai_image",
      "sfx_cue": "paper_slide"
    }},
    {{
      "scene_id": 5,
      "narration": "Breaking headline as the world reacted...",
      "visual_query": "historic press headline report about {topic}...",
      "visual_format": "newspaper",
      "sfx_cue": "highlighter"
    }},
    {{
      "scene_id": 6,
      "narration": "The viral reaction or unbelievable climax...",
      "visual_query": "triumphant celebration or viral spectacle of {topic}...",
      "visual_format": "ai_image",
      "sfx_cue": "impact"
    }}
  ]
}}"""


def _split_into_scenes(script: str, default_keyword: str) -> list[ScenePlan]:
    """Auto-split a plain script into 8-11 fast-paced micro-scenes (1.8-2.2s cuts) with alternating formats."""
    # Split on sentence boundaries and major clauses (dashes, semicolons)
    raw_parts = re.split(r"(?<=[.!?])\s+|(?<=[—;:])\s+", script.strip())
    parts = [p.strip() for p in raw_parts if p.strip()]

    # If sentences are long (>10 words), subdivide them into 5-8 word punchy micro-beats
    refined_parts: list[str] = []
    for part in parts:
        words = part.split()
        if len(words) > 10:
            mid = len(words) // 2
            refined_parts.append(" ".join(words[:mid]))
            refined_parts.append(" ".join(words[mid:]))
        else:
            refined_parts.append(part)

    if not refined_parts:
        refined_parts = [script]

    format_cycle = ["ai_image", "radar", "dossier", "ai_image", "counter", "newspaper", "ai_image", "dossier", "radar", "ai_image"]
    sfx_cycle = ["impact", "radar_ping", "stamp_thud", "paper_slide", "ticker", "highlighter", "whoosh", "paper_slide", "whoosh", "impact"]

    scenes: list[ScenePlan] = []
    for idx, clause in enumerate(refined_parts, start=1):
        vformat = format_cycle[(idx - 1) % len(format_cycle)]
        cue = sfx_cycle[(idx - 1) % len(sfx_cycle)]

        words = [re.sub(r"[^\w]", "", w).lower() for w in clause.split()]
        filtered = [w for w in words if len(w) > 4 and w not in {"there", "their", "about", "would", "could", "should", "every", "before"}]
        query = " ".join(filtered[:3]) if filtered else default_keyword

        scenes.append(
            ScenePlan(
                scene_id=idx,
                narration=clause,
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
    raw_kw = clean_text(data["visual_search"])
    stop_and_jargon = {
        "the", "a", "an", "this", "that", "these", "those", "is", "are", "was", "were",
        "of", "in", "on", "at", "to", "for", "with", "by", "from", "and", "or",
        "highprofile", "high-profile", "high", "profile", "uptick", "crisis", "shocking",
        "unbelievable", "mysterious", "secret", "truth", "viral", "why", "heres", "there",
        "has", "been", "yes", "no", "overview", "look", "report", "news", "trend", "trending"
    }
    candidate_words = [w for w in re.sub(r"[^\w\s]", "", raw_kw).split() if w.lower() not in stop_and_jargon]
    visual_search = candidate_words[0] if candidate_words else (raw_kw.split()[0] if raw_kw.split() else "viral")
    tags = clean_text(data["tags"])

    # Parse multi-scene plan if provided by model
    scenes: list[ScenePlan] = []
    raw_scenes = data.get("scenes")
    if isinstance(raw_scenes, list) and len(raw_scenes) >= 2:
        for idx, item in enumerate(raw_scenes, start=1):
            if isinstance(item, dict) and "narration" in item:
                vq = clean_text(item.get("visual_query", visual_search))
                vq_words = [w for w in re.sub(r"[^\w\s]", "", vq).split() if w.lower() not in stop_and_jargon]
                final_vq = " ".join(vq_words) if vq_words else visual_search
                scenes.append(
                    ScenePlan(
                        scene_id=item.get("scene_id", idx),
                        narration=clean_text(item["narration"]),
                        visual_query=final_vq,
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

    models_to_try = [model]
    for m in ["gemini-3.5-flash-lite", "gemini-3.5-flash"]:
        if m not in models_to_try:
            models_to_try.append(m)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        for m_candidate in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m_candidate,
                    contents=prompt,
                )
                raw_text = response.text
                result = _parse_response(raw_text, niche, hook)
                logger.info("Content generated via %s: title=%r (scenes=%d)", m_candidate, result.title, len(result.scenes))
                return result
            except json.JSONDecodeError as exc:
                logger.warning("Gemini model %s returned invalid JSON (%s)", m_candidate, exc)
            except Exception as exc:
                logger.warning("Gemini error on model %s (%s) - trying fallback model", m_candidate, exc)
    except Exception as exc:
        logger.warning("Gemini client initialization error (%s) - using fallback", exc)

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
