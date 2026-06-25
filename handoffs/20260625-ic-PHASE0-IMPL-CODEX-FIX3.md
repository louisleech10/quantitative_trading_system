STATUS: DONE

修了 `to_thread` 引入的 WS regression：

- `ICAnalysisService._run_analysis()` 捕捉主 event loop，worker thread 內的 progress notification 改用 `loop.call_soon_threadsafe(...)` 回主 loop。
- `api/websocket/ic_analysis_ws.py` 的 `notification_callback` 改用 `asyncio.run_coroutine_threadsafe(send_payload(...), loop)`，不再直接 `create_task()`。
- 新增測試覆蓋 analyzer 在 `to_thread` 內同步呼叫 progress callback，斷言不出現 `no running event loop` 且 coroutine 可排程。
- 順手讓前端 poll fallback 接管時清掉 stale「WebSocket 連線失敗」。

Gate 結果：

```text
pytest tests/momentum/test_ic*.py tests/api/test_ic_analysis_service.py -q
118 passed, 3 skipped, 102 warnings in 4.99s
```

額外驗證：

```text
pytest tests/api/test_ic_analysis_service.py -q
4 passed

cd frontend && npm test -- src/hooks/useICAnalysis.test.ts
4 passed
```