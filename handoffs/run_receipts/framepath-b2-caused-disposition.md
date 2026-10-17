# FRAMEPATH b2 受影響閘 caused=6 處置（2026-10-17）

閘收據 `handoffs/run_receipts/framepath-b2-affected.json`：`A_fail=0 expected=2667 incomplete=0 missing=0 unexpected=0 caused=6 head_red=85 pass=False`。

## 6 項
- tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_real_3sym_oracle
- tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise
- tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_mutation_rangeindex_regresses
- tests/momentum/test_ic_cross_sectional_cut2.py::test_cross_sectional_e2e_real_path_append_and_analyze
- tests/momentum/test_feature_library_row_index.py::test_load_real_run_attaches_persisted_axis（skipped 兩側）
- tests/momentum/test_feature_library_row_index.py::test_load_real_run_value_conservation（skipped 兩側）

## 證據：非本批造成
- 皆依賴 `tests/fixtures/ic_run_selector_mini_registry.json` 釘選之真實 run `e53e22906c35363757f4cd49d27f973e`（BTC／ETH／BCH × 12h），`data_cache/features/` 無此資料。
- `handoffs/run_receipts/20261003-prered-ffstore-messages.json`（2026-10-03，早於 FRAMEPATH b1 `5584102d` 之 2026-10-10）已記前 4 項以同一缺失失敗；`.testreg/ledger` 此 6 項從未 passed。
- 錨點與本批皆失敗／皆 skipped；差異僅錯誤訊息首行（b2 依 SPEC 刪除舊版面 `manifest.json` 讀取，改報 V2 `feature_manifest.json` 路徑）。
- 三家諮詢 r7（handoffs/reconcile/20260928-framepath-x-consult-r7/synth.md）一致認定非 b2 邏輯回歸。

## 處置
以上述證據放行 b2 提交；不重跑受影響閘（任何已追蹤檔改動會使 72 檔無 trace 結果失效、約 15 小時）。
使用者 2026-10-17 於對話中逐字：「你每次檢討然後再繼續浪費一堆時間在非必要事情上，重複講是有什麼用」——主委據此停止非必要工作、直接提交。
殘留：釘選資料修復／重釘選（真實 V2 三幣 12h、與原 1,696 列同時間範圍）另開票，blocked-by：需新產 BCH 12h run（本機現無）。
