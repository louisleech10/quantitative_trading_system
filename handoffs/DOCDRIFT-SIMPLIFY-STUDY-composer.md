# 文檔簡化研究 — Composer 互審
Task-id: docdrift-simplify | Reviewer: Composer | Date: 2026-07-12
> 輸入：`handoffs/DOCDRIFT-SIMPLIFY-STUDY-claude.md` + 實檔 `docs/ARCHITECTURE.md`(2044 行)、`docs/DEVELOPMENT_GUIDE.md`(2434 行)。**只讀研究，未改任何文件。**

## 實測對照（2026-07-12）
| 項目 | 主委提案 | 實測 | 備註 |
|------|----------|------|------|
| 總行數 | 4479 | **4478** | wc -l；DEV 2434 非 2435 |
| ARCH §已實現功能 | 853 行 | **853** L1000–1852 | 23 個 `### ✅` 子功能 |
| ARCH §解耦 | 401 | **401** L150–550 | 含 Artifact Contract、V2/V3 解耦路線 |
| ARCH §目錄結構 | 364 | **364** L636–999 | 逐檔枚舉 |
| DEV 通用教條 8 節合計 | ~1400 | **~1475** | 前端311+性能200+代碼173+Python171+錯誤169+LLM168+日誌162+註釋121 |
| DEV 錯置 API 區塊 | L1334 | **L1334–1403** | 整段為 API_SPEC 補丁草稿，且 L1277+ markdown 已損壞 |

---

## ① 三刀行數估算與收益 — 是否實際？有無砍到不該砍？

### 刀 1 — ARCH「已實現功能」853→~150
**AGREE（方向）**：853 行 / 42% 是最大漂移源；逐功能 UI 表、端點列、tests 計數（如 L1605「175 tests」）確實可從 code / `API_SPECIFICATION.md` / `HANDOFF.md` 重生。**AGREE** 改為「能力索引表」是最高 ROI 刀。

**CHALLENGE（行數）**：853→150 偏樂觀。23 功能 ×（名稱+模組+端點 pointer+狀態）實務約 **220–280 行**；若再加 2–3 個 domain 摘要列（FF / IC / Strategy）會到 **~300**。

**CHALLENGE（不可直接刪的架構內容）**：「已實現功能」內混有**不可重生、應上移而非刪除**的架構決策，例如：
- Feature Factory **7 層 Pipeline 表**（L1555–1567）、L6.5 四路徑表（L1588–1595）、七段式命名（L1610）
- Optuna **Score 公式**（L1093–1102）
- MultiTF / AlignmentMode 批次語意（L1722+ 區段）

這些不是「功能狀態」，是 **domain 架構**。若刀 1 只做索引表而不把上述搬到穩定章節（建議擴充現僅 37 行的 `## 模組詳細設計`，或新增 `## Domain 架構`），等於**把漂移從 A 章移到 B 章或直接丟失 onboarding 深度**。

**CHALLENGE（假綠）**：L1608「Rule 1-7 完全遵守」與 D1/D2 後 scanner 現況矛盾。索引表若只砍敘事、不修正狀態欄，假綠會濃縮成一行 — **簡化必須順手改狀態欄 → pointer `HANDOFF` / scanner receipt**。

**刀 1 修正估算**：853→**250–320**（淨砍 **530–600**），非 700。

### 刀 2 — DEV 通用教條 ~1400→~500
**AGREE（方向）**：8 節通用 best-practice 與 `CLAUDE.md` / `AGENTS.md` / `.cursorrules` 高度重疊；刪除+pointer 合理。L1334 錯置區塊應**刪除或併入** `API_SPECIFICATION.md`（非 DEV 頂層 `##`）。

**CHALLENGE（500 行地板）**：主委列「保留完整：數據真實性、測試規範」— 僅這兩節已 **245 行**（137+108）。再加上專案特有、不宜全刪的：
- `## 長時間任務開發規範`（88，與 TODO 觸發「API 節」語意相關）
- `## 硬體自適應開發規範`（~25，FF 跨 tier 相關）
- 壓縮後仍須留的專案範例：`get_logger`、retryable 分類、ResponsiveContainer、Numba hot-path（~80–120）

**現實剩餘量 ~850–1000 行**，非 ~500。淨砍 **~900–1100** 仍可達，但 **~500 目標需再砍測試範例或長時間任務**，與主委「保留測試規範」衝突。

**CHALLENGE（L1277+ 格式腐敗）**：`## 長時間任務` 末段起 markdown 結構已壞（標題/程式塊邊界缺失）。修復本身是小改，但**不能當「刪 72 行 API 區塊」處理** — 整段需重寫或併入 API_SPEC + 留 cross-link。

**刀 2 修正估算**：2434→**900–1050**（淨砍 **~900–1000**）。

