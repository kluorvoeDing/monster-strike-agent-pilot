import os
import sys
import time
import math
import re

# Ensure module import works from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilot import iPhoneClient

def wait_for_condition(client, condition_fn, desc, timeout_secs=10.0, poll_interval=0.5):
    start = time.time()
    while time.time() - start < timeout_secs:
        items = client.get_ocr_items()
        matched = condition_fn(items)
        if matched:
            return matched, items
        time.sleep(poll_interval)
    return None, items

def play_stage_with_verification(client, stage_num):
    print(f"\n==========================================")
    print(f"   [STAGE {stage_num}/2] Starting Verified Run")
    print(f"==========================================")
    t0 = time.time()
    
    # Check if already on '出擊' screen or '單人' screen
    items = client.get_ocr_items()
    it_deploy = next((it for it in items if it["text"].strip() == "出擊" and 0.58 <= it["y"] <= 0.68), None)
    it_single = next((it for it in items if "單人" in it["text"] and 0.55 <= it["y"] <= 0.68), None)
    
    if not it_deploy and not it_single:
        # Step 1: Ensure at main menu
        print("  Navigating to Main Menu...")
        client.tap(0.085, 0.943)
        time.sleep(1.0)
        
        # Step 2: Adventure
        print("  Tapping 冒險 (0.500, 0.804)...")
        client.tap(0.500, 0.804)
        wait_for_condition(client, lambda items: next((it for it in items if "訓練冒險" in it["text"]), None), "訓練冒險 menu", timeout_secs=5.0)
        
        # Step 3: Training Quests
        print("  Tapping 訓練冒險 (0.161, 0.360)...")
        client.tap(0.161, 0.360)
        wait_for_condition(client, lambda items: next((it for it in items if "NEW" in it["text"] or "獎勵關卡" in it["text"]), None), "Training list", timeout_secs=5.0)
        
        # Step 4: Find NEW regular area
        items = client.get_ocr_items()
        new_tag = next((it for it in items if 0.20 <= it["y"] <= 0.70 and "NEW" in it["text"]), None)
        if new_tag:
            target_area = {"text": f"Area Banner below NEW", "x": 0.400, "y": min(0.70, new_tag["y"] + 0.042)}
        else:
            target_area = next((it for it in items if 0.25 <= it["y"] <= 0.45 and any(k in it["text"] for k in ["要塞", "魔境", "危險地", "險地", "險所", "魔殿", "空間"])), None)
        if not target_area:
            target_area = {"text": "Target Area", "x": 0.380, "y": 0.296}
            
        print(f"  Tapping Area: {target_area['text']} at ({target_area['x']:.3f}, {target_area['y']:.3f})")
        client.tap(target_area["x"], target_area["y"])
        wait_for_condition(client, lambda items: next((it for it in items if "獎勵關卡" in it["text"] or "消耗" in it["text"] or "NEW" in it["text"]), None), "Sub-stages", timeout_secs=5.0)
        
        # Step 5: Locate regular stage (CRITICAL SAFETY: NEVER 獎勵關卡)
        items = client.get_ocr_items()
        regular_stage = None
        for it in items:
            if "獎勵關卡" in it["text"]:
                print(f"  [SAFETY CHECK] Detected 獎勵關卡 at y={it['y']:.3f} -> AVOIDING!")
                continue
            if 0.40 <= it["y"] <= 0.55:
                if not any(k in it["text"] for k in ["獎勵", "冒險", "訓綀", "？", "詳情", "NEW", "消耗", "："]) and len(it["text"]) >= 3:
                    regular_stage = it
                    break
        if not regular_stage:
            regular_stage = {"text": "Regular Stage Banner", "x": 0.250, "y": 0.448}
            
        target_tap_x = 0.250  # Tap title text center
        target_tap_y = regular_stage["y"]
        print(f"  Tapping regular stage banner: {regular_stage['text']} at ({target_tap_x:.3f}, {target_tap_y:.3f})")
        for _ in range(3):
            client.tap(target_tap_x, target_tap_y)
            it_single, _ = wait_for_condition(client, lambda items: next((it for it in items if "單人" in it["text"] and 0.55 <= it["y"] <= 0.68), None), "單人 button", timeout_secs=2.5)
            if it_single:
                break
                
    if not it_deploy:
        if not it_single:
            raise RuntimeError("Failed to reach '單人' button")
        print(f"  [Verified] Found '單人' at ({it_single['x']:.3f}, {it_single['y']:.3f}). Tapping...")
        client.tap(it_single["x"], it_single["y"])
        
        # Step 6: Helper selection
        it_helper_title, _ = wait_for_condition(client, lambda items: next((it for it in items if any(k in it["text"] for k in ["選擇幫手", "幫手", "大家的過關怪物"])), None), "Helper screen", timeout_secs=6.0)
        if not it_helper_title:
            raise RuntimeError("Failed to reach Helper selection screen")
        print("  [Verified] Helper screen ready. Selecting helper at (0.500, 0.680)...")
        client.tap(0.500, 0.680)
        
        # Step 7: Team confirmation (出擊)
        it_deploy, _ = wait_for_condition(client, lambda items: next((it for it in items if it["text"].strip() == "出擊" and 0.58 <= it["y"] <= 0.68), None), "出擊 button", timeout_secs=6.0)
        if not it_deploy:
            raise RuntimeError("Failed to reach Team confirmation screen ('出擊' not found)")
            
    print(f"  [Verified] Found exact '出擊' at ({it_deploy['x']:.3f}, {it_deploy['y']:.3f}). Deploying...")
    client.tap(it_deploy["x"], it_deploy["y"])
    
    # Step 8: Wait for battle (Strictly check BATTLE label at bottom)
    print("  Waiting for battle initialization...")
    it_battle, _ = wait_for_condition(client, lambda items: next((it for it in items if it["text"].startswith("BATTLE") and it["y"] > 0.80), None), "BATTLE label", timeout_secs=15.0)
    if not it_battle:
        raise RuntimeError("Battle failed to load (BATTLE label not found)")
    print(f"  [Verified] Battle active! Detected '{it_battle['text']}' at y={it_battle['y']:.3f}. Starting combat loop...")
    
    # Step 9: Robust Direct-Aiming Combat Loop
    turn_count = 0
    max_turns = 25
    combat_start = time.time()
    ball_pattern = re.compile(r'^(?:[1-4]|Ast|Ist|Jst)\s*(?:st|nd|rd|th|d|t)?[\'|\*|®|,|’]?$', re.IGNORECASE)
    
    while turn_count < max_turns:
        if time.time() - combat_start > 180:
            print("  Combat timeout reached")
            break
            
        items = client.get_ocr_items()
        
        # Check Stage Clear
        if any(any(k in it["text"] for k in ["特別獎勵", "過關獎勵", "破關情報", "STAGE CLEAR", "運氣獎勵"]) for it in items):
            print(f"  >>> Stage {stage_num} CLEARED in {turn_count} turns! <<<")
            break
            
        # Check Tip popup
        has_tip = False
        for it in items:
            if it["text"] == "OK" and 0.50 <= it["y"] <= 0.65:
                print(f"  Dismissing tip popup at ({it['x']:.3f}, {it['y']:.3f})...")
                client.tap(it["x"], it["y"])
                time.sleep(0.8)
                has_tip = True
                break
        if has_tip:
            continue
            
        # Locate balls
        balls = []
        for it in items:
            txt = it["text"].strip()
            if 0.16 <= it["y"] <= 0.69:
                if len(txt) > 6 or "," in txt or "." in txt:
                    continue
                if ball_pattern.match(txt) or any(txt.startswith(tag) for tag in ["1st", "2nd", "3rd", "4th", "Jst", "Ist", "Ast"]):
                    balls.append({"raw": txt, "x": it["x"], "y": it["y"]})
                    
        if len(balls) >= 2:
            turn_count += 1
            active = balls[0]
            target = None
            for b in balls[1:]:
                if math.hypot(b["x"] - active["x"], b["y"] - active["y"]) > 0.05:
                    target = b
                    break
            if not target:
                target = balls[1]
                
            dx = target["x"] - active["x"]
            dy = target["y"] - active["y"]
            dist = math.hypot(dx, dy)
            if dist < 0.01:
                ux, uy = 0.707, -0.707
            else:
                ux, uy = dx / dist, dy / dist
                
            pull_len = 0.22
            drag_x2 = max(0.08, min(0.92, 0.50 - pull_len * ux))
            drag_y2 = max(0.08, min(0.92, 0.50 - pull_len * uy))
            
            # Strike Shot trigger logic (at Boss wave or when stalling)
            is_boss_stage = any("BOSS" in it["text"] or "超速" in it["text"] for it in items)
            active_idx = 0
            for i, tag in enumerate(["1", "2", "3", "4"]):
                if tag in active["raw"] or ["1st", "2nd", "3rd", "4th"][i] in active["raw"]:
                    active_idx = i
                    break
            slot_x = [0.065, 0.250, 0.440, 0.630][active_idx]
            has_ss_ready = any("OK" in it["text"] and 0.72 <= it["y"] <= 0.76 and abs(it["x"] - slot_x) < 0.10 for it in items)
            
            if (is_boss_stage or turn_count >= 5) and has_ss_ready:
                print(f"  >>> [STRIKE SHOT ACTIVATED] Slot {active_idx+1} launching Strike Shot at ({slot_x:.3f}, 0.747)! <<<")
                client.tap(slot_x, 0.747)
                time.sleep(0.4)
                
            print(f"  [Turn {turn_count}] Active {active['raw']} -> Target {target['raw']} (vector: {ux:+.2f}, {uy:+.2f})")
            client.drag(0.50, 0.50, drag_x2, drag_y2, hold_ms=150, duration_ms=200)
            time.sleep(3.2)
        else:
            time.sleep(0.6)
            
    # Step 10: State-Reactive Settlement Handler (Zero blind clicks)
    print("  Entering state-reactive settlement handler...")
    settlement_start = time.time()
    while time.time() - settlement_start < 45.0:
        items = client.get_ocr_items()
        
        # 1. Check if already back in Main Hall
        if any(k in it["text"] for k in ["主選單", "階級", "999,999,999+", "侄彈探險團", "怪彈探險團"]):
            print("  [Settlement Complete] Confirmed returned to Main Hall. Stopping all clicks.")
            break
            
        # 2. Tutorial / Tip popup OK (y around 0.50~0.65)
        tip_ok = next((it for it in items if it["text"] == "OK" and 0.50 <= it["y"] <= 0.65 and abs(it["x"] - 0.50) < 0.10), None)
        if tip_ok or any("攻略提示" in it["text"] for it in items):
            print(f"  [Settlement] Dismissing tip popup OK...")
            client.tap(0.501, 0.605)
            time.sleep(0.8)
            continue
            
        # 3. Egg cracking / Drop reward screens
        if any(k in it["text"] for k in ["特別獎勵", "過關獎勵", "速度獎勵", "運氣獎勵", ">>"]):
            print("  [Settlement] Cracking reward eggs...")
            client.tap(0.500, 0.650)
            time.sleep(0.2)
            client.tap(0.500, 0.650)
            time.sleep(0.6)
            continue
            
        # 4. Final summary / Clear info OK (y > 0.85)
        bottom_ok = next((it for it in items if it["text"] == "OK" and it["y"] > 0.85 and abs(it["x"] - 0.50) < 0.10), None)
        if bottom_ok or any("破關情報" in it["text"] for it in items):
            print("  [Settlement] Tapping Summary OK...")
            client.tap(0.497, 0.921)
            time.sleep(1.5)
            # Check if still showing summary (second page of summary)
            sub_items = client.get_ocr_items()
            if any(k in it["text"] for k in ["破關情報", "自動合成結果", "阿誠"] for it in sub_items):
                print("  [Settlement] Tapping second summary page OK...")
                client.tap(0.497, 0.921)
                time.sleep(2.5)
            continue
            
        # 5. Connecting / sync with server
        if any("連線中" in it["text"] for it in items):
            print("  [Settlement] Server syncing, waiting...")
            time.sleep(1.0)
            continue
            
        time.sleep(0.5)
    
    elapsed = time.time() - t0
    print(f"=== Stage {stage_num} COMPLETED in {elapsed:.1f}s ===")
    return elapsed

def main():
    total_start = time.time()
    num_stages = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    client = iPhoneClient(owner="antigravity")
    stage_times = []
    try:
        for idx in range(1, num_stages + 1):
            t = play_stage_with_verification(client, idx)
            stage_times.append(t)
            
        # Verify final orbs
        items = client.get_ocr_items()
        orbs = None
        for it in items:
            if it["y"] < 0.12 and it["x"] > 0.80 and it["text"].isdigit():
                orbs = it["text"]
                break
                
        total_time = time.time() - total_start
        print(f"\n==========================================")
        print(f"  RUN COMPLETED: {num_stages} STAGE(S) IN {total_time:.1f}s ({total_time/60:.2f} mins)!")
        for i, t in enumerate(stage_times, 1):
            print(f"  Stage {i}: {t:.1f}s")
        print(f"  Final Total Orbs: {orbs}")
        print(f"==========================================")
    finally:
        client.release_owner()
        client.close()

if __name__ == "__main__":
    main()
