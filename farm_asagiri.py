import os
import sys
import time
import math
import re
import io
import base64
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilot import iPhoneClient

def has_text_any(items, keywords):
    for it in items:
        for k in keywords:
            if k in it["text"]:
                return True
    return False

def check_chest_active(client):
    try:
        res = client.call_tool("phone_screenshot")
        content = res.get("content", [])
        for item in content:
            if item.get("type") == "image":
                raw = base64.b64decode(item.get("data"))
                im = Image.open(io.BytesIO(raw))
                pix = im.load()
                # Check orange glowing border at x=35-42, y=800 in 552x1200 coordinates
                return any(pix[x, 800][0] > 140 and pix[x, 800][0] > 1.8 * pix[x, 800][2] for x in range(35, 42))
    except Exception as e:
        print(f"  [Warning] Screenshot check failed: {e}")
    return False

def navigate_to_battle(client, max_steps=35, allow_stamina_cans=True, enable_extra_chest=True):
    chest_activated = False
    for step in range(max_steps):
        items = client.get_ocr_items()
        
        # 1. Check if battle already started
        it_battle = next((it for it in items if it["text"].startswith("BATTLE") and it["y"] > 0.80), None)
        if it_battle:
            print(f"  [Verified] Battle active! Detected '{it_battle['text']}' at y={it_battle['y']:.3f}.")
            return it_battle
            
        # Check stamina recovery dialog ("體力不足" / "回復體力")
        if has_text_any(items, ["體力不足", "回復體力"]):
            it_can = next((it for it in items if "體力罐" in it["text"]), None)
            if it_can and allow_stamina_cans:
                print(f"  [Stamina] Using Stamina Can at ({it_can['x']:.3f}, {it_can['y']:.3f})...")
                client.tap(it_can["x"], it_can["y"])
                time.sleep(1.2)
                it_ok = next((it for it in client.get_ocr_items() if it["text"] in ["OK", "使用", "確定"]), None)
                if it_ok:
                    client.tap(it_ok["x"], it_ok["y"])
                    time.sleep(1.5)
                continue
            else:
                print("  [Stamina Depleted] No stamina cans allowed or available. Stopping gracefully.")
                return False
            
        # 2. Check if on Deploy confirmation ("出擊")
        it_deploy = next((it for it in items if it["text"].strip() == "出擊" and 0.58 <= it["y"] <= 0.82), None)
        if it_deploy:
            if enable_extra_chest and not chest_activated:
                # Real 寶箱+2 is the leftmost golden chest icon (2100 medals) at (0.136, 0.677)
                active = check_chest_active(client)
                if not active:
                    print("  [Assist Item] Real 寶箱+2 is NOT active. Tapping (0.136, 0.677) to activate...")
                    client.tap(0.136, 0.677)
                    time.sleep(0.8)
                else:
                    print("  [Assist Item] Verified REAL 寶箱+2 is ALREADY ACTIVATED (orange glowing border).")
                chest_activated = True
            print(f"  [Nav Step {step+1}] Deploying at ({it_deploy['x']:.3f}, {it_deploy['y']:.3f})...")
            client.tap(it_deploy["x"], it_deploy["y"])
            time.sleep(2.0)
            continue
            
        # 3. Check if on Helper selection ("選擇幫手" / "好友幫手角色")
        if any(any(k in it["text"] for k in ["選擇幫手", "好友幫手角色", "大家的過關怪物"]) for it in items):
            print(f"  [Nav Step {step+1}] Selecting helper at (0.500, 0.680)...")
            client.tap(0.500, 0.680)
            time.sleep(1.5)
            continue
            
        # 4. Check if on Single player popup ("單人")
        it_single = next((it for it in items if "單人" in it["text"] and 0.55 <= it["y"] <= 0.68), None)
        if it_single:
            print(f"  [Nav Step {step+1}] Tapping '單人' at ({it_single['x']:.3f}, {it_single['y']:.3f})...")
            client.tap(it_single["x"], it_single["y"])
            time.sleep(1.5)
            continue
            
        # 5. Check if on Quest List screen ("出現中的冒險" / "時間表" / "喚回冒險")
        is_quest_list = any(any(k in it["text"] for k in ["出現中的冒險", "時間表", "喚回冒險"]) for it in items)
        if is_quest_list:
            # Check if 究極 is visible
            it_diff = next((it for it in items if "究極" in it["text"] and 0.35 <= it["y"] <= 0.60), None)
            if it_diff:
                print(f"  [Nav Step {step+1}] Found '究極' at ({it_diff['x']:.3f}, {it_diff['y']:.3f}). Tapping...")
                client.tap(0.350, it_diff["y"])
                time.sleep(1.2)
                continue
                
            # If 究極 not visible, check for 朝霧與夜櫻 banner
            it_banner = next((it for it in items if any(k in it["text"] for k in ["朝霧與夜櫻", "金烏玉兔", "遊馬"])), None)
            if it_banner:
                print(f"  [Nav Step {step+1}] Expanding quest '{it_banner['text']}' at (0.350, {it_banner['y']:.3f})...")
                client.tap(0.350, it_banner["y"])
                time.sleep(1.2)
                continue
                
            # If banner not visible, ensure 合作活動 filter tab is selected
            tab_collab = next((it for it in items if it["text"] == "合作活動" and 0.22 <= it["y"] <= 0.26), None)
            if tab_collab:
                print(f"  [Nav Step {step+1}] Filtering 合作活動 at ({tab_collab['x']:.3f}, {tab_collab['y']:.3f})...")
                client.tap(tab_collab["x"], tab_collab["y"])
                time.sleep(1.2)
                continue
                
        # 6. Check if on Category screen ("選擇遊玩類型" / "更換操作" / "活動冒險")
        is_category = any(any(k in it["text"] for k in ["更換操作", "訓練冒險"]) for it in items) or (any("活動冒險" in it["text"] for it in items) and not is_quest_list)
        if is_category:
            print(f"  [Nav Step {step+1}] Category screen: tapping 活動冒險 banner at (0.161, 0.498)...")
            client.tap(0.161, 0.498)
            time.sleep(1.5)
            continue
            
        # 7. Check if on Quick Retry ("以相同隊伍再次挑戰" / "再挑戰")
        it_retry = next((it for it in items if any(k in it["text"] for k in ["再挑戰", "相同隊伍", "再次出擊"])), None)
        if it_retry:
            print(f"  [Nav Step {step+1}] Quick retry at ({it_retry['x']:.3f}, {it_retry['y']:.3f})...")
            client.tap(it_retry["x"], it_retry["y"])
            time.sleep(1.5)
            continue
            
        # 8. Check if on Main Menu
        is_menu = any(any(k in it["text"] for k in ["SHORT CUT", "怪彈探險團", "好運怪物", "任務"]) for it in items)
        if is_menu:
            print(f"  [Nav Step {step+1}] Main menu: tapping Quest center button at (0.502, 0.835)...")
            client.tap(0.502, 0.835)
            time.sleep(1.5)
            continue

        # 8b. Subscreen return: if in 怪物箱, 商店, 轉蛋 etc, return to Main Menu
        if has_text_any(items, ["怪物箱", "守護獸", "商店", "轉蛋", "好友", "變更排序"]) and not is_menu:
            it_home = next((it for it in items if "主選單" in it["text"] and it["y"] > 0.90), None)
            if it_home:
                print(f"  [Nav Step {step+1}] Subscreen detected: returning to Main menu via ({it_home['x']:.3f}, {it_home['y']:.3f})...")
                client.tap(it_home["x"], it_home["y"])
                time.sleep(1.5)
                continue
            
        # 9. Dismiss any unexpected tip or dialog OK
        tip_ok = next((it for it in items if it["text"] == "OK" and 0.50 <= it["y"] <= 0.65 and abs(it["x"] - 0.50) < 0.10), None)
        if tip_ok:
            print(f"  [Nav Step {step+1}] Dismissing popup OK at ({tip_ok['x']:.3f}, {tip_ok['y']:.3f})...")
            client.tap(tip_ok["x"], tip_ok["y"])
            time.sleep(1.0)
            continue
            
        time.sleep(1.0)
        
    raise RuntimeError("Failed to navigate to battle after max_steps")

