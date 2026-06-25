STATUS: DONE

修正了 `momentum/Analysis/ic_filter_orchestrator.py` 的 B3 regression：`_stage5_statistical_validation` 不使用 `feature_filter_info`，已移除這個誤加的必填參數；`feature_filter_info` 仍保留在 `_stage7_report` metadata 路徑。

pytest 摘要：

```text
pytest tests/momentum/test_ic*.py tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop -q
108 passed, 3 skipped, 102 warnings in 3.07s
```

已新增 handoff：`handoffs/20260625-ic-phase0-b3-regression-fix-codex.md`。