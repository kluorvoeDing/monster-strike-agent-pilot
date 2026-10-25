import time
from typing import Any, Dict, List, Optional, Tuple
from ..core.client import iPhoneClient
from ..core.vision import check_chest_2100_active, has_text_any, parse_current_luck
from ..core.physics import (
    compute_ally_aim_vector,
    extract_playfield_balls,
    vector_to_slingshot_drag,
)


def handle_stamina_recovery(
    client: iPhoneClient,
    items: List[Dict[str, Any]],
    allow_stamina_cans: bool = True,
) -> bool:
    """
    Two-step Stamina Can recovery loop.
    STRICT ZERO-ORB POLICY: Never taps Orbs (寶珠). Only uses Stamina Cans (體力罐).
    """
    if not allow_stamina_cans:
        print("  [Stamina] Stamina cans disabled by flag. Stopping gracefully.")
        return False

    it_can = next((it for it in items if "體力罐" in it["text"]), None)
    if it_can:
        print(f"  [Stamina] Tapping Stamina Can at ({it_can['x']:.3f}, {it_can['y']:.3f})...")
        client.tap(it_can["x"], it_can["y"])
        time.sleep(1.2)
        confirm_items = client.get_ocr_items()
        it_confirm = next(
            (
                it for it in confirm_items
                if any(k in it["text"] for k in ["是", "回復", "使用", "確定", "OK"])
                and 0.45 <= it["y"] <= 0.78
                and not any(bad in it["text"] for bad in ["寶珠", "取消", "否"])
            ),
            None,
        )
        if it_confirm:
            print(f"  [Stamina] Confirming Stamina Can recovery ('{it_confirm['text']}')...")
            client.tap(it_confirm["x"], it_confirm["y"])
            time.sleep(1.5)
            # Dismiss subsequent '已回復' OK popup if present
            post_items = client.get_ocr_items()
            it_post_ok = next((it for it in post_items if it["text"] == "OK"), None)
            if it_post_ok:
                client.tap(it_post_ok["x"], it_post_ok["y"])
                time.sleep(1.0)
            return True

    print("  [Stamina Depleted] No stamina cans available. Stopping to protect Orbs.")
    return False


