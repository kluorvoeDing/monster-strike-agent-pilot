# Monster Strike Agent Pilot (`ms_pilot`)
**《怪物彈珠》AI 視覺領航與四大模式全自動操控框架（iPhone USB CoreDevice + MCP）**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: iOS / macOS](https://img.shields.io/badge/Platform-iOS%20%7C%20macOS-blue.svg)](#)
[![Agent Skill: Included](https://img.shields.io/badge/Agent%20Skill-SKILL.md-brightgreen.svg)](skill/SKILL.md)

> **零越獄、零外掛封號風險的「Agentic Gaming」開源範式**  
> 結合 **Apple Vision OCR**、**PIL 像素探針（Pixel Probes）**、**2D 鏡像反射物理模擬器（Method of Images）** 與 **AI Agent 戰術推演**，透過實體 iPhone USB 連線實現擬真人類手勢操控。

---

## 核心特色 (Why This Project?)

1. **四大專門化遊玩模式**：
   - **模式一：極速刷運極模式 (`farm`)**：支援「相同隊伍再挑戰」捷徑、2100 徽章真寶箱橘光像素檢驗、結算畫面直接讀取運氣值（零繞路免進怪物箱）、主砲優先瞄準權重與體力罐二階確認閉環。
   - **模式二：追憶書庫橫掃模式 (`library`)**：自動篩選「未突破（NEW）」並優先鎖定 **「極」難度**，以 80% 強友情 4～6 手速推 ＋ 20%「4 回合卡死自救（自動切換大角度多段斜射）」雙態引擎橫掃初通寶珠。
   - **模式三：高難度轟絕戰術模式 (`boss-sim` / `tactical_boss`)**：結合賽前 Subagent 攻略檢索、**2D 物理反射模擬器（計算 1～2 次擦牆卡點/刷弱點）** 與 HP 血量/即死倒數監控自動開 SS 與守護獸。
   - **模式四：人機協作領航模式 (`copilot`)**：交接時自動進行隊伍 4 欄位視覺色彩與文字建檔（徹底消除 AI 記憶幻覺），支援自然語言即時覆寫瞄準優先順序。
2. **即插即用 AI Agent Skill (`skill/SKILL.md`)**：
   - 內建專為 **Antigravity / Claude Code / Codex** 設計的 [`SKILL.md`](skill/SKILL.md)，其他玩家 `git clone` 後，AI 即可直接載入所有座標常數與「5 大防雷鐵律」，不必從零摸索。

---

## 專案目錄結構 (Repository Structure)

```text
monster-strike/
├── README.md                      # 專案首頁、架構與 CLI 快速上手指南
├── LICENSE                        # MIT 開源授權條款
├── requirements.txt               # Python 依賴套件 (Pillow)
├── .env.example                   # 環境變數設定範本 (MCP 路徑與 Owner 租約)
├── .gitignore                     # 自動過濾個人截圖與隱私資訊
│
├── skill/
│   └── SKILL.md                   # 即插即用 AI Agent Skill (含 5 大防雷鐵律)
│
├── docs/
│   ├── PLAYBOOK.md                # 完整 UI 座標地圖、快跳時序與拉射物理公式
│   ├── MAX_LUCK_GUIDE.md          # 極速刷運極標準作業程序 (SOP)
│   └── OPTIMIZATION_ROADMAP.md    # 實戰復盤與四大操控模式架構藍圖
│
├── assets/
│   └── templates/                 # 脫敏後的純 UI 參考圖庫
│       ├── chest_2100_inactive.png
│       └── chest_2100_active.png
│
└── ms_pilot/                      # 核心模組化 Python 套件
    ├── __init__.py
    ├── __main__.py                # 統一 CLI 入口 (python3 -m ms_pilot ...)
    ├── core/
    │   ├── client.py              # MCP 通訊橋接、Context Manager 自動釋放鎖
    │   ├── vision.py              # 混合視覺引擎 (OCR + 寶箱橘光檢測 + 血條估算)
    │   └── physics.py             # 序號過濾、防打地板安全鉗、2D 鏡像反射計算器
    └── modes/
        ├── fast_farm.py           # 模式一：極速刷運極模式
        ├── library_sweep.py       # 模式二：追憶書庫橫掃模式
        ├── tactical_boss.py       # 模式三：高難度轟絕戰術模式
        └── copilot.py             # 模式四：人機協作領航模式
```

---

## 快速上手與 CLI 指令 (Quickstart)

### 1. 環境安裝
```bash
pip install -r requirements.txt
cp .env.example .env
```

### 2. 四大模式執行指令

#### 模式一：極速刷運極模式（單場 7～8 寶箱連刷）
```bash
# 連續刷 5 場「朝霧與夜櫻」，自動開啟 2100 寶箱+2，達 99 運極自動停機
python3 -m ms_pilot farm --quest "朝霧與夜櫻" "遊馬" --runs 5 --target-luck 99
```

#### 模式二：追憶書庫橫掃模式（優先刷「極」難度）
```bash
# 自動進入追憶書庫，優先挑選「極」難度連續速推 10 場（含 4 回合卡死自救）
python3 -m ms_pilot library --difficulty 極 --runs 10
```

#### 模式三：高難度 2D 壁面反射路徑模擬
```bash
# 計算從發射點 (0.25, 0.55) 經 1~2 次牆壁反彈擊中 Boss 弱點 (0.50, 0.30) 的精確角度
python3 -m ms_pilot boss-sim --start 0.25 0.55 --target 0.50 0.30 --bounces 2
```

#### 模式四：人機協作領航模式（視覺建檔 + 指定優先碰撞隊友）
```bash
# 自動掃描當前配好的隊伍，並指定優先撞擊第 2 號位主力大砲
python3 -m ms_pilot copilot --quest "朝霧與夜櫻" --prefer-slot 2 --runs 3
```

---

## 實戰沉澱文檔索引 (Documentation)

- **[`docs/MAX_LUCK_GUIDE.md`](docs/MAX_LUCK_GUIDE.md)**：極速刷運極 5 大鐵律（掉落最大化黃金三角、2100 徽章寶箱橘光檢測、禁止打一場查一場）。
- **[`docs/PLAYBOOK.md`](docs/PLAYBOOK.md)**：全螢幕正規化座標地圖、結算快跳批次指令、訓練冒險後期黑洞/魔法陣防坑指南。
- **[`docs/OPTIMIZATION_ROADMAP.md`](docs/OPTIMIZATION_ROADMAP.md)**：昨日 30+ 場零敗北實戰復盤與四大模式演進藍圖。
