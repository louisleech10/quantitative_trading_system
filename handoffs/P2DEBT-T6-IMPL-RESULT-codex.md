# P2DEBT-T6 implementation result — Codex
Task-id: t6-impl-codex | Date: 2026-07-12 | Status: BLOCKED

## 正在做 / 本次決策
- 三個 API fixture 的 label 寫入名已由 `label` 釘為 `return_5`。
- 三處均先設 `label_names`，再以 `assert label_names == ["return_5"]` 作 falsifiable floor。
- 未加 caplog best-effort；未改 `tests/api/test_ic_analysis_service.py`、`momentum/`、`api/`。

## Diff 摘要
- `tests/api/test_ic_deep_analysis.py`: +3/-1。
- `tests/api/test_ic_analysis_api.py`: +3/-1。
- `tests/api/test_export_api.py`: +3/-1。
- `git diff --stat -- momentum api`：空輸出；生產碼零變更。
- `git diff --check`：空輸出。

## 正反極性 receipt
- 正向命令：單一 `venv/bin/python -m pytest` 明列 reconcile 的 23 nodeid，先列 analysis 檔以沿用既有 `Client.ping` patch。
- 正向輸出：`collected 23 items`; `3 failed, 20 errors in 18.46s`，共同先行根因為 `cadence mismatch: expected 12h, got 0 days 00:00:01`，未達全綠。
- 首次三檔命令另於 collection 因 deep 檔先 import、Binance DNS 不可用而 `collected 18 items / 1 error`；調整 nodeid 順序後已排除該環境因素。
- 反向操作：暫將 `test_ic_analysis_api.py` 一處改成 `label_names = ["return_1"]`，測後已還原 `return_5`。
- 反向命令：`venv/bin/python -m pytest tests/api/test_ic_analysis_api.py::test_ic_task_status -q --tb=short`。
- 反向輸出：exit 1；`AssertionError: assert ['return_1'] == ['return_5']`；`1 error in 2.72s`。

## 待辦 / 阻塞 / 踩坑提醒
- BLOCKED：23 綠需擴大 scope 修正三 fixture 的 timestamp cadence（目前 `np.arange` 為 1 秒，meta 為 `12h`）；本票禁止越界故未改。
- 23 API 已驗證精確收集，但不可宣稱通過；亦不可宣稱 end-to-end horizon/purge 數值正確。
- 產出：`handoffs/P2DEBT-T6-IMPL-RESULT-codex.md`。
