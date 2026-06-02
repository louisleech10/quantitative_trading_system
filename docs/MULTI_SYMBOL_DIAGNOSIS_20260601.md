# 多 Symbol 特徵生成診斷報告（2026-06-01）

調查對象：`/feature-factory` 多 symbol 批次生成（task `6168aaed-77f8-4808-88a9-d9b69e9b1b8e`，
symbols=`[ETHUSDT, BTCUSDT, DOGEUSDT]`，timeframe=1h）。
對照：單 symbol run（log `case_search_api_20260530.log`）vs 多 symbol run（`case_search_api_20260601.log`）。

**本報告為事實彙整，作為規劃委員會輸入。所有結論附檔案行號或 log 證據。本次調查未改動任何程式碼。**

---

## 環境事實（決定性）

- 本機物理 RAM = **8.0 GB** → `8gb` tier。
- `get_slowpath_parallel_enabled()` 在 `物理RAM < 12GB` 回傳 False（[config.py:198-240](../momentum/core/config.py#L198-L240)）。
- 推論：本機**單 symbol 的 FracDiff joblib slow-path 本來就 n_jobs=1**。

---

## 六項問題根因

### ① 「批次任務輪詢逾時」— bug（輪詢預算過小且機制與單 symbol 不一致）
- 多 symbol：[featureFactoryStore.ts:617-638](../frontend/src/store/featureFactoryStore.ts#L617-L638)
  `for` 迴圈 `maxAttempts=600 × pollIntervalMs=1200ms ≈ 12 分鐘`上限，到頂 `set({ error: '批次任務輪詢逾時' })`。
- 單 symbol：[GenerationProgress.tsx:49](../frontend/src/components/feature-factory/GenerationProgress.tsx#L49)
  用 `setInterval`，**無次數上限**，跑到 `completed/failed` 才停。
- 實際 batch 耗時 ≈ 33 分鐘（registry 時戳：ETH→BTC ≈10min，BTC→DOGE ≈13min）≫ 12min 預算。
- **後端其實正常完成；純前端顯示層誤判。**

### ② 「目前 symbol」永遠落後一個 — bug（賦值時機錯）
- `task["current_symbol"]` 只在 [feature_factory_batch_service.py:419](../api/services/feature_factory_batch_service.py#L419)
  的 `_record_item_result` 賦值，而該函式在 `asyncio.as_completed` **item 完成後**才呼叫
  （[L378-401](../api/services/feature_factory_batch_service.py#L378-L401)）。item 開始計算時從不更新。
- concurrent=1 序列下：跑 BTC 時 current 停在剛完成的 ETH，跑 DOGE 時停在 BTC。差一個。

### ③ 「slow-path joblib disabled by FFACT_BATCH_NESTED=1」— 設計如此，非 bug
- [config.py:263](../momentum/core/config.py#L263)，由 batch 在
  [feature_factory_batch_service.py:363](../api/services/feature_factory_batch_service.py#L363)
  `batch_nested_environment(True)` 觸發。
- **8GB 機器上此設定無實際影響**：`get_slowpath_n_jobs` 即使不設 FFACT_BATCH_NESTED，
  也因 tier<12GB 回傳 1（[config.py:259-275](../momentum/core/config.py#L259-L275)）。
- 差異只在 ≥16GB tier 才咬得到。

### ④ Task 跑完看不到 / Refresh 後「已失效」— 設計缺陷 + UX bug + ①的連鎖後果
- batch task_id 是**記憶體編排 id**（`self._tasks`，TTL 3600s），非可瀏覽 result id。
  per-symbol 結果另註冊為 `browse_{symbol}_{timeframe}`。
- browse 註冊是**前端在 batch 完成後觸發**：
  [feature-factory/page.tsx:100-130](../frontend/src/app/feature-factory/page.tsx#L100-L130)
  依賴 `batchTask.results[sym]`。①逾時 → 前端拿不到 `completed` → 自動選取 effect 不觸發
  → BTC/DOGE 永不註冊。
- 證據：整份 0601 log **只有一筆** browse 註冊（`browse_ETHUSDT_1h`，21:57:13，手動點擊）。
- API 重啟 → `self._tasks` 清空 → `GET /batch/{id}` 404 → 「已失效」。
  checkpoint JSON 有落地，但 `get_status` 只讀記憶體（[L967-992](../api/services/feature_factory_batch_service.py#L967-L992)）。

### ⑤ 單/多 log 對比
| 項目 | 0530 單 | 0601 多 |
|---|---|---|
| ERROR / Traceback | 1 / 4 | 0 / 0 |
| WARNING | 58 | 32 |
| `Raw-sink start` / L6.5 heartbeat | 完整 | **完全沒有** |
| 檔案大小 | 392KB | 343KB |

- **子進程 log 全失**：batch 在 `ProcessPoolExecutor` 子進程跑 `_compute_single*`，
  子進程 logger 未寫入 API log 檔 → `Raw-sink start`、layer heartbeat、效率指標全丟。觀測性大降。
- **品質彙整全壞**：`Quality check failed for {ETH,BTC,DOGE}USDT: Unable to synchronously open file
  (file signature not found)`。`_compute_symbol_quality`
  [L912-923](../api/services/feature_factory_batch_service.py#L912-L923) 用 `h5py.File()` 開檔，
  但實際輸出是 `feature_manifest.json` + `raw/` 分片（實測 BTC 1h 目錄無 .h5，14MB manifest + raw/ 262 項）。
- **效率**：被 `FFACT_MULTI_SYMBOL_IC_FIRST` 強制 `concurrent_symbols=1`
  （[L491-496](../api/services/feature_factory_batch_service.py#L491-L496)）。整批全序列。
  但 per-symbol 計算在 8GB 上與單 symbol 一致（見③）。
- `20:36 RAM gate: available=1.44GB below required=4.00GB` 429 擋下啟動，屬正常 gate。

### ⑥ BTCUSDT 才有 12h 資料夾 — 非本次 batch 造成
- batch 21:23:59 建立、`timeframe=1h`（單一 tf，只 enqueue 1h，
  [L557-560](../api/services/feature_factory_batch_service.py#L557-L560)）。
- BTC 12h manifest 時戳 **21:21（早於 batch）**，config_hash `b86fa71`（≠ batch 的 `8440d93`）。
  → 0601 稍早一次獨立 BTC 12h 生成（對應 log 21:02/21:03 的 IC-First batch 嘗試）殘留。
- **附帶**：registry.json 有重複 12h 條目（同 hash `b86fa71`，feature_count 209057 與 268786 各一筆）→ 去重小 bug。

---

## 三項已收斂的設計方向（來自與使用者討論）

1. **輪詢統一**：多 symbol 改用單 symbol 的無上限 WS/poll 機制。（低爭議，定案）
2. **多=單 per-symbol 一致**：8GB 實測零代價。`concurrent=1` 時每 symbol 應完全複用單 symbol pipeline。
3. **worker 預算並行感知化**：取代 `FFACT_BATCH_NESTED` 一刀切。
   `concurrent=1` → 完整單 symbol 預算；`concurrent=N` → 預算除以 N（受 tier 表上限約束）。

---

## 送委員會裁決的爭議點

- **C1**：browse 註冊改後端在每個 symbol 完成時自動做（脫離前端＋記憶體依賴）的正確落點。
  落在 `_record_item_result`？還是 batch 完成 hook？checkpoint 是否需記錄 browse id 以撐過 API 重啟？
- **C2**：worker 預算並行感知化的具體公式與落點（取代 `FFACT_BATCH_NESTED` / `_resolve_concurrent_symbols`）。
  須同時滿足「concurrent=1 與單一致」與「未來 concurrent=N 不 OOM」。
- **C3**：`_compute_single_ic_first`（多 symbol 走 IC-First L7_raw）vs 單 symbol 標準路徑
  `_compute_single` 的內容差異是否該統一？此差異是否就是輸出格式/品質檢查/瀏覽分岔的根源？
  （本次調查未完全查證內容差異，需委員會深挖。）

## 不進委員會、直接列 SPEC 的低爭議項

- ①輪詢統一、②current_symbol 賦值時機、⑤品質檢查 h5py→正確 loader、⑤子進程 log 回收、⑥registry 去重。

---

## 委員會裁決（2026-06-01，Codex GPT-5.5 + Cursor Composer-2.5，read-only；Claude 實測佐證）

三方高度收斂。共識結論：

### C1 — browse 後端自動註冊
- **落點**：`_record_item_result` 的**成功分支**（每 symbol 完成即註冊），非 batch 完成 hook（避免 partial/斷線漏註冊）。
- **解耦**：batch service 不可直接 import `api.services` singleton（踩 Rule 4）→ 用 callback / protocol / 建構子注入 registrar。
- **持久化**：`browse_task_id` 寫入 checkpoint `completed_items[]`，但**僅寫 checkpoint 不夠**——API 重啟後 `get_status` 仍只讀記憶體；需靠 `_restore_persisted_tasks` re-hydrate register。
- **必修隱患（兩委員獨立指出）**：browse task_id **契約不一致**——手動 register 用 `browse_{sym}_{tf}`，磁碟 restore 用 `browse_{sym}_{tf}_{hash8}`（service.py:3718）。且固定 id 不含 config_hash → 不同 config/batch 互相覆蓋。SPEC 須先定 id 契約（含 config_hash 或明確接受「最新覆蓋」語義）。

### C2 — worker 預算並行感知化
- **取代一刀切**：拆掉 `batch_nested_environment ⇒ FFACT_BATCH_NESTED=1 ⇒ n_jobs=1`。
- **公式**：`get_slowpath_n_jobs(tier_gb, concurrent_symbols)` = `max(1, floor(tier_cap / concurrent_symbols))`，仍受 `get_slowpath_parallel_enabled()`（<12GB→1）約束。
- **傳遞**：父進程在 `run_in_executor` 前設 `FFACT_BATCH_SYMBOL_CONCURRENCY=N` env 給子進程讀，**不改函式簽名、不碰單 symbol 路徑**。
- **兩層預算必須分離**：symbol 並行（`_resolve_concurrent_symbols`）vs 子進程內 joblib，否則 16GB concurrent=2 會變 2×4 workers。
- **OOM 邊界 `floor(cap/N)` 是必要非充分**：RAM gate、memory_sanity downgrade、IC-First force-1 全部保留。`FFACT_BATCH_NESTED` 改語義為「強制安全模式」運維覆寫，不在 concurrent=1 預設開。
- **8GB 實測無加速**：此項為 ≥16GB 與未來 concurrent=N 鋪路，**不是本次 33min 主因**。

### C3 — IC-First vs 標準路徑
- **建議：統一執行機制、不強制統一 pipeline 變體**。batch 與 single 共用同一 `_compute_single` 入口，是否 IC-First 由與 UI 一致的顯式 flag（`FFACT_IC_FIRST_PIPELINE` / 請求級）決定；停用 `FFACT_MULTI_SYMBOL_IC_FIRST` 當「換函式+換 factory」的隱式開關。
- **否定報告 C3 前提**（Claude 實測 + 兩委員一致）：輸出格式分岔**不是** IC-First 造成——整棵樹零 .h5，單/多都是 manifest+parquet。`_compute_symbol_quality` 用 `h5py.File()` 是獨立的過時假設 bug；即使統一路徑仍要 manifest/parquet loader。
- **真正的 IC-First 差異在 L6.5 mode 語義**（只做 pre-IC winsor/fracdiff/ADF，跳過 rank/zscore/gaussian）→ 影響下游 ML selection/leakage。multi **不應靜默**與 single 不同；要改須 golden + IC stability gate，屬高風險 schema/數值變更，**最後做**。

### C3 更正（2026-06-01，Claude 實測 + 使用者澄清）
- 使用者澄清：Legacy/IC-First 是 UI 可選；0530 單 symbol 與 0601 多 symbol **都選 IC-First**。
- 實測路由：IC-First 由 **config 欄位 `preprocessing.ic_first_pipeline`** 決定
  （[feature_config.py:236](../momentum/FeatureEngineering/feature_config.py#L236)），
  `generate_features` 經 `_ic_first_enabled(config)`（[feature_factory.py:1700](../momentum/FeatureEngineering/feature_factory.py#L1700)）
  路由到 `_layer6_5_pre_ic`。**單/多都呼叫同一 `generate_features`、讀同一 config 欄位**。
- → 兩邊選 IC-First 時，**特徵計算完全一致**（同 `_layer6_5_pre_ic`、同 L7_raw 輸出）。
- `FFACT_MULTI_SYMBOL_IC_FIRST` + `_compute_single_ic_first` + `create_feature_factory_for_ic_batch`(注入 ICEngine)
  是**疊在 config 機制上的重複平行開關**；config_override 已帶 `ic_first_pipeline`，IC-First 早已生效。
  注入的 ICEngine 在 generate 路徑未被使用（僅 `run_ic_first_pipeline` 才用）。
- **C3 在開發階段降級為低風險清理**：刪重複的 multi-only 開關，多 symbol 改與單一致只靠 config 選 IC-First；
  僅保留「IC-First 時 concurrent=1」OOM 保護。**確認 6 症狀全在外層編排，與 IC-First 計算無關。**

### 建議實施順序（兩委員一致）
**C1（後端 per-item register + id 契約 + checkpoint）→ ⑤品質 loader（h5py→parquet/manifest）→ C2（worker 預算）→ C3（機制統一 + flag 收斂）**。低爭議 ①②⑤log⑥ 穿插其中。避免一次動 ML 路由 + 並行預算難回歸。
