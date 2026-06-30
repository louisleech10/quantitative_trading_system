# B2 比對效能實作 — Composer 收尾

**Task**: `20260629-FF-B2-PERF-IMPL`  
**Scope**: 僅 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 比對 helper  
**依據**: `handoffs/20260629-FF-B2-PERF-RECONCILE.md`

## 實作摘要

1. **批次讀 parquet**：`_group_sampled_by_parquet` + `_read_parquet_columns`；每檔 full/trunc 各讀一次指定欄，消除 `_assert_values_gate_main` / warmup 逐欄 `read_parquet`。
2. **columns gate**：維持全集（`_assert_columns_gate` 不變，只讀欄名 set）。
3. **分層抽樣** `_build_sampled_columns`：stem+suffix 分組鍵、K=min(40,組)+邊界、上限 8k、下限 3000（common≥3000 時）、每 parquet 至少 1 欄。
4. **mutation 硬保證**：`_select_required_probe_columns`（L3 mean、L4 lag_1、L65 winsor）∪ 抽樣；`_assert_mutation_layer_coverage` 缺層即 fail。
5. **fracdiff MR**：未改（`_assert_fracdiff_truncation_invariants` 仍全欄嚴格）。
6. **覆蓋率守衛**：`comparable / len(sampled) ≥ 0.95`；`_log_sampling_report` 輸出 sampled/total/groups/fallback/probes。

## 自驗（未跑全鏈）

- `python -m py_compile tests/feature_engineering/test_ff_fullchain_truncation_mr.py` — PASS
- `pytest tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_b2_sampling_helper_smoke` — PASS (0.25s)

全鏈 `test_c2_1` / mutation ×5 留 Claude 長 timeout 驗收。

---

ASSUMPTIONS_VERIFIED: 讀碼確認 L3 suffix `_{agg}_W{window}`、L4 `_Lag_{n}`、L65 stem 含 `L65` token；smoke 合成 parquet 驗證抽樣/批次讀/warmup 共用 sampled set。

TESTS_RUN: py_compile PASS; pytest::test_b2_sampling_helper_smoke PASS

FAILURES_SEEN: none

SCOPE_CHANGES: none

NUMERIC_OR_SCHEMA_IMPACT: 無（僅測試比對路徑；generate/storage/oracle 未動；比對欄數 220k→~8k 抽樣）

STATUS: DONE

---

## PROBEFIX（2026-06-29，Composer `20260629-FF-B2-PROBEFIX`）

**根因（讀碼實證）**：`feature_preprocessor.py` append 模式 winsor **原位**寫回 L1–L6 原欄（`_apply_winsorization` 不改欄名）；L65 parquet 僅含 `{col}_rank` / `{col}_gaussian` / `{col}_zscore_{w}` 追加欄。**無**含 `winsor` token 的 L65 欄 → 舊 `layer=="L65" and "winsor" in col` 永遠 miss。

**修法**：`_is_winsor_probe_layer`（L1–L6）；`_select_required_probe_columns` / `_assert_mutation_layer_coverage` 改偵測原位 winsor 欄（優先 L3 mean，與 L3 探針同欄）；smoke fixture L65 改 `_rank/_gaussian/_zscore_20`。

**自驗**：py_compile PASS；`test_b2_sampling_helper_smoke` PASS；probe 單元腳本確認 L3 mean 入選、L65 rank 不入 winsor probe。全鏈 `test_c2_1` + winsor mutation 留 Claude 長 timeout。

ASSUMPTIONS_VERIFIED: `feature_preprocessor.py:3407` append rank `f"{column}_rank"`；winsor in-place `result.loc[:, columns]`（L2675+）；L65 group 僅 new_cols（L864+）。

TESTS_RUN: py_compile PASS; pytest::test_b2_sampling_helper_smoke PASS (0.26s)

FAILURES_SEEN: none

SCOPE_CHANGES: none（僅 `test_ff_fullchain_truncation_mr.py`）

NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE

---

## MUTFIX（2026-06-30，Composer `20260630-FF-B2-MUTFIX`）

**依據**: `handoffs/20260630-FF-B2-MUTFIX-RECONCILE.md`（三方定案）

**修1 `test_mutation_l4_lag_shift_minus_one_fails`**:
- 注入：改 patch `LagProcessor.compute_all`，在呼叫期間暫時反轉 `pd.DataFrame.shift` 正 lag→`shift(-lag)`，覆蓋 production fast path 與 chunked path。
- Oracle：改 c2_2 尾端擾動（`patch_fetch` + `_patch_kline_tail_ohlcv`），值基偵測 shift(-lag) 把未來 OHLCV 滲入前綴。

**修2 `test_mutation_fracdiff_calibration_perturb_fails`**:
- 加行為不變 spy：`FeaturePreprocessor._calibration_series` wrapper 計數；`pytest.raises` 後斷言 `calibration_calls > 0`。

**自驗**: py_compile PASS; mutation_probe_static.py PASS（含 fracdiff 探針）

全鏈 5 mutation 真紅留 Claude 長 timeout。

ASSUMPTIONS_VERIFIED: L4 fast path 繞過 `_apply_lag`; 靜態 touches_system 需函式體內 monkeypatch。

TESTS_RUN: py_compile PASS; mutation_probe_static.py PASS (exit 0)

FAILURES_SEEN: none

SCOPE_CHANGES: none

NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
