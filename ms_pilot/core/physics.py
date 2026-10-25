import math
from typing import Any, Dict, List, Optional, Tuple

PLAYFIELD_BOUNDS = (0.04, 0.96, 0.17, 0.68)  # (x_min, x_max, y_min, y_max)


def parse_ordinal_slot(txt: str) -> Optional[int]:
    """
    Strictly parse ball slot tags (1st, 2nd, 3rd, 4th).
    NEVER match bare single digits ("1", "2", "3", "4") which are enemy attack turn counters.
    """
    t = txt.lower().strip()
    if any(k in t for k in ["1st", "ist", "jst"]):
        return 1
    if "2nd" in t:
        return 2
    if "3rd" in t:
        return 3
    if "4th" in t:
        return 4
    return None


def extract_playfield_balls(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Locate friendly balls strictly inside the active combat playfield (0.17 <= y <= 0.68)."""
    balls: List[Dict[str, Any]] = []
    for it in items:
        txt = it["text"].strip()
        if 0.17 <= it["y"] <= 0.68:
            if len(txt) > 6 or "," in txt or "." in txt:
                continue
            slot_num = parse_ordinal_slot(txt)
            if slot_num:
                balls.append({
                    "raw": txt,
                    "slot": slot_num,
                    "x": it["x"],
                    "y": it["y"],
                })
    return balls


def clamp_launch_vector(ux: float, uy: float) -> Tuple[float, float]:
    """Prevent pure vertical downward shots into the floor (uy > 0.85 -> 45 deg diagonal)."""
    if uy > 0.85:
        return (0.7071 if ux >= 0 else -0.7071), -0.7071
    return ux, uy


def compute_ally_aim_vector(
    active: Dict[str, Any],
    balls: List[Dict[str, Any]],
    role_weights: Optional[Dict[int, float]] = None,
) -> Tuple[Dict[str, Any], float, float]:
    """
    Direct Ally Raycast with optional Role Priority Weights.
    Higher weight on Slot 2/3/4 (Main Cannons) makes Slot 1 (Luck Leader) prioritize hitting them.
    """
    weights = role_weights or {1: 0.8, 2: 1.5, 3: 1.5, 4: 1.3}
    candidates = [
        b for b in balls
        if b != active and math.hypot(b["x"] - active["x"], b["y"] - active["y"]) > 0.05
    ]
    if not candidates:
        candidates = [b for b in balls if b != active]

    if not candidates:
        return active, 0.7071, -0.7071

    def score_candidate(b: Dict[str, Any]) -> float:
        dist = max(0.05, math.hypot(b["x"] - active["x"], b["y"] - active["y"]))
        w = weights.get(b.get("slot", 2), 1.0)
        # Prefer high role weight and moderate/short distance
        return dist / w

    target = min(candidates, key=score_candidate)
    dx = target["x"] - active["x"]
    dy = target["y"] - active["y"]
    dist = math.hypot(dx, dy)
    if dist < 0.03:
        ux, uy = 0.7071, -0.7071
    else:
        ux, uy = clamp_launch_vector(dx / dist, dy / dist)

    return target, ux, uy


def solve_2d_wall_bounce(
    start_pos: Tuple[float, float],
    target_pos: Tuple[float, float],
    bounces: int = 1,
    bounds: Tuple[float, float, float, float] = PLAYFIELD_BOUNDS,
) -> List[Dict[str, Any]]:
    """
    2D Method-of-Images Wall Reflection Solver for High-Difficulty Tactical Boss Mode.
    Computes exact launch vectors that reflect off 1 or 2 playfield walls to strike a weak point
    or wedge into a narrow gap between enemies.
    """
    x_min, x_max, y_min, y_max = bounds
    x0, y0 = start_pos
    xt, yt = target_pos
    solutions: List[Dict[str, Any]] = []

    # 1-bounce virtual mirror images across Left, Right, Top, Bottom walls
    mirrors_1 = [
        ("LEFT_WALL", 2 * x_min - xt, yt),
        ("RIGHT_WALL", 2 * x_max - xt, yt),
        ("TOP_WALL", xt, 2 * y_min - yt),
        ("BOTTOM_WALL", xt, 2 * y_max - yt),
    ]
    for label, mx, my in mirrors_1:
        dx, dy = mx - x0, my - y0
        dist = math.hypot(dx, dy)
        if dist > 1e-4:
            solutions.append({
                "type": f"1_BOUNCE_{label}",
                "bounces": 1,
                "ux": dx / dist,
                "uy": dy / dist,
                "path_length": round(dist, 3),
            })

    if bounces >= 2:
        # 2-bounce corner & opposite wall reflections
        mirrors_2 = [
            ("LEFT_THEN_TOP", 2 * x_min - xt, 2 * y_min - yt),
            ("RIGHT_THEN_TOP", 2 * x_max - xt, 2 * y_min - yt),
            ("LEFT_THEN_RIGHT", 2 * x_min - (2 * x_max - xt), yt),
            ("RIGHT_THEN_LEFT", 2 * x_max - (2 * x_min - xt), yt),
        ]
        for label, mx, my in mirrors_2:
            dx, dy = mx - x0, my - y0
            dist = math.hypot(dx, dy)
            if dist > 1e-4:
                solutions.append({
                    "type": f"2_BOUNCE_{label}",
                    "bounces": 2,
                    "ux": dx / dist,
                    "uy": dy / dist,
                    "path_length": round(dist, 3),
                })

    return sorted(solutions, key=lambda s: s["path_length"])


def vector_to_slingshot_drag(
    ux: float,
    uy: float,
    anchor: Tuple[float, float] = (0.50, 0.50),
    pull_len: float = 0.24,
) -> Tuple[float, float, float, float]:
    """Convert launch unit vector (ux, uy) into reverse slingshot drag coordinates (x1, y1, x2, y2)."""
    ax, ay = anchor
    x2 = max(0.06, min(0.94, ax - pull_len * ux))
    y2 = max(0.06, min(0.94, ay - pull_len * uy))
    return ax, ay, x2, y2