def navigate_to_farm_battle(
    client: iPhoneClient,
    quest_keywords: List[str],
    difficulty: str = "究極",
    max_steps: int = 30,
    allow_stamina_cans: bool = True,
    enable_extra_chest: bool = True,
) -> Tuple[bool, Optional[int]]:
    """
    Navigate to the target quest battle.
    Prioritizes Quick Retry ('以相同隊伍再次挑戰'), checks banner Luck along the way,
    and verifies the 2100-medal '寶箱+2' orange glowing border before deploying.
    """
    chest_checked = False
    detected_luck: Optional[int] = None

    for step in range(max_steps):
        items = client.get_ocr_items()

        luck = parse_current_luck(items)
        if luck is not None:
            detected_luck = luck
            print(f"  [Luck Monitor] Detected current Luck on screen: {detected_luck}/99")
            if detected_luck >= 99:
                return False, 99

        # 1. Check if battle already started
        it_battle = next((it for it in items if it["text"].startswith("BATTLE") and it["y"] > 0.80), None)
        if it_battle:
            print(f"  [Battle Active] Detected '{it_battle['text']}'.")
            return True, detected_luck

        # 2. Check Stamina Recovery Dialog
        if has_text_any(items, ["體力不足", "回復體力"]):
            if handle_stamina_recovery(client, items, allow_stamina_cans):
                continue
            return False, detected_luck

        # 3. Quick Retry Priority ('以相同隊伍再次挑戰' / '再挑戰' -> saves 15s navigation)
        it_retry = next(
            (it for it in items if any(k in it["text"] for k in ["再挑戰", "相同隊伍", "再次出擊"])),
            None,
        )
        if it_retry:
            print(f"  [Quick Retry] Tapping '{it_retry['text']}' at ({it_retry['x']:.3f}, {it_retry['y']:.3f})...")
            client.tap(it_retry["x"], it_retry["y"])
            time.sleep(1.4)
            continue

        # 4. Deploy Confirmation ('出擊') + Real 2100 Chest Item Pixel Check
        it_deploy = next((it for it in items if it["text"].strip() == "出擊" and 0.58 <= it["y"] <= 0.82), None)
        if it_deploy:
            if enable_extra_chest and not chest_checked:
                if not check_chest_2100_active(client):
                    print("  [Assist Item] Activating 2100-medal 寶箱+2 at (0.136, 0.677)...")
                    client.tap(0.136, 0.677)
                    time.sleep(0.8)
                else:
                    print("  [Assist Item] Verified 2100-medal 寶箱+2 is ALREADY ACTIVE (orange glow).")
                chest_checked = True
            print(f"  [Deploy] Tapping 出擊 at ({it_deploy['x']:.3f}, {it_deploy['y']:.3f})...")
            client.tap(it_deploy["x"], it_deploy["y"])
            time.sleep(2.0)
            continue

        # 5. Helper Selection
        if has_text_any(items, ["選擇幫手", "好友幫手角色", "大家的過關怪物"]):
            print("  [Helper] Selecting top helper at (0.500, 0.680)...")
            client.tap(0.500, 0.680)
            time.sleep(1.5)
            continue

        # 6. Single-Player Selection ('單人')
        it_single = next((it for it in items if "單人" in it["text"] and 0.55 <= it["y"] <= 0.68), None)
        if it_single:
            client.tap(it_single["x"], it_single["y"])
            time.sleep(1.4)
            continue

        # 7. Quest List Screen
        is_quest_list = has_text_any(items, ["出現中的冒險", "時間表", "喚回冒險"])
        if is_quest_list:
            it_diff = next((it for it in items if difficulty in it["text"] and 0.35 <= it["y"] <= 0.65), None)
            if it_diff:
                client.tap(0.350, it_diff["y"])
                time.sleep(1.2)
                continue

            it_banner = next(
                (it for it in items if any(k in it["text"] for k in quest_keywords)),
                None,
            )
            if it_banner:
                print(f"  [Quest] Expanding '{it_banner['text']}' at y={it_banner['y']:.3f}...")
                client.tap(0.350, it_banner["y"])
                time.sleep(1.2)
                continue

        # 8. Category Screen ('活動冒險')
        is_category = has_text_any(items, ["更換操作", "訓練冒險"]) or (
            has_text_any(items, ["活動冒險"]) and not is_quest_list
        )
        if is_category:
            client.tap(0.161, 0.498)
            time.sleep(1.5)
            continue

        # 9. Main Menu or Subscreen Return
        is_menu = has_text_any(items, ["SHORT CUT", "怪彈探險團", "好運怪物"])
        if is_menu:
            client.tap(0.502, 0.835)
            time.sleep(1.5)
            continue

        it_home = next((it for it in items if "主選單" in it["text"] and it["y"] > 0.90), None)
        if it_home:
            client.tap(it_home["x"], it_home["y"])
            time.sleep(1.5)
            continue

        time.sleep(0.8)

    return False, detected_luck


