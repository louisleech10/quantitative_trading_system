# FF 一致性整併 R1 互審 — Codex 審 Claude/Composer

範圍:只審 `20260619-ffconsist-r1-claude.md` 與 `-composer.md`;未自審 Codex 版。核對了真實路徑:單路徑 `feature_factory_service.py:227` thread;批次 `feature_factory_batch_service.py:464` ProcessPool;layer metrics `:1162-1180`;batch browse register `:583`;uvicorn `main.py:401 access_log=True`。

## Claude
- #1 log:同意。worker 內 setup logging 是必要方向;有正確點出多 worker 同檔交錯。補充:若直接共用 rotating handler 有 rotate 競態,應偏 queue listener 或 child non-rotating append。
- Q3 進度:同意但不完整。單路徑補 RSS、schema 共用正確;「batch 補 rolling 10/100」需確認目前 callback message 是否足夠,且 concurrent>1 不能呈現唯一 current stage,需保留 per-symbol map/降級語義。
- Q5 terminal:部分反對。`access_log=False` 成本低,但全關會少一層 HTTP debug 訊號;較穩做法是 env/config 控制或先過濾 noise,不應無條件定死。
- Q2 workflow:同意方向,但方案風險低估。把 batch 從自動持久化改 staging 會碰 checkpoint/resume/quality summary/磁碟清理一致性;若 user 已定要做,應先定 retention state machine。
- E 執行模型:同意「不把 executor 整併成同一種」。理由正確:批次 subprocess 提供 OOM/crash 隔離與 wave 後釋放;單路徑 thread 低延遲且 callback/lease 自然。漏洞:把「抽共用執行層」評為回報低過頭;仍應抽觀察/retention/progress contract 與 contract tests,否則兩套 glue 會繼續漂移。

## Composer
- #1 log:同意。`_compute_single` 入口 init worker logging 符合實際路徑;non-rotating FileHandler 避 rotate 競態判斷合理。補充:多進程同檔 append 仍需壓測/行原子性驗證。
- Q3 進度:同意。指出單路徑 RSS 含 API 噪音、批次 child RSS 語義不同,這是 Claude 漏掉的重點。反對點:優先序 P3 偏低;進度 schema 是 Q2 對話與 batch UX 的基礎,應至少 P1/P2。
- Q5 terminal:部分反對。直接 `access_log=False` 能解 stdout,但與 Claude 一樣低估 HTTP 可觀測性損失;建議設設定開關,dev 預設可安靜但可恢復。
- Q2 workflow:同意大方向與「browse 註冊延後」更貼近現況證據(`batch_service:583` 目前立即 register)。漏洞:每 item 彈 dialog 可能造成 N 次打擾;應優先整批一次+可展開逐項,且刪除已落盤輸出要同步 checkpoint state。
- E 執行模型:同意。Composer 的 hidden-risk 清單更具體:`_df_cache`/browse coalesce/warmup thread/lease、BLAS cap、wave gc 都是真實整併成本。補充:「不可單升 ProcessPool」太絕對;未來可用 ProcessRunner adapter 做可選隔離,但本輪不應改預設。

## E 三方結論
- 同意三方都對核心裁決:維持 thread 單 / subprocess 多,不要為一致性犧牲批次隔離或單路徑互動性。
- 被忽略的整併好處:不是統一 executor,而是統一 `ProgressSink/LogSink/RetentionSink`、payload schema、錯誤分類與 contract tests;這能降低 #1/Q3/Q2 未來再漂移。
- 維持現狀的隱藏風險:兩套 runner glue 會持續複製 logging/progress/retention 行為;batch concurrent>1 的進度語義仍可能被前端誤讀;access log 全關會讓非 FF API 問題較難追。
- 建議定案:executor 不動;先 Q5 設定化/P0小改,再 #1+Q3 contract 化,最後 Q2 retention state machine。不要把 E 標成「完全不做」,應標「不整併 executor,做 contract/adapter 防漂移」。
