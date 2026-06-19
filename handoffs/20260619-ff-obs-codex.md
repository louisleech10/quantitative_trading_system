# 20260619 FF Observability Codex Review

Scope: read-only architecture cross-exam; only this handoff written.
Sources: docs/FF_OBSERVABILITY_COMMITTEE_BRIEF.md; api/core/middleware.py; api/core/logging.py; api/services/feature_factory_batch_service.py; momentum/FeatureEngineering/feature_factory.py.

## T1 log 噪音
Position: 同意「消雙記 + quiet default」，反對直接刪掉較有價值欄位。
Evidence: middleware 同一請求先 Started/Completed，再呼叫 log_api_request 產生 api.request；後者只有 method/path/status/duration，缺 request_id/client。
Challenge: 留 middleware 不是免費；Started 對高頻 polling 幾乎無診斷價值，Completed 才有 status/duration。
Alternative: 保留單一 middleware completion log；移除/停用 Started；quiet 模式 suppress 已知 polling path 的 2xx fast request，保留 >=400、>=N ms、非 GET write、unknown path。
Do not: 只把 api.request 降 DEBUG；root logger DEBUG 仍會回來洗版，且雙記仍存在。
Max risk: path allowlist 過寬會藏掉「polling endpoint 本身退化但仍 200」。
Priority: P1，先做；低風險、高回報，且不碰數值/schema。

## T2 batch layer 進度 + per-layer observability
Position: 部分同意 Claude；反對一開始就用高頻 mp.Queue 當主方案。
Evidence: batch 已有 child_metrics.jsonl sidecar，但只在 worker 結束時寫 symbol 級 peak_rss_mb/duration/status；FeatureFactory 已有 progress_callback，但 _compute_single 未傳 callback，所以子進程 layer progress 不回父。
Challenge: ProcessPool + Queue heartbeat 是新生命週期問題：queue drain、worker crash、parent cancellation、backpressure 都會變成批次穩定性風險。
Alternative: 最小改法是 worker 內 progress_callback append JSONL event：symbol/timeframe/stage/progress/message/rss_mb/ts/elapsed；父進程用低頻 poll/tail 合併到 task status。
Granularity: layer start/end + L6.5/IC gate start/end + final artifact sizes；不要 per-row/per-column heartbeat。
Unify: single-symbol websocket 繼續用 progress_callback；batch 只是給 callback 換一個 sink(JSONL)，不要另造 layer taxonomy。
Max risk: 多 worker 同寫 JSONL 若非 O_APPEND 單 write 會破行；目前 _append_child_metrics_jsonl 已用 O_APPEND，可沿用但需事件 schema version。
Priority: P0，先於 T3；沒有可信 layer/RSS 資料，並行 gate 只是猜。

## T3 多 symbol 並行
Position: 反對現在恢復 tier-aware 並行；同意保守維持 concurrent_symbols=1 作為當前 default。
Evidence: _resolve_concurrent_symbols 無條件返回 1；現有 RAM gate 只看 available RAM，沒有 per-symbol 真峰值；child metrics 的 peak_rss_mb 是結束瞬間 RSS，不是真 peak。
Counterexample: IC gate 已有 _PeakRssTracker 只包 compute_ic_from_l7_raw，metadata 有 run_ic_gate_peak_rss_gb；但整個 symbol 的峰值可能出現在 L2/L3/L6.5/raw write，不等於 IC gate peak。
Alternative: T3 分兩階段：先產生真實 run profile；再做 opt-in 並行實驗，不改 default。
Gate formula later: require measured p95 per-symbol full-run peak RSS + parent overhead + raw/artifact transient + safety margin；可用 RAM 不足即降序列。
Do not: 用 437K feature count 或 tier_gb 推估峰值；feature count 對 row count、dtype、memmap、raw write transient 不足以保證 OOM safety。
Max risk: 並行失敗不是普通慢，是 OOM/SIGKILL/半成品 artifact/resume 複雜度；違反多 symbol 穩定優先於 runtime。
Priority: P2，延後；先做 F1/T2 觀測，量到 IC-First 真實峰值 RSS，再決定並行。

Overall order: T2/F1 instrumentation -> T1 quiet access logs -> T3 opt-in experiment.
Decision: 特別回答 T3，是，必須先把 F1/T2 觀測性做好、量到 IC-First 真實 full-run peak RSS，再決定是否恢復多 symbol 並行。
Blocked: none.
