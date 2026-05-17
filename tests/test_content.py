"""Tests for shadowvault.content - JSON parsing and fallback logic."""

import json
import pytest

from shadowvault.content import (
    _parse_response, _pick_hook, _build_prompt,
    NICHE_CONFIG, WORD_COUNTS, DEFAULT_NICHE, generate_content,
)
from shadowvault.models import ContentResult


class TestParseResponse:
    def test_valid_json(self):
        raw = json.dumps({
            "title": "SCARY TITLE",
            "script": "The story begins here.",
            "visual_search": "dark forest",
            "tags": "#horror #scary #fyp",
        })
        result = _parse_response(raw, "horror", "The story begins.")
        assert isinstance(result, ContentResult)
        assert result.title == "SCARY TITLE"
        assert result.script == "The story begins here."
        assert result.visual_search_keyword == "dark"
        assert result.niche == "horror"
        assert result.hook == "The story begins."

    def test_json_with_markdown_fences(self):
        raw = '```json\n' + json.dumps({
            "title": "TITLE",
            "script": "Script text.",
            "visual_search": "horror",
            "tags": "#tags",
        }) + '\n```'
        result = _parse_response(raw, "facts", "hook")
        assert result.title == "TITLE"

    def test_missing_keys_raises(self):
        raw = json.dumps({"title": "TITLE"})
        with pytest.raises(ValueError, match="missing keys"):
            _parse_response(raw, "horror", "hook")

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_response("not json at all", "horror", "hook")

    def test_visual_search_takes_first_word(self):
        raw = json.dumps({
            "title": "T",
            "script": "S",
            "visual_search": "foggy forest night",
            "tags": "#t",
        })
        result = _parse_response(raw, "horror", "h")
        assert result.visual_search_keyword == "foggy"


class TestNicheConfig:
    def test_all_niches_have_required_keys(self):
        for niche_name, cfg in NICHE_CONFIG.items():
            assert "hooks" in cfg, f"{niche_name} missing hooks"
            assert "style" in cfg, f"{niche_name} missing style"
            assert "fallback" in cfg, f"{niche_name} missing fallback"
            assert len(cfg["hooks"]) > 0, f"{niche_name} has no hooks"

    def test_fallbacks_are_content_results(self):
        for niche_name, cfg in NICHE_CONFIG.items():
            fb = cfg["fallback"]
            assert isinstance(fb, ContentResult)
            assert fb.title
            assert fb.script
            assert fb.niche == niche_name


class TestGenerateContentFallback:
    def test_fallback_on_invalid_api_key(self):
        """With an invalid API key, should fall back gracefully."""
        result = generate_content(
            niche="horror",
            api_key="invalid-key-xxx",
            model="gemini-2.0-flash",
        )
        assert isinstance(result, ContentResult)
        assert result.title  # fallback has a title
        assert result.niche == "horror"

    def test_unknown_niche_defaults_to_horror(self):
        result = generate_content(
            niche="nonexistent",
            api_key="invalid-key-xxx",
            model="gemini-2.0-flash",
        )
        assert result.niche == "horror"

    def test_motivation_fallback(self):
        result = generate_content(
            niche="motivation",
            api_key="invalid-key-xxx",
            model="gemini-2.0-flash",
        )
        assert result.niche == "motivation"
        assert result.title

    def test_facts_fallback(self):
        result = generate_content(
            niche="facts",
            api_key="invalid-key-xxx",
            model="gemini-2.0-flash",
        )
        assert result.niche == "facts"
        assert result.title


class TestPickHook:
    def test_returns_string(self):
        hook = _pick_hook("horror")
        assert isinstance(hook, str)
        assert len(hook) > 0

    def test_hook_from_correct_niche(self):
        for niche in ["horror", "motivation", "facts"]:
            hook = _pick_hook(niche)
            assert hook in NICHE_CONFIG[niche]["hooks"]

    def test_unknown_niche_falls_back_to_default(self):
        hook = _pick_hook("nonexistent")
        assert hook in NICHE_CONFIG[DEFAULT_NICHE]["hooks"]


class TestBuildPrompt:
    def test_contains_hook(self):
        prompt = _build_prompt("horror", "This is a test hook.", "short")
        assert "This is a test hook." in prompt

    def test_contains_word_count(self):
        prompt = _build_prompt("horror", "Hook.", "short")
        assert str(WORD_COUNTS["short"]) in prompt

    def test_long_length(self):
        prompt = _build_prompt("horror", "Hook.", "long")
        assert str(WORD_COUNTS["long"]) in prompt

    def test_contains_niche_style(self):
        prompt = _build_prompt("motivation", "Hook.", "short")
        assert "motivational" in prompt.lower()

    def test_requests_json_output(self):
        prompt = _build_prompt("horror", "Hook.", "short")
        assert "JSON" in prompt
        assert '"title"' in prompt
        assert '"script"' in prompt

    def test_all_niches_produce_prompts(self):
        for niche in NICHE_CONFIG:
            prompt = _build_prompt(niche, "Hook text.", "short")
            assert len(prompt) > 100


class TestParseResponseEdgeCases:
    def test_cleans_markdown_from_values(self):
        raw = json.dumps({
            "title": "**BOLD TITLE**",
            "script": "Script with [brackets] and #hashes",
            "visual_search": "dark",
            "tags": "#tag1 #tag2",
        })
        result = _parse_response(raw, "horror", "hook")
        assert "**" not in result.title
        assert "[" not in result.script
        assert "#" not in result.script

    def test_whitespace_in_response(self):
        raw = '  \n  ' + json.dumps({
            "title": "T",
            "script": "S",
            "visual_search": "v",
            "tags": "#t",
        }) + '  \n  '
        result = _parse_response(raw, "horror", "hook")
        assert result.title == "T"

    def test_extra_keys_ignored(self):
        raw = json.dumps({
            "title": "T",
            "script": "S",
            "visual_search": "v",
            "tags": "#t",
            "extra_field": "ignored",
        })
        result = _parse_response(raw, "horror", "hook")
        assert result.title == "T"
