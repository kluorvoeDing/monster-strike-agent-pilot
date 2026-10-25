import os
import sys
import time
import math
import re
from pilot import iPhoneClient

def play_one_stage(client, stage_idx):
    print(f"\n==========================================")
    print(f"   STARTING STAGE {stage_idx}/2")
    print(f"==========================================")
    t0 = time.time()
    
    # Step 1: Return to main menu if not already there, then go to Adventure
    print("[1] Navigating to Adventure...")
    client.tap(0.085, 0.943)  # Main menu
    time.sleep(1.0)
    client.tap(0.500, 0.804)  # Adventure
    time.sleep(1.2)
    
    # Step 2: Training Quests
    print("[2] Tapping 訓練冒險...")
    client.tap(0.161, 0.360)
    time.sleep(1.2)
    
    # Step 3: Find NEW training area
    items = client.get_ocr_items()
    target_area = None
    for it in items:
        if 0.20 <= it["y"] <= 0.80:
            if "NEW" in it["text"]:
                target_area = it
                break
                
    if not target_area:
        # If NEW not isolated, find highest area on screen that isn't cleared
        for it in items:
            if 0.25 <= it["y"] <= 0.50 and any(k in it["text"] for k in ["要塞", "空間", "區段", "深處", "荒野", "遺跡", "山谷", "雪原"]):
                target_area = it
                break
                
    if not target_area:
        # Default fallback area coordinate
        target_area = {"text": "Default Area", "x": 0.380, "y": 0.315}
        
    print(f"  Selected Area: {target_area['text']} at ({target_area['x']:.3f}, {target_area['y']:.3f})")
    client.tap(target_area["x"], target_area["y"])
    time.sleep(1.2)
    
    # Step 4: Find regular sub-stage (STRICTLY AVOID 獎勵關卡)
    items = client.get_ocr_items()
    sub_stage = None
    for it in items:
        if "獎勵關卡" in it["text"]:
            print(f"  [SAFETY WARNING] Detected 獎勵關卡 at ({it['x']:.3f}, {it['y']:.3f}) -> STRICTLY SKIPPING!")
            continue
        if 0.40 <= it["y"] <= 0.58:
            if "NEW" in it["text"] or "消耗" in it["text"] or len(it["text"]) >= 4:
                if not any(k in it["text"] for k in ["獎勵", "冒險", "訓綀", "？", "詳情"]):
                    sub_stage = it
                    break
                    
    if not sub_stage:
        sub_stage = {"text": "Regular Sub-stage", "x": 0.200, "y": 0.448}
        
    print(f"  Tapping regular sub-stage: {sub_stage['text']} at ({sub_stage['x']:.3f}, {sub_stage['y']:.3f})")
    client.tap(sub_stage["x"], sub_stage["y"])
    time.sleep(1.0)
    
    # Step 5: Single Player & Helper & Deploy
    print("[3] Deploying Lucifer Team...")
    client.tap(0.271, 0.618)  # 單人
    time.sleep(1.0)
    client.tap(0.500, 0.680)  # Helper
    time.sleep(1.5)
    client.tap(0.498, 0.633)  # 出擊
    print("  Battle loading (4.2s)...")
    time.sleep(4.2)
    
    # Step 6: Direct-Aiming Battle Loop
    print("[4] Executing Direct-Aiming Battle Loop...")
    battle_start = time.time()
    turn_count = 0
    max_turns = 12
    ball_pattern = re.compile(r'^(?:[1-4]|Ast|Ist|Jst)\s*(?:st|nd|rd|th|d|t)?[\'|\*|®|,|’]?$', re.IGNORECASE)
    
    while turn_count < max_turns:
        if time.time() - battle_start > 100:
            print("  Battle timeout!")
            break
            
        items = client.get_ocr_items()
        
        # Clear detection
        if any(any(k in it["text"] for k in ["特別獎勵", "過關獎勵", "破關情報", "STAGE CLEAR", "運氣獎勵"]) for it in items):
            print(f"  >>> Stage {stage_idx} Cleared in {turn_count} turns! <<<")
            break
            
        # Tips / OK popup
        tip_dismissed = False
        for it in items:
            if it["text"] == "OK" and 0.50 <= it["y"] <= 0.65:
                print(f"  Dismissing tip dialog at ({it['x']:.3f}, {it['y']:.3f})...")
                client.tap(it["x"], it["y"])
                time.sleep(0.8)
                tip_dismissed = True
                break
        if tip_dismissed:
            continue
            
        # Ball detection
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
            
            print(f"  [Turn {turn_count}] Active {active['raw']} -> Target {target['raw']} (vector: {ux:+.2f}, {uy:+.2f})")
            client.drag(0.50, 0.50, drag_x2, drag_y2, hold_ms=150, duration_ms=200)
            time.sleep(3.2)
        else:
            time.sleep(0.6)
            
    # Step 7: Post-battle fast skip
    print("[5] Fast-forward post-battle skip...")
    for _ in range(6):
        client.tap(0.500, 0.650)
        time.sleep(0.18)
    time.sleep(0.8)
    client.tap(0.497, 0.921)
    time.sleep(1.0)
    client.tap(0.497, 0.921)
    time.sleep(2.0)
    
    # Return to main menu
    client.tap(0.085, 0.943)
    time.sleep(1.5)
    
    elapsed = time.time() - t0
    print(f"=== Stage {stage_idx} Finished in {elapsed:.1f}s ===")
    return elapsed

def main():
    start_total = time.time()
    client = iPhoneClient(owner="antigravity")
    try:
        t1 = play_one_stage(client, 1)
        t2 = play_one_stage(client, 2)
        
        # Check final orbs
        items = client.get_ocr_items()
        final_orbs = None
        for it in items:
            if it["y"] < 0.12 and it["x"] > 0.80 and it["text"].isdigit():
                final_orbs = it["text"]
                break
                
        total_time = time.time() - start_total
        print(f"\n==========================================")
        print(f"  DOUBLE CLEAR COMPLETED IN {total_time:.1f}s ({total_time/60:.2f} mins)!")
        print(f"  Stage 1 Duration: {t1:.1f}s")
        print(f"  Stage 2 Duration: {t2:.1f}s")
        print(f"  Final Orbs Count: {final_orbs}")
        print(f"==========================================")
    finally:
        client.release_owner()
        client.close()

if __name__ == "__main__":
    main()
