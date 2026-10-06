"""
shadowvault/trend_scanner.py
Real-time Viral Trend Scanner for automated YouTube Shorts and TikTok content.

Pulls live high-velocity topics from:
1. Google Trends Live Daily RSS (US and global)
2. Wikipedia 'On This Day' high-drama historical events
3. Reddit OAuth / Public RSS fallback

Categorizes topics into high-retention niches:
- heists (robberies, financial scams, security breaches)
- glitches (bizarre historical anomalies, strange phenomena)
- business (corporate battles, shocking founder moves)
- dark_psychology (secrets, mind paradoxes, behavioral mysteries)
- facts (astronomy, science discoveries, unbelievable human feats)
- horror (unsolved mysteries, creepy real events)
"""

from __future__ import annotations

import datetime
import html
import logging
import random
import re
import xml.etree.ElementTree as ET
from typing import Optional, Sequence

import requests

from shadowvault.models import TrendingTopic

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 12

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 FacelessVideoGenerator/1.0"
)

# Niche classification heuristics
KEYWORD_NICHE_MAP = {
    "heists": ["heist", "stolen", "thief", "robbery", "scam", "fraud", "vault", "million", "billion", "crypto", "hack"],
    "glitches": ["glitch", "anomaly", "unexplained", "phenomenon", "strange", "bizarre", "island", "illusion", "mystery"],
    "business": ["market", "stock", "ceo", "apple", "google", "microsoft", "amazon", "nvidia", "tesla", "startup", "company", "bank"],
    "dark_psychology": ["brain", "psychology", "mind", "lie", "fbi", "interrogation", "memory", "subconscious", "behavior"],
    "horror": ["death", "dead", "murder", "killer", "creepy", "ghost", "dark", "abandoned", "curse", "cemetery"],
    "facts": ["exoplanet", "space", "telescope", "nasa", "discovery", "scientists", "planet", "galaxy", "ocean", "dna", "quantum", "physics"],
}

EVERGREEN_FALLBACK_TRENDS: list[TrendingTopic] = [
    TrendingTopic(
        title="Astronomers Confirm Discovery of the Youngest Known Exoplanet Ever",
        summary="Deep in the cosmos, astronomers using high-resolution spectroscopy detected a newborn world orbiting a star only a few million years old, challenging all models of planetary formation.",
        source="google_trends",
        search_volume="500K+",
        suggested_niche="facts",
        keywords=["exoplanet", "astronomy", "space discovery", "cosmos"],
    ),
    TrendingTopic(
        title="The Antwerp Diamond Heist Solved by a Half-Eaten Sandwich",
        summary="Thieves broke through ten layers of impenetrable biometric vault security to steal $100M in diamonds, only to be caught because an accomplice left his lunch on a roadside curb.",
        source="editorial",
        search_volume="1M+",
        suggested_niche="heists",
        keywords=["diamond heist", "antwerp vault", "impossible crime"],
    ),
    TrendingTopic(
        title="The 1518 Dancing Plague That Baffled Doctors for Centuries",
        summary="Hundreds of citizens in Strasbourg danced uncontrollably for weeks without rest or explanation, collapsing and dying in the streets while onlookers watched in horror.",
        source="wikipedia",
        search_volume="250K+",
        suggested_niche="glitches",
        keywords=["dancing plague", "historical mystery", "unexplained phenomenon"],
    ),
]


def _classify_niche(text: str) -> str:
    """Classify topic text into one of the target niches."""
    text_lower = text.lower()
    for niche, kw_list in KEYWORD_NICHE_MAP.items():
        if any(kw in text_lower for kw in kw_list):
            return niche
    return "facts"


