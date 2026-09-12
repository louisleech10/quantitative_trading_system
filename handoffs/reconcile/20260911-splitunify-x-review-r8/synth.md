# Reconcile — 20260911-splitunify-x-review-r8

**來源** 20260911-splitunify-x-review-r8-codex.md　|　**roster** codex

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 入口轉換在契約上不可執行（缺全框標的歸屬輸入）**——「D-001已閉合R7的global→sy」 | P1 | CODEX-R8-P1-01 | 採納（斷言全採且抽驗屬實：既有 helper 需要全框 `symbol_arr`，而 R7 版之新簽名與 `SplitPlan` 皆無此向量 ⇒ R7 所寫之入口整批轉換叫不動。🔴 **修法落點改採等價方案**：不補全框輸入，改為 `SplitPlan` 新增 `row_index_local` 欄由 producer attest，投影端只消費該欄、內部一律不索引 `row_index`，缺欄即 fail-closed 且不得回退。理由：三個 producer 皆已持有標的內序號故寫入零成本，建 plan 之處 `symbol_arr` 皆可得故 attest 可用同一支具名 helper 逐值驗證，且不把全框輸入送回投影可避免 R7 之歧義復發。新增五條驗證段斷言與變異 `M-SU-D1-11`、`M-SU-D1-12`） |

**Verdict**: 需修補後合併——W1 為 P1 擋項，D-001 依上表修訂後須由原提出方於 R9 重驗閉合；因修法落點與原建議不同，R9 併派第二家審該取捨是否等價。

## 本輪程序記錄

- R8 為閉合輪，原提出方重驗 R7：`CODEX-R7-P1-01` 與 `CODEX-R6-P1-01` **皆確認閉合**（見交件檔 `CLOSED:` 行）。
- 該家獨立讀完 `derive_event_split_from_plans` 全函式，確認消費全框列號者僅四處＋指紋一處、**無第六處**：purge（`:501-515`）只消費已導出之 `test_start_ms`、cluster（`:519`）只吃 manifest、summary（`:521-533`）只吃已導出結果。此結論與主委 R7 所列封閉清單一致，該清單因此獲獨立覆核。
- 主委抽驗 W1：`momentum/core/contracts.py:504-519` 之 helper 簽名確需 `symbol_arr`；`SplitPlan`（`:377-390`）欄位表無此向量；`derive` 簽名（D-001-C1 第 1 點）亦無。斷言成立。
- 主委另行抽驗三個 producer 之可行性（此為改採等價方案之依據）：`contracts.py:659-661` 之 `train_local`／`test_local` 現成；`ic_split_adapter.py:230-231` 同；`ic_filter_orchestrator.py:631-643` 之 frame 為單標的（`symbols` 全為同一值，`:643`），其 `row_index` 本即標的內序號。建 plan 之處 `symbol_arr` 皆可得（`contracts.py:690`、`ic_split_adapter.py:258`、`ic_filter_orchestrator.py:643-648`）。
- 🔴 **此輪揭露之既有不對稱**：`row_index` 之座標語意在三個 producer 之間**本來就不一致**（兩處全框、一處標的內）。此事實此前未被任何一輪指出，已寫入 D-001-C2 第 4 點。
- 🔴 該家交件檔附之戳記寫 `sha256:PLACEHOLDER`，**非有效戳記**；且 D-001 於本輪後續有實質改動，戳記本即失效。R9 brief 已逐字要求戳記須帶 `reconcile_body_hash.sh` 之實際輸出。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

