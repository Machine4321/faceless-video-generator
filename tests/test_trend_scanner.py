"""
tests/test_trend_scanner.py
Unit tests for shadowvault.trend_scanner.
"""

from unittest.mock import MagicMock, patch

import pytest

from shadowvault.models import TrendingTopic
from shadowvault.trend_scanner import (
    _classify_niche,
    get_hottest_viral_topic,
    scan_google_trends,
    scan_wikipedia_on_this_day,
)

SAMPLE_GOOGLE_TRENDS_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:ht="https://trends.google.com/trending/rss">
  <channel>
    <title>Daily Search Trends</title>
    <item>
      <title>Exoplanet Discovery</title>
      <ht:approx_traffic>500K+</ht:approx_traffic>
      <ht:news_item>
        <ht:news_item_title>Astronomers discover newborn exoplanet orbiting nearby star</ht:news_item_title>
        <ht:news_item_snippet>A groundbreaking telescope observation reveals an exoplanet.</ht:news_item_snippet>
      </ht:news_item>
    </item>
    <item>
      <title>Antwerp Diamond Vault</title>
      <ht:approx_traffic>200K+</ht:approx_traffic>
      <ht:news_item>
        <ht:news_item_title>New details emerge on historic $100M vault robbery</ht:news_item_title>
      </ht:news_item>
    </item>
  </channel>
</rss>
"""


def test_classify_niche_heists():
    assert _classify_niche("Thief stole $50M from bank vault") == "heists"
    assert _classify_niche("Massive crypto scam unmasked") == "heists"


def test_classify_niche_glitches():
    assert _classify_niche("Unexplained strange island mystery anomaly") == "glitches"


def test_classify_niche_facts():
    assert _classify_niche("NASA telescope detects exoplanet in deep space") == "facts"


def test_classify_niche_business():
    assert _classify_niche("Apple and Nvidia reach new market valuation record") == "business"


@patch("shadowvault.trend_scanner.requests.get")
def test_scan_google_trends_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.content = SAMPLE_GOOGLE_TRENDS_RSS
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    topics = scan_google_trends(geo="US", max_items=5)
    assert len(topics) == 2
    assert topics[0].title == "Exoplanet Discovery"
    assert topics[0].search_volume == "500K+"
    assert topics[0].suggested_niche == "facts"
    assert "Astronomers discover" in topics[0].summary
    assert topics[1].title == "Antwerp Diamond Vault"
    assert topics[1].suggested_niche == "heists"


@patch("shadowvault.trend_scanner.requests.get")
def test_scan_google_trends_failure_handled(mock_get):
    mock_get.side_effect = Exception("Network timeout")
    topics = scan_google_trends(geo="US", max_items=5)
    assert topics == []


@patch("shadowvault.trend_scanner.requests.get")
def test_scan_wikipedia_on_this_day_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "selected": [
            {
                "year": 1908,
                "text": "The Messina earthquake struck southern Italy with immense power.",
            }
        ]
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    topics = scan_wikipedia_on_this_day(max_items=3)
    assert len(topics) == 1
    assert "1908:" in topics[0].title
    assert topics[0].source == "wikipedia"


@patch("shadowvault.trend_scanner.scan_niche_news")
@patch("shadowvault.trend_scanner.scan_google_trends")
@patch("shadowvault.trend_scanner.scan_wikipedia_on_this_day")
def test_get_hottest_viral_topic_with_preference(mock_wiki, mock_gt, mock_niche):
    mock_niche.return_value = []
    mock_gt.return_value = [
        TrendingTopic(
            title="Massive Diamond Robbery",
            summary="A vault was raided cleanly.",
            source="google_trends",
            suggested_niche="heists",
        ),
        TrendingTopic(
            title="Mars Ocean Evidence",
            summary="Water found on Mars.",
            source="google_trends",
            suggested_niche="facts",
        ),
    ]
    mock_wiki.return_value = []

    topic = get_hottest_viral_topic(preferred_niche="heists")
    assert topic.suggested_niche == "heists"
    assert topic.title == "Massive Diamond Robbery"


@patch("shadowvault.trend_scanner.scan_niche_news")
@patch("shadowvault.trend_scanner.scan_google_trends")
@patch("shadowvault.trend_scanner.scan_wikipedia_on_this_day")
def test_get_hottest_viral_topic_fallback_when_offline(mock_wiki, mock_gt, mock_niche):
    mock_niche.return_value = []
    mock_gt.return_value = []
    mock_wiki.return_value = []

    topic = get_hottest_viral_topic()
    assert topic is not None
    assert topic.title != ""
    assert len(topic.summary) > 20
