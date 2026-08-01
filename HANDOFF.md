# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-01 | **Branch**: **main** | **狀態**: **P1-6 B5 線 A ✅CLOSED、線 B ✅定案入 docs；線 C 未開。帳本 0 OPEN。**

## ▶ 下一步

1. **線 C（債務事件分檔）** — 使用者定序：線 B 完成後以線 C 當實戰，走 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` 全套
2. **Task 3.2** — mutation 探針＋既有測試回歸（B5 未竟）
3. **`P16-GATE-D1-STRUCTURED-VERDICT`** — B3 遺留必做項

**🔴 B5 完工判定綁線 C**（composer 裁定）：**線 C 閉合前 B5 一律 NOT-CLOSED**，不得靠拆線提早宣告收工。

## ✅ 線 B 定案（2026-08-01）

`docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` v1.0（147 行，6 節）
REF: `handoffs/reconcile/20260801-gov-amend-r7/synth.md` 三家 APPROVED，body sha `a36725a55cd3`
VERIFY: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260801-gov-amend-r7/synth.md` → rc=0

- **範圍＝只擋意外，不防蓄意**；蓄意類問題列 §4「記錄，不修」（7 項）
- **零新增檢查器**；用既有 `completeness_check`／`reconcile_stamps_check`／`debt_ledger`
- v0.1–v0.6 六版草案**全部作廢**（`handoffs/20260801-GOV-AMEND-PROCEDURE-DRAFT-V0{1..6}.md`）

### 失控機制（比規則更該記住）

把「修訂約定」做成「防蓄意繞過系統」→ 對抗審成無限迴圈（寫防護→找洞→補洞→找新洞）。
**委員每輪都對，問題在題目沒邊界。** 使用者定「沒 100% 解就先解 95%、殘留記錄、再犯再說」
→ 邊界釘死 → **同一批委員下一輪就給定案路徑**（R2–R6 全判「不可實作」；R7 三家皆「文字修補即可定案」）。
成本：7 輪、33 次派工、**約 50% 是純程序開銷**。

## 🔧 本 session 新增

- `scripts/draft_selfcheck.sh` — 治理草案起草缺陷五條檢查（**ADVISORY，不得掛 gate**，R4 收斂裁定）
  回溯命中 v0.3 全部 4 條 BLOCKING P0、v0.4／v0.5 各自的假宣稱原句
- `handoffs/gov_rejected_mechanisms.tsv` — 已否決機制錨點（append-only，防換名回歸）
- `handoffs/20260801-GOV-AMEND-BACKLOG.md` — 8 項實作待辦（B-1～B-8），**不具規範效力**

## ⚠️ 待辦票（優先）

`GOV-STAMP-TASKID-INJECT`（backlog B-7）— `cx_run.sh` 已注入 `ROUND_ID`，應同樣注入 `TASK_ID` 並自動
`register-output`。**本 session 因此多花 5 輪補正**（R4 兩家抄 brief 範例值；R5／R7 三家 provenance pending）。

其餘：`GOV-FORMAT-SSOT`（同型已 8 次）／`P16-DEBT-ROSTER-BINDING`／`GOV-VERIFY-RECEIPT-RUNNER`／
`GOV-REJECTED-LIST-ACK`／`GOV-TOKEN-WORKTREE-BIND`

## 📌 使用者定死（本 session）

1. **沒 100% 解 → 做 95/99% 那版現在收；殘留具名記錄，再犯再說**（記憶 `feedback_95_percent_then_record`）
2. **精確+效率 ≠ 便宜**：效率＝審查面小而準，不是省簽核
3. 禁統計手法充當達標；做不到就提案改 SPEC
4. 修訂凍結文件走延伸檔，非就地改
5. 暫存輸出一律放 `.claude/tmp/`

VERIFY: `pytest tests/governance -q` → **447 passed**（137.56s）；`bash scripts/restore_golden_inventory.sh` rc=0
