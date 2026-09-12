# SPLITUNIFY b8 審碼 R2 — codex
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R2; family: codex; findings-round: R2
R1 複驗：P1-01 CLOSED；P1-02 原始放行洞 CLOSED（adapter 新增 typed-error P2）；P2-03 CLOSED。
CLOSED_DETAIL: P1-01＝float64/bool/object producer 均 dtype ValueError；nullable Int64 合法 int64，matrix 形狀 ValueError，custom __index__ object dtype ValueError；三 cast 入口皆有 gate。
CLOSED_DETAIL: P1-02＝split_per_symbol NaT ValueError；adapter 整軸 guard 命中但暴露 CODEX-R2-P2-01；orchestrator `:285-286` AlignmentViolationError。
CLOSED_DETAIL: P2-03＝projection 只有 local 座標消費；其餘 row_index 文字限於全框 identity/universe guard 或明示禁止回退。

## CODEX-R2-P2-01
**斷言**: `ICSplitAdapter._with_row_positions` 的 NaT guard 引用未 import 的 `AlignmentViolationError`，NaT 輸入實際拋 `NameError` 而非預期的 typed fail-closed error。
**碼證**: `momentum/Analysis/ic_split_adapter.py:13-22,190-198` 缺該 import 但直接 raise；獨立 probe stdout=`adapter._with_row_positions: NameError name 'AlignmentViolationError' is not defined`。RECHECK：補同一 contracts import，重跑該 probe 與 adapter 測試。
**來源摘要**: momentum/Analysis/ic_split_adapter.py#8517730f1b29; momentum/core/contracts.py#1471cef968a3
[P2/high] 影響限於含 NaT 的 invalid-input 路徑，仍 fail-closed 但會變成內部錯誤；可行性證據：`contracts.py:933` 已有類別，orchestrator `:73` 已用同一 import；只在記憶體補該 binding 的 probe 回 `AlignmentViolationError` 且 `EXPECTED_TYPED_FAIL_CLOSED=True`。

## §0 被挑戰的前提
**dtype**：float64/bool/object、nullable `Int64`、`np.matrix`、`__index__` object 均無靜默錯誤 plan；nullable 無缺值正規化為合法 int64，matrix 後續因二維索引 ValueError fail-closed。
**NaT**：split_per_symbol 與 adapter 都在 coerce 後檢查整軸；invalid 字串在 coerce 內直接 raise；orchestrator `ic_filter_orchestrator.py:285-286` 檢查 `ts.hasnans`。未驗證範圍：真實 IC 端到端數值未跑。

ASSUMPTIONS_VERIFIED: 三條 R1 反例、額外型別 probe、三 cast 入口、projection row_index 語意與 NaT 路徑均實跑/讀碼核對；source 工作樹無本輪修改。
TESTS_RUN: producer+adapter `27 passed`; derive selectors `22 passed, 56 deselected`; disclosure `28 passed`; `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`; typed-fix feasibility probe → `AlignmentViolationError`, `EXPECTED_TYPED_FAIL_CLOSED=True`。
FAILURES_SEEN: 新 finding 的 NaT adapter probe 為 `NameError`；其餘 targeted tests/golden pass。
SCOPE_CHANGES: none；未改 code、tests、SPEC、root HANDOFF.md 或 data_cache；只新增本交件檔。
NUMERIC_OR_SCHEMA_IMPACT: none；未改輸出數值、schema、檔案大小或測試斷言。
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-b8-review-r2-codex.md；`find /tmp -maxdepth 1 -mindepth 1 -print` 無 workdir，無需刪除，保留 claude-501 條件成立。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P2-03
STATUS: DONE
