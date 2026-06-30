# B2 required-probe winsor 偵測修復 — Composer 收尾

**Task**: `20260629-FF-B2-PROBEFIX`  
**Scope**: `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`

## 根因

append 模式 L6.5：winsor 原位寫入 L1–L6 原欄（欄名不變）；`{group_id}_L65` parquet 僅含 `_rank` / `_gaussian` / `_zscore_{w}` 追加欄。舊邏輯 `L65 + "winsor" in col` 在真實產物上永遠 0 命中 → `missing ['L65_winsor']`。

## 改動

- `_WINSOR_PROBE_LAYERS` + `_is_winsor_probe_layer()`
- `_select_required_probe_columns`：winsor probe 改抓 L1–L6 原位欄（無 L3 mean 時 fallback 任一 winsor 層欄）
- `_assert_mutation_layer_coverage`：`has_winsor` 同上
- smoke fixture L65 欄改真實後綴（rank/gaussian/zscore_20）

## 自驗

- `python -m py_compile tests/feature_engineering/test_ff_fullchain_truncation_mr.py` — PASS
- `pytest ...::test_b2_sampling_helper_smoke` — PASS

全鏈 `test_c2_1` / `test_mutation_causal_winsor_full_fit_fails` 未跑（依派工留 Claude 長 timeout）。

---

ASSUMPTIONS_VERIFIED: 讀 `feature_preprocessor.py` append rename（rank L3407、gaussian L3502、zscore L3549）；winsor in-place L2675+；L65 sink 僅 new_cols L864+

TESTS_RUN: py_compile PASS; pytest::test_b2_sampling_helper_smoke PASS

FAILURES_SEEN: none

SCOPE_CHANGES: none

NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
