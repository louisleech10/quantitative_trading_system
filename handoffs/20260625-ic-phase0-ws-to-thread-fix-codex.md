# 20260625 IC Phase 0 WS to_thread Fix Codex Handoff

正在做: 修正 IC analysis to_thread 後 WebSocket progress callback 在 worker thread 呼叫 asyncio.create_task 的 regression。
已完成: ICAnalysisService._run_analysis captures main loop and uses loop.call_soon_threadsafe for progress notifications emitted from analyzer worker thread.
已完成: api/websocket/ic_analysis_ws.py notification_callback captures endpoint loop and uses asyncio.run_coroutine_threadsafe(send_payload(...), loop).
已完成: Frontend poll fallback clears stale WebSocket connection error when polling takes over.
已完成: Added test_progress_callback_from_to_thread_schedules_on_event_loop to reproduce worker-thread progress callback scheduling.
驗證通過: pytest tests/api/test_ic_analysis_service.py -q -> 4 passed.
驗證通過: pytest tests/momentum/test_ic*.py tests/api/test_ic_analysis_service.py -q -> 118 passed, 3 skipped.
驗證通過: cd frontend && npm test -- src/hooks/useICAnalysis.test.ts -> 4 passed.
阻塞: none.
踩坑提醒: Any callback registered from websocket layer must not assume it is invoked on the event loop thread unless service explicitly schedules it there.
