# IC1CFR-B1 Code Review R3 — Codex
task-id: IC1CFR-B1 | reviewer: Codex | date: 2026-07-15 | scope: R2 rework delta；唯讀，僅本檔產出

## 逐項複驗
1. **CLOSED — B-R2-1**：legacy cache FR=0.42 + `force_modules=["trend_analysis"]` 實跑為 §U unavailable、無有限葉、summary unavailable、completed=1；無 `CACHE_FORCE_MERGE_LEAK`。
2. **CLOSED — 第三/第四 cache 路徑**：另跑 force `factor_returns`、force `factor_returns+trend_analysis`、force-write 後再 no-force hit；輸出與 `_deep_analysis_cache` 均 unavailable/無有限葉。控制流掃描確認 public 正常出口僅 deep-off 早退（無 FR 節）與最終 sanitizer；唯一 cache writer caller 在 sanitize 後。
3. **CLOSED — B-R2-2**：`test_sanitizer_markdown_legacy` 驗真實 Markdown；monkeypatch `_build_module_summaries` 回 `{"factor_returns":{"size":1}}` 時 `test_mutation_m2d_markdown_restore_size_meta` 的真實產物 oracle 確實 raise，probe 綠。

## M1 裁決與 delta 掃描
- **ACCEPT** runner+exit-sanitizer 雙層繞過語意：統一出口使「只恢復 runner」成為 public-output 等價 mutation；另有 `test_runner_raises_module_unavailable` 直接釘死 runner 必須 raise，故單層 runner 回歸仍使完整 gate 紅，未形成 mutation 弱化。
- 雙層 probe 驗 end-to-end「有限 FR 直出」；component fail-close 由具名 runner test 驗。建議日後將 M1 docstring 明稱 combined-defense probe（NON-BLOCKING）。
- rework delta 未發現新 public FR 洩漏、cache 污染或 Markdown oracle 假綠；deep-off 早退保持 `not_run`+無 results 節。

ASSUMPTIONS_VERIFIED: SPEC/TODO reconcile 三方 APPROVED；`run_deep_analysis` return/cache-writer 控制流已掃；未動 analyzer/monotonicity/net_ic/long_short/data_cache。
TESTS_RUN: 精準 7 nodeids→7 passed；兩檔完整 gate `venv/bin/pytest ... -q`→46 passed；mutation gate→9 passed；三條額外 cache probe均無有限葉；受審三檔 `git diff --check`→exit 0。
FAILURES_SEEN: 首次精準命令誤加不存在 class nodeid→collection rc4，修正為 module-level nodeid 後 7 passed；首次 standalone probe import API test 觸發禁網，改用 momentum-only fixture；首次額外 probe import 錯 DeepAnalysisReport 模組，依 `rg` 更正後通過。
SCOPE_CHANGES: none；只新增本 review 檔。
NUMERIC_OR_SCHEMA_IMPACT: rework 將所有 public/cache FR finite legacy payload 收斂為 §U unavailable 並重算 counts；非 FR schema/數值未見新變更。
CODE-REVIEW-R3: APPROVE
