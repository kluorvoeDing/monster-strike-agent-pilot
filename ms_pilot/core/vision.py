import re
from typing import Any, Dict, List, Optional
from .client import iPhoneClient


def has_text_any(items: List[Dict[str, Any]], keywords: List[str]) -> bool:
    for it in items:
        for k in keywords:
            if k in it["text"]:
                return True
    return False


def check_chest_2100_active(client: iPhoneClient) -> bool:
    """
    Pixel-level inspection of the leftmost '寶箱+2' (2100 medals) assist item card.
    Returns True if the orange/gold selection border glow is active, preventing accidental unchecking.
    """
    try:
        im = client.get_screenshot_image()
        if im is None:
            return False
        w, h = im.size
        pix = im.load()
        # Scale reference coordinates (x=35..42, y=800 in 552x1200 logical frame)
        y_probe = int(h * (800 / 1200.0))
        x_start = int(w * (35 / 552.0))
        x_end = int(w * (42 / 552.0))
        for x in range(x_start, x_end + 1):
            r, g, b = pix[x, y_probe][:3]
            if r > 140 and r > 1.8 * b:
                return True
    except Exception as e:
        print(f"  [Vision] Warning checking chest active glow: {e}")
    return False


def parse_current_luck(items: List[Dict[str, Any]]) -> Optional[int]:
    """
    Zero-detour Luck tracker: extracts character Luck directly from settlement popups
    ('達成運極', '自動合成') or quest banners ('最高 89', '最高 極') without entering Monster Box.
    """
    for it in items:
        txt = it["text"].strip()
        if any(k in txt for k in ["達成運極", "最高 極", "運極達成"]):
            return 99
        m = re.search(r"最高\s*(\d{1,2})", txt)
        if m:
            return int(m.group(1))
        m_syn = re.search(r"運氣\s*(\d{1,2})\s*[+＋]", txt)
        if m_syn:
            return int(m_syn.group(1))
    return None


def estimate_hp_ratio(client: iPhoneClient) -> float:
    """
    Estimate current player HP ratio (0.0 to 1.0) by sampling the horizontal HP bar
    located above the character deck (y ~ 0.706, x ~ 0.16 to 0.92).
    """
    try:
        im = client.get_screenshot_image()
        if im is None:
            return 1.0
        w, h = im.size
        pix = im.load()
        y_bar = int(h * 0.706)
        x_min = int(w * 0.18)
        x_max = int(w * 0.90)
        total_samples = 30
        lit_samples = 0
        for i in range(total_samples):
            x = x_min + int((x_max - x_min) * (i / max(1, total_samples - 1)))
            r, g, b = pix[x, y_bar][:3]
            # HP bar is bright green, yellow, or red; empty bar is dark gray/black
            if max(r, g) > 110:
                lit_samples += 1
        return round(lit_samples / total_samples, 2)
    except Exception:
        return 1.0


def profile_team_on_screen(client: iPhoneClient, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Visual team profiler for Co-Pilot handover: inspects the 4 party slots on the deploy
    or combat screen to record dominant attribute color and luck/status labels.
    """
    im = client.get_screenshot_image()
    slot_centers_x = [0.16, 0.36, 0.56, 0.76]
    profiles: List[Dict[str, Any]] = []

    for idx, cx in enumerate(slot_centers_x, start=1):
        dominant_attr = "unknown"
        if im is not None:
            w, h = im.size
            pix = im.load()
            px, py = int(w * cx), int(h * 0.45)
            r, g, b = pix[px, py][:3]
            if r > max(g, b) + 30:
                dominant_attr = "fire/red"
            elif b > max(r, g) + 30:
                dominant_attr = "water/blue"
            elif g > max(r, b) + 30:
                dominant_attr = "wood/green"
            elif r > 160 and g > 160:
                dominant_attr = "light/yellow"
            else:
                dominant_attr = "dark/purple"

        nearby_labels = [
            it["text"]
            for it in items
            if abs(it["x"] - cx) < 0.10 and 0.32 <= it["y"] <= 0.58
        ]
        profiles.append({
            "slot": idx,
            "x": cx,
            "dominant_color": dominant_attr,
            "labels": nearby_labels,
        })
    return profiles