def run_fast_farm_batch(
    client: iPhoneClient,
    quest_keywords: Optional[List[str]] = None,
    num_runs: int = 5,
    target_luck: int = 99,
    allow_stamina_cans: bool = True,
    enable_extra_chest: bool = True,
    role_weights: Optional[Dict[int, float]] = None,
) -> Dict[str, Any]:
    """Execute continuous Fast-Farming batch until num_runs or target_luck (99) is reached."""
    keywords = quest_keywords or ["朝霧與夜櫻", "金烏玉兔", "遊馬"]
    weights = role_weights or {1: 0.7, 2: 1.5, 3: 1.5, 4: 1.3}
    run_times: List[float] = []
    current_luck: Optional[int] = None

    for idx in range(1, num_runs + 1):
        print(f"\n==========================================")
        print(f"   [FAST-FARM RUN {idx}/{num_runs}] Target: {keywords[0]}")
        print(f"==========================================")
        t0 = time.time()

        ok, luck = navigate_to_farm_battle(
            client,
            quest_keywords=keywords,
            allow_stamina_cans=allow_stamina_cans,
            enable_extra_chest=enable_extra_chest,
        )
        if luck is not None:
            current_luck = luck
        if current_luck is not None and current_luck >= target_luck:
            print(f"  >>> TARGET LUCK {target_luck} REACHED ({current_luck})! Stopping batch! <<<")
            break
        if not ok:
            print("  [Batch Stopped] Could not enter battle (stamina depleted or navigation halted).")
            break

        # Combat Loop
        turn_count = 0
        combat_start = time.time()
        while turn_count < 35 and (time.time() - combat_start) < 240:
            items = client.get_ocr_items()
            if has_text_any(items, ["特別獎勵", "過關獎勵", "破關情報", "STAGE CLEAR", "運氣獎勵"]):
                print(f"  >>> STAGE CLEARED in {turn_count} turns! <<<")
                break

            tip_ok = next((it for it in items if it["text"] == "OK" and 0.50 <= it["y"] <= 0.65), None)
            if tip_ok:
                client.tap(tip_ok["x"], tip_ok["y"])
                time.sleep(0.5)
                continue

            balls = extract_playfield_balls(items)
            if len(balls) >= 2:
                turn_count += 1
                expected_slot = ((turn_count - 1) % 4) + 1
                active = next((b for b in balls if b.get("slot") == expected_slot), balls[0])
                target, ux, uy = compute_ally_aim_vector(active, balls, role_weights=weights)

                # Strike Shot trigger on Boss wave
                is_boss = has_text_any(items, ["BOSS", "超速"])
                slot_idx = (active.get("slot") or expected_slot) - 1
                slot_x = [0.065, 0.250, 0.440, 0.630][slot_idx]
                has_ss = any(
                    "OK" in it["text"] and 0.72 <= it["y"] <= 0.76 and abs(it["x"] - slot_x) < 0.10
                    for it in items
                )
                if (is_boss or turn_count >= 5) and has_ss:
                    print(f"  >>> [STRIKE SHOT] Activating Slot {slot_idx+1} SS! <<<")
                    client.tap(slot_x, 0.747)
                    time.sleep(0.3)

                x1, y1, x2, y2 = vector_to_slingshot_drag(ux, uy)
                print(
                    f"  [Turn {turn_count}] Slot {expected_slot} ({active['raw']}) -> "
                    f"Ally {target['raw']} (vec: {ux:+.2f}, {uy:+.2f})"
                )
                client.drag(x1, y1, x2, y2, hold_ms=100, duration_ms=150)
                time.sleep(2.3)
            else:
                time.sleep(0.4)

        # State-Reactive Settlement Loop with In-Settlement Luck OCR
        settlement_start = time.time()
        while time.time() - settlement_start < 60.0:
            items = client.get_ocr_items()
            luck = parse_current_luck(items)
            if luck is not None:
                current_luck = luck
                print(f"  [Settlement Luck OCR] Current Luck: {current_luck}/99")

            if has_text_any(
                items,
                ["主選單", "階級", "999,999,999+", "選擇遊玩類型", "出現中的冒險", "再挑戰", "相同隊伍"],
            ):
                break

            friend_cancel = next(
                (it for it in items if any(k in it["text"] for k in ["不申請", "取消", "拒絕"])),
                None,
            )
            if friend_cancel:
                client.tap(friend_cancel["x"], friend_cancel["y"])
                time.sleep(0.8)
                continue

            if has_text_any(items, ["特別獎勵", "過關獎勵", "速度獎勵", "運氣獎勵", ">>"]):
                client.run_steps([
                    {"kind": "tap", "x": 0.500, "y": 0.650},
                    {"kind": "pause", "ms": 200},
                    {"kind": "tap", "x": 0.500, "y": 0.650},
                ])
                time.sleep(0.6)
                continue

            generic_ok = next((it for it in items if it["text"] == "OK" and 0.45 <= it["y"] <= 0.95), None)
            if generic_ok or has_text_any(items, ["破關情報", "獲得徽章", "合成", "道具", "階級提升", "達成運極"]):
                tap_x = generic_ok["x"] if generic_ok else 0.497
                tap_y = generic_ok["y"] if generic_ok else 0.921
                client.tap(tap_x, tap_y)
                time.sleep(1.2)
                continue

            time.sleep(0.5)

        elapsed = time.time() - t0
        run_times.append(elapsed)
        print(f"=== RUN {idx} COMPLETED in {elapsed:.1f}s (Luck: {current_luck or 'unknown'}) ===")

        if current_luck is not None and current_luck >= target_luck:
            print(f"  >>> MAX LUCK ({target_luck}) ACHIEVED! Stopping batch! <<<")
            break

    return {"runs_completed": len(run_times), "run_times": run_times, "final_luck": current_luck}
