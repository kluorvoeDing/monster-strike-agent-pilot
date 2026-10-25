import time
from typing import Any, Dict, List, Optional, Tuple
from ..core.client import iPhoneClient
from ..core.vision import estimate_hp_ratio, has_text_any
from ..core.physics import (
    compute_ally_aim_vector,
    extract_playfield_balls,
    solve_2d_wall_bounce,
    vector_to_slingshot_drag,
)


def execute_tactical_boss_turn(
    client: iPhoneClient,
    items: List[Dict[str, Any]],
    turn_count: int,
    weak_point_pos: Optional[Tuple[float, float]] = None,
    prefer_bounces: int = 1,
    hp_crisis_threshold: float = 0.35,
) -> bool:
    """
    Mode 3: High-Difficulty Tactical Boss Step.
    - Monitors HP bar ratio; triggers Guardian Beast / Strike Shot on low HP or Boss phase.
    - Computes 1- or 2-wall reflection trajectories via 2D Method of Images when targeting
      Boss weak points or enemy pinch gaps.
    """
    balls = extract_playfield_balls(items)
    if not balls:
        return False

    expected_slot = ((turn_count - 1) % 4) + 1
    active = next((b for b in balls if b.get("slot") == expected_slot), balls[0])
    hp_ratio = estimate_hp_ratio(client)
    is_boss = has_text_any(items, ["BOSS", "超速"])

    # Crisis / Boss Strike Shot & Guardian Beast Decision Tree
    slot_idx = (active.get("slot") or expected_slot) - 1
    slot_x = [0.065, 0.250, 0.440, 0.630][slot_idx]
    has_ss = any(
        "OK" in it["text"] and 0.72 <= it["y"] <= 0.76 and abs(it["x"] - slot_x) < 0.10
        for it in items
    )

    if hp_ratio <= hp_crisis_threshold:
        print(f"  [Tactical Crisis] HP low ({hp_ratio*100:.0f}%). Checking Guardian Beast / SS...")
        # Guardian Beast icon sits on the right side of the deck bar (~0.88, 0.747)
        client.tap(0.885, 0.747)
        time.sleep(0.4)

    if (is_boss or hp_ratio <= hp_crisis_threshold) and has_ss:
        print(f"  >>> [TACTICAL SS] Slot {slot_idx+1} activating Strike Shot (HP: {hp_ratio*100:.0f}%)! <<<")
        client.tap(slot_x, 0.747)
        time.sleep(0.3)

    # Trajectory Calculation: 2D Wall-Bounce Reflection vs Direct Ally Raycast
    target_pt = weak_point_pos or (0.500, 0.340)  # Default Boss center-upper weakpoint zone
    if prefer_bounces >= 1 and is_boss:
        solutions = solve_2d_wall_bounce(
            start_pos=(active["x"], active["y"]),
            target_pos=target_pt,
            bounces=prefer_bounces,
        )
        best = solutions[0]
        ux, uy = best["ux"], best["uy"]
        print(
            f"  [Turn {turn_count} | 2D RAYCAST] {best['type']} -> "
            f"Target ({target_pt[0]:.2f}, {target_pt[1]:.2f}) vec=({ux:+.2f}, {uy:+.2f})"
        )
    else:
        ally, ux, uy = compute_ally_aim_vector(active, balls)
        print(
            f"  [Turn {turn_count} | TACTICAL ALLY] Slot {expected_slot} -> "
            f"{ally['raw']} vec=({ux:+.2f}, {uy:+.2f})"
        )

    x1, y1, x2, y2 = vector_to_slingshot_drag(ux, uy)
    client.drag(x1, y1, x2, y2, hold_ms=120, duration_ms=160)
    return True
