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
    "heists": ["heist", "stolen", "thief", "robbery", "scam", "fraud", "vault", "million", "billion", "crypto", "hack", "smuggling", "cartel"],
    "glitches": ["glitch", "anomaly", "unexplained", "phenomenon", "strange", "bizarre", "island", "illusion", "mystery", "signal", "alien", "ufo", "uap", "bermuda"],
    "business": ["market", "stock", "ceo", "apple", "google", "microsoft", "amazon", "nvidia", "tesla", "startup", "company", "bank", "billionaire"],
    "dark_psychology": ["brain", "psychology", "mind", "lie", "fbi", "cia", "interrogation", "memory", "subconscious", "behavior", "conspiracy", "secret", "classified", "senate", "leak", "buried", "pentagon"],
    "horror": ["death", "dead", "murder", "killer", "creepy", "ghost", "dark", "abandoned", "curse", "cemetery", "haunted", "grave", "cult", "nightmare"],
    "facts": ["exoplanet", "space", "telescope", "nasa", "discovery", "scientists", "planet", "galaxy", "ocean", "dna", "quantum", "physics"],
}

# Irrelevant superficial topics to filter out for Shadow Vault's serious investigative brand
BANNED_TOPIC_KEYWORDS = {
    " vs ", "vs.", "score", "game", "nba", "nfl", "mlb", "nhl", "premier league",
    "quarterback", "touchdown", "celebrity", "red carpet", "actor", "actress",
    "box office", "season finale", "real housewives", "bachelor", "sports", "coach",
}

