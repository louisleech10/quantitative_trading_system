以下為規劃顧問立場（只讀、未改檔），依你要求的格式。

---

## C1

**建議：** 在 `_record_item_result` 的**成功分支**（`error is None` 且 `hdf5_path` 非空）同步呼叫 `feature_factory_service.register_hdf5_for_browse`，並把回傳的 `browse_task_id` 寫進 checkpoint 的 `completed_items[]`；前端改為讀 status/checkpoint 裡的 id，不再依 `batchTask.results` 事後註冊。

**理由：**
- 落點對齊「per-symbol 完成」語意，不必等整批 `completed`；可解 ① 輪詢逾時後仍無法瀏覽後續 symbol 的連鎖問題。
- `register_hdf5_for_browse` 已冪等（`browse_{symbol}_{timeframe}`，重複呼叫只更新 result），適合每 item 完成時觸發。
- IC-First 實際回傳的是 `feature_manifest.json` 路徑（見 `feature_factory.py` L2412），`Path.exists()` 仍成立；browse 的 CGSA/`_load_task_context` 本來就支援 manifest，比前端硬傳「HDF5」語意更一致。

**風險／反對：**
- **僅寫 checkpoint 不夠**：API 重啟後 `get_status` 仍只讀 `self._tasks`（L967-992），batch task 仍 404；browse 要靠「已 register 進 service」或 `_restore_persisted_tasks` Pass 2。checkpoint 存 `browse_task_id` 是給**重啟後 re-hydrate register** 用，不能取代 per-item register。
- **task_id 不一致**：手動 register 用 `browse_{sym}_{tf}`，磁碟 restore 用 `browse_{sym}_{tf}_{hash8}`（L3718）。後端自動 register 應固定一種契約，並讓 `/browse/available` 與前端對齊。
- **不建議只用 batch 完成 hook**：整批結束才註冊無法在中途點 symbol 預覽，也無法修復「partial + 前端斷線」。
- **Race**：`concurrent_symbols>1` 時同一 wave 不應重複同一 (symbol, tf)；若未來允許，需 wave 內去重 + register 鎖。現況 concurrent=1 風險低。

---

## C2

**建議：** 拆掉「`batch_nested_environment(True)` ⇒ `FFACT_BATCH_NESTED=1` ⇒ `n_jobs=1`」的一刀切；改為 `get_slowpath_n_jobs(tier_gb, concurrent_symbols)`，公式 `max(1, floor(tier_cap / concurrent_symbols))`，且仍受 `get_slowpath_parallel_enabled()`（<12GB → 1）約束；`concurrent=1` 時**不要**設 `FFACT_BATCH_NESTED`。

**理由：**
- 報告已證實 8GB 上 nested 無實測差異；真正受害的是 ≥16GB 且 `concurrent=1` 卻被壓成單執行緒 FracDiff。
- `_resolve_concurrent_symbols` 在 task 啟動時解析（L250），與 wave 內 `batch_nested_environment` 分離；並行度應由 tier + `FFACT_MULTI_SYMBOL_IC_FIRST`（OOM 時 force 1）決定，不應與 joblib 預算綁同一 env。
- 子進程需看見 divisor：父進程在 `run_in_executor` 前設 `FFACT_BATCH_SYMBOL_CONCURRENCY={N}`（或把 N 傳入 static worker），由 `get_slowpath_n_jobs` 讀取；比改 `_resolve_concurrent_symbols` 簽名更局部、不碰單 symbol WS 路徑。

**風險／反對：**
- **8GB 仍無加速**：tier_cap 表為 2 但 parallel auto=OFF → 仍 1；C2 是為 16GB+ 與未來 `concurrent=N` 鋪路，不是修本次 33min 主因。
- **OOM 邊界**：`floor(cap/N)` 是必要非充分；RAM gate（L524+）、`memory_sanity_failed` 降 concurrent、IC-First force 1 應保留。cap 表宜保守（總 process ≈ `N × n_jobs` + executor）。
- **保留 `FFACT_BATCH_NESTED` 作運維覆寫**可以，但語意應改為「強制 nested/安全模式（n_jobs=1）」，**不要**在 `concurrent=1` 預設開啟。
- **不同意「改 `_resolve_concurrent_symbols` 簽名就夠」**：它管 symbol 並行，不管子進程內 joblib；兩層預算必須分離，否則 16GB concurrent=2 會變 2×4 workers。

---

## C3

**建議：** **統一執行機制、不強制統一 pipeline 變體**——batch 與 single 共用同一 `_compute_single` 入口，是否 IC-First 只由與 UI 一致的 env（`FFACT_IC_FIRST_PIPELINE` / 請求級 flag）決定；**停用** `FFACT_MULTI_SYMBOL_IC_FIRST` 作為「換函式 + 換 factory」開關，僅保留其「force concurrent=1」若仍需要。

**理由：**
- 現況分岔在 L358-362：`get_multi_symbol_ic_first_enabled()` 選 `_compute_single_ic_first` vs `_compute_single`，後者還換 `create_feature_factory_for_ic_batch`，與 single 路徑不對稱。
- **品質檢查 h5py 失敗**（L912-923）主因是 loader 假設 HDF5，與「是否 IC-First」部分相關（輸出常為 manifest+raw），但即使統一路徑、只要輸出是 CGSA manifest 仍會壞——需 manifest/parquet loader（報告已列低爭議項），不能靠 C3 單獨治癒。
- **瀏覽分岔**主因是「前端事後 register + 輪詢/記憶體」與 task_id 契約（C1），不是 IC-First 本身；manifest 在 `_restore_persisted_tasks` 可自動還原，與手動 register 的 id 規則不一致才是隱患。
- ML：`FFACT_IC_FIRST_PIPELINE=1` 會改 L6.5 路由（rank/zscore 相對 IC 的時點），影響 selection/leakage 語意；multi 不應**靜默**與 single 不同。應讓使用者/同一 config 顯式開 IC-First，兩邊一致。

**風險／反對：**
- **「都走標準」**：若 production 已預設 `FFACT_MULTI_SYMBOL_IC_FIRST=1`，會改輸出體積/時間/記憶體，需 golden + IC stability gate。
- **「都走 IC-First」**：單 symbol 預設非 IC-First 時會改行為面太大，不建議為了 multi=single 而強推。
- **不同意「C3 就是 343KB vs 392KB、無 L6.5 log 的根」**：子進程 log 未回 API log（ProcessPool）與 pipeline 選擇是**兩個**觀測問題；統一路徑可減少驚喜，但不取代子進程 logging 方案。
- IC-First 記憶體更高（docstring L490-495）— 即使統一機制，`concurrent=1` + 較嚴 RAM gate 仍合理；與 C2 的 per-symbol worker 預算需一起評估。

---

### 與報告「已收斂方向」的對齊

| 項目 | 委員會建議 |
|------|------------|
| 輪詢統一 | 同意（低爭議，與 C1 正交） |
| multi=single @ concurrent=1 | C2（8GB 無感）+ C3（行為一致）+ C1（可瀏覽性） |
| worker 預算並行感知 | 即 C2，勿再用 `FFACT_BATCH_NESTED` 預設綁死 |

如需下一步 SPEC，建議順序：**C1（後端 per-item register + checkpoint browse_id）→ 品質 loader → C2 → C3（機制統一 + feature flag 收斂）**，避免一次改動 ML 路由與並行預算難以回歸。
