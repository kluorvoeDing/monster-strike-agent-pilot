---
name: monster-strike-pilot
description: Autonomous & Co-Pilot AI Agent Skill for playing Monster Strike (怪物彈珠) on a physical iPhone via iphone-use-mcp. Includes 4 specialized gameplay modes (Fast-Farming Max-Luck 99, Library of Memories Sweep, High-Difficulty Tactical Boss 2D Wall-Bounce Solver, and Human-in-the-Loop Co-Pilot) and strict anti-pitfall guardrails.
---

# Monster Strike Agent Pilot Skill (`monster-strike-pilot`)

Use this skill whenever the user asks to automate, farm, clear, or co-pilot **Monster Strike (《怪物彈珠》)** on iPhone.

---

## 1. Five Iron Rules (Mandatory Guardrails)

1. **STRICT ZERO-ORB CONSUMPTION (絕對不消耗寶珠)**:
   - Never spend Orbs (寶珠) to recover stamina or continue after defeat.
   - Only use **Stamina Cans (體力罐)** via the 2-step confirmation loop (`體力罐` $\to$ `是` / `回復`). If no Stamina Cans remain, stop gracefully.
2. **REAL 2100-MEDAL CHEST VERIFICATION (認清 2100 徽章真寶箱與橘光檢測)**:
   - On the Deploy (`出擊`) screen, the **"寶箱＋2 (Extra 2 Chests)"** item is the **leftmost card (Slot 1, Golden Treasure Chest with red patterns, price `2100` medals)** at `(0.136, 0.677)`.
   - Never tap the `4200` medal item (Slot 3, purple Strike Shot orb).
   - Always run `check_chest_2100_active(client)` (pixel RGB check `r > 140 and r > 1.8 * b` at `x=35..42, y=800`) before tapping: if the orange border glow is already active, **DO NOT tap it again** (tapping an active item unchecks it!).
3. **BATCH EXECUTION — NEVER CHECK MONSTER BOX AFTER EVERY RUN (禁止打一場查一場)**:
   - Run 3–5 continuous runs per batch.
   - Track Luck directly during settlement or on the quest banner (`parse_current_luck`) and use **Quick Retry (`以相同隊伍再次挑戰`)** whenever available.
4. **STRICT ORDINAL BALL FILTER & FLOOR CLAMP (排除小怪倒數與防打地板)**:
   - Constrain ball detection strictly to the playfield: `0.17 <= y <= 0.68`.
   - Match only ordinal tags (`1st`, `2nd`, `3rd`, `4th`). Never match bare single digits (`"1"`, `"2"`, `"3"`, `"4"`), which are enemy attack countdown timers.
   - Clamp downward vectors (`if uy > 0.85: ux, uy = ±0.707, -0.707`) to prevent shooting vertically into the bottom floor.
5. **ZERO TEAM HALLUCINATION & ALWAYS RELEASE OWNER (杜絕隊伍幻覺並確保釋放鎖)**:
   - Never assume what characters are in the user's team from past memory. Always inspect the current screen (`profile_team_on_screen`) when a user hands over a new team.
   - Always use `with iPhoneClient() as client:` so `phone_release_owner` is guaranteed on exit.

---

## 2. Four Specialized Gameplay Modes (`ms_pilot`)

### Mode 1: Fast-Farming & Max-Luck 99 (`ms_pilot farm`)
- **Use Case**: Farming collaboration / event `究極` quests to Luck 99 (`運極`).
- **Setup**: Slot 1 = Luck 99 Leader (+2 chests) + `2100` Medal Chest item (+2 chests) = **7–8 chests/run**.
- **Command**:
  ```bash
  python3 -m ms_pilot farm --quest "朝霧與夜櫻" --runs 5 --target-luck 99
  ```

### Mode 2: Library of Memories Sweep (`ms_pilot library`)
- **Use Case**: Sweeping **「追憶書庫」** un-cleared (`NEW`) stages, prioritizing **「極」** difficulty where 80%+ of stages are steamrolled in 4–6 turns by strong Friendship Combos.
- **Built-in Anti-Stall**: Automatically switches to $35^\circ / 145^\circ$ multi-bounce sweeps if stuck on any wave for $>4$ turns.
- **Command**:
  ```bash
  python3 -m ms_pilot library --difficulty 極 --runs 10
  ```

### Mode 3: High-Difficulty Tactical Boss (`ms_pilot boss-sim` / `tactical_boss.py`)
- **Use Case**: `轟絕` / `黎絕` / `超究極` stages requiring wall-bounce weak-point strikes or enemy gap wedging (`卡點`).
- ** workflow**:
  1. Dispatch a `research` subagent to look up GameWith / Bahamut stage gimmicks (Gravity, Damage Wall, Warp, Mines, Transfer Wall, Pierce/Reflect restriction).
  2. Use `solve_2d_wall_bounce(start_pos, target_pos, bounces=2)` (Method of Images) to compute exact 1- or 2-wall reflection vectors.
  3. Monitor HP bar (`estimate_hp_ratio`) to trigger Guardian Beast and Strike Shots when $\text{HP} \le 35\%$.

### Mode 4: Human-in-the-Loop Co-Pilot (`ms_pilot copilot`)
- **Use Case**: User builds the team or specifies custom turn rules (e.g., "prioritize hitting Slot 2").
- **Command**:
  ```bash
  python3 -m ms_pilot copilot --quest "朝霧與夜櫻" --prefer-slot 2 --runs 3
  ```
