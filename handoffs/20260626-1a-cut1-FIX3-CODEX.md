# 1a cut1 FIX3 Codex handoff

## 正在做
- FIX3 default-ON 分因回退：`insufficient_data` / `rolling_warmup_insufficient` 回退 full-sample + `applied:false` metadata。
- `TimestampDiscontinuityError` 維持 fail-closed；新增 orchestrator 頻率檢查，`np.arange` 假 timestamp 不回退。

## 已改
- `momentum/Analysis/ic_filter_orchestrator.py`：split build skipped 與 stage4 warmup skipped 皆以 flag-off 重跑 full-sample，報告 metadata 標 `requested:true/applied:false/scope:full_sample_legacy/oos_guarantees:false/reason/details`，移除 fallback 報告頂層 `scope:test`。
- success OOS metadata 改為 `requested:true/applied:true/scope:train_test_holdout/oos_guarantees:true`。
- `tests/momentum/Analysis/test_ic_1a_cut1_oos.py`：補 3 個 FIX3 測試（insufficient fallback、irregular fail-closed、足量 applied true）。
- `tests/api/test_ic_analysis_api.py`：合成 plumbing request 設 `ic_train_test_split:false`；test-local stub `Client.ping` 避免 collection 觸網。

## 驗證
- PASS：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` → 13 passed。
- PASS：`pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` → 33 passed（含 leakage tests + G-OLD）。
- PASS：`grep -rE "from api\\." momentum/ || true` → no output。
- FAIL：`pytest tests/api/test_ic_analysis_api.py -q -k "not deep and not export"` → no network error after stub, but fixture times out waiting task status.

## 阻塞
- API timeout root cause is outside specified FIX3 files: status endpoint keeps returning `{"status":"running","progress":1.0,"current_stage":"report","error":null}` after analysis writes report; result endpoint returns 404.
- Two API rounds used: (1) collection failed on Binance ping under restricted network; (2) ping stub + opt-out runs analysis but task store never reaches completed/result.

## 待辦
- 需 Claude 核准擴大 scope 到 `api/services/ic_analysis_service.py` / task result bookkeeping，或接受調整 API test wait semantics。

## 踩坑提醒
- Rolling-warmup fallback 必須重跑 flag-off；不能在已 train-fit preprocessing 後把 `split_context=None` 繼續跑，否則不等同 legacy。
