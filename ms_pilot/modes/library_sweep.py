import math
import time
from typing import Any, Dict, List, Optional
from ..core.client import iPhoneClient
from ..core.vision import has_text_any
from ..core.physics import (
    compute_ally_aim_vector,
    extract_playfield_balls,
    vector_to_slingshot_drag,
)
from .fast_farm import handle_stamina_recovery


def navigate_to_library_stage(
    client: iPhoneClient,
    difficulty: str = "極",
    allow_stamina_cans: bool = True,
    max_steps: int = 30,
) -> bool:
    """
    Navigate into '追憶書庫' (Library of Memories), select an un-cleared ('NEW') quest,
    and enter the specified difficulty (default: '極' for fast Friendship Combo sweeping).
    """
    for step in range(max_steps):
        items = client.get_ocr_items()

        it_battle = next((it for it in items if it["text"].startswith("BATTLE") and it["y"] > 0.80), None)
        if it_battle:
            print(f"  [Library] Battle started ('{it_battle['text']}').")
            return True

        if has_text_any(items, ["體力不足", "回復體力"]):
            if handle_stamina_recovery(client, items, allow_stamina_cans):
                continue
            return False

        if has_text_any(items, ["書庫點數不足", "點數已用完"]):
            print("  [Library] Daily Library Points (書庫點數) depleted! Stopping gracefully.")
            return False

        it_deploy = next((it for it in items if it["text"].strip() == "出擊" and 0.58 <= it["y"] <= 0.82), None)
        if it_deploy:
            client.tap(it_deploy["x"], it_deploy["y"])
            time.sleep(2.0)
            continue

        if has_text_any(items, ["選擇幫手", "好友幫手角色", "大家的過關怪物"]):
            client.tap(0.500, 0.680)
            time.sleep(1.5)
            continue

        it_single = next((it for it in items if "單人" in it["text"] and 0.55 <= it["y"] <= 0.68), None)
        if it_single:
            client.tap(it_single["x"], it_single["y"])
            time.sleep(1.4)
            continue

        # Inside Library of Memories Quest List
        is_library = has_text_any(items, ["追憶書庫", "書庫點數", "篩選"])
        if is_library and not has_text_any(items, ["更換操作", "訓練冒險"]):
            # 1. Check if target difficulty ('極' or '究極') is already expanded
            it_diff = next(
                (
                    it for it in items
                    if it["text"].strip() == difficulty and 0.35 <= it["y"] <= 0.75
                ),
                None,
            )
            if not it_diff and difficulty == "極":
                # Match '極' while excluding '究極' or '超究極'
                it_diff = next(
                    (
                        it for it in items
                        if "極" in it["text"]
                        and "究" not in it["text"]
                        and 0.35 <= it["y"] <= 0.75
                    ),
                    None,
                )
            if it_diff:
                print(f"  [Library] Selecting difficulty '{it_diff['text']}' at y={it_diff['y']:.3f}...")
                client.tap(0.350, it_diff["y"])
                time.sleep(1.3)
                continue

            # 2. Find quest banner with 'NEW' tag or first available quest banner
            it_new = next((it for it in items if "NEW" in it["text"] and 0.28 <= it["y"] <= 0.78), None)
            if it_new:
                tap_y = min(0.80, it_new["y"] + 0.035)
                print(f"  [Library] Expanding NEW quest banner at y={tap_y:.3f}...")
                client.tap(0.350, tap_y)
                time.sleep(1.3)
                continue

            # Fallback: tap first quest banner slot in the list
            print("  [Library] Tapping top quest banner at (0.350, 0.420)...")
            client.tap(0.350, 0.420)
            time.sleep(1.3)
            continue

        # Category Screen -> Tap '追憶書庫' at (0.377, 0.497)
        if has_text_any(items, ["更換操作", "訓練冒險", "活動冒險"]):
            print("  [Category] Tapping 追憶書庫 at (0.377, 0.497)...")
            client.tap(0.377, 0.497)
            time.sleep(1.5)
            continue

        # Main Menu
        if has_text_any(items, ["SHORT CUT", "怪彈探險團"]):
            client.tap(0.502, 0.835)
            time.sleep(1.5)
            continue

        it_home = next((it for it in items if "主選單" in it["text"] and it["y"] > 0.90), None)
        if it_home:
            client.tap(it_home["x"], it_home["y"])
            time.sleep(1.5)
            continue

        time.sleep(0.8)

    return False


