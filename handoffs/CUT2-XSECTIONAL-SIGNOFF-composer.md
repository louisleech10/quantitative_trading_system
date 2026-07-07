# CUT2 cross_sectional 資料正確性簽核 — Composer 獨立驗證腿

> 日期 2026-07-07 | Composer 實作端獨立複核（git diff + 自跑 pytest，非盲信 IMPL 報告）

## 獨立檢查方法
1. `git diff` 審 `api/services/ic_analysis_service.py`、`momentum/Analysis/ic_filter_orchestrator.py`、`momentum/Analysis/ic_config_schema.py`、測試檔。
2. 自跑驗收：`pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py` → **18 passed**；`test_analyze_cross_sectional_includes_symbol_matrix_and_validation` → **1 passed**。
3. 解耦：`grep -r "from api\." momentum/` → **0**。

## F1 per-symbol datetime 對齊、forward 無 look-ahead
- **diff 證據**：`_append_cross_sectional_labels` 將 kline `timestamp`(int64 秒) 轉 `DatetimeIndex` 設為 `close.index`，再 `reindex(symbol_index)`；僅寫 `return_1`，不動其他欄。
- **forward 語意未改**：仍呼叫 `generate_returns_by_type(close, 1, "log")` → `close.shift(-1)`（`label_generator.py`），label 在 t、特徵在 t，無 look-ahead。
- **fail-closed 時間戳**：非整數/負值/非單調 duplicate → `ValueError`。
- **實測**：`test_append_cross_sectional_labels_real_3sym_oracle` 真 3sym×12h e53e2290，非 NaN ≥5085/5088，逐幣 byte 級對 kline oracle，末列 NaN，同 ts 三幣 label 互異（無跨界污染）。
- **mutation**：`test_append_cross_sectional_labels_mutation_rangeindex_regresses` 還原 RangeIndex → 0/5088（red-on-break）。

## F2 labels_path 單軸 fail-closed
- **diff 證據**：移除 `label_series.reindex(features.index.droplevel(symbol))` 廣播分支；`_labels_df_has_symbol_dimension` 為 false → `InvalidInputError("單軸不支援")`。
- **grep**：`ic_filter_orchestrator.py` 無 `droplevel(symbol` 殘留。
- **實測**：`test_cross_sectional_labels_path_single_axis_raises` PASS；`labels_path` 缺席走 column 路徑 PASS。

## F3 全域時間邊界 test-only、purge/embargo 真強制
- **diff 證據**：`_build_cross_sectional_global_split` 用 union unique timestamp 切 `T_train_end` / `test_start = T_train_end + purge_td + embargo_td`；`purge_td = effective_horizon(1) × expected_freq`；`analysis_df = numeric_df.iloc[test_mask]`。
- **全部 report 輸出源自 analysis_df**：`grouped`/`ic_series`/`summary_table`/`rolling_ic_series`/`symbol_ic_matrix`/`cross_symbol_validation`/`metadata.n_timestamps`/`filter_log.n_timestamps` 皆由 test frame 衍生（diff L819–943）。
- **gap 雙重強制**：(1) `actual_gap < purge_td+embargo_td` → `InvalidInputError`；(2) `split_per_symbol` + `validate_split_pair_integrity`。
- **split 失敗 fail-closed**：`ic_train_test_split` 例外包裝 raise，無 silent full-sample fallback。
- **實測**：gap 不等式 PASS；train 污染 hash 不變（R1）PASS；`effective_horizon=0` mutation → `SplitPairLeakageError`（真 red-on-break，非套套）。

## F4 per-symbol 守衛 fail-closed
- **diff 證據**：`_enforce_cross_sectional_label_coverage` per-symbol；all-NaN / `len_s≤horizon` / `coverage < floor×(1-tol)` → `InvalidInputError`；floor=`(len−horizon)/len`。
- **實測**：全 NaN、1/3 幣全 NaN、短序列 PASS raise；正常 metadata 有 `per_symbol_coverage`；monkeypatch 關守衛後壞資料靜默通過（證守衛非假綠）。

## 特徵值/欄/列未變、無跨界洩漏
- F1 僅新增/填充 `return_1`；F3 僅 `iloc` 選 test 列，不改 `.values`。
- 既有 `test_ic_filter_orchestrator.py` 僅加 `ic_train_test_split=False`（保 synthetic full-sample），matrix/validation 斷言未刪未弱。
- E2E 真路徑 `test_cross_sectional_e2e_real_path_append_and_analyze`：row_index→append→analyze OOS PASS。

## 殘留（非 blocking）
- §G.2 特徵 byte-equal golden 無獨立測試，但實作僅選列 + train 污染 hash 隔離已證偽洩漏路徑。
- `_append_cross_sectional_labels` 內 matched-timestamp `assert_allclose` 為生產路徑防呆（輕量開銷，非正確性缺陷）。

SIGNOFF: composer DATA-CORRECT PASS — git diff 獨立確認 F1–F4 與 SPEC 一致，自跑 18+1 pytest 全綠，真 3sym oracle/OOS 隔離/mutation 均可證偽，特徵矩陣僅 label 對齊與 test 選列。

STATUS: DONE