### 刀 3 — ARCH 目錄 364→~80 + 解耦收斂
**AGREE**：目錄樹 364→80（頂層 domain + 關鍵入口 +「完整樹 = repo」）可行，淨砍 **~280** 符合估算。

**CHALLENGE（解耦 401 收斂幅度）**：
- **可砍**：Protocol 長範例（L180–219）、Factory 分類清單（L225–~350 量級）→ pointer `protocols.py` / `factories.py`（D2 已標權威）。
- **不可砍**：**Artifact Contract Table**（L365–377）、**Service Pattern 圖**（L350–363）、**V2/V3 解耦路線 + 新模組 checklist**（L379–430）— 這是跨 domain 契約與演進策略，**code 無單一權威源**，刪了比端點枚舉傷害更大。
- **保留但縮**：解耦主表（L155–174）應留「現況+scanner pointer」，已是 D1/D2 成果。

**刀 3 修正估算**：解耦 401→**180–220**（非暗示的 ~150）；連目錄樹合計淨砍 **~420–480**。

### 三刀合計 vs 45% 目標
| 場景 | 估計剩餘行數 | vs 4478 |
|------|-------------|---------|
| 主委樂觀 | ~2500 | −44% |
| Composer 修正（含 domain 上移） | **~2600–2900** | **−35%–42%** |

**結論①**：**AGREE 三刀優先序與大方向**；**CHALLENGE 45%/2500 略樂觀 ~300–400 行**；最大風險不是砍多，而是**把 domain 架構當「可重生枚舉」刪掉**。

---

## ② 外移 vs 刪除界線

| 內容類型 | 建議 | 理由 |
|----------|------|------|
| REST 端點 / Request-Response 欄位 | **外移→`API_SPECIFICATION.md`** | 已有單一真相源；L1334 即錯置例 |
| 檔案樹 / route 檔名 / model 檔名列表 | **刪除**（留 domain 入口表） | `git ls-tree` / IDE 可重生；永遠漂移 |
| Protocol / Factory 完整清單 | **刪除枚舉，留 1 段機制+pointer** | 權威在 `.py` |
| 通用 PEP8 / React / Git 教條 | **刪除+pointer `CLAUDE.md`** | 執行端合約不在 DEV_GUIDE |
| Ultra Think / First Principle 長流程 | **刪除→~30 行摘要+pointer ORCH/CLAUDE** | 治理已遷移 |
| 功能完成度 / Phase 狀態 / test 計數 | **刪除→索引表狀態欄→`HANDOFF`/`ROADMAP`** | 狀態權威不在 ARCH |
| FF 7-layer / Artifact 路徑 / 數據流 | **保留在 ARCH**（可從「已實現」**搬移**，非刪） | 跨檔契約，非單一 code 檔可代 |
| 數據真實性 L0/L1/L2 分層 | **保留在 DEV**（可壓縮範例） | D2 成果 + 三方簽核依據 |
| 測試分層 + IC real kline 要件 | **保留在 DEV** | 與 `IC_API_TEST_LAYERING.md` 互指 |
| 長時間任務 / 硬體自適應 | **保留在 DEV**（壓縮通用輪詢教條） | 專案 API/FF 特有模式 |

**CHALLENGE 主委自陳反駁**：「外移只是搬家」— 若把 DEV 教條搬到新 `CODING_STANDARDS.md` 確實沒減負。**同意應刪則刪**；唯一外移主體應是**已存在的 API_SPEC**，禁止為搬家新建第三份大檔。

---

## ③ 簡化 ROI 與節奏建議

### 量化（粗估）
| 成本/收益 | 估算 |
|-----------|------|
| 全檔 on-demand 讀取 | 4478 行 ≈ **~18k tokens** / 次 |
| 精簡後全檔讀 | ~2700 行 ≈ **~11k tokens** / 次 |
| 單次省讀 | **~7k tokens**（僅在「整檔讀」時） |
| 讀取頻率 | **TGF V13 已改按需觸發**（`templates/TODO_GENERATION_PROMPT.md` L24–29），非每 session 全讀 → **邊際收益較 2026-06 下降** |
| 一次性改+雙家族審+錨點稽核 | **中任務**（2 檔、~2000 行 diff 級、需 SPEC） |
| 長期維護 | **已實現功能**每 feature 省 ~30 行同步 → **漂移 ROI 高** |

### 建議節奏
| 選項 | 建議 |
|------|------|
| 三刀全做 | 可達 −35%–42%，但需先解「domain 上移」設計，避免砍錯 |
| **只做刀 1** | **最推薦首包**：單章 853 行、漂移收益最大、scope 較窄 |
| 刀 2 全做 | 次包；但 **500 行目標不應硬追**，以 900–1000 為驗收 |
| 刀 3 解耦大砍 | **緩做**；目錄樹可先砍，解耦僅砍 Protocol/Factory 枚舉 |
| 全面緩做 | 若近期無 doc 專項人力，維持 status quo + 禁止再膨脹「已實現」 |

