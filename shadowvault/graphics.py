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
    desk_color: tuple[int, int, int] = (24, 20, 18),
    angle: float = -1.8,
    desk_w: int = 1080,
    desk_h: int = 1920,
    center_y: int = 860,
    warm_spotlight: bool = True,
) -> Image.Image:
    """
    Composite a physical document sheet with soft blurred drop shadow onto a rich warm investigation desk surface.
    Gives realistic 3D depth, soft warm directional lighting, and separation typical of Vox / MagnatesMedia documentaries.
    """
    bg = Image.new("RGB", (desk_w, desk_h), desk_color)

    # Warm directional desk lamp spotlight
    if warm_spotlight:
        spotlight = Image.new("RGBA", (desk_w, desk_h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(spotlight)
        s_draw.ellipse([100, 240, desk_w - 100, desk_h - 320], fill=(255, 235, 195, 34))
        spotlight = spotlight.filter(ImageFilter.GaussianBlur(160))
        bg.paste(spotlight, (0, 0), spotlight)

    sw, sh = sheet.size

    # Multi-layered realistic blurred drop shadow
    shadow_pad = 70
    shadow = Image.new("RGBA", (sw + shadow_pad * 2, sh + shadow_pad * 2), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rectangle([shadow_pad, shadow_pad, sw + shadow_pad, sh + shadow_pad], fill=(0, 0, 0, 185))
    shadow = shadow.filter(ImageFilter.GaussianBlur(32))

    # Apply subtle physical angle
    sheet_rot = sheet.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    shadow_rot = shadow.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)

    pos_x = (desk_w - sheet_rot.width) // 2
    pos_y = center_y - (sheet_rot.height // 2)

    # Offset shadow down-right to simulate overhead office desk lighting
    bg.paste(shadow_rot, (pos_x - 10, pos_y + 18), shadow_rot)
    bg.paste(sheet_rot, (pos_x, pos_y), sheet_rot)

    return bg


def render_newspaper_frame(
    headline: str,
    snippet: str = "",
    date_str: str = "SPECIAL REPORT",
    photo_path: Optional[str] = None,
    caption: str = "",
    dest_path: str = "",
    width: int = 1080,
    height: int = 1920,
) -> str:
    """
    Render an authentic, high-impact broadsheet newspaper resting on an investigation desk
    with an embedded photograph of the subject, realistic typography, and vibrant fluorescent yellow highlighter.
    """
    if dest_path and os.path.dirname(dest_path):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    sheet_w, sheet_h = 960, 1540
    paper_color = (244, 239, 230, 255)  # Vintage warm newsprint
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
    font_masthead = _load_font("serif", size=54, bold=True)
    draw.text((sheet_w // 2, 115), random.choice(mastheads), fill=(20, 20, 20), font=font_masthead, anchor="mm")

    draw.line([(40, 170), (sheet_w - 40, 170)], fill=(30, 30, 30), width=3)

    # Sub-bar (Volume, Date, Edition, Price)
    font_sub = _load_font("sans", size=20, bold=False)
    draw.text((sheet_w // 2, 200), f"VOL. CXLII No. 48,219 • WORLD EXCLUSIVE • {date_str.upper()} • $1.50", fill=(70, 70, 70), font=font_sub, anchor="mm")
    draw.line([(40, 230), (sheet_w - 40, 230)], fill=(30, 30, 30), width=2)

    # Main Headline (All-caps, high-impact)
    font_hl = _load_font("impact", size=72)
    wrapped = textwrap.fill(headline.upper(), width=22)
    lines = wrapped.split("\n")

    start_y = 270
    line_h = 86

    # Highlighter wipe layer
    highlighter = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(highlighter)

    # Highlight the most dramatic line in fluorescent yellow
    hl_line_idx = min(1, len(lines) - 1)
    hl_y = start_y + (hl_line_idx * line_h)
    h_draw.rounded_rectangle([45, hl_y + 6, sheet_w - 45, hl_y + 82], radius=6, fill=(255, 236, 0, 155))
    sheet.paste(highlighter, (0, 0), highlighter)

    # Draw headline text
    curr_y = start_y
    for line in lines:
        draw.text((sheet_w // 2, curr_y + 44), line, fill=(18, 18, 18), font=font_hl, anchor="mm")
        curr_y += line_h

    # Divider below headline
    draw.line([(40, curr_y + 15), (sheet_w - 40, curr_y + 15)], fill=(30, 30, 30), width=3)
    curr_y += 35

    # Simulated newspaper columns below
    font_body = _load_font("serif", size=21, bold=False)
    font_cap = _load_font("sans", size=16, bold=False)

    has_photo = photo_path and os.path.isfile(photo_path)
    if has_photo:
        try:
            p_img = Image.open(photo_path).convert("RGB")
            p_img = p_img.resize((430, 310))
            sheet.paste(p_img, (55, curr_y))
            draw.rectangle([55, curr_y, 55 + 430, curr_y + 310], outline=(40, 40, 40), width=2)
            cap_text = caption or "PHOTO ARCHIVE: Subject documented during record-setting performance."
            draw.text((55, curr_y + 322), cap_text[:65], fill=(75, 75, 75), font=font_cap)

            # Article text beside photo
            col_text = (
                snippet or
                "International observers and independent analysts were left completely stunned as verified documentation surfaced today. "
                "The documented precision and rhythmic timing completely surpassed existing world standards."
            )
            draw.multiline_text((515, curr_y), textwrap.fill(col_text, width=27), fill=(40, 40, 40), font=font_body, spacing=6)

            # Lower broadsheet text spanning below
            lower_y = curr_y + 360
            draw.line([(40, lower_y), (sheet_w - 40, lower_y)], fill=(160, 160, 160), width=1)
            lower_y += 20
            col1 = (
                "Witnesses present at the event confirmed the atmosphere was electric as the performance concluded without a single error. "
                "Official scorecards were signed by senior committee members within minutes."
            )
            col2 = (
                "Video documentation has circulated through multiple international news outlets. "
                "Inquiries continue as historians record this moment among the most exceptional documented cases."
            )
            draw.multiline_text((55, lower_y), textwrap.fill(col1, width=28), fill=(45, 45, 45), font=font_body, spacing=6)
            draw.line([(sheet_w // 2, lower_y), (sheet_w // 2, lower_y + 260)], fill=(180, 180, 180), width=1)
            draw.multiline_text((sheet_w // 2 + 25, lower_y), textwrap.fill(col2, width=28), fill=(45, 45, 45), font=font_body, spacing=6)
        except Exception as exc:
            has_photo = False

    if not has_photo:
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
        draw.multiline_text((60, curr_y), textwrap.fill(col1_text, width=25), fill=(45, 45, 45), font=font_body, spacing=8)
        draw.line([(sheet_w // 2, curr_y), (sheet_w // 2, curr_y + 450)], fill=(150, 150, 150), width=1)
        draw.multiline_text((sheet_w // 2 + 25, curr_y), textwrap.fill(col2_text, width=25), fill=(45, 45, 45), font=font_body, spacing=8)

    # Composite physical paper onto warm investigation desk
    desk_rot = random.uniform(-2.0, -1.2)
    desk = _composite_sheet_on_desk(sheet, desk_color=(24, 20, 18), angle=desk_rot, center_y=860, warm_spotlight=True)
    desk = add_film_grain(desk, intensity=6.5)
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
    "beats per minute": "BPM",
    "beat per minute": "BPM",
    "steps per minute": "STEPS/MIN",
    "step per minute": "STEPS/MIN",
    "light-year": "LIGHT-YEARS",
    "light-years": "LIGHT-YEARS",
    "lightyear": "LIGHT-YEARS",
    "lightyears": "LIGHT-YEARS",
    "ton": "TONS", "tons": "TONS",
    "dollar": "$", "dollars": "$",
    "hour": "HOURS", "hours": "HOURS",
    "second": "SECONDS", "seconds": "SECONDS",
    "minute": "MINUTES", "minutes": "MINUTES",
    "day": "DAYS", "days": "DAYS",
    "year": "YEARS", "years": "YEARS",
    "mile": "MILES", "miles": "MILES",
    "can": "CANS", "cans": "CANS",
    "layer": "LAYERS", "layers": "LAYERS",
    "percent": "%",
    "bpm": "BPM", "beat": "BPM", "beats": "BPM",
    "step": "STEPS/MIN", "steps": "STEPS/MIN",
    "view": "VIEWS", "views": "VIEWS",
    "stream": "STREAMS", "streams": "STREAMS",
    "point": "POINTS", "points": "POINTS",
}


def parse_stat_from_narration(narration: str, fallback_query: str = "") -> tuple[int, str, str, str]:
    """
    Intelligently extract the primary numerical stat, prefix, suffix, and contextual label
    from narration text, supporting both word numbers ("eighty-four thousand tons")
    and digits ("$100M", "84,000", "72 seconds", "180 BPM").
    If narration has no numbers, checks fallback_query.

    Returns: (target_value, prefix, suffix, contextual_label)
    """
    # Check narration first, then fallback_query if needed
    for candidate_text in [narration, fallback_query]:
        if not candidate_text:
            continue
        clean = re.sub(r"(\w+)-(\w+)", r"\1 \2", candidate_text.lower())

        # Detect unit across the sentence (longest match first)
        detected_unit = ""
        for w in sorted(UNITS_KEYWORDS.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(w) + r"\b", clean):
                detected_unit = UNITS_KEYWORDS[w]
                break

        # 1. First check explicit digit patterns e.g. $100M, 84,000 tons, 10 layers, 1,420 mhz, 180 bpm
        m_dig = re.search(
            r"(\$)?\s*(\d[\d,]*(?:\.\d+)?)(?:\s*\b(k|m|b|million|billion|thousand|mhz|ghz|tons|km|bpm|views)\b)?",
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
            if not suffix and scale_str in {"mhz", "ghz", "tons", "km", "bpm", "views"}:
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

    # 3. Contextual intelligent fallback based strictly on subject matter
    combined = f"{narration} {fallback_query}".lower()
    if any(k in combined for k in ["salsa", "dance", "dog", "tempo", "rhythm", "music", "clave", "feet", "paws"]):
        return (180, "", "BPM", "CANINE RHYTHMIC TEMPO")
    if any(k in combined for k in ["space", "astronomy", "signal", "radio", "telescope", "pulse", "wow"]):
        return (1420, "", "MHZ", "INTERCEPTED FREQUENCY")
    if any(k in combined for k in ["dust", "meteor", "venus", "debris", "tons", "acid"]):
        return (84000, "", "TONS", "ANNUAL SPACE DEBRIS")
    if any(k in combined for k in ["speed", "light", "distance", "galaxy", "orbit", "km"]):
        return (60, "", "KM", "ATMOSPHERIC ALTITUDE")
    if any(k in combined for k in ["view", "views", "viral", "tiktok", "youtube"]):
        return (50_000_000, "", "VIEWS", "GLOBAL VIRAL AUDIENCE")
    if any(k in combined for k in ["year", "century", "decades", "timeline"]):
        return (49, "", "YEARS", "RECORDED TIMELINE")
    if any(k in combined for k in ["heist", "stolen", "vault", "cash", "dollar", "robbery"]):
        return (100_000_000, "$", "", "STOLEN VALUATION")

    return (100, "", "%", "RECORDED PRECISION")


def _categorize_stat(num: int, prefix: str, suffix: str, text: str) -> tuple[int, str, str, str]:
    """Determine high-impact contextual label based on metric and subject."""
    text_l = text.lower()
    if suffix in {"BPM", "STEPS/MIN"} or any(w in text_l for w in ["tempo", "salsa", "dance", "rhythm"]):
        label = "CANINE RHYTHMIC TEMPO"
    elif suffix in {"VIEWS", "STREAMS"} or any(w in text_l for w in ["viral", "views"]):
        label = "GLOBAL VIRAL AUDIENCE"
    elif "debris" in text_l or "dust" in text_l or suffix == "TONS":
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
    bg_image_path: Optional[str] = None,
) -> str:
    """
    Render an ultra-smooth animated counting-up motion graphic video.
    The number rapidly rolls/climbs upwards from 0 to the target number
    over the first 1.35 seconds with cubic ease-out, displaying real rolling digits,
    surrounded by pulsating rhythmic audio equalizer bars and set over a rich blurred backdrop.
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
        elif "tempo" in lbl_lower or "salsa" in lbl_lower or "dance" in lbl_lower or suffix == "BPM":
            theme = "cyan"
        elif "threat" in lbl_lower or "alert" in lbl_lower or "danger" in lbl_lower:
            theme = "crimson"
        else:
            theme = random.choice(["gold", "emerald", "cyan"])

    palette = COUNTER_THEMES.get(theme, COUNTER_THEMES["cyan"])

    font_lbl = _load_font("sans", size=32, bold=True)
    font_val = _load_font("impact", size=108)
    font_sub = _load_font("mono", size=24, bold=False)

    # 1. Prepare Base Background once (to ensure fast rendering)
    if bg_image_path and os.path.isfile(bg_image_path):
        try:
            base_bg = Image.open(bg_image_path).convert("RGB")
            # Aspect fill to width x height
            scale = max(width / base_bg.width, height / base_bg.height)
            new_w, new_h = int(base_bg.width * scale), int(base_bg.height * scale)
            base_bg = base_bg.resize((new_w, new_h), Image.Resampling.BICUBIC)
            x0 = (new_w - width) // 2
            y0 = (new_h - height) // 2
            base_bg = base_bg.crop((x0, y0, x0 + width, y0 + height))
            base_bg = base_bg.filter(ImageFilter.GaussianBlur(34))
            dim_overlay = Image.new("RGBA", (width, height), (8, 12, 22, 185))
            base_bg = Image.alpha_composite(base_bg.convert("RGBA"), dim_overlay).convert("RGB")
        except Exception:
            base_bg = Image.new("RGB", (width, height), (12, 16, 24))
    else:
        base_bg = Image.new("RGB", (width, height), (12, 16, 24))

    # Center ambient colored glow
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse([140, 440, width - 140, 1200], fill=palette["glow"] + (36,))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    base_bg.paste(glow, (0, 0), glow)

    writer = imageio.get_writer(
        dest_path,
        fps=fps,
        codec="libx264",
        macro_block_size=1,
        quality=8,
    )

    card_box = [80, 470, width - 80, 1170]
    bracket_len = 26

    # Equalizer bar geometry
    num_bars = 21
    bar_w = 14
    bar_gap = 12
    total_eq_w = num_bars * (bar_w + bar_gap) - bar_gap
    start_eq_x = (width - total_eq_w) // 2
    eq_y_base = 715

    try:
        val_str = ""
        import math
        for f_idx in range(frames_total):
            if f_idx < anim_frames:
                tau = f_idx / float(anim_frames)
                prog = 1.0 - (1.0 - tau) ** 3  # cubic ease-out
                cur_num = int(target_value * prog)
                val_str = f"{prefix}{cur_num:,} {suffix}".strip()
            else:
                cur_num = target_value
                val_str = f"{prefix}{target_value:,} {suffix}".strip()

            img = base_bg.copy()
            draw = ImageDraw.Draw(img)

            # Frosted glass card backdrop
            card_glass = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            cg_draw = ImageDraw.Draw(card_glass)
            cg_draw.rounded_rectangle(card_box, radius=26, fill=(10, 16, 26, 225))
            img.paste(card_glass, (0, 0), card_glass)

            # Double outline
            draw.rounded_rectangle(card_box, radius=26, outline=palette["border"], width=3)
            draw.rounded_rectangle([88, 478, width - 88, 1162], radius=18, outline=palette["inner_border"], width=1)

            # Corner tactical brackets (+ / L-markers)
            draw.line([(80, 470 + bracket_len), (80, 470), (80 + bracket_len, 470)], fill=(255, 255, 255), width=3)
            draw.line([(width - 80 - bracket_len, 470), (width - 80, 470), (width - 80, 470 + bracket_len)], fill=(255, 255, 255), width=3)
            draw.line([(80, 1170 - bracket_len), (80, 1170), (80 + bracket_len, 1170)], fill=(255, 255, 255), width=3)
            draw.line([(width - 80 - bracket_len, 1170), (width - 80, 1170 - bracket_len), (width - 80, 1170)], fill=(255, 255, 255), width=3)

            # Category Header Label
            header_text = f"● {stat_label.upper()} ●"
            draw.text((width // 2, 560), header_text, fill=palette["label"], font=font_lbl, anchor="mm")
            draw.line([(width // 2 - 160, 600), (width // 2 + 160, 600)], fill=palette["accent"], width=2)

            # Dynamic pulsating rhythmic equalizer bars
            for b_i in range(num_bars):
                if f_idx < anim_frames:
                    # Rapid bouncy pulse while counting
                    h_bar = int(16 + 36 * abs(math.sin(b_i * 0.45 + f_idx * 0.40)))
                else:
                    # Rhythmic smooth pulse once locked
                    h_bar = int(14 + 20 * abs(math.sin(b_i * 0.40 + f_idx * 0.18)))
                bx = start_eq_x + b_i * (bar_w + bar_gap)
                draw.rounded_rectangle([bx, eq_y_base - h_bar, bx + bar_w, eq_y_base + h_bar], radius=6, fill=palette["accent"])

            # Animated Rising Number Value (Theme Color)
            num_color = palette["val_done"] if f_idx >= anim_frames else palette["val_anim"]
            draw.text((width // 2, 880), val_str.upper(), fill=num_color, font=font_val, anchor="mm")

            # Sub-caption
            sub_label = "• OFFICIAL WORLD COMPETITION RECORD •" if suffix in {"BPM", "POINTS"} else "• OFFICIALLY RECORDED EVIDENCE •"
            draw.text((width // 2, 1050), sub_label, fill=(175, 210, 230), font=font_sub, anchor="mm")

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
