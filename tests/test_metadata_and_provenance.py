"""
tests/test_metadata_and_provenance.py
Tests for automated metadata generation, source provenance auditing,
and niche-specific breaking news trend scanning.
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from shadowvault.models import (
    AudioResult,
    ContentResult,
    MediaResult,
    PipelineRun,
    ScenePlan,
    TrendingTopic,
    VideoResult,
)
from shadowvault.metadata import (
    generate_metadata_text,
    write_metadata_file,
    print_metadata_summary,
)
from shadowvault.trend_scanner import (
    scan_niche_news,
    get_hottest_viral_topic,
    NICHE_NEWS_QUERIES,
)


@pytest.fixture
def sample_pipeline_run():
    content = ContentResult(
        title="SCIENTISTS DETECTED A 7-HOUR SIGNAL FROM DEEP SPACE",
        script="Astronomers pointed giant radio dishes into space and detected an anomaly.",
        visual_search_keyword="deep space telescope",
        tags="#shorts #mystery #space",
        niche="glitches",
        hook="Astronomers pointed giant radio dishes into space.",
        scenes=[
            ScenePlan(1, "Astronomers pointed giant radio dishes into space.", "radio telescope", "impact"),
            ScenePlan(2, "The signal repeated for seven hours without interruption.", "classified signal memo", "paper_slide"),
        ],
    )
    media = MediaResult(
        video_path="output/FacelessVideo_12345.mp4",
        scenes_media=[
            {
                "scene_id": 1,
                "path": "temp/scene_1.jpg",
                "format": "ai_image",
                "source_desc": "Pollinations Flux AI Image (Prompt: 'radio telescope')",
            },
            {
                "scene_id": 2,
                "path": "temp/scene_2.jpg",
                "format": "dossier",
                "source_desc": "Procedural Classified Dossier (Pillow 3D Desk)",
            },
        ],
    )
    audio = AudioResult(
        audio_path="temp/audio_12345.mp3",
        duration=25.4,
        voice="en-US-ChristopherNeural",
    )
    video = VideoResult(
        video_path="output/FacelessVideo_12345.mp4",
        duration=25.4,
    )
    trend = TrendingTopic(
        title="Astronomers detected a strong signal from space lasting seven hours",
        summary="A repeating narrowband signal was recorded by radio observatories.",
        source="google_news",
        source_name="BBC Sky at Night Magazine",
        source_url="https://news.google.com/sample-article",
        published_date="Mon, 14 Sep 2026 07:00:00 GMT",
        search_volume="Breaking News",
        suggested_niche="glitches",
        keywords=["astronomers", "signal", "radio", "space"],
    )
    return PipelineRun(
        run_id=12345,
        niche="glitches",
        trend_topic=trend,
        content=content,
        media=media,
        audio=audio,
        video=video,
    )


class TestMetadataGeneration:
    def test_metadata_contains_all_core_sections(self, sample_pipeline_run):
        text = generate_metadata_text(sample_pipeline_run)

        # Core header
        assert "#12345" in text
        assert "glitches" in text
        assert "FacelessVideo_12345.mp4" in text

        # YouTube Shorts section
        assert "1. 📱 YOUTUBE SHORTS UPLOAD METADATA" in text
        assert "PRIMARY TITLE:" in text
        assert "VIRAL ALTERNATIVE HOOK TITLES" in text
        assert "TAGS" in text
        assert "CATEGORY:" in text

        # TikTok section
        assert "2. 🎵 TIKTOK UPLOAD METADATA" in text
        assert "RECOMMENDED CAPTION" in text
        assert "#shadowvault" in text
        assert "TIKTOK SOUND STRATEGY:" in text

        # Full Provenance section
        assert "3. 🔍 COMPLETE PROVENANCE & SOURCE AUDIT" in text
        assert "BBC Sky at Night Magazine" in text
        assert "https://news.google.com/sample-article" in text
        assert "en-US-ChristopherNeural" in text
        assert "Pollinations Flux AI Image" in text
        assert "Procedural Classified Dossier" in text
        assert "sfx/stamp_thud.wav" in text

    def test_write_metadata_file_creates_file(self, tmp_path, sample_pipeline_run):
        out_dir = str(tmp_path / "out")
        meta_path = write_metadata_file(sample_pipeline_run, output_dir=out_dir)

        assert os.path.exists(meta_path)
        assert meta_path.endswith("FacelessVideo_12345_metadata.txt")
        assert sample_pipeline_run.metadata_path == meta_path

        with open(meta_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "THE SHADOW VAULT" in content
            assert "BBC Sky at Night Magazine" in content

    def test_print_metadata_summary_executes_cleanly(self, sample_pipeline_run, capsys):
        print_metadata_summary(sample_pipeline_run)
        captured = capsys.readouterr()
        assert "VIDEO METADATA & PROVENANCE SUMMARY" in captured.out
        assert "FacelessVideo_12345.mp4" in captured.out


class TestNicheNewsScanner:
    def test_niche_news_queries_configured(self):
        assert "glitches" in NICHE_NEWS_QUERIES
        assert "heists" in NICHE_NEWS_QUERIES
        assert "dark_psychology" in NICHE_NEWS_QUERIES
        assert "horror" in NICHE_NEWS_QUERIES

    @patch("requests.get")
    def test_scan_niche_news_parses_feed(self, mock_get):
        mock_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Mysterious Deep Space Burst Detected - BBC News</title>
                    <link>https://news.google.com/sample</link>
                    <pubDate>Mon, 05 Oct 2026 12:00:00 GMT</pubDate>
                    <source url="https://bbc.com">BBC News</source>
                    <description>&lt;p&gt;Radio telescopes detected an anomaly.&lt;/p&gt;</description>
                </item>
            </channel>
        </rss>"""
        mock_resp = MagicMock()
        mock_resp.content = mock_xml
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        topics = scan_niche_news("glitches", max_items=2)
        assert len(topics) == 1
        top = topics[0]
        assert top.title == "Mysterious Deep Space Burst Detected"
        assert top.source_name == "BBC News"
        assert top.source == "google_news"
        assert top.suggested_niche == "glitches"
        assert top.source_url == "https://news.google.com/sample"
        assert "Radio telescopes detected an anomaly." in top.summary

    @patch("shadowvault.trend_scanner.scan_niche_news")
    def test_get_hottest_viral_topic_prefers_niche_news(self, mock_niche_news):
        mock_topic = TrendingTopic(
            title="Fresh Breaking Discovery",
            summary="Scientists announced a major breakthrough.",
            source="google_news",
            source_name="Nature",
            source_url="https://nature.com/news",
            suggested_niche="glitches",
        )
        mock_niche_news.return_value = [mock_topic]

        chosen = get_hottest_viral_topic(preferred_niche="glitches")
        assert chosen.title == "Fresh Breaking Discovery"
        assert chosen.source_name == "Nature"
        assert chosen.source == "google_news"
