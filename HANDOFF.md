# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-02 | **Branch**: **main**（同步，`141e4b8`） | **狀態**: **P1-6 B5 線 A ✅／線 B ✅；線 C 未開。工作區乾淨、帳本 0 OPEN。**

## ▶ 下一步＝線 C（債務事件分檔）

**🔴 B5 完工判定綁線 C**（composer 裁定）：**線 C 閉合前 B5 一律 NOT-CLOSED**，不得拆線提早收工。

### 問題（實測數據，2026-08-02 重跑）

`.claude/gate/audit.log` **30,956 行**，但債務狀態機事件只佔極小比例：

| 內容 | 行數 | 佔比 |
|---|---|---|
| 舊式散文 gate 派工紀錄（非 JSON） | 28,516 | **92.1%** |
| `committee_dispatch` | 1,208 | 3.9% |
| `committee_output` | 577 | 1.9% |
| `gate_deny` | 366 | 1.2% |
| **債務狀態機**（`round_open` 83＋`family_result` 123＋`debt_abandon` 67＋`debt_clear` 16） | **289** | **0.93%** |

**兩個後果**：
1. `debt_ledger.sh` 每次 `--has-open` 要掃 3 萬行才撈到 289 行有效資料
2. **composer 已具名**：`_append_gate_deny_audit` 寫的是同一個 `${GATE_DIR}/audit.log`
   → **每次 gate 擋人都使快取失效** → 熱路徑在最需要時反而不存在（已讀碼確認）

### 做法

- **走 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` 全套**（第一個實戰案例）
- 這是**真設計變更**（新事件檔、遷移、雙寫或切換），非文字修訂 ⇒ 依 §1 屬 **R 重開**，完整三家審＋使用者裁定
- 效能 finding `CODEX-R2-P1-02` 已裁定外推到線 C，一併處理
- **禁**用統計手法讓效能數字看起來達標（使用者定死）；效能結果隨環境變動，須多次實跑並誠實記錄

### 開工前必做

1. 依 CLAUDE.md 稽核 HANDOFF／ROADMAP vs repo 實況（本檔數據為 2026-08-02 實跑，仍請重驗）
2. `bash scripts/agent_preflight.sh`
3. 派工一律 `committee_run.sh`（自動開債）；收集節點用 `reconcile_build.sh`

## 後續（線 C 之後）

`Task 3.2`（mutation 探針＋既有測試回歸）→ `P16-GATE-D1-STRUCTURED-VERDICT`（B3 遺留）

## ⚠️ 待辦票（線 C 前建議先做，會省很多輪）

**`GOV-STAMP-TASKID-INJECT`**（`handoffs/20260801-GOV-AMEND-BACKLOG.md` B-7）：
`cx_run.sh` 已注入 `ROUND_ID` 卻未注入 `TASK_ID`，且戳記後需人工 `gate.sh register-output`。
**本 session 因此多花 5 輪**（R4 兩家抄 brief 範例值致 provenance 失敗；R5／R7 三家 pending 需逐一補記）。

其餘：`GOV-FORMAT-SSOT`（同型已 8 次）／`P16-DEBT-ROSTER-BINDING`／`GOV-VERIFY-RECEIPT-RUNNER`／
`GOV-REJECTED-LIST-ACK`／`GOV-TOKEN-WORKTREE-BIND`

## ✅ 已完成（`141e4b8`，細節見 git log 與 ROADMAP）

- **線 A**：`gate.sh` 債務閘上線並實際擋下派工；壞行 fail-closed；`verify_b2` §7 三層
- **線 B**：`docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` v1.0 定案（147 行，三家戳記 `a36725a55cd3`）
  範圍＝**只擋意外不防蓄意**、**零新增檢查器**；v0.1–v0.6 六版草案作廢
- 新增 `scripts/draft_selfcheck.sh`（起草缺陷五條檢查，**ADVISORY 不得掛 gate**）
- VERIFY: `pytest tests/governance -q` → **447 passed**（137.56s）；`restore_golden_inventory.sh` rc=0

## 📌 使用者定死（本 session 新增）

1. **沒 100% 解 → 做 95/99% 那版現在收；殘留具名記錄，再犯再說**（記憶 `feedback_95_percent_then_record`）
   ⇒ **委員 brief 須明文宣告不受理範圍**，否則對抗審沒有終點（線 B 因此燒了 6 輪）
2. **精確+效率 ≠ 便宜**：效率＝審查面小而準，不是省簽核
3. 禁統計手法充當達標；做不到就提案改 SPEC
4. 修訂凍結文件走延伸檔（現已有正式程序）
5. 暫存輸出一律放 `.claude/tmp/`
