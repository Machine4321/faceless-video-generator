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
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    sheet_w, sheet_h = 940, 1540
    paper_color = (244, 239, 230, 255)
    sheet = Image.new("RGBA", (sheet_w, sheet_h), paper_color)
    draw = ImageDraw.Draw(sheet)

    # Top Masthead Lines
    draw.line([(40, 50), (sheet_w - 40, 50)], fill=(30, 30, 30), width=4)
    draw.line([(40, 60), (sheet_w - 40, 60)], fill=(30, 30, 30), width=2)

    # Masthead Name
    font_masthead = _load_font("serif", size=54, bold=True)
    draw.text((sheet_w // 2, 115), "THE GLOBAL CHRONICLE", fill=(20, 20, 20), font=font_masthead, anchor="mm")

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
    desk = _composite_sheet_on_desk(sheet, desk_color=(18, 16, 14), angle=-1.6, center_y=820)
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
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    sheet_w, sheet_h = 920, 1520
    doc_bg = (230, 224, 212, 255)  # Aged manila parchment
    sheet = Image.new("RGBA", (sheet_w, sheet_h), doc_bg)
    draw = ImageDraw.Draw(sheet)

    # Outer border rule
    draw.rectangle([20, 20, sheet_w - 20, sheet_h - 20], outline=(65, 60, 55), width=2)

    # Header
    font_hdr = _load_font("mono", size=32, bold=True)
    draw.text((sheet_w // 2, 80), "FEDERAL INVESTIGATION ARCHIVE", fill=(35, 30, 25), font=font_hdr, anchor="mm")
    draw.text((sheet_w // 2, 125), "SPECIAL INTELLIGENCE DIVISION // EYES ONLY", fill=(95, 85, 75), font=font_hdr, anchor="mm")
    draw.line([(40, 160), (sheet_w - 40, 160)], fill=(70, 65, 60), width=2)

    # Metadata
    font_meta = _load_font("mono", size=24, bold=False)
    draw.text((50, 195), f"REF: {case_id.upper()}", fill=(50, 45, 40), font=font_meta)
    draw.text((50, 235), "STATUS: DECLASSIFIED UNDER DIRECTIVE 14-B", fill=(175, 35, 35), font=font_meta)
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

    # Red Rubber Stamp (Angled Grunge Stamp)
    stamp_w, stamp_h = 440, 135
    stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(stamp_img)
    s_draw.rectangle([6, 6, stamp_w - 6, stamp_h - 6], outline=(195, 30, 30, 230), width=7)
    font_stamp = _load_font("impact", size=64)
    s_draw.text((stamp_w // 2, stamp_h // 2), stamp_text.upper(), fill=(195, 30, 30, 230), font=font_stamp, anchor="mm")

    angle = random.choice([-14, -10, 12, 15])
    stamp_rot = stamp_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    pos_x = sheet_w - stamp_rot.width - 60
    pos_y = sheet_h - stamp_rot.height - 180
    sheet.paste(stamp_rot, (pos_x, pos_y), stamp_rot)

    # Composite physical document onto dark tactical desk
    desk = _composite_sheet_on_desk(sheet, desk_color=(22, 20, 18), angle=1.7, center_y=820)
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


def parse_stat_from_narration(narration: str) -> tuple[int, str, str, str]:
    """
    Intelligently extract the primary numerical stat, prefix, suffix, and contextual label
    from narration text, supporting both word numbers ("eighty-four thousand tons")
    and digits ("$100M", "84,000", "72 seconds").

    Returns: (target_value, prefix, suffix, contextual_label)
    """
    clean = re.sub(r"(\w+)-(\w+)", r"\1 \2", narration.lower())

    # Detect unit across the sentence
    detected_unit = ""
    for w, u in UNITS_KEYWORDS.items():
        if re.search(r"\b" + re.escape(w) + r"\b", clean):
            detected_unit = u
            break

    # 1. First check explicit digit patterns e.g. $100M, 84,000 tons, 10 layers
    m_dig = re.search(
        r"(\$)?\s*(\d[\d,]*(?:\.\d+)?)(?:\s*\b(k|m|b|million|billion|thousand)\b)?",
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
        return _categorize_stat(num, prefix, suffix, narration)

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
        return _categorize_stat(total, prefix, suffix, narration)

    # 3. Fallback default
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
    elif "signal" in text_l or suffix in {"HOURS", "SECONDS", "MINUTES"}:
        label = "RECORDED DURATION"
    elif "distance" in text_l or suffix == "LIGHT-YEARS":
        label = "COSMIC DISTANCE"
    elif "can" in text_l:
        label = "ANNUAL SALES VOLUME"
    elif "year" in text_l or suffix == "YEARS":
        label = "HISTORICAL TIMELINE"
    else:
        label = "DOCUMENTED RECORD"
    return (num, prefix, suffix, label)


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
) -> str:
    """
    Render an ultra-smooth animated counting-up motion graphic video.
    The number rapidly rolls/climbs upwards from 0 to the target number
    over the first 1.35 seconds with cubic ease-out, then locks in with a gold glow.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    frames_total = max(1, int(fps * duration))
    anim_frames = min(frames_total, max(1, int(fps * 1.35)))

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
            else:
                cur_num = target_value

            if target_value >= 1_000_000_000 and target_value % 1_000_000_000 == 0:
                val_str = f"{prefix}{cur_num // 1_000_000_000}B {suffix}".strip()
            elif target_value >= 1_000_000 and target_value % 1_000_000 == 0:
                val_str = f"{prefix}{cur_num // 1_000_000}M {suffix}".strip()
            else:
                val_str = f"{prefix}{cur_num:,} {suffix}".strip()

            img = Image.new("RGB", (width, height), (12, 14, 20))
            draw = ImageDraw.Draw(img)

            # Center ambient gold glow
            glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            g_draw = ImageDraw.Draw(glow)
            glow_intensity = 35 if f_idx >= anim_frames else 22
            g_draw.ellipse([180, 480, width - 180, 1180], fill=(255, 215, 0, glow_intensity))
            glow = glow.filter(ImageFilter.GaussianBlur(130))
            img.paste(glow, (0, 0), glow)

            # Golden tactical card outline (Y: 500 to 1120)
            draw.rounded_rectangle([90, 500, width - 90, 1120], radius=24, outline=(255, 215, 0, 180), width=3)
            draw.rounded_rectangle([98, 508, width - 98, 1112], radius=18, outline=(255, 215, 0, 60), width=1)

            # Category Header Label
            draw.text((width // 2, 610), stat_label.upper(), fill=(200, 200, 200), font=font_lbl, anchor="mm")
            draw.line([(width // 2 - 140, 655), (width // 2 + 140, 655)], fill=(255, 215, 0, 140), width=2)

            # Animated Rising Number Value (Glowing Gold)
            num_color = (255, 235, 30) if f_idx >= anim_frames else (255, 215, 0)
            draw.text((width // 2, 795), val_str.upper(), fill=num_color, font=font_val, anchor="mm")

            # Sub-caption
            draw.text((width // 2, 975), "OFFICIALLY RECORDED EVIDENCE", fill=(160, 160, 160), font=font_sub, anchor="mm")

            writer.append_data(np.array(img))
    finally:
        writer.close()

    logger.info("Rendered animated counter video -> %s (%s: %s)", dest_path, stat_label, val_str)
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
