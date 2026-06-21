# FF 單/多 symbol 一致性整併 — 最終定案（兩輪三方委員會）

流程:R1(三方獨產→互審→統整→受審) + R2 交叉詰問(同流程)。交叉詰問**校正了 Claude 3 處**(下標 ✎)。E 與「不整併 executor」兩輪三方+四份互審一致。

## E 執行模型 — 維持現狀,只統一觀察契約
**不整併 executor**:單=`run_in_executor` thread(低延遲/callback/lease/_df_cache/warmup);多=ProcessPool 子進程(OOM/crash 隔離/wave gc/BLAS cap/per-symbol RSS)。單升 ProcessPool 或多降 thread 都傷 FF 高風險路徑(8GB 多symbol OOM)。兩輪無翻案證據。
- **本輪 mandatory(✎ 三方裁:薄函式 mandatory,非僅型別)**:共用 `FeatureProgressEvent`/`FeatureRetentionEvent` schema + `error-class` enum + **單一 `normalize_progress_event()`/`normalize_retention_event()` 薄函式(兩路徑都經它 normalize/enrich/emit)** + 雙路徑 **parity tests**。
- **拒**:ProgressSink/LogSink 厚類、GenerationRunner/ThreadRunner/ProcessRunner adapter、任何 lifecycle 抽象(延後/不做)。
- 理由:只定 schema+test,兩路徑仍各自手組 payload→事後才抓漂移;薄 normalize 是 contract 釘點,結構性防漂移,成本低。

## 5 工作項（定案,含做法/風險/優先序）
**Q5 terminal〔P0a,最小先落〕**:uvicorn `access_log` 改 **env/config 開關**(dev 預設安靜、可恢復),非無條件全關(保 404/500 可觀測)。middleware 已進檔不漏。

**#1 log 一致〔P0b〕**:batch worker(`_compute_single` 入口)`init_worker_logging()`,對 momentum.*/api.* 掛 **non-rotating FileHandler** 指當日檔(env `FFACT_API_LOG_PATH`;避 TimedRotatingFileHandler 跨進程 rotate 競態),行加 `[pid sym tf]`。
- ✎ **mandatory smoke**(非僅 TODO):父+1~4 子進程各寫短行,assert 無破行/缺行,才算 P0 完成;concurrent>1 全壓測留 T-A。

**E minimal〔P0c,隨 #1/Q3 首次改 payload 同 PR 落,不另開軌〕**:上述 normalize 薄函式 + parity tests。
- **parity 驗收 5 條(可證偽)**:①兩路徑同 schema+`schema_version` ②同 error-class enum ③retention `pending→decided→(error)` 狀態轉移 ④concurrent>1 不輸出假單一 current_stage ⑤✎ batch item **無 `browse_task_id` 直到 retention decided**。

**Q3 進度一致〔P1〕**:單路徑 `_report_progress` 經 normalize 補 RSS+寫 WS;batch 維持 layer_metrics.jsonl 為 SSOT 經 bridge。
- **RSS 互斥分欄**:`process_rss_mb`(單,同進程含 API 噪音)/ `worker_rss_mb`(batch 子進程該 symbol),同 event 只填一個,前端各自標籤、**不跨路徑比較**;deprecate 泛名 `current_rss_mb`。
- rolling 10/100 sub-step 留 `message`(不升結構欄);concurrent>1 維持 coarse。

**Q2 批次保留對話〔Phase A=P2,Phase B=P2.5〕**(使用者已定做):
- **非阻塞**:retention 入 per-item `completionQueue`(含 batch_id),batch 續跑;前端=整批可展開面板(非 N 個強制 modal;現 Dialog 只取 queue[0] 需擴)。
- ✎ **磁碟背壓(mandatory)**:pending retained output bytes 超 **soft 閾值(env 可調,不硬編)**→暫停新 wave + UI 提示;與非阻塞並存(T-C 只防 run 內,不防 pending 累積)。
- **staging 切點(已實測確認)**:`_record_item_result` 成功分支(`batch_service:581-583`)目前**立即** `browse_registrar.register`→移到「checkpoint output_paths 後、register 前」,改寫 `staging_path`+checkpoint `retention_pending/decided/error`。
- **Phase A**:prompt+延後 register+per-item keep/discard+checkpoint 狀態機+resume 重建 pending queue。**Phase B**:後端交易式 bulk-delete endpoint(刪除同步失效 checkpoint/RunManager/quality summary/磁碟輸出;部分失敗標 retention_error 可重試;discard 刪檔但 checkpoint 失敗用 tombstone 防復活)。

## 實施順序
Q5(P0a) → #1+smoke(P0b) → E normalize+parity(P0c,隨首次 payload 改) → Q3(P1) → Q2-A(P2,含背壓) → Q2-B(P2.5)。

## 交叉詰問校正記錄（誠實）
✎1 E 薄 emitter:Claude 原「選做」→ 三方裁 mandatory。
✎2 Q2 磁碟背壓:Claude/Composer R2 原漏 → Codex 提,三方納入 mandatory。
✎3 #1 smoke:Claude 原「僅 TODO」→ 三方裁 mandatory P0 門檻。
