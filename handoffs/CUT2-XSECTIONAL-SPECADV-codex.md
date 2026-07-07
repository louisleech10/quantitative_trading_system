# CUT2-XSECTIONAL SPEC/TODO adversarial review — Codex

日期: 2026-07-07
角色: Codex(GPT 家族) adversarial reviewer
輸入已讀: HANDOFF.md, CLAUDE.md, handoffs/CUT2-XSECTIONAL-SPECADV-PROMPT.md, docs/IC_PHASE1_1a_CUT2_XSECTIONAL_SPEC.md, docs/IC_PHASE1_1a_CUT2_XSECTIONAL_TODO.md, handoffs/CUT2-XSECTIONAL-RECON.md, 指定程式碼。

## Findings

1. BLOCKING — `momentum/Analysis/ic_filter_orchestrator.py:analyze_cross_sectional` / SPEC Task 4.1
   - 反例: 現行 report 不只 `summary_table`，還輸出 `_build_cross_sectional_symbol_matrix()` 和 `_build_cross_symbol_validation()`；SPEC/TODO 只明確要求「grouped IC 只在 test 列」與「IC slice 數 == test timestamp 數」，沒有要求 symbol matrix / cross_symbol_validation / rolling_ic_series 全部只看 test 子集。實作者可能只在 grouped loop 前套 test mask，卻讓 symbol matrix 仍用 full-sample `numeric_df`，報告仍混入 in-sample label/feature 關係。
   - 修法建議: Task 4.1 明確定義 `analysis_df = numeric_df.loc[test_mask]`，summary、rolling_ic_series、symbol_matrix、cross_symbol_validation、metadata n_timestamps 全部以同一 test-only frame 生成；新增 red-on-break 測試：污染 train-only label/feature 後，所有 cross_sectional 輸出 hash 不變。

2. BLOCKING — `momentum/Analysis/ic_filter_orchestrator.py:_load_labels_hdf5` / SPEC Task 3.1
   - 反例: F2 要支援「labels_df 帶 symbol 維度→per-(ts,symbol) merge」，但現有 `_load_labels_hdf5()` 只讀 `labels`、`label_names`、`timestamps`，回傳單軸 DataFrame；沒有讀 symbol dataset、沒有建立 MultiIndex、也沒有定義 HDF5 schema。只改 `analyze_cross_sectional:554-562` 無法讓「帶 symbol 維度 labels_path」測試通過，除非測試繞過 loader，會是假綠。
   - 修法建議: SPEC/TODO 加入 labels HDF5 schema 與 loader 修改 scope：例如 `timestamps` + `symbols` 等長資料集，載入後建立 `MultiIndex(timestamp, _symbol)`；單軸 timestamp 在 cross_sectional 明確 raise。驗證必須經由實際 HDF5 `labels_path`，不可直接傳 DataFrame。

3. BLOCKING — SPEC §N / TODO Task 2.1 `min_label_coverage`
   - 反例: SPEC 說 floor 暫定 0.5 且「最終值待委員會裁定」，TODO 又把 Batch1 派工為可直接實作。這違反本專案「沒有來源不得寫死效能門檻/atol/rtol/API 欄位/量化假設」規則；實作者不是委員會，會被迫拍腦袋或留下不確定 gate。
   - 修法建議: 動工前在 reconcile 中明確 APPROVED `min_label_coverage` 預設值與 rationale，或把 gate 改成不需任意 floor 的兩層規則：全 NaN 必 raise；per-symbol 覆蓋率低於 oracle 可推導下界 `(n_rows - horizon) / n_rows` 或 config 明示值才 raise。

4. MAJOR — `api/services/ic_analysis_service.py:_append_cross_sectional_labels` / SPEC Task 1.1
   - 結論: F1 主修方向成立，但 timezone/單位/重複 timestamp 防線仍不足。SPEC 使用 `pd.to_datetime(raw["timestamp"], unit=...)` 未指定 `utc=True`，而既有 golden 腳本多處使用 `utc=True` 後再處理；若 feature row_index 是 UTC-aware 或被轉成 UTC-naive，而 kline 是 naive，`reindex` 仍可能全 NaN。timestamp 單位用 `max > 1e12` 是 heuristic，沒有負值/混合單位/非單調/重複 timestamp fail-closed。
   - 修法建議: 明確 normalize contract：kline 與 feature timestamp 都轉為 UTC 語義後去 tz 或都保留 UTC-aware，並在 append 前 assert no duplicate, monotonic increasing, unit consistent。新增測試：tz-aware feature index、ms timestamp、duplicated timestamp 必轉紅或 raise。

