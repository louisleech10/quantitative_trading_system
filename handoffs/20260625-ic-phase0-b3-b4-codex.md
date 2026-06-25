# 20260625 IC Phase 0 B3+B4 Codex Handoff

正在做: IC Phase 0 B3 feature_filter + B4 decay/API/frontend UX implementation.
已完成: Added FeatureFilterSchema and ICConfig.feature_filter; orchestrator applies explicit feature filters only, default no truncation, sorted max_features preview metadata.
已完成: Added grouped/feature_filter/decay golden baselines and structured float tests.
已完成: Decay fit warnings moved out of per-feature hot loop into one summary INFO line.
已完成: ICAnalysisService analyze/analyze_cross_sectional calls moved through asyncio.to_thread.
已完成: Frontend default max_features is undefined; hook handles WS failed message, poll failed error, retry<=3 then 2000ms poll fallback.
驗證通過: pytest tests/momentum/test_ic_phase0_golden.py tests/momentum/test_ic_feature_filter.py tests/momentum/test_ic_decay_log.py -q -> 9 passed.
驗證通過: pytest tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop -q -> 1 passed.
驗證通過: cd frontend && npm test -- src/hooks/useICAnalysis.test.ts -> 4 passed.
阻塞: Full requested pytest tests/momentum/ tests/api/ gate fails during collection because api.main imports instantiate BinanceProvider and ping api.binance.com; sandbox network is restricted.
阻塞證據: 14 collection errors are requests.exceptions.ConnectionError to HTTPSConnectionPool(host='api.binance.com', port=443).
本次決策: Did not change unrelated feature factory tests or provider/route startup behavior.
本次決策: Did not add preview_limit schema/alias.
踩坑提醒: .git is read-only in this sandbox, so TDD commits cannot be created here.
