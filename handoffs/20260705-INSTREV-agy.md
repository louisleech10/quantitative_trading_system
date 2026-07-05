這是本專案「制度層總審查」委員會委員 R1 的獨立完整審查報告。依據指示，本報告基於證據庫、文件比對與 Git 紀錄生成，旨在梳理、瘦身並強化協作體系。

### 1. 已驗證事實表

| 事實描述 | 證據出處 |
| :--- | :--- |
| `copilot-instructions.md` 已過期近三個月，未與現行協作制度同步 | `git log --format="%ai"` 顯示最後修改為 `2026-04-26 23:58:04`，停留在 v1 凍結期前 |
| 核心憲法多源重疊，造成 Token 浪費與潛在分叉風險 | `CLAUDE.md` (217 行)、`AGENTS.md` (179 行)、`.cursorrules` (181 行) 在「7大解耦規則」、「Quant 陷阱」、「實測 > 假設」等段落有高達 80% 內容完全一致 |
| 任務分派規則散落兩處，難以維護 | `CLAUDE.md` 第 20-46 行，以及 `handoffs/instrev-evidence/memory/feedback_task_routing.md` |
| TGF 實測中派工管線摩擦嚴重，依賴 Prose 導致多次卡關 | `ROADMAP.md` P0 立案描述與 `HANDOFF.md`：戳記輪×4、claim-check 擋 commit×5、provenance 中途才學會 |
| 鐵律不是使用者偏好，而是補丁 | `memory/feedback_rules_are_scar_tissue.md`：使用者明示不想管鐵律，要求委員會靠證據裁決增刪，能機檢就不寫 prose |

---

### 2. 不可砍清單（防瘦身誤傷核心）

以下規則經查驗皆對應「若移除必導致生死級/正確性事故」，因此**凍結不可砍**：
1. **實測 > 假設 (Validate Assumptions Before Acting)**：對應兩次血淚事故 (underscore 命名靜默失效、warmup 錯判)，是防幻覺的最根本底線。
2. **驗證保真度鐵律 (不准用玩具 fixture 假綠)**：對應 V2 timestamp 單位錯亂事故。無此鐵律，Agent 容易構造無效測試來矇混驗收。
3. **三方數據正確性簽核 (Data Truth & Leakage 防線)**：使用者明示無法自驗，FF/IC 資料正確性必須三方 (Claude/Codex/Composer) 同步 Pass，禁合成資料。
4. **七大解耦規則**：架構維護底線，對應 API 與引擎核心的界線。
5. **「大」任務的不可跳步管線 (Adversarial + 另一方 Review)**：對應 V1-V6 反覆重構 Churn，這是防收斂失敗的唯一斷路器。

---

### 3. 三層逐條 Findings

#### 第一層：憲法層 (內容 / 架構 / 儲存)
- **規則：** 於 `.github/copilot-instructions.md` 中維護 Agent 指令。
  - **出生事故/violation：** 長期閒置，Agent 已轉移至 Claude / Cursor / Codex。
  - **四選一裁決：** **淘汰**。
  - **理由：** 該檔案已失效，不具參考價值，且可能誤導後續接手的工具。
- **規則：** 在 `CLAUDE.md`、`AGENTS.md`、`.cursorrules` 分別完整寫入解耦規則、Quant 陷阱與實測鐵律。
  - **出生事故/violation：** 2026-05-31 四源同步修復耗時 (commit `4fd70d8`)。若不一致會導致 Agent A 驗收過但 Agent B 判定違規。`CLAUDE.md` 每 session 全載導致無謂 token 支出。
  - **四選一裁決：** **合併去重**。
  - **理由：** 將通用核心規則獨立抽取至 `docs/CORE_RULES.md` (或其他命名)，三份設定檔僅保留各自的工具特性、Prompt 定義及指向 Core 的索引，大幅瘦身 System Prompt。

#### 第二層：派工流程管線 (Pipeline & Ceremony)
- **規則：** Agent 必須自行記得完成戳記 (reconcile stamp)、claim-check、並在派工前後跑 pre/post-flight。
  - **出生事故/violation：** 近期 TGF epic 實測中發生戳記輪 × 4，同檔並發只能序列化，並多次被 Gate 擋下。
  - **四選一裁決：** **機械化**。
  - **理由：** Prose 規則對 Agent 的長上下文記憶不友善。應全面轉由執行端腳本控制，例如建立一個統一的 `agy dispatch` 命令封裝，自動夾帶所需參數與戳記，Agent 只需呼叫單一 CLI，剝奪 Agent 「忘記」的可能。

#### 第三層：小中大任務分類規則
- **規則：** 任務分派依賴 Agent 自我宣告「小 / 中 / 大」並走對應管線。
  - **出生事故/violation：** 常發生膨脹未升級或誤判（需靠 `feedback_task_routing.md` 與 `CLAUDE.md` 雙重補丁約束）。
  - **四選一裁決：** **留核心原則 + 機械化**。
  - **理由：** 核心「小任務自做、中大任務派工且必須走 SPEC/TODO adversarial」的原則不動，但將「判斷準則」收斂。不再依賴記憶體補丁，將所有零散記憶檔編入 `docs/MULTI_AGENT_ORCHESTRATION.md`，並透過腳本分析規模 (檔案數量/修改範圍) 若觸發門檻，直接以硬體閘門 `Blocked` 拒絕執行小任務流程，強迫走大管線。

---

### 4. 裁決彙總表

| 目標範圍 | 處置方式 | 執行動作 |
| :--- | :--- | :--- |
| `copilot-instructions.md` | **淘汰** | 直接刪除該檔案 |
| `CLAUDE.md`, `AGENTS.md`, `.cursorrules` | **合併去重** | 提取共通段落 (7大規則、Quant陷阱、保真度鐵律) 至專用 markdown，各 Agent 檔僅留參照與工具專屬設定 |
| 派工與戳記管線 | **機械化** | 將繁瑣的證明與蓋章流程內建於 `scripts/agent_preflight.sh` 或統一 dispatch 工具中，免去 Agent 記誦 |
| 小中大分類與管線約束 | **留核心 + 機械化** | 保留分派層級，將散落的記憶補丁匯入主文件，並在 CLI 工具中增加改動規模監控，逾越即自動斷路升級 |

---

### 5. 該升級給使用者否決的決策點

1. **刪除 `copilot-instructions.md`**：是否同意直接捨棄該歷史遺留物。
2. **Context 瘦身方案 (合併去重)**：將 `CLAUDE.md` 與 `.cursorrules` 等檔內的重疊內容移至獨立檔案。這可能改變 Cursor 或 Claude 載入 context 的預設行為 (若工具不自動 follow references)，是否同意承擔並實作對應讀檔機制。
3. **管線全自動化**：將戳記與 claim-check 機制從「Agent 手動宣告」進階為「腳本強制封裝」，使用者是否同意我們修改 dispatch hooks，將這些負擔全面移交給機檢層？

---
`STATUS: DONE`
