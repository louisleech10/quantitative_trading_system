# FF 一致性整併 — Composer 2.5 第 1 輪（獨立提案）

佐證：`feature_factory_service.py:227` thread、`batch_service.py:464-474` ProcessPool、`_compute_single:1162-1180` layer_metrics、`feature_factory.py:3518-3525` `_report_progress`、`RunRetentionDialog.tsx`、`main.py:401` access_log。

---

## #1 Log 一致
① **裁決**：子進程入口 `_compute_single` 開頭呼叫共用 `init_worker_logging()`；父進程在 wave 前設 `FFACT_API_LOG_PATH`（沿用 `case_search_api_*.log` 路徑）。子進程對 `momentum.*`/`api.*` 掛 `FileHandler`，log 行加 `[pid={pid} sym={symbol}]` 前綴。  
② **風險**：多子進程同檔寫入行交錯；`TimedRotatingFileHandler` 跨進程 rotate 可能重複/截斷。  
③ **優**：除錯與單路徑同檔可 grep；改動面小。**劣**：非嚴格順序；需避開 rotate 競態（worker 用 non-rotating `FileHandler` 指向當日檔）。  
④ **優先序**：**P2**（可觀測性核心，次於 Q5）。

## Q3 進度一致
① **裁決**：定義 canonical payload：`stage, progress, message, rss_mb`（batch 再加 `symbol/timeframe`）。抽 `api/utils/ff_progress.py`：`enrich_progress(event)` 內 `psutil` 取 RSS。單路徑：`progress_callback` 經 enrich 後寫 task + WS（補 `stage_progress`/`current_rss_mb`）。批路徑：保留 `layer_metrics.jsonl` 為 SSOT，tick 合併邏輯不變；`concurrent>1` 維持僅 coarse（`_apply_layer_metrics` 已 skip）。  
② **風險**：單路徑 RSS=同進程（含 API/browse 噪音），與子進程 RSS 語意略異；前端需同欄位渲染兩模式。  
③ **優**：WS mapper 已備欄位；sub-step 仍靠 `message`（rolling 10/100）。**劣**：高並發 batch 仍無 per-symbol layer 細節（設計取捨）。  
④ **優先序**：**P3**。

## Q5 Terminal
① **裁決**：`run_server()` 設 `access_log=False`；HTTP 請求繼續靠既有 middleware `log_api_request` 進檔。  
② **風險**：失去 uvicorn 原生 access 格式；極低。  
③ **優**：一行、stdout 立刻安靜。**劣**：雙重 access log 本來就冗餘。  
④ **優先序**：**P1**（最低成本先落地）。

## Q2 批次保留對話
① **裁決**：對齊單路徑語意——**算完即落盤，browse 註冊延後至使用者決定**。`_record_item_result` 移除即時 `browse_registrar.register`；每 item 完成推 WS `retention_prompt+run_identity`（或 batch 專用 `item_retention`），前端複用 `completionQueue`+`RunRetentionDialog`；`命名/保留`→register+alias，`刪除`→`deleteRun`，`關閉/未命名`→register 無 alias。checkpoint 增 `retention_pending/decided` 供 resume。  
② **風險**：N symbol 排隊 N 次對話；batch 繼續跑時使用者未及刪除→暫占磁碟（與單路徑相同）；resume 需回放 pending。  
③ **優**：使用者已定；Explorer 不再塞未確認 run。**劣**：前端/ checkpoint 改動大於 #1/Q3。  
④ **優先序**：**P4**（功能正確但依賴進度可見性先穩）。

## E 執行模型（thread vs subprocess）
① **裁決**：**維持現狀，不整併執行模型。** 觀察面（log/進度/retention/terminal）統一即可。  
② **風險（若硬整併）**：單→subprocess 會斷 `_df_cache`/browse coalesce/warmup thread/lease，互動延遲升；多→thread 失去 wave 間 `gc`、子進程 OOM 隔離、BLAS cap（`batch_service.py:1103`），8GB 多 symbol 易拖垮 API。  
③ **優（維持）**：各取所長——單=低延遲同進程；多=RAM 安全。**劣**：永遠兩套 shell，#1 必須在子進程補 logging。  
④ **若被迫選方向**：僅可接受「抽共用 `generate_features`+progress 契約」，**不可**把 batch 降 thread 或單升 ProcessPool。  
⑤ **優先序**：**決策項**（本輪定案：維持）。

---

## 建議實施順序
`Q5 → #1 → Q3 → Q2`；**E 不動架構**。

## 假設待第 2 輪挑戰
- 子進程 non-rotating FileHandler 是否足夠避 rotate 競態（需實測）。
- batch 保留不阻塞下一 symbol 是否可接受（我判可，與單路徑一致）。