def scan_google_trends(geo: str = "US", max_items: int = 10) -> list[TrendingTopic]:
    """
    Fetch trending topics from Google Trends RSS.
    Zero-auth, real-time query volume and news context.
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        ns = {"ht": "https://trends.google.com/trending/rss"}
        items = root.findall(".//item")
        topics: list[TrendingTopic] = []

        for item in items[:max_items]:
            title_el = item.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue

            traffic_el = item.find("ht:approx_traffic", ns)
            traffic = traffic_el.text.strip() if traffic_el is not None and traffic_el.text else "50K+"

            # Collect news headlines & snippets
            snippets: list[str] = []
            news_items = item.findall("ht:news_item", ns)
            for ni in news_items:
                nt_el = ni.find("ht:news_item_title", ns)
                if nt_el is not None and nt_el.text:
                    clean_nt = html.unescape(nt_el.text.strip())
                    clean_nt = re.sub(r"<[^>]+>", "", clean_nt)
                    snippets.append(clean_nt)

            summary = "; ".join(snippets[:2]) if snippets else title
            niche = _classify_niche(f"{title} {summary}")
            keywords = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", title)][:5]

            topics.append(
                TrendingTopic(
                    title=title,
                    summary=summary,
                    source="google_trends",
                    search_volume=traffic,
                    suggested_niche=niche,
                    keywords=keywords,
                )
            )

        logger.info("Scanned %d trending topics from Google Trends (%s)", len(topics), geo)
        return topics
    except Exception as exc:
        logger.warning("Google Trends scan failed: %s", exc)
        return []


def scan_wikipedia_on_this_day(max_items: int = 5) -> list[TrendingTopic]:
    """
    Fetch high-drama historical events for today's date from Wikipedia API.
    """
    now = datetime.datetime.now()
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/selected/{now.month:02d}/{now.day:02d}"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "FacelessVideoGenerator/1.0 (contact@machine4321.dev)"},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        selected = data.get("selected", [])

        topics: list[TrendingTopic] = []
        for item in selected[:max_items]:
            year = item.get("year", "")
            raw_text = item.get("text", "")
            clean_text = html.unescape(raw_text)
            clean_text = re.sub(r"\[.*?\]", "", clean_text)

            title = f"{year}: {clean_text.split('.')[0]}"
            niche = _classify_niche(clean_text)
            keywords = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", clean_text)][:5]

            topics.append(
                TrendingTopic(
                    title=title[:80],
                    summary=clean_text,
                    source="wikipedia",
                    search_volume="Historical",
                    suggested_niche=niche,
                    keywords=keywords,
                )
            )

        logger.info("Scanned %d events from Wikipedia On This Day", len(topics))
        return topics
    except Exception as exc:
        logger.warning("Wikipedia On This Day scan failed: %s", exc)
        return []


def get_hottest_viral_topic(
    preferred_niche: Optional[str] = None,
    allow_fallbacks: bool = True,
) -> TrendingTopic:
    """
    Discover the best single viral topic for today's video.
    Combines live Google Trends with historical shockers, matching preferred niche if given.
    """
    candidates: list[TrendingTopic] = []

    # 1. Fetch Google Trends
    gt_topics = scan_google_trends(geo="US", max_items=12)
    candidates.extend(gt_topics)

    # 2. Fetch Wikipedia historical drama
    wiki_topics = scan_wikipedia_on_this_day(max_items=5)
    candidates.extend(wiki_topics)

    # 3. Filter by preferred niche if specified
    if preferred_niche:
        niche_matches = [t for t in candidates if t.suggested_niche == preferred_niche]
        if niche_matches:
            chosen = random.choice(niche_matches[:3])
            logger.info("Selected niche-matched viral topic: %s (%s)", chosen.title, chosen.suggested_niche)
            return chosen

    # 4. Otherwise pick from top high-velocity topics
    if candidates:
        # Pick from the top 5 for variety
        chosen = random.choice(candidates[:min(5, len(candidates))])
        logger.info("Selected top viral topic: %s [%s]", chosen.title, chosen.suggested_niche)
        return chosen

    # 5. Offline / Rate-limited fallback
    if allow_fallbacks:
        chosen = random.choice(EVERGREEN_FALLBACK_TRENDS)
        logger.info("Using evergreen fallback viral topic: %s", chosen.title)
        return chosen

    raise RuntimeError("No viral topics available from any source.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== LIVE VIRAL TREND SCANNER ===")
    topics = scan_google_trends(max_items=8)
    for i, t in enumerate(topics, 1):
        print(f"[{i}] {t.title.upper()} ({t.suggested_niche}) - {t.search_volume}")
        print(f"    Summary: {t.summary[:100]}...")
