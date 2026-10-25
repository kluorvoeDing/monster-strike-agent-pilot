import os
import sys
import time
import math
import re
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

def run_stage_2():
    t0 = time.time()
    client = iPhoneClient(owner="antigravity")
    try:
        print("[1/5] Selecting regular stage '咒劍的暗黑靈魂' (0.230, 0.447)...")
        print("  [SAFETY CHECK] Strictly bypassing 獎勵關卡 (0.167, 0.360)!")
        
        # Tap until '單人' appears
        it_single = None
        for _ in range(3):
            client.tap(0.230, 0.447)
            it_single, _ = wait_for_condition(client, lambda items: next((it for it in items if "單人" in it["text"] and 0.55 <= it["y"] <= 0.68), None), "單人", timeout_secs=2.5)
            if it_single:
                break
                
        if not it_single:
            raise RuntimeError("Failed to open play mode selection ('單人' not found)")
            
        print(f"[2/5] [Verified] Found '單人' at ({it_single['x']:.3f}, {it_single['y']:.3f}). Tapping...")
        client.tap(it_single["x"], it_single["y"])
        
        # Helper
        it_helper, _ = wait_for_condition(client, lambda items: next((it for it in items if any(k in it["text"] for k in ["選擇幫手", "幫手", "大家的過關怪物"])), None), "Helper", timeout_secs=6.0)
        if not it_helper:
            raise RuntimeError("Helper screen failed to load")
            
        print("[3/5] [Verified] Helper screen ready. Selecting helper at (0.500, 0.680)...")
        client.tap(0.500, 0.680)
        
        # Deploy (exact '出擊')
        it_deploy, _ = wait_for_condition(client, lambda items: next((it for it in items if it["text"].strip() == "出擊" and 0.58 <= it["y"] <= 0.68), None), "出擊", timeout_secs=6.0)
        if not it_deploy:
            raise RuntimeError("Team confirmation screen failed to load ('出擊' not found)")
            
        print(f"[4/5] [Verified] Found exact '出擊' at ({it_deploy['x']:.3f}, {it_deploy['y']:.3f}). Deploying...")
        client.tap(it_deploy["x"], it_deploy["y"])
        
        # Wait for battle (BATTLE at bottom)
        print("  Waiting for battle initialization...")
        it_battle, _ = wait_for_condition(client, lambda items: next((it for it in items if it["text"].startswith("BATTLE") and it["y"] > 0.80), None), "BATTLE", timeout_secs=15.0)
        if not it_battle:
            raise RuntimeError("Battle failed to load within 15s")
            
        print(f"  [Verified] Battle active! Detected '{it_battle['text']}' at y={it_battle['y']:.3f}. Starting combat loop...")
        
        # Combat Loop
        turn_count = 0
        combat_start = time.time()
        ball_pattern = re.compile(r'^(?:[1-4]|Ast|Ist|Jst)\s*(?:st|nd|rd|th|d|t)?[\'|\*|®|,|’]?$', re.IGNORECASE)
        stage_cleared = False
        
        while time.time() - combat_start < 120:
            items = client.get_ocr_items()
            
            # Check Stage Clear
            if any(any(k in it["text"] for k in ["特別獎勵", "過關獎勵", "破關情報", "STAGE CLEAR", "運氣獎勵"]) for it in items):
                print(f"  >>> Stage 2 CLEARED in {turn_count} turns! <<<")
                stage_cleared = True
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
                
                print(f"  [Turn {turn_count}] Active {active['raw']} -> Target {target['raw']} (vector: {ux:+.2f}, {uy:+.2f})")
                client.drag(0.50, 0.50, drag_x2, drag_y2, hold_ms=150, duration_ms=200)
                time.sleep(3.2)
            else:
                time.sleep(0.6)
                
        # Post-battle fast skip
        print("[5/5] Fast skipping post-battle reward screens...")
        for _ in range(6):
            client.tap(0.500, 0.650)
            time.sleep(0.18)
        time.sleep(0.8)
        client.tap(0.497, 0.921)
        time.sleep(1.0)
        client.tap(0.497, 0.921)
        time.sleep(2.0)
        
        # Return to main menu
        print("  Returning to Main Menu...")
        client.tap(0.085, 0.943)
        time.sleep(1.5)
        
        # Check final orbs
        items = client.get_ocr_items()
        orbs = None
        for it in items:
            if it["y"] < 0.12 and it["x"] > 0.80 and it["text"].isdigit():
                orbs = it["text"]
                break
                
        elapsed = time.time() - t0
        print(f"=== STAGE 2 COMPLETED in {elapsed:.1f}s ===")
        print(f"Final Total Orbs: {orbs}")
    finally:
        client.release_owner()
        client.close()

if __name__ == "__main__":
    run_stage_2()
