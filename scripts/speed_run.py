import os
import sys
import time
import math
import re
from pilot import iPhoneClient

def run_speed_run_now():
    client = iPhoneClient(owner="antigravity")
    start_time = time.time()
    
    try:
        print("[1/5] Selecting regular stage '惡魔星光' (0.169, 0.447)...")
        print("  [SAFETY CHECK] STRICTLY bypassing 獎勵關卡 (0.167, 0.360)!")
        client.tap(0.169, 0.447)
        time.sleep(1.0)
        
        print("[2/5] Selecting Single Player (單人) (0.271, 0.618)...")
        client.tap(0.271, 0.618)
        time.sleep(1.0)
        
        print("[3/5] Selecting Helper (0.500, 0.680)...")
        client.tap(0.500, 0.680)
        time.sleep(1.2)
        
        print("[4/5] Deploying Team (出擊) (0.498, 0.633)...")
        client.tap(0.498, 0.633)
        print("  Loading battle (4.0s)...")
        time.sleep(4.0)
        
        print("[5/5] High-Speed Direct-Aiming Battle Loop...")
        battle_start = time.time()
        turn_count = 0
        max_turns = 10
        
        # Strict ball pattern: only 1st, 2nd, 3rd, 4th (with optional trailing symbols)
        # Strictly exclude pure numbers, damage numbers (e.g. 2,744,122), HP, or cooldown numbers
        ball_pattern = re.compile(r'^(?:[1-4]|Ast|Ist|Jst)\s*(?:st|nd|rd|th|d|t)?[\'|\*|®|,|’]?$', re.IGNORECASE)
        
        while turn_count < max_turns:
            now = time.time()
            if now - battle_start > 90:
                print("Battle loop timeout (90s)")
                break
                
            items = client.get_ocr_items()
            
            # Check for stage clear / rewards
            is_clear = False
            for it in items:
                if any(k in it["text"] for k in ["特別獎勵", "過關獎勵", "破關情報", "STAGE CLEAR", "運氣獎勵"]):
                    is_clear = True
                    break
            if is_clear:
                print(f"  >>> Stage clear detected after {turn_count} turns! <<<")
                break
                
            # Check for tutorial / tips popup
            has_ok = False
            for it in items:
                if it["text"] == "OK" and 0.52 <= it["y"] <= 0.65:
                    print(f"  Dismissing tip dialog at ({it['x']}, {it['y']})...")
                    client.tap(it["x"], it["y"])
                    time.sleep(0.8)
                    has_ok = True
                    break
            if has_ok:
                continue
                
            # Find balls on screen (playfield y in 0.16 ~ 0.69)
            balls = []
            for it in items:
                txt = it["text"].strip()
                if 0.16 <= it["y"] <= 0.69:
                    # Ignore damage numbers or long strings
                    if len(txt) > 6 or "," in txt or "." in txt:
                        continue
                    if ball_pattern.match(txt) or any(txt.startswith(tag) for tag in ["1st", "2nd", "3rd", "4th", "Jst", "Ist", "Ast"]):
                        balls.append({
                            "raw": txt,
                            "x": it["x"],
                            "y": it["y"]
                        })
                        
            if len(balls) >= 2:
                turn_count += 1
                active = balls[0]
                target = None
                for b in balls[1:]:
                    d = math.hypot(b["x"] - active["x"], b["y"] - active["y"])
                    if d > 0.05:
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
                    ux = dx / dist
                    uy = dy / dist
                    
                pull_len = 0.22
                drag_x2 = max(0.08, min(0.92, 0.50 - pull_len * ux))
                drag_y2 = max(0.08, min(0.92, 0.50 - pull_len * uy))
                
                print(f"  [Turn {turn_count}] Active {active['raw']} -> Target {target['raw']} (vector: {ux:+.2f}, {uy:+.2f})")
                client.drag(0.50, 0.50, drag_x2, drag_y2, hold_ms=150, duration_ms=200)
                
                # High-speed pause: only 3.2s
                time.sleep(3.2)
            else:
                # Balls moving or wave transitioning
                time.sleep(0.6)
                
        print("=== Rapid Post-Battle Skip Sequence ===")
        # Rapid egg opening
        for _ in range(6):
            client.tap(0.500, 0.650)
            time.sleep(0.18)
            
        time.sleep(0.8)
        client.tap(0.497, 0.921)
        time.sleep(1.0)
        client.tap(0.497, 0.921)
        time.sleep(1.2)
        
        items = client.get_ocr_items()
        orbs = None
        for it in items:
            if it["y"] < 0.12 and it["x"] > 0.80 and it["text"].isdigit():
                orbs = it["text"]
                break
                
        elapsed = time.time() - start_time
        print(f"=== HIGH-SPEED CLEAR COMPLETED ===")
        print(f"  Total Duration: {elapsed:.1f} seconds")
        print(f"  Total Turns: {turn_count}")
        print(f"  Updated Orbs: {orbs}")
        
    finally:
        client.release_owner()
        client.close()

if __name__ == "__main__":
    run_speed_run_now()
