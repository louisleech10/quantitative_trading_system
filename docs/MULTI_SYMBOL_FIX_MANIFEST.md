# 多 Symbol 批次修復 — Manifest（scope 契約，使用者讀這頁；機器 coverage_check 逐 ID 驗）

> 來源：`MULTI_SYMBOL_DIAGNOSIS_20260601.md`（6 症狀根因 + 委員會 C1/C2/C3 + adversarial findings）。
> 每項一行 + 驗證點。SPEC/TODO 須涵蓋每個 `[P*-*]` ID（否則 coverage_check FAIL）。

## Phase 1 — 低爭議群（真無依賴）
- `[P1-1]` 多 symbol 輪詢移除 600 次上限，對齊單 symbol 無上限。**驗證**：mock >600 次 running 不誤報逾時。
- `[P1-2]` current_symbol 在 item **submit 前**賦值（非完成後）。**驗證**：2-symbol 序列，跑中讀 current==當前。
- `[P1-3]` 子進程 log 回收為 JSONL（symbol/pid/peak_rss/duration/status）。**驗證**：解析 JSONL 每 symbol 一筆。
- `[P1-4]` registry 以 (symbol,timeframe,config_hash) upsert 去重。**驗證**：同 key register 兩次→1 筆最新。

## Phase 2 — 注入 seam + C1 + 品質 loader
- `[P2-1]` browse id 統一為 `browse_{sym}_{tf}`（B latest-overwrite，去掉 restore 的 _hash8）。**驗證**：601 與 3718 同 id。
- `[P2-2]` 注入 seam（Protocol IBrowseRegistrar/IQualityComputer，禁 import feature_factory_service）。**驗證**：grep import→0。
- `[P2-3]` `_record_item_result` 成功分支經注入 registrar 自動註冊 + 寫 checkpoint。**驗證**：成功 symbol 註冊數==成功數；重啟可 browse。
- `[P2-4]` `_compute_symbol_quality` 改 parquet/manifest（複用 _build_data_quality_cgsa）。**驗證**：G2 golden 與單 symbol 一致。
- `[P2-5]` 前端 handleSelectBatchSymbol 優先讀後端 browse_task_id。**驗證**：有 id 不再 call register（unit test）。

## Phase 3 — C2 worker 預算（包 FFACT_PARALLEL_BUDGET flag，預設 off）
- `[P3-1]` `get_slowpath_n_jobs(tier_gb, concurrent_symbols=1)` = max(1, cap//concurrent)。**驗證**：(16,1)=4、(16,2)=2、(8,*)=1。
- `[P3-2]` 父進程設 FFACT_BATCH_SYMBOL_CONCURRENCY env；peak RSS gate + thread 封頂。**驗證**：concurrency=2@16GB→n_jobs=2 且不超 RSS 上限。

## Phase 4 — C3 IC-First 清理（最後做）
- `[P4-1]` 凍結 G1 golden（reference=BTCUSDT 1h + **可審計 config**；名稱 sha256+數量+mean/std/nan_ratio+**全量 chunk hash**+NaN-mask hash+env_snapshot；+三 symbol smoke）。**驗證**：baseline 檔產出且可重跑比對；注入 1e-3 漂移→FAIL。
- `[P4-2]` 移除 _compute_single_ic_first / FFACT_MULTI_SYMBOL_IC_FIRST 換函式語義，統一走 _compute_single + config。**驗證**：G1 golden 全項通過（改前==改後、單==多）。
