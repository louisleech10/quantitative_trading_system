# SPLITUNIFY D-001 閉合確認 R8
task-id: 20260911-SPLITUNIFY-X-REVIEW-R8；family: codex；findings-round: R8
只讀 closure review；未改碼、未動 tracked 檔、未 commit/push、未跑 tests/governance 全套。

## CODEX-R8-P1-01
**斷言**: D-001 已閉合 R7 的 global→symbol-local 語意歧義，但新簽名仍缺少入口轉換所需的全框 symbol membership 輸入；保留全框 `SplitPlan.row_index` 與 per-symbol 短 `feature_index` 的組合下，b8 契約不可執行。
**碼證**: 必答1：D-001:31-44 明定短索引且禁直接索引，D-001:65-72 明定入口整批轉換、同一 helper、fail-closed 與交錯測試，故 `CODEX-R7-P1-01` 語意修法已落字。必答2：上述同一組落點補足 R6 原缺的 membership bridge，故 `CODEX-R6-P1-01` 隨之閉合。必答3：完整讀 `derive_event_split_from_plans`：row_index 的執行消費只有長度/值域閘 `:454-458`、首尾對證 `:477`、train/test 時刻集合 `:486-487`、test 起點 `:488`；purge `:501-515` 只消費已導出的 `test_start_ms`，cluster `:519` 只吃 manifest，summary `:521-533` 只吃 event_keys/assignments/purged/clusters，無第六個 row_index 消費點。` :367-370` 的缺欄檢查、`:460-462` 的空段判定與 docstring `:351-354` 不是額外座標索引；C2:68 已涵蓋 docstring 改寫。必答4：有一個必要的全框輸入，但只在入口 global→local 轉換：`_local_ordinals_for_symbol(row_index, symbol_arr, symbol)` 需 `symbol_arr`；D-001:31-39 的簽名只有 plans、event_keys、`feature_index_by_symbol`，而 `SplitPlan:378-390` 沒有該向量。cluster/purge/summary 不需全框索引。必答5：`VERDICT: blocked`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#5502603ab805；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/event_samples/split_projection.py#98ee62905643；handoffs/reconcile/20260911-splitunify-x-review-r7/synth.md#
不改會在 b8 交錯資料落地時失敗：既有 helper 無法被正確呼叫；若直接以全框 row_index 索引 B 的短 index，會越界或取錯時刻；若另猜映射，則違反 D-001:69 的單一 helper 與 fail-closed 要求。修法：在 D-001-C1 簽名或 plan 契約補入與 producer universe 同序、同長度的全框 symbol membership 向量（或等價且具名、可驗證的 global-row→symbol 映射），入口先以 `_local_ordinals_for_symbol` 轉兩個 plan，再進五個既定消費點；pipeline、producer-attested 測試與交錯 fixture 一併列入。
ASSUMPTIONS_VERIFIED: `HANDOFF.md`、`CLAUDE.md`、本 brief、D-001、SPLITUNIFY_TODO、R7 synth 已讀；D-001 sha256=5502603ab805e94633e098882758acc98bb2d8733380269e633da352a89c3d93；完整函式與 `_local_ordinals_for_symbol` 實際讀取；原工作區 dirty 狀態已記錄並保留。
TESTS_RUN: `bash scripts/agent_preflight.sh` → rc=0；`shasum -a 256` 來源檔命令 → D-001 及四個碼證檔 digest 已輸出；`awk` derive row_index 靜態盤點 → 僅上述四個執行消費落點；completeness 同一 script/檔案/family 參數（family 值於 shell 展開）→ `COMPLETENESS PASS`、rc=0。
FAILURES_SEEN: 一次複合只讀命令被 PreToolUse 以 `[GATE BLOCKED] kind=dispatch` 誤分類；completeness literal 命令首次亦被同一閘擋，後續 family 值正確展開後格式檢查先 rc=1（quoting 導致 family-binding mismatch），修正展開後 rc=0。未繞過閘。
SCOPE_CHANGES: none；僅新增本產出檔，未改 tracked code/data 或測試。
NUMERIC_OR_SCHEMA_IMPACT: none；未改產品數值、資料、golden 或既有 schema；本 finding 僅要求補齊投影契約輸入。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r8-codex.md
TMP_CLEANUP: 審查前 `find /tmp -maxdepth 1 -mindepth 1 \( -name '*workdir*' -o -name 'claude-501' \)` 無輸出；未發現可清理的 workdir，無 `claude-501` 可保留。

## 戳記
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:da4ad7aab7a6bd5ab5dc49c8213c19452b98e59a86c57951ec538828917d9e88 task:20260911-SPLITUNIFY-X-REVIEW-R8
VERDICT: blocked
BLOCKED-BY: CODEX-R8-P1-01
CLOSED: CODEX-R7-P1-01,CODEX-R6-P1-01
STATUS: DONE