def play_one_asagiri_run(client, run_idx, allow_stamina_cans=True, enable_extra_chest=True):
    print(f"\n==========================================")
    print(f"   [FARM RUN {run_idx}] Starting 朝霧與夜櫻")
    print(f"==========================================")
    t0 = time.time()
    
    battle = navigate_to_battle(client, max_steps=20, allow_stamina_cans=allow_stamina_cans, enable_extra_chest=enable_extra_chest)
    if not battle:
        print(f"  [Run {run_idx} Aborted] Navigation to battle failed or stamina depleted.")
        return None
    print("  Battle confirmed active! Starting combat loop...")
    
    # Combat Loop
    turn_count = 0
    max_turns = 35
    combat_start = time.time()
    ball_pattern = re.compile(r'^(?:[1-4]|Ast|Ist|Jst)\s*(?:st|nd|rd|th|d|t)?[\'|\*|®|,|’]?$', re.IGNORECASE)
    
    def parse_slot(txt):
        t = txt.lower().strip()
        # Strictly match ordinal tags (1st, 2nd, 3rd, 4th); NEVER match bare numbers (enemy turn counters)
        if any(k in t for k in ["1st", "ist", "jst"]):
            return 1
        if "2nd" in t:
            return 2
        if "3rd" in t:
            return 3
        if "4th" in t:
            return 4
        return None
    
    while turn_count < max_turns:
        if time.time() - combat_start > 240:
            print("  Combat timeout reached")
            break
            
        items = client.get_ocr_items()
        
        # Check Stage Clear
        if has_text_any(items, ["特別獎勵", "過關獎勵", "破關情報", "STAGE CLEAR", "運氣獎勵"]):
            print(f"  >>> 朝霧與夜櫻 CLEARED in {turn_count} turns! <<<")
            break
            
        # Check Tip popup
        has_tip = False
        for it in items:
            if it["text"] == "OK" and 0.50 <= it["y"] <= 0.65:
                print(f"  Dismissing tip popup at ({it['x']:.3f}, {it['y']:.3f})...")
                client.tap(it["x"], it["y"])
                time.sleep(0.6)
                has_tip = True
                break
        if has_tip:
            continue
            
        # Locate balls
        balls = []
        for it in items:
            txt = it["text"].strip()
            # Strictly constrain to playfield (0.17 <= y <= 0.68)
            if 0.17 <= it["y"] <= 0.68:
                if len(txt) > 6 or "," in txt or "." in txt:
                    continue
                slot_num = parse_slot(txt)
                if slot_num:
                    balls.append({"raw": txt, "slot": slot_num, "x": it["x"], "y": it["y"]})
                    
        if len(balls) >= 2:
            turn_count += 1
            expected_slot = ((turn_count - 1) % 4) + 1
            
            # Find active ball matching current slot rotation
            active = next((b for b in balls if b.get("slot") == expected_slot), None)
            if not active:
                active = balls[0]
                
            # Pick the best teammate target (different slot or different position)
            candidates = [b for b in balls if b != active and math.hypot(b["x"] - active["x"], b["y"] - active["y"]) > 0.05]
            if not candidates:
                candidates = [b for b in balls if b != active]
            
            # Target closest teammate to trigger friendship combo reliably
            if candidates:
                target = min(candidates, key=lambda b: math.hypot(b["x"] - active["x"], b["y"] - active["y"]))
            else:
                target = balls[1]
                
            dx = target["x"] - active["x"]
            dy = target["y"] - active["y"]
            dist = math.hypot(dx, dy)
            if dist < 0.03:
                ux, uy = 0.707, -0.707  # Up-right diagonal sweep fallback
            else:
                ux, uy = dx / dist, dy / dist
                # Prevent pure vertical downward shoots into floor
                if uy > 0.85:
                    ux, uy = (0.707 if ux >= 0 else -0.707), -0.707
                
            pull_len = 0.24  # High velocity sling pull for multi-bounce triggers
            drag_x2 = max(0.06, min(0.94, 0.50 - pull_len * ux))
            drag_y2 = max(0.06, min(0.94, 0.50 - pull_len * uy))
            
            # Strike Shot check
            is_boss_stage = any("BOSS" in it["text"] or "超速" in it["text"] for it in items)
            active_slot_idx = (active.get("slot") or expected_slot) - 1
            slot_x = [0.065, 0.250, 0.440, 0.630][active_slot_idx]
            has_ss_ready = any("OK" in it["text"] and 0.72 <= it["y"] <= 0.76 and abs(it["x"] - slot_x) < 0.10 for it in items)
            
            if (is_boss_stage or turn_count >= 5) and has_ss_ready:
                print(f"  >>> [STRIKE SHOT ACTIVATED] Slot {active_slot_idx+1} launching Strike Shot at ({slot_x:.3f}, 0.747)! <<<")
                client.tap(slot_x, 0.747)
                time.sleep(0.3)
                
            print(f"  [Turn {turn_count}] Slot {expected_slot} ({active['raw']}) -> Teammate {target['raw']} (vector: {ux:+.2f}, {uy:+.2f})")
            client.drag(0.50, 0.50, drag_x2, drag_y2, hold_ms=100, duration_ms=150)
            time.sleep(2.3)
        else:
            time.sleep(0.4)
            
    # State-Reactive Settlement Handler for Event Quests
    print("  Entering state-reactive settlement handler...")
    settlement_start = time.time()
    while time.time() - settlement_start < 60.0:
        items = client.get_ocr_items()
        
        # 1. Check if back in Main Hall or selection screen or quick retry
        if has_text_any(items, ["主選單", "階級", "999,999,999+", "選擇遊玩類型", "出現中的冒險", "再挑戰", "相同隊伍"]):
            print("  [Settlement Complete] Reached menu / retry. Stopping settlement.")
            break
            
        # 2. Friend request dialog: tap "不申請" or "取消"
        friend_cancel = next((it for it in items if any(k in it["text"] for k in ["不申請", "取消", "拒絕"])), None)
        if friend_cancel:
            print(f"  [Settlement] Dismissing friend request at ({friend_cancel['x']:.3f}, {friend_cancel['y']:.3f})...")
            client.tap(friend_cancel["x"], friend_cancel["y"])
            time.sleep(0.8)
            continue
            
        # 3. Tip popup OK
        tip_ok = next((it for it in items if it["text"] == "OK" and 0.50 <= it["y"] <= 0.65 and abs(it["x"] - 0.50) < 0.10), None)
        if tip_ok or any("攻略提示" in it["text"] for it in items):
            print(f"  [Settlement] Dismissing tip popup OK...")
            client.tap(0.501, 0.605)
            time.sleep(0.6)
            continue
            
        # 4. Reward / Egg cracking
        if has_text_any(items, ["特別獎勵", "過關獎勵", "速度獎勵", "運氣獎勵", ">>"]):
            print("  [Settlement] Cracking reward eggs...")
            client.tap(0.500, 0.650)
            time.sleep(0.2)
            client.tap(0.500, 0.650)
            time.sleep(0.6)
            continue
            
        # 5. Summary pages (Drops, Badges, Points, Mission clear) - Keep tapping bottom OK
        bottom_ok = next((it for it in items if it["text"] == "OK" and it["y"] > 0.85 and abs(it["x"] - 0.50) < 0.10), None)
        if bottom_ok or has_text_any(items, ["破關情報", "獲得徽章", "阿誠", "合成", "道具", "階級提升"]):
            print("  [Settlement] Tapping Summary OK (0.497, 0.921)...")
            client.tap(0.497, 0.921)
            time.sleep(1.4)
            continue
            
        if any("連線中" in it["text"] for it in items):
            print("  [Settlement] Server syncing, waiting...")
            time.sleep(0.8)
            continue
            
        time.sleep(0.4)
        
    elapsed = time.time() - t0
    print(f"=== 朝霧與夜櫻 RUN {run_idx} COMPLETED in {elapsed:.1f}s ===")
    return elapsed

def main():
    num_runs = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3
    allow_cans = "--no-cans" not in sys.argv
    enable_extra = "--no-chest" not in sys.argv
    client = iPhoneClient(owner="antigravity")
    total_start = time.time()
    run_times = []
    try:
        for idx in range(1, num_runs + 1):
            t = play_one_asagiri_run(client, idx, allow_stamina_cans=allow_cans, enable_extra_chest=enable_extra)
            if t is None:
                print("  Stopping farming batch early.")
                break
            run_times.append(t)
            time.sleep(1.5)
            
        total_time = time.time() - total_start
        print(f"\n==========================================")
        print(f"  FARMING BATCH COMPLETED: {len(run_times)} RUNS IN {total_time:.1f}s ({total_time/60:.2f} mins)!")
        for i, t in enumerate(run_times, 1):
            print(f"  Run {i}: {t:.1f}s")
        print(f"==========================================")
    finally:
        client.release_owner()
        client.close()

if __name__ == "__main__":
    main()
