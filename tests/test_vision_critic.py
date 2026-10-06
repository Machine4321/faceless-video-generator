"""
tests/test_vision_critic.py
Unit tests for Gemini Vision Critic visual inspection.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest

from shadowvault.vision_critic import verify_image_relevance


@pytest.fixture
def sample_image(tmp_path):
    img_path = str(tmp_path / "test_frame.jpg")
    img = Image.new("RGB", (300, 300), color=(40, 50, 70))
    img.save(img_path)
    return img_path


def test_verify_image_nonexistent_file():
    passed, score, reason = verify_image_relevance("nonexistent_path_xyz.jpg", "narration")
    assert passed is False
    assert score == 0


def test_verify_image_offline_mode(sample_image):
    passed, score, reason = verify_image_relevance(
        sample_image,
        narration="Two thieves broke into the gallery",
        api_key="fake-key",
    )
    assert passed is True
    assert score == 100
    assert "Offline" in reason


def test_verify_image_rejection_low_score(sample_image):
    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"match": false, "score": 35, "reason": "Fashion model detected instead of museum vault"}'
        mock_instance.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_instance

        passed, score, reason = verify_image_relevance(
            sample_image,
            narration="Two thieves broke into the gallery",
            visual_query="art museum gallery",
            api_key="live-key-abc",
        )
        assert passed is False
        assert score == 35
        assert "Fashion model" in reason


def test_verify_image_accepted(sample_image):
    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"match": true, "score": 92, "reason": "Dark gallery hallway matches heist mood"}'
        mock_instance.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_instance

        passed, score, reason = verify_image_relevance(
            sample_image,
            narration="Two thieves broke into the gallery",
            visual_query="art museum gallery",
            api_key="live-key-abc",
        )
        assert passed is True
        assert score == 92
        assert "Dark gallery" in reason
