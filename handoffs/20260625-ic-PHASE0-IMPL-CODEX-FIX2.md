STATUS: DONE

修了 Composer review 的 blocking/major items：

- `config/ic_config.yaml` 的 `by_volatility` 改為 `false`，並加 Phase 0 migration 註解。
- 檢查 `config/user_ic_config.yaml`：沒有 `by_volatility`，無需同步。
- `compute_ic_decay()` 現在每次都固定輸出一行 `Decay: x/total ...` summary，包括全成功 `0/total`。
- 補了預設 grouped config 測試、orchestrator `analyze()` feature_filter 整合測試、45k 欄位穩定性測試、timeaxis 邊界測試。
- 已寫 handoff：`handoffs/20260625-ic-phase0-composer-review-fix-codex.md`

Gate 結果：

```text
pytest tests/momentum/test_ic*.py tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop -q
115 passed, 3 skipped, 102 warnings in 3.46s
```