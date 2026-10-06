"""
shadowvault/graphics.py
Procedural Documentary & Evidence Motion Graphics Generator (Vox / MagnatesMedia style).

Renders broadcast-quality 1080x1920 graphic frames:
- Newspaper Breaking News Clipping (with fluorescent highlighter marker wipe)
- Classified FBI / CIA Dossier (with red rubber stamp & black redaction bars)
- Stat & Number Counter Badge (for money and dates)
- 35mm Analog Film Grain Overlay
"""

from __future__ import annotations

import logging
import os
import random
import textwrap
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)


def _load_font(
    family: str = "sans",
    size: int = 40,
    bold: bool = False,
) -> ImageFont.FreeTypeFont:
    """Load appropriate system font on Windows/Linux."""
    if family == "serif":
        candidates = [
            r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf",
            "times.ttf",
            "georgia.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]
    elif family == "mono":
        candidates = [
            r"C:\Windows\Fonts\courbd.ttf" if bold else r"C:\Windows\Fonts\cour.ttf",
            "cour.ttf",
            "consolas.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    elif family == "impact":
        candidates = [
            r"C:\Windows\Fonts\impact.ttf",
            "impact.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ]
    else:  # sans
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
            "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def add_film_grain(img: Image.Image, intensity: float = 8.0) -> Image.Image:
    """Add subtle organic 35mm film grain to break digital sterility."""
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, intensity, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def render_newspaper_frame(
    headline: str,
    snippet: str = "",
    date_str: str = "SPECIAL REPORT",
    dest_path: str = "",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    Render a high-impact vintage/modern newspaper clipping with a fluorescent highlighter effect.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    # Aged paper background
    paper_color = random.choice([
        (243, 238, 228),  # Classic vintage cream
        (238, 233, 222),  # Slightly aged parchment
        (246, 243, 236),  # Modern broadsheet off-white
    ])
    img = Image.new("RGB", (width, height), paper_color)
    draw = ImageDraw.Draw(img)

    # Top Masthead Lines
    draw.line([(50, 160), (width - 50, 160)], fill=(30, 30, 30), width=4)
    draw.line([(50, 172), (width - 50, 172)], fill=(30, 30, 30), width=2)

    # Masthead Name
    font_masthead = _load_font("serif", size=60, bold=True)
    draw.text((width // 2, 240), "THE GLOBAL CHRONICLE", fill=(20, 20, 20), font=font_masthead, anchor="mm")

    draw.line([(50, 305), (width - 50, 305)], fill=(30, 30, 30), width=3)

    # Sub-bar (Date, Edition)
    font_sub = _load_font("sans", size=24, bold=False)
    draw.text((width // 2, 340), f"WORLD EXCLUSIVE • {date_str.upper()} • BREAKING DISPATCH", fill=(75, 75, 75), font=font_sub, anchor="mm")
    draw.line([(50, 375), (width - 50, 375)], fill=(30, 30, 30), width=2)

    # Main Headline (All-caps, high-impact)
    font_hl = _load_font("impact", size=86)
    wrapped = textwrap.fill(headline.upper(), width=18)
    lines = wrapped.split("\n")

    # Center headline vertically around y = 620
    start_y = 540
    line_h = 100
    total_hl_h = len(lines) * line_h

    # Highlighter wipe layer
    highlighter = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(highlighter)

    # Highlight the most dramatic line in fluorescent yellow
    hl_line_idx = min(1, len(lines) - 1)
    hl_y = start_y + (hl_line_idx * line_h)
    h_draw.rectangle([80, hl_y - 10, width - 80, hl_y + 85], fill=(255, 235, 0, 125))
    img.paste(highlighter, (0, 0), highlighter)

    # Draw headline text
    curr_y = start_y
    for line in lines:
        draw.text((width // 2, curr_y + 40), line, fill=(15, 15, 15), font=font_hl, anchor="mm")
        curr_y += line_h

    # Divider below headline
    draw.line([(60, curr_y + 30), (width - 60, curr_y + 30)], fill=(30, 30, 30), width=3)

    # Simulated newspaper columns below
    col_w = (width - 160) // 2
    y_body = curr_y + 70
    font_body = _load_font("serif", size=26, bold=False)

    col1_text = (
        snippet or
        "Investigative authorities confirmed the unprecedented details early this morning. "
        "Key witnesses reported irregular activities that completely bypassed conventional detection systems. "
        "According to confidential sources close to the inquiry, the operation required months of meticulous coordination."
    )
    col2_text = (
        "Independent analysts were left stunned as further documentation surfaced today. "
        "Questions remain unanswered regarding the true scale of the impact. "
        "International observers are calling this one of the most remarkable incidents in modern record."
    )

    draw.multiline_text((80, y_body), textwrap.fill(col1_text, width=28), fill=(45, 45, 45), font=font_body, spacing=10)
    draw.line([(width // 2, y_body), (width // 2, y_body + 420)], fill=(120, 120, 120), width=1)
    draw.multiline_text((width // 2 + 30, y_body), textwrap.fill(col2_text, width=28), fill=(45, 45, 45), font=font_body, spacing=10)

    # Apply authentic 35mm film grain
    img = add_film_grain(img, intensity=9.0)
    img.save(dest_path, "JPEG", quality=95)
    return dest_path


def render_classified_dossier(
    title: str,
    body_text: str,
    case_id: str = "CASE FILE #8492-X",
    stamp_text: str = "TOP SECRET",
    dest_path: str = "",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    Render a classified FBI / CIA document with redacted censor bars and red rubber stamp.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    # Dark tactical background
    img = Image.new("RGB", (width, height), (32, 30, 28))
    draw = ImageDraw.Draw(img)

    # Inner document sheet
    pad = 70
    doc_bg = (226, 219, 206)
    draw.rectangle([pad, pad + 80, width - pad, height - pad - 80], fill=doc_bg)
    draw.rectangle([pad + 16, pad + 96, width - pad - 16, height - pad - 96], outline=(65, 60, 55), width=2)

    # Header
    font_hdr = _load_font("mono", size=36, bold=True)
    draw.text((width // 2, pad + 150), "FEDERAL INVESTIGATION ARCHIVE", fill=(35, 30, 25), font=font_hdr, anchor="mm")
    draw.text((width // 2, pad + 200), "SPECIAL INTELLIGENCE DIVISION // EYES ONLY", fill=(95, 85, 75), font=font_hdr, anchor="mm")
    draw.line([(pad + 50, pad + 240), (width - pad - 50, pad + 240)], fill=(70, 65, 60), width=2)

    # Metadata
    font_meta = _load_font("mono", size=26, bold=False)
    draw.text((pad + 60, pad + 280), f"REF: {case_id.upper()}", fill=(50, 45, 40), font=font_meta)
    draw.text((pad + 60, pad + 325), "STATUS: DECLASSIFIED UNDER DIRECTIVE 14-B", fill=(175, 35, 35), font=font_meta)
    draw.text((pad + 60, pad + 370), f"SUBJECT: {title.upper()[:36]}", fill=(50, 45, 40), font=font_meta)
    draw.line([(pad + 50, pad + 415), (width - pad - 50, pad + 415)], fill=(70, 65, 60), width=2)

    # Typewriter Body Text
    font_body = _load_font("mono", size=34, bold=True)
    y = pad + 480
    lines = textwrap.wrap(body_text.upper(), width=32)

    for idx, line in enumerate(lines):
        draw.text((pad + 60, y), line, fill=(35, 30, 25), font=font_body)

        # Draw realistic black redaction censor bars on select lines
        if idx in {1, 3} and len(line) > 10:
            bar_start = pad + 60 + random.randint(0, 100)
            bar_len = random.randint(220, 400)
            draw.rectangle([bar_start, y - 6, min(width - pad - 60, bar_start + bar_len), y + 38], fill=(15, 15, 15))

        y += 65

    # Red Rubber Stamp (Angled Grunge Stamp)
    stamp_w, stamp_h = 480, 150
    stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stamp_img)
    s_draw.rectangle([8, 8, stamp_w - 8, stamp_h - 8], outline=(195, 30, 30, 225), width=8)
    font_stamp = _load_font("impact", size=70)
    s_draw.text((stamp_w // 2, stamp_h // 2), stamp_text.upper(), fill=(195, 30, 30, 225), font=font_stamp, anchor="mm")

    # Rotate stamp
    angle = random.choice([-14, -10, 12, 16])
    stamp_rot = stamp_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    pos_x = width - stamp_rot.width - 100
    pos_y = height - stamp_rot.height - 350
    img.paste(stamp_rot, (pos_x, pos_y), stamp_rot)

    img = add_film_grain(img, intensity=8.5)
    img.save(dest_path, "JPEG", quality=95)
    return dest_path


def render_stat_counter_card(
    stat_value: str,
    stat_label: str,
    dest_path: str = "",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    Render a high-tech glowing stat card (e.g. '$100,000,000' or 'YEAR 1518').
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    img = Image.new("RGB", (width, height), (12, 14, 20))
    draw = ImageDraw.Draw(img)

    # Ambient glowing background circle
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([200, 600, width - 200, height - 600], fill=(255, 215, 0, 30))
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    img.paste(glow, (0, 0), glow)

    # Center card outline
    draw.rectangle([80, 580, width - 80, height - 580], outline=(255, 215, 0, 160), width=3)

    # Stat Label
    font_lbl = _load_font("sans", size=36, bold=True)
    draw.text((width // 2, 720), stat_label.upper(), fill=(200, 200, 200), font=font_lbl, anchor="mm")

    # Giant Stat Value
    font_val = _load_font("impact", size=115)
    draw.text((width // 2, 880), stat_value.upper(), fill=(255, 225, 0), font=font_val, anchor="mm")

    img = add_film_grain(img, intensity=7.0)
    img.save(dest_path, "JPEG", quality=95)
    return dest_path
