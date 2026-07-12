# P2DEBT T6 adversarial（Codex）
task-id: t6-adv-codex | 日期: 2026-07-12 | verdict: **BLOCK**

## 裁決
- A1–A3 rename 方向正確，且有效設定為 5：`config/ic_config.yaml` 的 `global.default_horizon: 5`、`labels.horizons` 含 5；三檔 request/config_override 均未覆寫兩者。
- 但 SPEC/TODO 的 PASS gate 只能證明合法欄名讓流程變綠，不能證明 N=5；在補上 horizon/purge oracle 前不可核可。

## 可證偽反例（blocking）
- 將 A1 或 A3 寫成 `return_1`：resolver 會回 1，`analyze()` 會把 `effective_horizon`/`purge_gap` 設為 1，而非預期 5（orchestrator L866-906）。
- fixture label 是獨立 `rng.normal`，現有斷言僅查 HTTP 200、task completed、`summary_table`/export content；沒有 assertion 查 `metadata.ic_train_test_split.effective_horizon == 5` 或 `purge_gap == 5`。
- 因此 `return_1` 可在不觸發經濟 oracle 的情況下綠；這正是草案自述的靜默 alignment/purge 風險。反例可用同一測試的 `return_1` mutation 證偽：若仍綠，現 gate 無辨識力。
- 必補：至少一個走真 orchestrator 且 split 開啟的測試，斷言 result metadata 的 effective_horizon 與 purge_gap 均為 5；最好對 A1–A3 共用 fixture 直接查 label_names=`return_5`。

## B1 與契約
- `test_run_analysis_does_not_block_event_loop` 的 `_SleepingAnalyzer.analyze_cross_sectional(**_kwargs)` 忽略 features/label，B1 不走 orchestrator resolver；rename 對該測試行為零影響，應排除 Task 2.4。
- service 無 labels_path 時才 append `return_1`；B1 自帶 labels_path，但 stub 仍不讀檔。append 三個 oracle 現碼已驗 `return_1`，與 B1 無關。
- 生產 `analyze_cross_sectional` 明確保留 in-frame 候選優先序 `label > return_N > ...`；裸 `label` 會以 structural horizon=1 運作。故不能宣稱「生產一概不接受 label」；縱向 HDF5 fail-closed 與橫截面 in-frame 是兩份契約。

## 驗證與限制
- TESTS_RUN: `venv/bin/pytest` 單命令選 7 nodeid；collection 因 Binance ping 網路失敗，0 tests executed，未驗 pytest 狀態。
- DELEGATED: 首個單一 Python 大量讀碼工作 >60s 無輸出後終止；核心查核改以兩個縮小的單一 Python 命令完成。
- ASSUMPTIONS_VERIFIED: default=5；A1–A3 無 horizon override；N 進入 alignment lag/purge；B1 stub 不進 orchestrator。
- FAILURES_SEEN: pytest collection external-network failure；SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: none。
- 產出: `handoffs/P2DEBT-T6-ADV-codex.md`；僅新增本報告，未改程式/測試/HANDOFF.md。

STATUS: DONE
