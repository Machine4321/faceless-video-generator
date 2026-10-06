"""
shadowvault/graphics.py
Procedural Documentary & Evidence Motion Graphics Generator (Vox / MagnatesMedia style).

Renders broadcast-quality 1080x1920 graphic frames:
- Newspaper Breaking News Clipping (physical paper on investigation desk + fluorescent highlighter wipe)
- Classified FBI / CIA Dossier (aged parchment with drop shadow, red rubber stamp & black redaction bars)
- Stat & Number Counter Badge (for money, metrics, and dates)
- 35mm Analog Film Grain Overlay
"""

from __future__ import annotations

import logging
import math
import os
import random
import re
import textwrap
from typing import Optional

import imageio
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


def add_film_grain(img: Image.Image, intensity: float = 7.5) -> Image.Image:
    """Add subtle organic 35mm film grain to break digital sterility."""
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, intensity, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _composite_sheet_on_desk(
    sheet: Image.Image,
    desk_color: tuple[int, int, int] = (18, 16, 14),
    angle: float = -1.8,
    desk_w: int = 1080,
    desk_h: int = 1920,
    center_y: int = 860,
) -> Image.Image:
    """
    Composite a physical document sheet with soft blurred drop shadow onto a dark desk surface.
    Gives realistic 3D depth and separation typical of Vox / MagnatesMedia documentaries.
    """
    bg = Image.new("RGB", (desk_w, desk_h), desk_color)
    bg_draw = ImageDraw.Draw(bg)

    # Subtle vignette / light falloff on desk
    vignette = Image.new("RGBA", (desk_w, desk_h), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    v_draw.ellipse([80, 200, desk_w - 80, desk_h - 200], fill=(255, 255, 255, 18))
    vignette = vignette.filter(ImageFilter.GaussianBlur(160))
    bg.paste(vignette, (0, 0), vignette)

    sw, sh = sheet.size

    # Realistic blurred drop shadow
    shadow_pad = 60
    shadow = Image.new("RGBA", (sw + shadow_pad * 2, sh + shadow_pad * 2), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rectangle([shadow_pad, shadow_pad, sw + shadow_pad, sh + shadow_pad], fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))

    # Apply subtle physical angle
    sheet_rot = sheet.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    shadow_rot = shadow.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

    pos_x = (desk_w - sheet_rot.width) // 2
    pos_y = center_y - (sheet_rot.height // 2)

    # Offset shadow down-right to simulate overhead office desk lighting
    bg.paste(shadow_rot, (pos_x - 12, pos_y + 18), shadow_rot)
    bg.paste(sheet_rot, (pos_x, pos_y), sheet_rot)

    return bg


def render_newspaper_frame(
    headline: str,
    snippet: str = "",
    date_str: str = "SPECIAL REPORT",
    dest_path: str = "",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    Render a high-impact newspaper clipping resting on an investigation desk
    with a vibrant fluorescent yellow highlighter marker wipe.
    """
    if dest_path and os.path.dirname(dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    sheet_w, sheet_h = 940, 1540
    paper_tints = [
        (244, 239, 230, 255),  # Vintage warm newsprint
        (240, 236, 226, 255),  # Aged editorial archive
        (238, 232, 220, 255),  # Sepia dispatch
    ]
    paper_color = random.choice(paper_tints)
    sheet = Image.new("RGBA", (sheet_w, sheet_h), paper_color)
    draw = ImageDraw.Draw(sheet)

    # Top Masthead Lines
    draw.line([(40, 50), (sheet_w - 40, 50)], fill=(30, 30, 30), width=4)
    draw.line([(40, 60), (sheet_w - 40, 60)], fill=(30, 30, 30), width=2)

    # Dynamic Masthead Name
    mastheads = [
        "THE GLOBAL CHRONICLE",
        "THE DAILY INVESTIGATOR",
        "THE EVENING DISPATCH",
        "INTERNATIONAL HERALD",
        "THE NATIONAL TRIBUNE",
    ]
    font_masthead = _load_font("serif", size=52, bold=True)
    draw.text((sheet_w // 2, 115), random.choice(mastheads), fill=(20, 20, 20), font=font_masthead, anchor="mm")

    draw.line([(40, 170), (sheet_w - 40, 170)], fill=(30, 30, 30), width=3)

    # Sub-bar (Date, Edition)
    font_sub = _load_font("sans", size=22, bold=False)
    draw.text((sheet_w // 2, 200), f"WORLD EXCLUSIVE • {date_str.upper()} • BREAKING DISPATCH", fill=(75, 75, 75), font=font_sub, anchor="mm")
    draw.line([(40, 230), (sheet_w - 40, 230)], fill=(30, 30, 30), width=2)

    # Main Headline (All-caps, high-impact)
    font_hl = _load_font("impact", size=76)
    wrapped = textwrap.fill(headline.upper(), width=20)
    lines = wrapped.split("\n")

    start_y = 280
    line_h = 88
    total_hl_h = len(lines) * line_h

    # Highlighter wipe layer
    highlighter = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(highlighter)

    # Highlight the most dramatic line in fluorescent yellow
    hl_line_idx = min(1, len(lines) - 1)
    hl_y = start_y + (hl_line_idx * line_h)
    h_draw.rectangle([50, hl_y - 8, sheet_w - 50, hl_y + 76], fill=(255, 235, 0, 140))
    sheet.paste(highlighter, (0, 0), highlighter)

    # Draw headline text
    curr_y = start_y
    for line in lines:
        draw.text((sheet_w // 2, curr_y + 36), line, fill=(15, 15, 15), font=font_hl, anchor="mm")
        curr_y += line_h

    # Divider below headline
    draw.line([(40, curr_y + 25), (sheet_w - 40, curr_y + 25)], fill=(30, 30, 30), width=3)

    # Simulated newspaper columns below
    y_body = curr_y + 55
    font_body = _load_font("serif", size=24, bold=False)

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

    draw.multiline_text((60, y_body), textwrap.fill(col1_text, width=24), fill=(45, 45, 45), font=font_body, spacing=8)
    draw.line([(sheet_w // 2, y_body), (sheet_w // 2, y_body + 380)], fill=(130, 130, 130), width=1)
    draw.multiline_text((sheet_w // 2 + 25, y_body), textwrap.fill(col2_text, width=24), fill=(45, 45, 45), font=font_body, spacing=8)

    # Composite physical paper onto dark investigation desk
    desk_rot = random.uniform(-2.2, -1.2)
    desk = _composite_sheet_on_desk(sheet, desk_color=(18, 16, 14), angle=desk_rot, center_y=820)
    desk = add_film_grain(desk, intensity=8.0)
    desk.save(dest_path, "JPEG", quality=95)
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
    Render a physical classified FBI / CIA document resting on a tactical desk
    with redacted censor bars and an authentic red rubber stamp.
    """
    if dest_path and os.path.dirname(dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    sheet_w, sheet_h = 920, 1520
    doc_tints = [
        (230, 224, 212, 255),  # Aged manila
        (235, 228, 218, 255),  # Vintage government parchment
        (225, 218, 204, 255),  # Cold War archive folder
    ]
    doc_bg = random.choice(doc_tints)
    sheet = Image.new("RGBA", (sheet_w, sheet_h), doc_bg)
    draw = ImageDraw.Draw(sheet)

    # Outer border rule
    draw.rectangle([20, 20, sheet_w - 20, sheet_h - 20], outline=(65, 60, 55), width=2)

    # Header
    font_hdr = _load_font("mono", size=32, bold=True)
    draw.text((sheet_w // 2, 80), "FEDERAL INVESTIGATION ARCHIVE", fill=(35, 30, 25), font=font_hdr, anchor="mm")
    draw.text((sheet_w // 2, 125), "SPECIAL INTELLIGENCE DIVISION // EYES ONLY", fill=(95, 85, 75), font=font_hdr, anchor="mm")
    draw.line([(40, 160), (sheet_w - 40, 160)], fill=(70, 65, 60), width=2)

    # Dynamic case and directive reference
    cid = case_id if case_id != "CASE FILE #8492-X" else f"CASE FILE #{random.randint(1000, 9999)}-X"
    directive = random.choice(["DIRECTIVE 14-B", "EXECUTIVE ORDER 11905", "FREEDOM OF INFORMATION ACT 552", "NATIONAL SECURITY DIRECTIVE 84"])

    font_meta = _load_font("mono", size=24, bold=False)
    draw.text((50, 195), f"REF: {cid.upper()}", fill=(50, 45, 40), font=font_meta)
    draw.text((50, 235), f"STATUS: DECLASSIFIED UNDER {directive}", fill=(175, 35, 35), font=font_meta)
    draw.text((50, 275), f"SUBJECT: {title.upper()[:36]}", fill=(50, 45, 40), font=font_meta)
    draw.line([(40, 315), (sheet_w - 40, 315)], fill=(70, 65, 60), width=2)

    # Typewriter Body Text
    font_body = _load_font("mono", size=30, bold=True)
    y = 370
    lines = textwrap.wrap(body_text.upper(), width=34)

    for idx, line in enumerate(lines[:10]):
        draw.text((50, y), line, fill=(35, 30, 25), font=font_body)

        # Draw realistic black redaction censor bars on select lines
        if idx in {1, 3} and len(line) > 10:
            bar_start = 50 + random.randint(0, 80)
            bar_len = random.randint(200, 360)
            draw.rectangle([bar_start, y - 4, min(sheet_w - 50, bar_start + bar_len), y + 34], fill=(15, 15, 15))

        y += 58

    # Dynamic Red Rubber Stamp
    stamps = ["TOP SECRET", "DECLASSIFIED", "RESTRICTED", "EYES ONLY", "CONFIDENTIAL"]
    actual_stamp = stamp_text if stamp_text != "TOP SECRET" else random.choice(stamps)

    stamp_w, stamp_h = 440, 135
    stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stamp_img)
    s_draw.rectangle([6, 6, stamp_w - 6, stamp_h - 6], outline=(195, 30, 30, 230), width=7)
    font_stamp = _load_font("impact", size=60)
    s_draw.text((stamp_w // 2, stamp_h // 2), actual_stamp.upper(), fill=(195, 30, 30, 230), font=font_stamp, anchor="mm")

    angle = random.choice([-14, -10, 10, 13, 16])
    stamp_rot = stamp_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    pos_x = sheet_w - stamp_rot.width - 60
    pos_y = sheet_h - stamp_rot.height - 180
    sheet.paste(stamp_rot, (pos_x, pos_y), stamp_rot)

    # Composite physical document onto dark tactical desk
    desk_rot = random.uniform(1.2, 2.2)
    desk = _composite_sheet_on_desk(sheet, desk_color=(22, 20, 18), angle=desk_rot, center_y=820)
    desk = add_film_grain(desk, intensity=8.0)
    desk.save(dest_path, "JPEG", quality=95)
    return dest_path


WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000,
}

UNITS_KEYWORDS = {
    "ton": "TONS", "tons": "TONS",
    "dollar": "$", "dollars": "$",
    "hour": "HOURS", "hours": "HOURS",
    "second": "SECONDS", "seconds": "SECONDS",
    "minute": "MINUTES", "minutes": "MINUTES",
    "day": "DAYS", "days": "DAYS",
    "year": "YEARS", "years": "YEARS",
    "mile": "MILES", "miles": "MILES",
    "light-year": "LIGHT-YEARS", "light-years": "LIGHT-YEARS",
    "lightyear": "LIGHT-YEARS", "lightyears": "LIGHT-YEARS",
    "can": "CANS", "cans": "CANS",
    "layer": "LAYERS", "layers": "LAYERS",
    "percent": "%",
}


def parse_stat_from_narration(narration: str, fallback_query: str = "") -> tuple[int, str, str, str]:
    """
    Intelligently extract the primary numerical stat, prefix, suffix, and contextual label
    from narration text, supporting both word numbers ("eighty-four thousand tons")
    and digits ("$100M", "84,000", "72 seconds").
    If narration has no numbers, checks fallback_query.

    Returns: (target_value, prefix, suffix, contextual_label)
    """
    # Check narration first, then fallback_query if needed
    for candidate_text in [narration, fallback_query]:
        if not candidate_text:
            continue
        clean = re.sub(r"(\w+)-(\w+)", r"\1 \2", candidate_text.lower())

        # Detect unit across the sentence
        detected_unit = ""
        for w, u in UNITS_KEYWORDS.items():
            if re.search(r"\b" + re.escape(w) + r"\b", clean):
                detected_unit = u
                break

        # 1. First check explicit digit patterns e.g. $100M, 84,000 tons, 10 layers, 1,420 mhz
        m_dig = re.search(
            r"(\$)?\s*(\d[\d,]*(?:\.\d+)?)(?:\s*\b(k|m|b|million|billion|thousand|mhz|ghz|tons|km)\b)?",
            clean,
        )
        if m_dig:
            prefix = "$" if (m_dig.group(1) or detected_unit == "$" or "dollar" in clean) else ""
            raw_num = float(m_dig.group(2).replace(",", ""))
            scale_str = (m_dig.group(3) or "").lower()
            if scale_str in {"k", "thousand"}:
                num = int(raw_num * 1_000)
            elif scale_str in {"m", "million"}:
                num = int(raw_num * 1_000_000)
            elif scale_str in {"b", "billion"}:
                num = int(raw_num * 1_000_000_000)
            else:
                num = int(raw_num)
            suffix = detected_unit if detected_unit != "$" else ""
            if not suffix and scale_str in {"mhz", "ghz", "tons", "km"}:
                suffix = scale_str.upper()
            return _categorize_stat(num, prefix, suffix, candidate_text)

        # 2. Parse English written words (e.g. "eighty-four thousand", "one hundred million")
        words = re.findall(r"\b[a-z\-]+\b", clean)
        total = 0
        current = 0
        found_any = False

        for w in words:
            if w in WORD_TO_NUM:
                current += WORD_TO_NUM[w]
                found_any = True
            elif w in SCALES:
                scale = SCALES[w]
                current = (current if current != 0 else 1) * scale
                if scale >= 1000:
                    total += current
                    current = 0
                found_any = True
            else:
                if found_any:
                    break

        total += current
        if found_any and total > 0:
            prefix = "$" if (detected_unit == "$" or "dollar" in clean) else ""
            suffix = detected_unit if detected_unit != "$" else ""
            return _categorize_stat(total, prefix, suffix, candidate_text)

    # 3. Contextual intelligent fallback based on keywords instead of blind $100M
    combined = f"{narration} {fallback_query}".lower()
    if any(k in combined for k in ["space", "astronomy", "signal", "radio", "telescope", "pulse", "wow"]):
        return (1420, "", "MHZ", "INTERCEPTED FREQUENCY")
    if any(k in combined for k in ["dust", "meteor", "venus", "debris", "tons", "acid"]):
        return (84000, "", "TONS", "ANNUAL SPACE DEBRIS")
    if any(k in combined for k in ["speed", "light", "distance", "galaxy", "orbit", "km"]):
        return (60, "", "KM", "ATMOSPHERIC ALTITUDE")
    if any(k in combined for k in ["year", "century", "decades", "timeline"]):
        return (49, "", "YEARS", "RECORDED TIMELINE")

    return (100_000_000, "$", "", "DOCUMENTED RECORD")


def _categorize_stat(num: int, prefix: str, suffix: str, text: str) -> tuple[int, str, str, str]:
    """Determine high-impact contextual label based on metric and subject."""
    text_l = text.lower()
    if "debris" in text_l or "dust" in text_l or suffix == "TONS":
        label = "ANNUAL SPACE DEBRIS"
    elif "layer" in text_l or suffix == "LAYERS":
        label = "VAULT SECURITY PROTOCOLS"
    elif "stolen" in text_l or "heist" in text_l:
        label = "STOLEN VALUATION"
    elif "dollar" in text_l or prefix == "$":
        label = "FINANCIAL RECORD"
    elif "mhz" in text_l or suffix == "MHZ":
        label = "INTERCEPTED FREQUENCY"
    elif "signal" in text_l or suffix in {"HOURS", "SECONDS", "MINUTES"}:
        label = "RECORDED DURATION"
    elif "distance" in text_l or suffix in {"LIGHT-YEARS", "KM", "MILES"}:
        label = "COSMIC MEASUREMENT"
    elif "can" in text_l:
        label = "ANNUAL SALES VOLUME"
    elif "year" in text_l or suffix == "YEARS":
        label = "HISTORICAL TIMELINE"
    else:
        label = "DOCUMENTED RECORD"
    return (num, prefix, suffix, label)


COUNTER_THEMES = {
    "gold": {
        "glow": (255, 215, 0),
        "border": (255, 215, 0, 190),
        "inner_border": (255, 215, 0, 60),
        "accent": (255, 215, 0, 140),
        "val_done": (255, 235, 30),
        "val_anim": (255, 215, 0),
        "label": (210, 210, 210),
    },
    "emerald": {
        "glow": (0, 255, 136),
        "border": (0, 255, 136, 190),
        "inner_border": (0, 255, 136, 60),
        "accent": (0, 255, 136, 140),
        "val_done": (30, 255, 160),
        "val_anim": (0, 255, 136),
        "label": (190, 240, 210),
    },
    "cyan": {
        "glow": (0, 220, 255),
        "border": (0, 220, 255, 190),
        "inner_border": (0, 220, 255, 60),
        "accent": (0, 220, 255, 140),
        "val_done": (90, 245, 255),
        "val_anim": (0, 220, 255),
        "label": (200, 240, 255),
    },
    "crimson": {
        "glow": (255, 60, 60),
        "border": (255, 60, 60, 190),
        "inner_border": (255, 60, 60, 60),
        "accent": (255, 60, 60, 140),
        "val_done": (255, 90, 90),
        "val_anim": (255, 60, 60),
        "label": (255, 200, 200),
    },
}


def render_animated_counter_video(
    target_value: int,
    prefix: str = "",
    suffix: str = "",
    stat_label: str = "DOCUMENTED RECORD",
    dest_path: str = "",
    duration: float = 4.0,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
    theme: Optional[str] = None,
) -> str:
    """
    Render an ultra-smooth animated counting-up motion graphic video.
    The number rapidly rolls/climbs upwards from 0 to the target number
    over the first 1.35 seconds with cubic ease-out, displaying real rolling digits
    before locking in with an intense thematic glow.
    """
    if dest_path and os.path.dirname(dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    frames_total = max(1, int(fps * duration))
    anim_frames = min(frames_total, max(1, int(fps * 1.35)))

    # Auto-select visual theme if not provided
    if not theme:
        lbl_lower = stat_label.lower()
        if prefix == "$" or "financial" in lbl_lower or "stolen" in lbl_lower or "vault" in lbl_lower:
            theme = "gold"
        elif "frequency" in lbl_lower or "radar" in lbl_lower or suffix in {"MHZ", "GHZ"}:
            theme = "emerald"
        elif "cosmic" in lbl_lower or "space" in lbl_lower or "distance" in lbl_lower or suffix in {"KM", "LIGHT-YEARS"}:
            theme = "cyan"
        elif "threat" in lbl_lower or "alert" in lbl_lower or "danger" in lbl_lower:
            theme = "crimson"
        else:
            theme = random.choice(["gold", "emerald", "cyan"])

    palette = COUNTER_THEMES.get(theme, COUNTER_THEMES["gold"])

    font_lbl = _load_font("sans", size=36, bold=True)
    font_val = _load_font("impact", size=96)
    font_sub = _load_font("mono", size=26, bold=False)

    writer = imageio.get_writer(
        dest_path,
        fps=fps,
        codec="libx264",
        macro_block_size=1,
        quality=8,
    )

    try:
        val_str = ""
        for f_idx in range(frames_total):
            if f_idx < anim_frames:
                tau = f_idx / float(anim_frames)
                prog = 1.0 - (1.0 - tau) ** 3  # cubic ease-out
                cur_num = int(target_value * prog)
                # During animation, display actual rolling digits for maximum kinetic thrill
                val_str = f"{prefix}{cur_num:,} {suffix}".strip()
            else:
                cur_num = target_value
                val_str = f"{prefix}{target_value:,} {suffix}".strip()

            img = Image.new("RGB", (width, height), (12, 14, 20))
            draw = ImageDraw.Draw(img)

            # Center ambient glow
            glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            g_draw = ImageDraw.Draw(glow)
            glow_intensity = 42 if f_idx >= anim_frames else 26
            glow_color = palette["glow"] + (glow_intensity,)
            g_draw.ellipse([180, 480, width - 180, 1180], fill=glow_color)
            glow = glow.filter(ImageFilter.GaussianBlur(130))
            img.paste(glow, (0, 0), glow)

            # Tactical card outline (Y: 500 to 1120)
            draw.rounded_rectangle([90, 500, width - 90, 1120], radius=24, outline=palette["border"], width=3)
            draw.rounded_rectangle([98, 508, width - 98, 1112], radius=18, outline=palette["inner_border"], width=1)

            # Category Header Label
            draw.text((width // 2, 610), stat_label.upper(), fill=palette["label"], font=font_lbl, anchor="mm")
            draw.line([(width // 2 - 140, 655), (width // 2 + 140, 655)], fill=palette["accent"], width=2)

            # Animated Rising Number Value (Theme Color)
            num_color = palette["val_done"] if f_idx >= anim_frames else palette["val_anim"]
            draw.text((width // 2, 795), val_str.upper(), fill=num_color, font=font_val, anchor="mm")

            # Sub-caption
            draw.text((width // 2, 975), "OFFICIALLY RECORDED EVIDENCE", fill=(160, 160, 160), font=font_sub, anchor="mm")

            writer.append_data(np.array(img))
    finally:
        writer.close()

    logger.info("Rendered animated counter video -> %s (%s: %s | theme: %s)", dest_path, stat_label, val_str, theme)
    return dest_path


def render_stat_counter_card(
    stat_value: str,
    stat_label: str,
    dest_path: str = "",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    Render a high-tech glowing static stat card (fallback).
    Positioned in upper-middle area to prevent subtitle collision.
    """
    if dest_path and os.path.dirname(dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    img = Image.new("RGB", (width, height), (12, 14, 20))
    draw = ImageDraw.Draw(img)

    # Ambient glowing background circle
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([180, 480, width - 180, 1180], fill=(255, 215, 0, 28))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    img.paste(glow, (0, 0), glow)

    # Center card outline (Y: 480 to 1100, safely above Y: 1320 subtitle zone)
    draw.rounded_rectangle([90, 500, width - 90, 1120], radius=24, outline=(255, 215, 0, 180), width=3)
    draw.rounded_rectangle([98, 508, width - 98, 1112], radius=18, outline=(255, 215, 0, 60), width=1)

    # Stat Label
    font_lbl = _load_font("sans", size=32, bold=True)
    draw.text((width // 2, 620), stat_label.upper(), fill=(200, 200, 200), font=font_lbl, anchor="mm")
    draw.line([(width // 2 - 120, 660), (width // 2 + 120, 660)], fill=(255, 215, 0, 120), width=2)

    # Giant Stat Value
    font_val = _load_font("impact", size=108)
    draw.text((width // 2, 800), stat_value.upper(), fill=(255, 225, 0), font=font_val, anchor="mm")

    # Sub-caption inside card
    font_sub = _load_font("mono", size=24, bold=False)
    draw.text((width // 2, 980), "OFFICIALLY RECORDED EVIDENCE", fill=(160, 160, 160), font=font_sub, anchor="mm")

    img = add_film_grain(img, intensity=7.0)
    img.save(dest_path, "JPEG", quality=95)
    return dest_path


def render_radar_scope_frame(
    target_name: str = "UNEXPLAINED EMISSION",
    coordinates: str = "RA 19h 28m // DEC -27° 00'",
    dest_path: str = "",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    Render an authentic green-phosphor CRT radar/oscilloscope telemetry scope.
    Used for deep space signals, military radar anomalies, and high-frequency tracking.
    Positioned in upper-middle area (Y: 340 to 1200) to keep subtitles fully clear.
    """
    if dest_path and os.path.dirname(dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    img = Image.new("RGB", (width, height), (10, 15, 14))
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, 780
    r_max = 420

    # Ambient deep green CRT glow
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([cx - r_max - 50, cy - r_max - 50, cx + r_max + 50, cy + r_max + 50], fill=(0, 255, 120, 24))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img.paste(glow, (0, 0), glow)

    # Tactical Outer Circle & Bezel
    draw.ellipse([cx - r_max, cy - r_max, cx + r_max, cy + r_max], outline=(0, 255, 136, 180), width=4)
    draw.ellipse([cx - r_max - 12, cy - r_max - 12, cx + r_max + 12, cy + r_max + 12], outline=(0, 255, 136, 70), width=2)

    # Concentric Range Rings
    for r in [130, 240, 330]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 200, 110, 80), width=1)

    # Crosshair Axes & Degree Ticks
    draw.line([(cx - r_max, cy), (cx + r_max, cy)], fill=(0, 220, 120, 90), width=1)
    draw.line([(cx, cy - r_max), (cx, cy + r_max)], fill=(0, 220, 120, 90), width=1)
    draw.line([(cx - int(r_max * 0.707), cy - int(r_max * 0.707)), (cx + int(r_max * 0.707), cy + int(r_max * 0.707))], fill=(0, 200, 110, 45), width=1)
    draw.line([(cx - int(r_max * 0.707), cy + int(r_max * 0.707)), (cx + int(r_max * 0.707), cy - int(r_max * 0.707))], fill=(0, 200, 110, 45), width=1)

    # Translucent Radar Sweep Sector (Dynamic Angle)
    sweep = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(sweep)
    sweep_start = random.randint(-180, 180)
    sweep_end = sweep_start + 65
    s_rad = math.radians(sweep_end)
    s_draw.pieslice([cx - r_max, cy - r_max, cx + r_max, cy + r_max], start=sweep_start, end=sweep_end, fill=(0, 255, 140, 45))
    s_draw.line([(cx, cy), (cx + int(r_max * math.cos(s_rad)), cy + int(r_max * math.sin(s_rad)))], fill=(0, 255, 160, 220), width=3)
    img.paste(sweep, (0, 0), sweep)

    # Target Blip with reticle brackets (Dynamic position)
    blip_dist = random.randint(140, 280)
    blip_ang = math.radians(random.randint(0, 360))
    blip_x = cx + int(blip_dist * math.cos(blip_ang))
    blip_y = cy + int(blip_dist * math.sin(blip_ang))
    draw.ellipse([blip_x - 8, blip_y - 8, blip_x + 8, blip_y + 8], fill=(255, 50, 50, 255))
    draw.rectangle([blip_x - 22, blip_y - 22, blip_x + 22, blip_y + 22], outline=(255, 80, 80, 200), width=2)

    font_mono_sm = _load_font("mono", size=22, bold=True)
    font_mono_md = _load_font("mono", size=26, bold=True)
    font_hud_title = _load_font("mono", size=32, bold=True)

    sigmas = ["+28 SIGMA", "+30 SIGMA", "+34 SIGMA", "+42 SIGMA"]
    draw.text((blip_x + 30, blip_y - 12), f"TARGET LOCK [{random.choice(sigmas)}]", fill=(255, 80, 80), font=font_mono_sm)

    # Top HUD Telemetry
    draw.text((width // 2, 220), "FREQUENCY SPECTRUM MONITOR", fill=(0, 255, 136), font=font_hud_title, anchor="mm")
    draw.line([(width // 2 - 200, 250), (width // 2 + 200, 250)], fill=(0, 255, 136, 120), width=2)
    draw.text((width // 2, 280), f"SIGNAL: {target_name.upper()[:36]}", fill=(190, 230, 210), font=font_mono_md, anchor="mm")

    # Bottom HUD Telemetry
    draw.text((width // 2, 1260), f"COORDINATES: {coordinates.upper()}", fill=(0, 255, 136), font=font_mono_md, anchor="mm")
    draw.text((width // 2, 1300), "SIGNAL TYPE: NARROWBAND PULSE // UNIDENTIFIED", fill=(170, 200, 190), font=font_mono_sm, anchor="mm")

    img = add_film_grain(img, intensity=8.0)
    img.save(dest_path, "JPEG", quality=95)
    return dest_path
