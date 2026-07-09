# IC1A-ALIGN-FIX-B2-RESULT
task-id: ic1a-align-fix-b2
date: 2026-07-09

正在做: B2 MIXED 裁定修復完成；stage2 label 生成移除 float64 強轉，保留 raw close dtype，只改 timestamp index 語義。
待辦: 交 Claude 接回 diff/code review；baseline JSON 位於 tests/golden/ic_phase1_1a_cut1/，目前 git 未追蹤該兩檔。
阻塞: none。
本次決策: stage0 validation-only close 仍可用 float64；stage2 production label 改為 raw_data["close"].to_numpy(copy=False)。
本次決策: _slice_raw_data_by_mask 同屬 B2 2.3，改用 timestamp 欄正規化 raw kline，避免 G-NEW RangeIndex fail。
踩坑提醒: turnover_analysis 數值 payload 與 baseline 相等，但 timestamp serialization 因 D-4 DatetimeIndex 由 epoch 秒變 ISO。
踩坑提醒: quantile_returns 也因 label index 對齊復活；不屬 float64 drift，與 rolling/summary 同源。

diff收斂證明: in-memory no-persist replay，grouped_ic exact_equal=True；turnover numeric_payload_equal=True（timestamps excluded）；top-level residual含 filter_log/rolling_ic_series/summary_table/quantile_returns。
重凍前後 removed counts: old 原始 50/0 -> 43/7；new 原始 50/0 -> 43/7（ic_mean/icir）。
重凍檔案: tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h_a384e6d2.json sha256=963ba4f210f192c3d8c96870f06022b93b254fc04ae949a6dc2e69a555c0e820 bytes=99095197。
重凍檔案: tests/golden/ic_phase1_1a_cut1/baseline_new_btc_1h_a384e6d2.json sha256=946591ad73a402dc1b5a0c3fff1c1474fa55e4f252f1ee25bc0a6315b1fabbe8 bytes=22886988。
命令輸出: pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q => 2 passed, 3 warnings in 37.92s。
命令輸出: pytest tests/momentum/core/ tests/momentum/Analysis/ -q => 390 passed, 273 warnings in 79.37s。
命令輸出: pytest tests/momentum/ -k 'alignment_gate or slice_alignment or event_filter' -q => 25 passed, 959 deselected in 1.82s。
data_cache: 測試既有設計寫入 data_cache/reports/ic_report_ic_gatekeeper.json；未發現 git tracked data_cache 變更。
