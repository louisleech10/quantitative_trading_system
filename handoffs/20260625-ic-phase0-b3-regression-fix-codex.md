# 20260625 IC Phase 0 B3 Regression Fix Codex Handoff

正在做: 修正 B3 feature_filter_info 誤加到 _stage5_statistical_validation 簽名造成既有測試崩潰。
已完成: 移除 _stage5_statistical_validation 未使用的 feature_filter_info 必填參數。
已完成: 保留 feature_filter_info 在 _stage7_report/report metadata 的使用。
驗證通過: pytest tests/momentum/test_ic*.py tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop -q -> 108 passed, 3 skipped.
本次決策: stage5 不消費 feature_filter_info，維持原 public/internal helper 呼叫相容性。
阻塞: none.
踩坑提醒: feature_filter metadata 應只在 report stage 注入，不應穿透 stage5 validation。