EVERGREEN_FALLBACK_TRENDS: list[TrendingTopic] = [
    TrendingTopic(
        title="The Antwerp Diamond Heist Solved by a Half-Eaten Sandwich",
        summary="Thieves broke through ten layers of impenetrable biometric vault security to steal $100M in diamonds, only to be caught because an accomplice left his lunch on a roadside curb.",
        source="editorial",
        search_volume="1M+",
        suggested_niche="heists",
        keywords=["diamond heist", "antwerp vault", "impossible crime"],
    ),
    TrendingTopic(
        title="The 1977 Wow! Signal That Came From Deep Uncharted Space",
        summary="For 72 seconds, the Big Ear radio telescope detected a powerful narrowband radio signal from Sagittarius that matched no known natural source, remaining completely unexplained to this day.",
        source="editorial",
        search_volume="500K+",
        suggested_niche="glitches",
        keywords=["wow signal", "deep space", "unexplained frequency"],
    ),
    TrendingTopic(
        title="Operation Midnight Climax: The CIA Secret Safehouses",
        summary="Declassified CIA files revealed government safehouses in San Francisco where unsuspecting citizens were secretly dosed with experimental compounds behind two-way mirrors.",
        source="editorial",
        search_volume="750K+",
        suggested_niche="dark_psychology",
        keywords=["cia declassified", "mk ultra", "secret safehouse"],
    ),
    TrendingTopic(
        title="The 1518 Dancing Plague That Baffled Doctors for Centuries",
        summary="Hundreds of citizens in Strasbourg danced uncontrollably for weeks without rest or explanation, collapsing and dying in the streets while onlookers watched in horror.",
        source="wikipedia",
        search_volume="250K+",
        suggested_niche="horror",
        keywords=["dancing plague", "historical mystery", "unexplained phenomenon"],
    ),
    TrendingTopic(
        title="The Central Bank of Iraq Heist: $1 Billion Taken in Cash",
        summary="Hours before bombs fell over Baghdad, three tractor-trailers pulled up to the Central Bank of Iraq to haul away nearly one billion dollars in physical cash that never resurfaced.",
        source="editorial",
        search_volume="1M+",
        suggested_niche="heists",
        keywords=["iraq bank heist", "billion dollar cash", "untold mystery"],
    ),
    TrendingTopic(
        title="Astronomers Confirm Discovery of the Youngest Known Exoplanet Ever",
        summary="Deep in the cosmos, astronomers using high-resolution spectroscopy detected a newborn world orbiting a star only a few million years old, challenging all models of planetary formation.",
        source="google_trends",
        search_volume="500K+",
        suggested_niche="facts",
        keywords=["exoplanet", "astronomy", "space discovery", "cosmos"],
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
    Filters out sports and superficial gossip for high-retention documentary focus.
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        ns = {"ht": "https://trends.google.com/trending/rss"}
        items = root.findall(".//item")
        topics: list[TrendingTopic] = []

        for item in items:
            title_el = item.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue

            # Skip sports, games, and celebrity gossip
            title_l = title.lower()
            if any(banned in title_l for banned in BANNED_TOPIC_KEYWORDS):
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


NICHE_NEWS_QUERIES: dict[str, str] = {
    "glitches": "(unexplained+signal+OR+ocean+anomaly+OR+cosmic+mystery)+when:30d",
    "heists": "vault+heist+OR+stolen+millions+OR+art+theft+when:30d",
    "dark_psychology": "declassified+files+OR+cia+secret+OR+fbi+mystery+when:30d",
    "horror": "unsolved+mystery+discovery+OR+cold+case+when:30d",
    "business": "corporate+scandal+OR+billionaire+battle+when:30d",
    "facts": "deep+space+discovery+OR+quantum+breakthrough+when:30d",
}


def scan_niche_news(
    niche: str,
    query: Optional[str] = None,
    max_items: int = 8,
) -> list[TrendingTopic]:
    """
    Fetch breaking, non-recycled news stories for a specific niche from Google News RSS.
    Returns list of TrendingTopic objects with direct URLs, publishers, and publication dates.
    """
    search_q = query or NICHE_NEWS_QUERIES.get(niche, NICHE_NEWS_QUERIES["glitches"])
    url = f"https://news.google.com/rss/search?q={search_q}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        topics: list[TrendingTopic] = []

        for item in items[:max_items]:
            raw_title = item.find("title").text if item.find("title") is not None else ""
            if not raw_title:
                continue
            clean_title = html.unescape(raw_title)
            # Remove publisher suffix e.g. " - BBC Sky at Night Magazine"
            clean_title = re.sub(r"\s*-\s*[^-]+$", "", clean_title).strip()

            # Skip banned sports/celebrity keywords
            if any(banned in clean_title.lower() for banned in BANNED_TOPIC_KEYWORDS):
                continue

            link_el = item.find("link")
            source_url = link_el.text.strip() if link_el is not None and link_el.text else ""

            source_el = item.find("source")
            source_name = source_el.text.strip() if source_el is not None and source_el.text else "News"

            pub_el = item.find("pubDate")
            pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

            desc_el = item.find("description")
            raw_desc = desc_el.text if desc_el is not None and desc_el.text else ""
            clean_desc = html.unescape(raw_desc)
            clean_desc = re.sub(r"<[^>]+>", " ", clean_desc).strip()
            summary = clean_desc if clean_desc else clean_title

            keywords = [w.lower() for w in re.findall(r"\b[A-Za-z]{4,}\b", clean_title)][:5]

            topics.append(
                TrendingTopic(
                    title=clean_title,
                    summary=summary,
                    source="google_news",
                    source_name=source_name,
                    source_url=source_url,
                    published_date=pub_date,
                    search_volume="Breaking News",
                    suggested_niche=niche,
                    keywords=keywords,
                )
            )

        logger.info("Scanned %d real-time breaking topics from Google News RSS for niche '%s'", len(topics), niche)
        return topics
    except Exception as exc:
        logger.warning("Google News niche scan failed for '%s': %s", niche, exc)
        return []


def get_hottest_viral_topic(
    preferred_niche: Optional[str] = None,
    allow_fallbacks: bool = True,
) -> TrendingTopic:
    """
    Discover the best single viral topic for today's video.
    Combines live Google Trends with historical shockers, matching preferred niche if given.
    """
    # 1. If a preferred niche is specified, check live breaking news first!
    if preferred_niche:
        niche_news = scan_niche_news(preferred_niche, max_items=8)
        if niche_news:
            chosen = random.choice(niche_news[:min(4, len(niche_news))])
            logger.info(
                "Selected breaking niche news topic: %r [%s] from %s (%s)",
                chosen.title,
                chosen.suggested_niche,
                chosen.source_name,
                chosen.source_url[:50] + "...",
            )
            return chosen

    candidates: list[TrendingTopic] = []

    # 2. Fetch Google Trends
    gt_topics = scan_google_trends(geo="US", max_items=12)
    candidates.extend(gt_topics)

    # 3. Fetch Wikipedia historical drama
    wiki_topics = scan_wikipedia_on_this_day(max_items=5)
    candidates.extend(wiki_topics)

    # 4. Filter by preferred niche if specified
    if preferred_niche:
        niche_matches = [t for t in candidates if t.suggested_niche == preferred_niche]
        if niche_matches:
            chosen = random.choice(niche_matches[:3])
            logger.info("Selected niche-matched viral topic: %s (%s)", chosen.title, chosen.suggested_niche)
            return chosen

        # Never compromise the channel's niche: fallback to curated topic in that specific niche
        niche_fallbacks = [t for t in EVERGREEN_FALLBACK_TRENDS if t.suggested_niche == preferred_niche]
        if niche_fallbacks:
            chosen = random.choice(niche_fallbacks)
            logger.info("Using niche-matched evergreen topic: %s (%s)", chosen.title, chosen.suggested_niche)
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
