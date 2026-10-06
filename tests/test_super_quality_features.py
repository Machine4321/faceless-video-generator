"""
tests/test_super_quality_features.py
Tests for high-retention video features:
- Procedural studio SFX generation
- Millisecond word-level timing estimation
- MrBeast / Hormozi kinetic subtitle rendering
- Dynamic emoji triggers
- Multi-scene sequence assembly & Ken Burns effect
- High-retention niche presets
"""

import os
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from shadowvault.models import WordTiming, ScenePlan, ContentResult
from shadowvault.utils.sfx_generator import (
    generate_whoosh,
    generate_impact,
    generate_cash,
    generate_glitch,
    generate_heartbeat,
    ensure_default_sfx,
)
from shadowvault.audio import _generate_estimated_word_timings
from shadowvault.video import (
    _detect_emoji,
    _render_kinetic_chunk_frame,
    _build_kinetic_subtitle_clips,
    _create_ken_burns_clip,
    _build_multi_scene_background,
)
from shadowvault.media import fetch_scene_media, fetch_multi_scene_media
from shadowvault.content import NICHE_CONFIG


# ---------------------------------------------------------------------------
# SFX Generator Tests
# ---------------------------------------------------------------------------

class TestSFXGenerator:
    def test_whoosh_shape_and_range(self):
        audio = generate_whoosh(0.4)
        assert isinstance(audio, np.ndarray)
        assert len(audio) > 1000
        assert np.max(np.abs(audio)) <= 1.0

    def test_impact_decay(self):
        audio = generate_impact(0.8)
        assert isinstance(audio, np.ndarray)
        assert len(audio) > 1000
        # Peak near beginning, decay towards end
        first_quarter = np.max(np.abs(audio[:len(audio)//4]))
        last_quarter = np.max(np.abs(audio[3*len(audio)//4:]))
        assert first_quarter > last_quarter

    def test_cash_chime(self):
        audio = generate_cash(0.5)
        assert isinstance(audio, np.ndarray)
        assert np.max(np.abs(audio)) <= 1.0

    def test_glitch_noise(self):
        audio = generate_glitch(0.3)
        assert isinstance(audio, np.ndarray)
        assert np.max(np.abs(audio)) <= 1.0

    def test_heartbeat_pulse(self):
        audio = generate_heartbeat(0.8)
        assert isinstance(audio, np.ndarray)
        assert np.max(np.abs(audio)) <= 1.0

    def test_ensure_default_sfx_creates_files(self, tmp_path):
        sfx_dir = str(tmp_path / "sfx")
        paths = ensure_default_sfx(sfx_dir)
        for name in ["whoosh", "impact", "cash", "glitch", "heartbeat"]:
            assert name in paths
            assert os.path.isfile(paths[name])
            assert os.path.getsize(paths[name]) > 500


# ---------------------------------------------------------------------------
# Word Timing Alignment Tests
# ---------------------------------------------------------------------------

class TestWordTimingEstimation:
    def test_estimated_timings_cover_duration(self):
        text = "He stole one hundred million dollars from the vault"
        duration = 3.5
        timings = _generate_estimated_word_timings(text, duration)
        assert len(timings) == len(text.split())
        assert timings[0].start == 0.0
        assert timings[-1].end <= duration
        # Check monotonic progression
        for i in range(len(timings) - 1):
            assert timings[i].start <= timings[i+1].start

    def test_empty_text_returns_empty(self):
        assert _generate_estimated_word_timings("", 5.0) == []
        assert _generate_estimated_word_timings("hello", 0.0) == []


# ---------------------------------------------------------------------------
# Kinetic Subtitle & Emoji Tests
# ---------------------------------------------------------------------------

class TestKineticCaptions:
    def test_detect_emoji_matches_money(self):
        assert _detect_emoji(["stole", "millions"]) in ["💰", "💸", "🥷"]
        assert _detect_emoji(["bank", "vault"]) in ["🏦", "💎"]
        assert _detect_emoji(["fbi", "police"]) in ["🚨", "🕵️", "👮"]
        assert _detect_emoji(["random", "unrelated"]) is None

    def test_render_kinetic_chunk_frame(self):
        words = ["HEIST", "OF", "THE", "CENTURY"]
        frame = _render_kinetic_chunk_frame(
            words_in_chunk=words,
            active_idx=0,
            canvas_w=1080,
            canvas_h=420,
        )
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (420, 1080, 4)
        # Non-transparent pixels present
        assert frame[:, :, 3].max() > 0

    def test_build_kinetic_subtitle_clips(self):
        timings = [
            WordTiming("He", 0.0, 0.3),
            WordTiming("left", 0.3, 0.6),
            WordTiming("the", 0.6, 0.8),
            WordTiming("vault", 0.8, 1.2),
        ]
        clips = _build_kinetic_subtitle_clips(timings, output_width=1080, words_per_chunk=2)
        # 4 words in chunks of 2 words -> each word gets its active clip
        assert len(clips) == 4
        assert clips[0].start == 0.0
        assert clips[0].duration >= 0.12


# ---------------------------------------------------------------------------
# Multi-Scene Media & Ken Burns Tests
# ---------------------------------------------------------------------------

class TestMultiSceneMedia:
    def test_procedural_scene_generation(self, tmp_path):
        scene = ScenePlan(
            scene_id=1,
            narration="He bypassed laser security",
            visual_query="vault lasers",
            sfx_cue="impact",
        )
        item = fetch_scene_media(scene, str(tmp_path), api_key="")
        assert item["scene_id"] == 1
        assert os.path.isfile(item["path"])
        assert item["type"] == "image"

    def test_fetch_multi_scene_media(self, tmp_path):
        scenes = [
            ScenePlan(1, "Scene one narration", "query 1", "impact"),
            ScenePlan(2, "Scene two narration", "query 2", "whoosh"),
            ScenePlan(3, "Scene three narration", "query 3", "cash"),
        ]
        res = fetch_multi_scene_media(scenes, str(tmp_path), api_key="")
        assert len(res.scenes_media) == 3
        for item in res.scenes_media:
            assert os.path.isfile(item["path"])

    def test_ken_burns_clip_creation(self, tmp_path):
        # Create a test image
        from PIL import Image
        img_path = str(tmp_path / "test_photo.jpg")
        img = Image.new("RGB", (1200, 1600), (40, 50, 70))
        img.save(img_path)

        clip = _create_ken_burns_clip(img_path, duration=2.0, target_w=1080, target_h=1920)
        assert clip.duration == 2.0
        frame = clip.get_frame(1.0)
        assert frame.shape == (1920, 1080, 3)

    def test_build_multi_scene_background(self, tmp_path):
        from PIL import Image
        scenes_media = []
        for i in range(3):
            p = str(tmp_path / f"scene_{i}.jpg")
            Image.new("RGB", (800, 1200), (20*i, 30*i, 40*i)).save(p)
            scenes_media.append({"scene_id": i+1, "path": p, "type": "image"})

        bg = _build_multi_scene_background(scenes_media, total_duration=6.0, output_width=1080, output_height=1920)
        assert bg.duration == 6.0


# ---------------------------------------------------------------------------
# High-Retention Niche Presets Tests
# ---------------------------------------------------------------------------

class TestViralNiches:
    def test_viral_niches_exist(self):
        for niche in ["heists", "glitches", "business", "dark_psychology", "horror", "motivation", "facts"]:
            assert niche in NICHE_CONFIG
            fb = NICHE_CONFIG[niche]["fallback"]
            assert isinstance(fb, ContentResult)
            assert len(fb.scenes) >= 4, f"{niche} fallback should have at least 4 scenes"
            for sc in fb.scenes:
                assert sc.narration
                assert sc.visual_query


class TestWatermarkAndTrends:
    def test_watermark_empty_returns_blank(self):
        from shadowvault.video import _render_watermark_frame
        frame = _render_watermark_frame(1080, 1920, handle="")
        assert frame.shape == (1920, 1080, 4)
        assert frame[:, :, 3].max() == 0, "Empty handle must result in 100% transparent frame"

    def test_watermark_with_handle_renders(self):
        from shadowvault.video import _render_watermark_frame
        frame = _render_watermark_frame(1080, 1920, handle="@MyCustomHandle")
        assert frame.shape == (1920, 1080, 4)
        assert frame[:, :, 3].max() > 0, "Custom handle must render text"

    def test_content_with_trend_topic(self):
        from shadowvault.content import generate_content
        from shadowvault.models import TrendingTopic
        topic = TrendingTopic(
            title="Youngest Exoplanet Discovered",
            summary="Astronomers detected a baby planet.",
            source="google_trends",
            suggested_niche="facts",
        )
        # Using api_key="fake-key" triggers the dynamic trend fallback safely
        res = generate_content(api_key="fake-key", topic=topic)
        assert "YOUNGEST EXOPLANET" in res.title.upper()
        assert len(res.scenes) >= 3


class TestRadarAndPacingEnhancements:
    def test_radar_ping_sfx_generation(self):
        from shadowvault.utils.sfx_generator import generate_radar_ping
        audio = generate_radar_ping(0.5)
        assert isinstance(audio, np.ndarray)
        assert len(audio) > 1000
        assert np.max(np.abs(audio)) <= 1.0

    def test_render_radar_scope_frame(self, tmp_path):
        from shadowvault.graphics import render_radar_scope_frame
        dest = str(tmp_path / "radar.jpg")
        out = render_radar_scope_frame(target_name="TEST SIGNAL", dest_path=dest)
        assert os.path.isfile(out)
        assert os.path.getsize(out) > 5000

    def test_fetch_scene_media_radar_format(self, tmp_path):
        scene = ScenePlan(
            scene_id=2,
            narration="A strange signal was detected.",
            visual_query="deep space frequency",
            visual_format="radar",
        )
        res = fetch_scene_media(scene, str(tmp_path), api_key="fake-key")
        assert res["format"] == "radar"
        assert res["type"] == "image"
        assert os.path.isfile(res["path"])

    def test_kinetic_subtitles_strict_non_overlapping(self):
        timings = [
            WordTiming("LEAKED", 0.50, 0.85),
            WordTiming("SENATE", 0.80, 1.20),
            WordTiming("MEMO", 1.25, 1.60),
            WordTiming("REVEALED", 1.55, 2.00),
        ]
        clips = _build_kinetic_subtitle_clips(timings, output_width=1080)
        assert len(clips) == 4
        # Verify strict non-overlapping constraint: clip[i] end <= clip[i+1] start
        for i in range(len(clips) - 1):
            c_curr = clips[i]
            c_next = clips[i + 1]
            curr_end = c_curr.start + c_curr.duration
            next_start = c_next.start
            assert curr_end <= next_start + 1e-4, f"Clips {i} and {i+1} overlap! {curr_end} > {next_start}"

    def test_split_into_scenes_doubled_rhythm(self):
        from shadowvault.content import _split_into_scenes
        script = (
            "On August 15, 1977, a radio telescope in Ohio intercepted an artificial signal from deep space. "
            "It was thirty times louder than cosmic background noise. "
            "The frequency was locked exactly to 1,420 megahertz, the hydrogen line. "
            "Astronomer Jerry Ehman circled the code on a printout and scribbled Wow. "
            "The signal broadcast continuously for seventy-two seconds."
        )
        scenes = _split_into_scenes(script, "deep space")
        # Should produce 8 or more micro-scenes for doubled visual rhythm
        assert len(scenes) >= 8
        formats = {s.visual_format for s in scenes}
        assert "radar" in formats
        assert "dossier" in formats
        assert "ai_image" in formats


