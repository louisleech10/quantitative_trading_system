# SPLITUNIFY D-001 閉合確認 R9（codex）

task-id: 20260911-SPLITUNIFY-X-REVIEW-R9；brief-kind: closure；findings-round: R9
只讀 closure review；未改碼、未動 tracked 檔、未 commit/push、未跑 `tests/governance` 全套。

## CODEX-R9-P1-01

**斷言**: R8 的 global→symbol-local 契約缺口已由 `row_index_local` 補上，但 producer 一次性 attest 不足以維持 `row_index`／`row_index_local` 的並存不變式；`SplitPlan(frozen=True)` 的 numpy 陣列仍可原地修改，故 b8 仍可能在投影與既有全框消費端之間產生漂移。

**碼證**: D-001:66-75、118-122 明定 producer 以 `_local_ordinals_for_symbol` 逐值 attest、derive 只消費 `row_index_local` 且缺欄不得回退；`momentum/core/contracts.py:377-403` 顯示 `SplitPlan` 只以 `@dataclass(frozen=True)` 凍結欄位，`row_index: np.ndarray` 且 `__post_init__` 沒有 defensive copy、`setflags(write=False)` 或兩欄的持續對證。實跑 `venv/bin/python -c '...'` 輸出 `mutated_frozen_field [99, 2]`，證明 frozen dataclass 的 numpy 欄仍可原地改寫。既有 consumer 仍以全框欄位取值：`momentum/Analysis/ic_filter_orchestrator.py:1318` 的 `features_df.index[test_plan.row_index]`、`:1335` 的 selection count、`:1359-1360` 的 rows count；新投影契約則改讀 local 欄。具體路徑是 producer attest 後有人執行 `test_plan.row_index[0] = ...`：derive 讀到未變的 `row_index_local`／fingerprint 而可通過，orchestrator 及 row identity consumer 卻讀到已變的 `row_index`，兩套結果分歧。靜態查核 `rg -n 'setflags|writeable|deep.?freeze|row_index_local' momentum/core/contracts.py momentum/Analysis/event_samples/split_projection.py momentum/Analysis/ic_split_adapter.py momentum/Analysis/ic_filter_orchestrator.py` 未見此契約的防漂移 guard。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#b978f441274b；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a；momentum/Analysis/event_samples/split_projection.py#98ee62905643

本 finding 不否定 R8 修法在「未被變異的 producer plan」上的座標等價性：`row_index_local` 使 derive 不需全框 symbol vector，交錯 symbol 的越界／錯時刻路徑已被設計上的 producer attest 與缺欄 fail-closed 擋住。因此 `CODEX-R8-P1-01` 已閉合。惟它不等價於「每次 derive 入口依當下 `row_index` 重新轉換」：後者不會繞過同一個 plan 的最新全框欄位，而新方案在 producer attest 後把全框欄位的變動與投影欄位脫鉤。

必答 1：已閉合，證據為 D-001:66-75 的 `row_index_local` producer attest、D-001:70-71 的 derive-only local consumption／缺欄 fail-closed，以及 D-001:118-122 的五條驗證斷言。

必答 2：在 producer 產生後不再變異的前提下，落點等價；在現行 mutable numpy array 契約下不完全等價，具體失效路徑如上。

必答 3：兩欄會漂移；producer 一次性 attest 不足，因 frozen dataclass 未提供深層不可變性，且 derive 刻意不再讀 `row_index`，無法在該入口重建 global→local 關聯。修法需在 D-001／`SplitPlan` 契約中加入兩個 row array 的 defensive copy＋唯讀 guard（或不可變 row 容器）及 mutation regression；單靠 producer attest 不足。

必答 4：orchestrator 單標的初始狀態下 `row_index_local == row_index`，故座標不對稱本身已被消除；但相同的原地變異會使 local 欄保持舊值而 orchestrator 的既有 `row_index` consumer 讀到新值，殘留風險仍在。

必答 5：目前不可進實作，`VERDICT: blocked`。若不補不變式，b8 可通過 construction-time attest／交錯 fixture，卻在 plan 共享後的原地變異路徑中同時產生不同的投影歸屬與 IC 選樣／row identity 數字。

ASSUMPTIONS_VERIFIED: `HANDOFF.md`、`CLAUDE.md`、本 brief、`docs/SPLITUNIFY_SPEC.D-001.md`、`docs/SPLITUNIFY_TODO.md`、R8 reconcile synth 與 R8 source 已讀；D-001 目前 body hash 為 `b9bff86647f633e6a4ecea7dbbf55378e7e252baf23b9d2ab39ec41dedf0c636`；`SplitPlan` shallow-frozen array probe 實跑輸出 `mutated_frozen_field [99, 2]`；R8 producer-attest／derive-local 落點逐條對讀。
TESTS_RUN: `bash scripts/agent_preflight.sh` → rc=0；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `b9bff86647f633e6a4ecea7dbbf55378e7e252baf23b9d2ab39ec41dedf0c636`；`venv/bin/python -c '...SplitPlan...p.row_index[0]=99...'` → `mutated_frozen_field [99, 2]`；`rg -n 'setflags|writeable|deep.?freeze|row_index_local' ...` → 未見 SplitPlan row-array 防漂移 guard。未跑產品 pytest，因 brief 明定 closure／禁改碼且不得跑 `tests/governance` 全套。
FAILURES_SEEN: literal `bash scripts/completeness_check.sh --single ... --family codex` once blocked by PreToolUse dispatch/debt gate before script start；shell-expanded same arguments then passed rc=0；審查期間未執行修正輪。
SCOPE_CHANGES: none；只新增本交件檔，未改 tracked code/data、未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；未改產品數值、schema、golden 或輸出資料；本 finding 建議補契約不可變性與 mutation test。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r9-codex.md
TMP_CLEANUP: `find /tmp -maxdepth 1 -mindepth 1 \( -name '*workdir*' -o -name 'claude-501' \) -print` → no candidates；未刪除任何項目，`claude-501` 不在場。

## 戳記
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:28a56a9e2e939b1b6fb8a2351ebf69487a34ae99f868fb9eb6192568d968d531 task:20260911-SPLITUNIFY-X-REVIEW-R9
VERDICT: blocked
BLOCKED-BY: CODEX-R9-P1-01
CLOSED: CODEX-R8-P1-01,CODEX-R7-P1-01,CODEX-R6-P1-01
STATUS: DONE