**結論③**：**AGREE 簡化有長期 ROI（抗漂移 > 省 token）**；**CHALLENGE「為省 on-demand token 做一次大改」單獨 justification 偏弱** — 應以**停止假綠與減少同步面**為主訴。

---

## ④ 更好結構？ARCH 拆 overview + appendix？

**CHALLENGE 拆成兩檔（lean + appendix）為預設首選**：
- 多一個「詳細檔」往往再長回來（`ARCHITECTURE_EXTENSIBILITY_GUIDE` 已在 Archived）
- 引用錨點、`CLAUDE.md`「治理以本檔+ORCH 為準」已分散；再拆增加「讀哪份」決策成本

**AGREE 更好的單檔內分層**（不增檔案）：
```
ARCHITECTURE.md
├── A. 穩定核心（必讀，~500–600）
│   系統概覽、技術棧摘要、解耦 pointer+現況表、整體架構、
│   Artifact Contract、數據流、Domain 架構（FF/IC/Strategy）
├── B. 能力索引（~250）
│   功能 | 狀態→HANDOFF | module | API→API_SPEC | UI→code
└── C. 維運短節（~100）
    性能/安全/擴展性 pointer、相關文檔
```
- **版本 changelog**（現 L5–17，16 行）可砍成「見 git log」或移 **Archived**，減少假精確日期。

**DEV_GUIDE** 應明確降級為 **how-to 補充**（檔頭已有 pointer banner）：只留數據真實性、測試分層、長任務、硬體自適應 + 短範例。

---

## ⑤ 11+8 引用錨點保全

### 引用面實測（非 handoff / 非 Archived 的現役 md）
- `ARCHITECTURE.md`：**~12** 檔（CLAUDE、AGENTS、README、PRODUCT_VISION、TGF 系列、INSTREV SPEC/TODO、GUIDELINES 等）
- `DEVELOPMENT_GUIDE.md`：**~8–10** 檔
- **帶 `#` 錨點的外部連結**：僅 **3** 份 Archived PLAN（`#解耦架構原則`）— 風險低
- **語意錨點（無 `#` 但 gate 依賴）** — 風險**高**：
  - `TODO_GENERATION_PROMPT.md` L27：`ARCHITECTURE.md` **Feature Factory 章** — 現藏在 `### ✅ 16` 深層，**無獨立 H2**
  - L28：`DEVELOPMENT_GUIDE.md` **API 節** — **現役檔無此 H2**；僅錯置的 `## GET /api/v1/search/task/{task_id}`

### 保全機制（建議寫進實作 SPEC）
1. **先建後刪**：新增穩定 H2 `## Feature Factory 架構`、`## API 與長時間任務`（或改 TGF 觸發表指向 `API_SPECIFICATION.md` + DEV §長時間任務）
2. **刪除前** `rg 'ARCHITECTURE\.md#|DEVELOPMENT_GUIDE\.md#'` + `rg 'Feature Factory 章|API 節' templates/ docs/`
3. **一版過渡 stub**：舊 H2 留一行「內容已移至 §X / API_SPEC Lnn」— 可選，Archived 錨點幾乎無需
4. **同步修正** `README.md` L682–684 錯誤行數（~1800/~3500 vs 實際 2044/2434）
5. **禁止裸刪** `#解耦架構原則` H2 標題本身（可縮內容）

**結論⑤**：**AGREE 主委「禁裸刪、要 pointer」**；**CHALLENGE「11+8 多半檔名級、錨點風險實在 TGF 語意觸發」** — 簡化驗收必含 **TGF 觸發表與新 H2 對齊**，否則按需讀會斷鏈。

---

## 綜合表：逐刀 AGREE / CHALLENGE

| 刀 | AGREE | CHALLENGE |
|----|-------|-----------|
| 1 已實現→索引 | 最大漂移源；索引+pointer 優於長敘事 | 150 行過緊；domain 架構須上移；假綠須修 |
| 2 DEV 教條 | 刪通用+pointer CLAUDE | 500 行不可行；L1277+ 須修復；保留節加總 >500 |
| 3 目錄+解耦 | 目錄樹可大砍 | 解耦不可砍 Artifact/V2V3；Factory 只砍枚舉 |

---

VERDICT: **分兩階段做 — 先做刀1（已實現→索引表+domain 架構上移+狀態欄誠實化，驗收 ARCH ~1750–1850 行），再做刀2 選刪（DEV 刪通用教條+修 L1334/長任務格式，驗收 ~950–1050 行，不追 500）；刀3 只做目錄樹+Protocol/Factory 枚舉刪除，解耦保留 Artifact Contract 與 checklist；不拆新檔，用單檔 A/B/C 分層；實作前另立 SPEC 並跑錨點+TGF 觸發對照。全三刀一次做僅在有人力做 domain 上移設計時才值得。**
