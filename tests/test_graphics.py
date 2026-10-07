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


def test_procedural_foley_sfx(tmp_path):
    from shadowvault.utils.sfx_generator import (
        ensure_default_sfx,
        generate_highlighter,
        generate_paper_slide,
        generate_stamp_thud,
        generate_ticker,
    )

    sfx_map = ensure_default_sfx(str(tmp_path / "sfx"))
    assert "stamp_thud" in sfx_map
    assert "paper_slide" in sfx_map
    assert "highlighter" in sfx_map
    assert "ticker" in sfx_map

    for name in ["stamp_thud", "paper_slide", "highlighter", "ticker"]:
        assert os.path.isfile(sfx_map[name])
        assert os.path.getsize(sfx_map[name]) > 500


def test_parse_stat_from_narration():
    from shadowvault.graphics import parse_stat_from_narration

    # 1. Word number with tons
    num, pre, suf, lbl = parse_stat_from_narration(
        "Instead, eighty-four thousand tons of space debris vaporize there annually."
    )
    assert num == 84000
    assert pre == ""
    assert suf == "TONS"
    assert "DEBRIS" in lbl

    # 2. Word number with dollars
    num, pre, suf, lbl = parse_stat_from_narration(
        "Thieves stole one hundred million dollars in diamonds."
    )
    assert num == 100000000
    assert pre == "$"
    assert "VALUATION" in lbl or "FINANCIAL" in lbl

    # 3. Hours duration
    num, pre, suf, lbl = parse_stat_from_narration(
        "The signal lasted for seven hours without interruption."
    )
    assert num == 7
    assert suf == "HOURS"
    assert "DURATION" in lbl


def test_render_animated_counter_video(tmp_path):
    from shadowvault.graphics import render_animated_counter_video

    dest = str(tmp_path / "test_counter.mp4")
    out = render_animated_counter_video(
        target_value=84000,
        prefix="",
        suffix="TONS",
        stat_label="ANNUAL SPACE DEBRIS",
        dest_path=dest,
        duration=1.5,
        fps=15,
        width=360,
        height=640,
    )
    assert os.path.isfile(out)
    assert os.path.getsize(out) > 1000


def test_render_hook_banner_frame():
    from shadowvault.graphics import render_hook_banner_frame
    import numpy as np

    frame = render_hook_banner_frame(
        headline="THE $100M APPLE HEIST",
        category="CLASSIFIED CASE",
        canvas_w=1080,
        canvas_h=1920,
    )
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (1920, 1080, 4)
    # Check that alpha channel has non-transparent pixels
    assert np.max(frame[:, :, 3]) > 200


