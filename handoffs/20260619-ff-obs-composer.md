# FF Observability — Composer 獨立審查 (2026-06-19)

審查者: Composer (cursor-agent) | 證據: brief + middleware/logging/batch_service/feature_factory

## T1 Log 噪音
**立場: 部分同意 Claude，反對「全降 DEBUG」作預設。**
- 同意消雙記:`middleware.py:49-59` 每請求 3 行(Started + `api.request` + Completed);`api.request` 無 request-id,應刪 `log_api_request` 呼叫,保留 middleware(含 `X-Request-ID`)。
- 反對 blanket DEBUG:輪詢 404/500 若跟著降級會藏掉「task_id 打錯」類除錯信號。
- **替代(path-filter,零新 env):** prefix 靜音 `GET /api/v1/features/batch/{id}`、`/browse/` 且 status=200 且 duration<Nms;非 2xx/慢請求/POST 仍 INFO。比 `API_ACCESS_LOG` 少一個旋鈕。
- **最大風險:** 靜音後 2h run 只剩 symbol 級 log,仍看不到 layer——T1 不解 F1。
- **優先序: P0** — 改動小、立刻讓 api log 可讀。

## T2 批次 layer 進度 + F1
**立場: 同意「子進程觀測性缺失」,反對先上 mp.Queue 雙通道。**
- 根因確認:`feature_factory.py:541/622` layer RSS 在 worker logger;batch 只 symbol 級 WS(`feature_factory_ws.py:202`);`_compute_single` 未傳 `progress_callback`。
- **已有半成品:** `child_metrics.jsonl`(`FFACT_CHILD_METRICS_PATH`)但 `peak_rss_mb` 是 run 結束快照(`batch_service.py:1076`),非 L3/L6.5 真峰值;父進程 `rss_peak`(`:480`)量的是 parent RSS,**看不到子進程**——Claude 的 F1 缺口仍成立。
- **替代(更簡):** worker 在 layer start/done 以 O_APPEND 寫 `{artifact_dir}/layer_metrics.jsonl`(每 symbol ~16 行);父進程輪詢 tail 併入 `get_status`/`batch_progress` WS,不必 Queue。粒度=layer 邊界,非 heartbeat。
- **最大風險:** Queue 高頻 + worker crash → 父狀態卡死;檔案 append 可事後診斷 2h run。
- **優先序: P1** — F1 是 T3 前置;先做檔案版,再視需要做 IPC。

## T3 多 symbol 並行
**立場: 反對現階段恢復 tier 並行(B);強烈支持「先觀測再決定」。**
- `_resolve_concurrent_symbols` 硬編碼 1(`:643`);`hardware_utils` 的 24→2/32→3 已死碼。B2.2b 合理:IC-First 437K×multi-TF 峰值未量到前,父 RAM gate(`1GB` sequential)與 tier soft cap 都**不綁 child peak**。
- **「先 F1/T2 再 T3」: 是,且必要條件是 per-layer child peak RSS**,不是 symbol 尾端 `child_metrics`。
- **替代:** 維持 symbol 序列;若需提速先攻 **wave 間 gc + 子進程 peak 寫檔驗證**,再試 `FFACT_CONCURRENT_SYMBOLS` 顯式 override=2 於 32GB 單一標的對照 run,禁預設 tier 表。
- **最大風險:** 並行=2 時兩個 L3 同時撐滿 → SIGKILL,resume 複雜度 > 省下的 1× wall time(Opt #2>#4)。
- **優先序: P3(擱置)** — 無 child layer RSS 分佈前動 T3=賭。

## 總序
T1 → T2(檔案 layer_metrics) → 用真實 IC-First peak 填表 → 再議 T3。

HANDOFF_NOT_UPDATED: read-only 審查任務,不覆寫根 HANDOFF。
