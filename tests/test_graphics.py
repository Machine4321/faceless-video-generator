"""
tests/test_graphics.py
Unit tests for shadowvault.graphics and shadowvault.image_gen.
"""

import os
from unittest.mock import MagicMock, patch

from shadowvault.graphics import (
    add_film_grain,
    render_classified_dossier,
    render_newspaper_frame,
    render_stat_counter_card,
)
from shadowvault.image_gen import generate_ai_image


def test_render_newspaper_frame(tmp_path):
    dest = str(tmp_path / "newspaper.jpg")
    out = render_newspaper_frame(
        headline="THIEF STEALS $100M IN DIAMONDS",
        snippet="Police confirmed the heist happened at midnight.",
        dest_path=dest,
    )
    assert os.path.isfile(out)
    assert os.path.getsize(out) > 5000


def test_render_classified_dossier(tmp_path):
    dest = str(tmp_path / "dossier.jpg")
    out = render_classified_dossier(
        title="ANTWERP OPERATION",
        body_text="Subject bypassed ten security layers undetected.",
        dest_path=dest,
    )
    assert os.path.isfile(out)
    assert os.path.getsize(out) > 5000


def test_render_stat_counter_card(tmp_path):
    dest = str(tmp_path / "counter.jpg")
    out = render_stat_counter_card(
        stat_value="$100,000,000",
        stat_label="TOTAL VALUE TAKEN",
        dest_path=dest,
    )
    assert os.path.isfile(out)
    assert os.path.getsize(out) > 5000


@patch("shadowvault.image_gen.requests.get")
def test_generate_ai_image_success(mock_get, tmp_path):
    from PIL import Image
    dest = str(tmp_path / "ai_img.jpg")
    img = Image.new("RGB", (768, 1344), (20, 25, 35))
    img.save(dest, "JPEG")
    with open(dest, "rb") as f:
        fake_content = f.read()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = fake_content
    mock_get.return_value = mock_resp

    success = generate_ai_image(prompt="dark bank vault", dest_path=dest)
    assert success is True
    assert os.path.isfile(dest)
