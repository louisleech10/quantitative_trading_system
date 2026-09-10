不可進 B2b：CODEX-R1-P1-01、CODEX-R1-P1-02。
## CODEX-R1-P1-01
**斷言**: D-002「覆寫」兩個 touchset 錨點不是 BASE 實際存在的 heading，違反 frozen D 程序，故無法作為可機檢的原檔覆寫。
**碼證**: `FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md:84-95` 要求 heading 逐字存在；`git show e0f3cb52:docs/GAP3_EVENT_UX_SPEC.md | rg 'B1\.3|n_train|n_test|n_purged|summary\.split'` 無輸出(rc=1)；`D-002:12` 仍宣告兩項，實際 B1.3 heading 在 `GAP3_EVENT_TODO.md:115`。
**來源摘要**: docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md#176c58e0c914; docs/GAP3_EVENT_UX_SPEC.D-002.md#92cd70b1f366
正文：[MAJOR] 信心度=High。修法是改用正確 BASE/實際 heading，或將 touchset 宣告為 `none` 並升 R 處理；RECHECK：重跑上述 `git show ... | rg ...` 與 dext template check。
## CODEX-R1-P1-02
**斷言**: Task 1.3 驗證條件「清單行數等於 receipt 的 `^FAILED ` 行數」對 frozen receipt 不成立：19 ≠ 30。
**碼證**: `SPLITUNIFY_SPEC.md:405-411`、`SPLITUNIFY_TODO.md:144-149` 寫 raw 計數；實跑 `raw_FAILED=30, filtered_nodeids=19, baseline_list=19, set_diff=empty, pytest_rc=1`，receipt summary 為 `19 failed, 1103 passed, 15 skipped`。
**來源摘要**: docs/SPLITUNIFY_SPEC.md#1bf699fbde5b; docs/SPLITUNIFY_TODO.md#f18c6a09ec30; handoffs/run_receipts/splitunify-analysis-baseline.stdout#12b86d456500
正文：[MAJOR] 信心度=High。raw 進度列含非 nodeid 的 `FAILED`，會令自有驗收 gate 永遠誤判；修法是用與產檔相同的 `awk '/^FAILED / && $2 ~ /::/'` 計數。RECHECK：重跑該 extractor、`comm` 差集及 baseline nodeid collect-only。
## CODEX-R1-P2-03
**斷言**: B1 contract test 的「兩端對證」只有 JSON↔SPEC 字面 substring 檢查，不是獨立的 JSON↔Python 語意證明。
**碼證**: `test_splitunify_contract.py:97-109` 只查 `spec_text` 是否含 literals；`tests/...:112-115` 明示 Python constants/import-raise 延至 B2b；本測試實跑 8 passed。
**來源摘要**: tests/momentum/Analysis/test_splitunify_contract.py#901b0758baca; docs/SPLITUNIFY_TODO.md#f18c6a09ec30
正文：[MINOR] 信心度=High。B1 不動生產碼使此限制可理解，但不可把它稱為完整 self-proof；B2b 應補 JSON loader、集合相等與缺鍵 import-raise mutation。
## 必答 1–7
1. 無第二份邊界算術：B2a 沿用 `holdout_split_point`/`holdout_test_row_index`，ms 由其返回 row 取值；Timestamp、`np.datetime64`、epoch-ms `int64` 與 tz-aware probe 均一致於自身 epoch。
2. 目前 `rg` 僅命中 builder/測試，無 production caller；`test_start_ms=None` 合約正確，B2b 先以 `missing_test_plan` fail-closed，分工正確。
3. 不算真正兩端證，見 P2-03；不改生產碼的 B1 只能標示為 lexical bridge，Python 常數證留給 B2b。
4. 19 條可信：receipt 過濾結果=19、清單=19、差集空、collect-only rc=0；HANDOFF 的 20/1615 是不同或較舊 aggregate。差異本身不改清單，但 P1-02 的 raw-count gate 必須修正。
5. 不對，見 P1-01；兩項不是 BASE 的實際 heading 錨點。6. 合規：原檔 index diff 為 `1 insertion/1 deletion`，符合 §2.3 唯一允許的索引行變更。
7. 不可進 B2b：P1-01、P1-02 未解除；其餘 11 類無新增 finding（測試品質由 P1-02/P2-03 覆蓋）。
## Verdict
不可進 B2b：CODEX-R1-P1-01、CODEX-R1-P1-02；先修正式 touchset 與 Task 1.3 計數 gate，再重審。P2-03 為 B2b 必補證據，非單獨阻擋項。
ASSUMPTIONS_VERIFIED: 三個 RECONCILE-STAMP 全 APPROVED；本輪未改 code、SPEC/TODO、reconcile synth；`holdout_boundary` 無 caller、tz 行為、19 條集合與 collect-only 均已驗證，未把 HANDOFF 20 條當當前 receipt 事實。
TESTS_RUN: contract pytest 8 passed；boundary pytest 9 passed；timezone probe rc=0；baseline collect-only 19 items rc=0；D-002 template check PASS；restore script rc=128（sandbox 禁 `.git/index.lock`）。
FAILURES_SEEN: restore script 無法建立 `.git/index.lock`；已以 patch 還原其唯一測試副作用 `tests/golden/l65/test_inventory.txt`，diff 清空。
SCOPE_CHANGES: none；OUTPUT: handoffs/20260911-splitunify-b1-review-r1-codex.md；NUMERIC_OR_SCHEMA_IMPACT: 未修改，報告記錄 raw FAILED=30、filtered/list=19。
