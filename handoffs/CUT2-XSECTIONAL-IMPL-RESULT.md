# CUT2-XSECTIONAL 實作收尾（Composer）

**task-id**: CUT2-XSECTIONAL-IMPL  
**日期**: 2026-07-07

## 改動摘要

### Batch1 — F1 + F4
- `api/services/ic_analysis_service.py::_append_cross_sectional_labels`：kline `timestamp` int64 秒 fail-closed 驗證 → `DatetimeIndex` 對齊 → `reindex` 到 feature 時間軸；subset 斷言。
- `momentum/Analysis/ic_filter_orchestrator.py`：`_enforce_cross_sectional_label_coverage` per-symbol 推導下界 `(len−horizon)/len`；`ICConfig.min_label_coverage_tol`。
- `_run_analysis` 傳 `timeframe` 至 `analyze_cross_sectional`。

### Batch2 — F2
- `analyze_cross_sectional`：單軸 `labels_path` → `InvalidInputError` fail-closed；移除 droplevel 廣播。

### Batch3 — F3
- `_build_cross_sectional_global_split`：全域 unique timestamp 切分；`purge_td=horizon×freq`（horizon=1）；test-only 覆蓋全部 report 輸出。
- 審計：`split_per_symbol` + `validate_split_pair_integrity`（`purge_semantic=timedelta`）+ `ICSplitAdapter._base_universe_hash`；時間 gap 不等式斷言。

## 修改檔案
- `api/services/ic_analysis_service.py`
- `momentum/Analysis/ic_filter_orchestrator.py`
- `momentum/Analysis/ic_config_schema.py`
- `tests/api/test_ic_analysis_service.py`（F1 Golden + F4 單元）
- `tests/momentum/test_ic_cross_sectional_cut2.py`（F2/F3/e2e/mutation）
- `tests/momentum/test_ic_filter_orchestrator.py`（既有測試加 `ic_train_test_split=False`）

## ASSUMPTIONS_VERIFIED
- RECONCILE-STAMP codex+composer APPROVED（`handoffs/CUT2-XSECTIONAL-SPECADV-RECONCILE.md`）
- 真 3sym×12h e53e2290：`return_1` 非 NaN ≥5085/5088；逐幣 oracle 相等（實跑）
- `purge_semantic=timedelta` + SplitPlan `purge_gap=0`：契約驗證用列序；時間隔離由 `test_min−train_max≥purge_td+embargo_td` 斷言（`validate_split_pair_integrity` 列序 purge 與日曆切分不相容，已實測 SplitPairLeakageError 後調整）

## TESTS_RUN
- `grep -r "from api\." momentum/ | wc -l` → **0**
- `pytest tests/api/test_ic_analysis_service.py -k "append_cross_sectional_labels or cross_sectional_coverage_guard" -q` → **5 passed**
- `pytest tests/momentum/ -k "cross_sectional_labels_path or cross_sectional_oos_split" -q` → **4 passed**
- 額外：`pytest tests/momentum/test_ic_cross_sectional_cut2.py -q` → **7 passed**（含 e2e 真路徑、R1 污染 hash、F4 mutation）

## FAILURES_SEEN
- Round1：oracle 比對 index 不對齊 → 改 `droplevel` 對齊
- Round1：`ts_series.to_numpy` AttributeError → 改 `pd.Series`
- Round1：`SplitPairLeakageError`（列序 purge_gap=1 與日曆切分衝突）→ SplitPlan `purge_gap=0` + 時間不等式

## SCOPE_CHANGES
- none

## NUMERIC_OR_SCHEMA_IMPACT
- `ICConfig` 新增 `min_label_coverage_tol`（預設 0.01）
- `analyze_cross_sectional` 新增 `timeframe` 參數；metadata 新增 `per_symbol_coverage`/`ic_train_test_split`（cross_sectional）
- 僅 label 對齊與 split 選列；特徵值/欄/列數不變

STATUS: DONE

---

## Fix-round（Composer，2026-07-07）

**依據**: `handoffs/CUT2-XSECTIONAL-FIXROUND-PROMPT.md`（Codex code review 4 findings）

### 修復
- **FIX-1 F4**: `_enforce_cross_sectional_label_coverage` 開頭加 `all-NaN` 與 `len_s≤horizon` fail-closed；測試 `test_cross_sectional_coverage_guard_short_series_all_nan`
- **FIX-2 F3 mutation**: 刪套套不等式；改 `effective_horizon=0` → `SplitPairLeakageError`（真縮 purge 洩漏現形）
- **FIX-3 F1 Option B**: `_append_cross_sectional_labels` 缺孔→NaN（不 raise）；有 kline 列斷言對齊無錯位；測試 `test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise`
- **FIX-4**: `np.issubdtype(ts_raw.dtype, np.integer)` 整數 epoch 秒契約

### ASSUMPTIONS_VERIFIED
- `len_s==horizon` 全 NaN 現 raise（非靜默 `per_symbol_coverage=0`）
- kline 挖孔：該列 NaN、其餘 holed-oracle 對齊、F4 續行
- `effective_horizon=0` 觸發 `SplitPairLeakageError`（生產 split 路徑）

### TESTS_RUN
- `grep -r "from api\." momentum/ | wc -l` → **0**
- `pytest tests/api/test_ic_analysis_service.py tests/momentum/test_ic_cross_sectional_cut2.py -q` → **18 passed**

### FAILURES_SEEN
- Round1：kline hole oracle 用全量 kline → 改 holed oracle；`all_nan` match 字串；`horizon=0` 觸發 `SplitPairLeakageError` 非 gap 縮小 → 改斷言 leakage raise

### SCOPE_CHANGES
- none

### NUMERIC_OR_SCHEMA_IMPACT
- none（語義：缺孔容許 NaN；F4 邊界更嚴）

STATUS: DONE
