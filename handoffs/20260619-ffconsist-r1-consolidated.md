# FF 一致性整併 R1 統整 — Claude(ops)

依三方獨產(claude/codex/composer r1)+ 兩份互審(codex審claude+composer、composer審claude+codex)。

## 核心共識（三方 + 兩審一致）
**E 執行模型：不整併 executor（單 thread / 多 subprocess）——但統一觀察契約防漂移。**
- 不整併理由(全體):subprocess=OOM/crash 隔離 + TA-Lib/Numba spawn 安全 + wave 後 gc/BLAS cap + per-symbol RSS;thread=低延遲 + callback/lease/warmup/_df_cache 自然。單升 ProcessPool 或多降 thread 都直接傷 FF 高風險路徑(8GB 多 symbol OOM)。
- **互審糾正我(Claude)**:我原寫「抽共用層回報低≈不做」**過絕**。修正裁決:**不整併 executor,但 DO 抽 `ProgressSink/LogSink/RetentionSink` + 共用 payload schema + error 分類 + contract tests**。
- **維持現狀的隱藏風險(兩審指出,我原漏)**:兩套 runner glue 會持續複製 logging/progress/retention → **沒 contract test 就會在本次修好後再分叉**。故 contract tests 非可選,是防漂移的關鍵。

## 逐項定案（reconciled 優先序）
**P0 Q5 terminal**:uvicorn access_log 改 **env/config 開關**(dev 預設安靜、可恢復),**非無條件全關**(保留 404/500 HTTP 可觀測性)。middleware 已進檔不漏。一行+開關,零 FF 路徑風險。

**P0 #1 log 一致**:batch worker(`_compute_single` 入口)`init_worker_logging()`,對 momentum.*/api.* 掛 **non-rotating FileHandler 指當日檔**(避 `TimedRotatingFileHandler` 跨進程 rotate 競態),行加 `[pid sym tf]` context。queue listener 列**可選**非預設(父死 listener 孤兒風險);concurrent=1 下 FileHandler+pid 已足。需壓測行原子性。

**P1 Q3 進度一致**:共用 `FeatureProgressEvent{stage,progress,message,rss_mb,symbol,timeframe,batch_id,ts,schema_version}`;單路徑 `_report_progress` 經 enrich 補 RSS+寫 WS;batch 維持 layer_metrics.jsonl 為 SSOT 經 bridge 映同 schema。
- **concurrent>1 不得呈現單一 current_stage**(維持 coarse/per-symbol map;現 `_apply_layer_metrics` 只 concurrent==1 顯示是正確防誤導)。
- **RSS 語意差(兩審指出)**:單路徑 RSS=同進程含 API/browse 噪音;子進程 RSS=該 symbol。**欄位加註解或分 `process_rss_mb` vs `worker_rss_mb`**,前端標示,勿直接跨路徑比較。
- sub-step 細節(rolling 10/100)靠 message 欄,不硬塞 batch 併發。

**P2 Q2 批次保留對話**(使用者已定做):**算完延後 browse 註冊**(現 `batch_service:583` 立即 register→改 staging)。**整批一次 dialog + 可展開逐項**(非 N 次打擾)。需 **retention state machine**:checkpoint 加 `retention_pending/decided`;`保留/命名`→register+alias、`刪除`→deleteRun+**同步失效 checkpoint/quality summary/RunManager/磁碟輸出**、`未命名`→register 無 alias。批量刪除宜後端交易式彙總(逐 run delete 慢)。先實測 `_record_item_result` 定 staging 切點。

**E（持續）**:不整併 executor;抽 Sink/schema contract + **contract tests**(防 #1/Q3/Q2 雙路徑再漂移)。adapter(GenerationRunner/ThreadRunner/ProcessRunner 共享 contract)為可選未來,本輪只做 contract+tests。

## 實施順序
Q5(P0) → #1(P0) → Q3(P1) → Q2(P2) → E contract tests(隨各項落地,防漂移)。

## 待 R2 交叉詰問的點
1. #1 多進程同檔 append 行原子性是否需壓測證明(非僅假設 O_APPEND 安全)。
2. Q3 RSS 雙語意:分欄 vs 註解,哪個前端較不誤導。
3. Q2 retention state machine 與既有 resume/checkpoint 的相容切點(實測 _record_item_result)。
4. E contract tests 的最小集(覆蓋哪些行為才足以防漂移)。
5. 優先序:#1 與 Q5 是否真該並列 P0,還是 Q5 先(更小)。