def run_library_sweep(
    client: iPhoneClient,
    difficulty: str = "極",
    max_runs: int = 10,
    allow_stamina_cans: bool = True,
) -> Dict[str, Any]:
    """
    Mode 2: Library of Memories ('追憶書庫') Sweep Mode.
    Uses 80% High-Friendship Steamroll + 4-Turn Anti-Stall Diagonal Fallback.
    """
    completed = 0
    for idx in range(1, max_runs + 1):
        print(f"\n==========================================")
        print(f"   [LIBRARY SWEEP {idx}/{max_runs}] Difficulty: {difficulty}")
        print(f"==========================================")
        if not navigate_to_library_stage(client, difficulty=difficulty, allow_stamina_cans=allow_stamina_cans):
            break

        turn_count = 0
        current_wave = "BATTLE 1"
        wave_turns = 0
        combat_start = time.time()

        while turn_count < 30 and (time.time() - combat_start) < 210:
            items = client.get_ocr_items()
            if has_text_any(items, ["特別獎勵", "過關獎勵", "破關情報", "STAGE CLEAR"]):
                print(f"  >>> LIBRARY STAGE CLEARED in {turn_count} turns! <<<")
                break

            it_wave = next((it for it in items if it["text"].startswith("BATTLE")), None)
            if it_wave and it_wave["text"] != current_wave:
                current_wave = it_wave["text"]
                wave_turns = 0

            balls = extract_playfield_balls(items)
            if len(balls) >= 2:
                turn_count += 1
                wave_turns += 1
                expected_slot = ((turn_count - 1) % 4) + 1
                active = next((b for b in balls if b.get("slot") == expected_slot), balls[0])

                # Anti-Stall Check: if stuck on the same wave > 4 turns, switch to wide multi-bounce sweep
                if wave_turns > 4:
                    angle_deg = 35 if (wave_turns % 2 == 1) else 145
                    rad = math.radians(angle_deg)
                    ux, uy = math.cos(rad), -math.sin(rad)
                    print(
                        f"  [Turn {turn_count} | ANTI-STALL] Wave stuck ({wave_turns} turns). "
                        f"Executing {angle_deg}° multi-bounce sweep!"
                    )
                else:
                    target, ux, uy = compute_ally_aim_vector(active, balls)
                    print(
                        f"  [Turn {turn_count}] Slot {expected_slot} -> Ally {target['raw']} "
                        f"(vec: {ux:+.2f}, {uy:+.2f})"
                    )

                x1, y1, x2, y2 = vector_to_slingshot_drag(ux, uy)
                client.drag(x1, y1, x2, y2, hold_ms=100, duration_ms=150)
                time.sleep(2.2)
            else:
                time.sleep(0.4)

        # Fast Settlement
        for _ in range(25):
            items = client.get_ocr_items()
            if has_text_any(items, ["追憶書庫", "主選單", "選擇遊玩類型"]):
                break
            if has_text_any(items, ["特別獎勵", "過關獎勵", ">>"]):
                client.tap(0.500, 0.650)
                time.sleep(0.4)
                continue
            it_ok = next((it for it in items if it["text"] == "OK"), None)
            if it_ok:
                client.tap(it_ok["x"], it_ok["y"])
                time.sleep(1.0)
                continue
            time.sleep(0.5)

        completed += 1

    return {"completed_runs": completed}
