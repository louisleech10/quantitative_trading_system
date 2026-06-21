# FF consistency r1 — Codex independent proposal

Scope: read-only architecture plan. Did not read `handoffs/20260619-ffconsist-r1-*`.
Evidence read: brief + specified backend/frontend files.

## #1 log 一致
做法/裁決: P0. 維持 batch subprocess,但在 worker 啟動時明確初始化 logging queue/file handler 或子進程 file handler,讓 `momentum.*`/`api.*` 進同一 log sink;保留 `batch_id/symbol/timeframe/pid` context。
風險: 多進程同寫檔可能 interleave/rotation 競態;queue listener 需處理父進程退出與 worker crash。
優點: 解決目前 batch 子進程計算細節不進檔;不改數值路徑。
缺點: 需測 log volume/rotation;實作在 infra 層,容易漏 spawn/fork 差異。
優先序: P0,先做;可單獨驗收。

## Q3 進度一致
做法/裁決: P0. 定義共用 `FeatureProgressEvent` schema: `stage,progress,message,rss_mb,symbol,timeframe,batch_id,ts,schema_version`;單路徑 callback 直接送 WS+task state,批次仍經 jsonl bridge 後映射同 schema。
風險: batch 併發>1 時不存在唯一 current stage;目前 `_apply_layer_metrics_to_task` 只在 `concurrent_symbols==1` 顯示是合理防誤導。
優點: 前端可用同一 rendering component;單 symbol 補 RSS;batch 保留 subprocess 隔離。
缺點: 多併發需顯示 per-symbol map 或「多標的併行,展開看明細」,不能硬塞單一 current_stage。
優先序: P0,但分兩步: schema 統一先於多併發 UI。

## Q5 terminal
做法/裁決: P1. 將 `api/main.py` 的 uvicorn `access_log` 改為設定控制,dev 預設可關或過濾健康檢查/WS noise;應讓 access log 進正式 logger 或明確關閉 stdout spam。
風險: 關掉 access log 會少一層 HTTP 可觀測性;若直接全關,debug 404/500 變慢。
優點: terminal 與檔案 log 行為一致,減少 T1 後仍吵的 uvicorn stdout。
缺點: 不是 FF 專屬;可能影響全 API 開發習慣。
優先序: P1,在 #1 後做;需 env/config 開關。

## Q2 批次加保留/丟棄對話
做法/裁決: P0/P1. 使用者已定要做。建議新增 batch completion prompt:完成後以 `batch_id + successful run identities` 入 queue;提供「命名並保留整批」「保留未命名」「刪除整批成功輸出」「關閉」。命名走既有 batch alias API;刪除逐 run 調既有 delete API或新增後端批量刪除 endpoint。
風險: batch 已自動持久化且 checkpoint/resume 依賴 completed_items;刪除輸出後 checkpoint/quality summary/RunManager 需一致失效或標記 discarded。
優點: 與單 symbol 使用者心智一致;避免批次無感留下大量 run。
缺點: 批量刪除部分失敗需可恢復;大批次逐項刪除慢,最好後端交易式彙總回報。
優先序: P0 for prompt+alias, P1 for robust batch discard endpoint。

## E 執行模型 thread-vs-subprocess
做法/裁決: 建議維持現狀,只整併觀察契約與 adapter,不要把單/批次強行改成同一 executor。
為何分歧合理: 單 symbol `run_in_executor` 同進程可直接使用 task state/callback/retention lease,互動延遲低;批次 subprocess 是為多 symbol RAM 隔離、OOM containment、per-wave concurrency、child RSS metrics,且已有 checkpoint/resume。
整併方向若未來要做: 抽 `GenerationRunner` 介面與 `ProgressSink/LogSink/RetentionSink`;實作 `ThreadRunner` 與 `ProcessRunner`,共享 payload schema,不是共享同一執行模型。
整併風險: 單改 subprocess 會破壞 callback/lease/warmup/lifecycle,增加 pickle/env/log complexity;批改 thread 會失去 OOM 隔離並放大 RSS 累積風險。兩者都直接碰 FF 高風險路徑。
優點(維持): 行為一致可達成,計算路徑風險最低;保留批次穩定性。
缺點(維持): 仍有兩套 runner glue;需要以 contract tests 防漂移。
優先序: P2 僅抽 adapter/contract tests;不做 executor 整併。

## Suggested order
1. P0 progress schema + single RSS + batch prompt/alias.
2. P0 worker logging bridge.
3. P1 batch discard endpoint + terminal access_log config.
4. P2 runner adapter abstraction/contract tests only.
