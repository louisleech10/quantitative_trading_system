# CXSTAMP — 三家審碼 R2（閉合 R1 之 X1／X2）

brief-kind: review
task-id: `20260913-CXSTAMP-X-REVIEW-R2`
findings-round: R2

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行；findings 用 `## <FAMILY>-R2-P<0-3>-<NN>`；P0／P1 之 `**碼證**` 必含 `CODE-ANCHOR:`＋`MUTATION:`。

## ⚠️ 前置說明
- `handoffs/reconcile/*/synth.md` 非 gating 檔。本輪 **review**，**禁改碼**。
- R1 收斂：`handoffs/reconcile/20260913-cxstamp-x-review-r1/synth.md`（X1 兩家 P1 採納並修；X2 codex P2 採納並修；X3 composer 零 finding）。

## 任務
1. **codex／grok（原提出方，§B8 閉合確認）**：重跑你們 R1 的同一反例——改竄交件後以異路徑（stamp-target 自動登記／`handoffs/unrelated.md`）register，再跑 `debt_clear` ⇒ 須 **rc≠0**（R1 為 rc=0）；同路徑重登（sha 相符）⇒ rc=0。附實跑 rc。
2. **codex**：重跑 X2 interaction 探針（有效 RECONCILE-STAMP target＋缺 `**碼證**` 之 P3-00 交件）⇒ `COMMITTEE_OUTPUT_COUNT` 應 1→0。附實跑。
3. **三家**：審本輪 diff 有無新缺口——路徑正規化（相對／絕對／`..`／symlink）是否可繞；`_fmt_rc` 動態作用域在其他呼叫路徑（harness stub、`preserve*`）是否誤擋合法登記。
4. 三家：可否結票並進 stamp 輪。

## 審查標的（🔴 只餵 current block ＋ 本輪 diff）
- **current block**：`scripts/debt_clear.sh` 解鎖分支之 `_norm()` 與路徑等式；`scripts/cx_run.sh:_maybe_register_stamp_output` 之 `_fmt_rc` 守衛（條件①之後、body_hash 之前）。
- **本輪 diff**：`git diff ede04741..HEAD -- scripts/cx_run.sh scripts/debt_clear.sh tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py`
- 🔴 **不在範圍**：R1 已通過之 A（stamp 輪跑 --single）、B 之其餘五向、DOCROT。

## 前提
fact-verified: 修後 `test_debt_clear_stamp_unlock.py` 6 條、`test_cxrun_stamp_format_gate.py` 5 條、`test_debt_clear.py` 30 條、`test_govb1_b31_recovery.py`、`test_stamp_taskid_inject.py` → 143 passed；紅 5＝b31「工作區 debt_clear 無 diff」守衛（commit 後綠）＋stamp_taskid_inject 基準 4 條（隔離 repo 缺依賴，名單與 HANDOFF 基準相同）。
assumed: `Path.resolve()` 正規化足以擋相對／`..`／絕對混寫；symlink 指向同檔會被視為同一份（合理）。請攻。
assumed: `_fmt_rc` 在 `_run_cli_and_emit` 之外的呼叫路徑不存在（`_maybe_register_stamp_output` 只由該函式呼叫）⇒ `${_fmt_rc:-0}` 預設 0 不會誤擋。請攻：`grep -n "_maybe_register_stamp_output" scripts/cx_run.sh`。

## 必答
1. 反例重跑 rc（閉合／未閉合）。
2. 兩條 assumed 攻擊結果。
3. 可否結票進 stamp 輪？

## 產出
canonical 四欄 findings（或零 findings sentinel，含 `**斷言**`＋`**碼證**`）＋ `VERDICT: proceed|blocked`（`CLOSED:` 列出你閉合的 R1 ID）。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