5. MAJOR — `momentum/core/contracts.py:split_per_symbol` / SPEC Task 4.1
   - 結論: `split_per_symbol` 的 row position 契約本身可防跨 symbol row 泄漏；但 cross-sectional IC 的 per-timestamp universe 會因 per-symbol 不齊與 per-symbol split 邊界不同而變成「同一 timestamp 只有部分 symbols 在 test」。這不是 train/test 泄漏，但會讓 rank corr 的可比較 universe 漂移，且可能讓 n_slices 包含 2-of-3 而非完整 3-of-3。
   - 修法建議: SPEC 要裁定語義：允許 partial test universe 時 metadata 記錄 per-slice symbol_count 並測 `min_symbols_per_slice >= 2`；若要求同一 cross-section universe，則 grouped IC 只保留所有 selected symbols 同時在 test 的 timestamp。現在 TODO 只說 len<2 跳過，對研究輸出品質不夠可證偽。

6. MAJOR — SPEC §V / TODO Batch3 mutation
   - 反例: 「mutation 移除 purge_gap（設 0）→ validate_split_pair_integrity raise」不一定成立。`validate_split_pair_integrity()` 只按傳入的 `purge_gap` 建 forbidden interval；若 mutation 把 purge 設 0，train 在 test 開始前、test 在 split 後，本身不重疊，就不會 raise。這條 mutation 容易變成廉價綠燈。
   - 修法建議: red-on-break 應直接斷言 `test_start_local >= split_point + effective_horizon + embargo` 或污染 purge gap rows 後 test-only IC 不變；不要期待 contract 在 purge_gap=0 時替你知道 horizon。

7. MINOR — consumer map 完整性
   - 結論: 依 repo grep，SPEC §C 已涵蓋本刀主要 cross_sectional consumer：`_append_cross_sectional_labels`、`analyze_cross_sectional`、`_run_analysis`、symbol matrix/validation。未發現另一個明顯對 `load_multi` 結果做 cross_sectional label reindex/merge 的漏列 consumer。
   - 補強建議: 把既有 `tests/momentum/test_ic_filter_orchestrator.py` 中 labels_path 單軸測試納入更新清單，避免 F2 fail-closed 後舊測試被臨時放寬。

8. MINOR — Phase 依賴
   - 結論: P4 ← P1,P2 合理；P3 與 P1 正交也合理。唯一風險是 P4 實作若同時碰 labels_path 與 embedded label 欄，會暗中依賴 P3 的對齊 helper；TODO 可要求共用一個 `(timestamp,symbol)` label resolver，降低分支漂移。

## 特別挑戰逐項結論

- F1: 主因與修法方向可接受；仍需補 UTC 語義、單位判斷 fail-closed、重複/亂序 timestamp 測試。
- F3 OOS: `split_per_symbol` 可防跨 symbol row 泄漏；但 test-only 必覆蓋全部 cross_sectional outputs，且 partial timestamp universe 需明確裁定。
- F4: floor=0.5 目前未核可，阻塞實作；高 NaN 暖機場景應以 per-symbol oracle 下界或明示 config 處理，不能拍腦袋。
- consumer map: 本次主要 consumer map 未見新漏項；既有 labels_path 測試更新需列入。
- red-on-break: F2 loader schema 與 F3 purge mutation 現在有假綠風險。
- Phase 依賴: 大致正確，P4 輸出路由與 P3 helper 共用需要寫死。

ASSUMPTIONS_VERIFIED: 讀碼確認 analyze_cross_sectional 會產 summary_table/rolling_ic_series/cross_sectional_symbol_ic/cross_symbol_validation；_load_labels_hdf5 只載入 labels/label_names/timestamps；split_per_symbol 回全 frame row position 且 validate 依傳入 purge_gap 驗證。
TESTS_RUN: read-only review；未跑 pytest。執行過 `sed`/`rg` 讀取指定文件與程式碼。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增本 review 檔。
NUMERIC_OR_SCHEMA_IMPACT: none；但 findings 要求 SPEC 在 labels_path HDF5 schema、min_label_coverage、test-only output 範圍上補明確決策。
STATUS: DONE
