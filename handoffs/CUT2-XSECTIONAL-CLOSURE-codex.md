# CUT2-XSECTIONAL Closure — Codex
Date: 2026-07-07
Task: 複驗 Codex code review 4 findings fix-round closure

## Findings
- FIX-1 BLOCKING F4: CLOSED. 原反例「1 timestamp/symbol + return_1 all NaN + ic_train_test_split=False」重跑，現在 raise `InvalidInputError: symbol BTC has all-NaN labels (fail-closed)`；非 `NO_RAISE`。
- FIX-2 MAJOR F3 mutation: CLOSED. `test_cross_sectional_oos_split_mutation_shrunk_purge_fails` 現在呼叫 `_build_cross_sectional_global_split(... effective_horizon=0)` 並期待 `SplitPairLeakageError`；舊套套斷言已不在測試中。指定 pytest 覆蓋此測試 PASS。
- FIX-3 MAJOR F1 kline hole: CLOSED. `_append_cross_sectional_labels` 使用 kline DatetimeIndex 精確 reindex；缺孔測試驗證 hole row 為 NaN、不 raise，且其餘 matched rows 對 oracle `assert_allclose`。指定 pytest PASS。
- FIX-4 MINOR timestamp dtype: CLOSED. `api/services/ic_analysis_service.py` 已用 `np.issubdtype(ts_raw.dtype, np.integer)`，並檢查負值、單調遞增、無重複。

## Evidence
- `source venv/bin/activate && pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py -q` -> 18 passed, 4748 warnings.
- 原 BLOCKING repro script -> `RAISED InvalidInputError: symbol BTC has all-NaN labels (fail-closed)`.

## Signoff
SIGNOFF: codex DATA-CORRECT PASS — 四個原 review finding 反例均已閉合，F4 blocking repro 現在 fail-closed raise。

ASSUMPTIONS_VERIFIED: RECONCILE-STAMP codex+composer APPROVED；逐項檢查 diff/測試；原 F4 BLOCKING repro 實跑已 raise。
TESTS_RUN: `pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py -q` -> 18 passed；原 F4 repro python script -> InvalidInputError。
FAILURES_SEEN: none.
SCOPE_CHANGES: none; closure review + handoff only.
NUMERIC_OR_SCHEMA_IMPACT: none by this closure; reviewed implementation touches label alignment, split metadata, coverage metadata.
STATUS: DONE
