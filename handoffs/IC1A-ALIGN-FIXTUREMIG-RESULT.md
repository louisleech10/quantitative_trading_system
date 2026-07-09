# IC1A ALIGN Fixture Migration Result
task-id: ic1a-align-fixture-mig
date: 2026-07-09
status: DONE

正在做: 已完成 5 個 IC fixture migration。
待辦: 無；後續只剩既有 FF 紅測另案處理。
阻塞: 無。
本次決策: 將 labels 欄名由 `label` 改為 resolver 可解析的 `return_1`。
本次決策: 將 synthetic timestamp 改為 12h epoch-second cadence，與 HDF5 group `BTCUSDT/12h` 一致。
本次決策: `return_1` label 尾端設 1 個 NaN，符合 horizon=1 structural tail gate。
修改檔案: tests/momentum/test_ic_e2e.py; tests/momentum/test_ic_feature_filter.py。
未改: production code; assertions; thresholds; data_cache tracked files。
驗證1: `pytest tests/momentum/test_ic_e2e.py tests/momentum/test_ic_feature_filter.py -q` -> 11 passed, 1 skipped。
驗證2: `pytest tests/momentum/ -q` -> 2 failed, 986 passed, 3 skipped。
剩餘紅: tests/momentum/test_feature_factory_optimization_e2e.py::test_pipeline_with_preprocessing。
剩餘紅: tests/momentum/test_feature_factory_optimization_perf.py::test_full_pipeline_overhead。
踩坑提醒: 第一輪只改欄名後，5 測試改紅於 cadence mismatch: expected 12h, got 1s。
踩坑提醒: 既有 analyzer 測試路徑仍 log 寫入 data_cache/features 與 data_cache/reports；git status 無 tracked data_cache diff。
NUMERIC_OR_SCHEMA_IMPACT: test fixture HDF5 label column schema changed from `label` to `return_1`; no production schema change。
