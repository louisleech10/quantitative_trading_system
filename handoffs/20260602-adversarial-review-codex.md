## Findings

- [BLOCKING] G1 golden 擋不住 C3 數值漂移  
  證據：SPEC §1.4 只比「feature 名稱 sha256 / 數量 / schema / mean / std / nan_ratio」（lines 47-55）；TODO T3.1 驗收更只寫「feature 集合/schema 一致」（lines 32-33）。  
  問題：mean/std/nan_ratio 可被局部時間對齊錯誤、值重排、少量大漂移、同矩分布漂移繞過；TODO 也漏掉 SPEC 要求的 mean/std/nan_ratio ≤1e-9。  
  建議修法：G1 增加按 index 對齊的 per-feature value hash 或抽樣固定 rows hash、`max_abs_diff/max_rel_diff`、NaN mask hash；TODO T3.1 必須明列完整 G1 compare 命令與 pass/fail 條件。

- [BLOCKING] 1e-9 容差定義不合理且不分尺度  
  證據：SPEC §1.4「每 feature mean/std/nan_ratio 與 baseline 差 ≤ 1e-9」（line 53）。  
  問題：對大尺度特徵絕對 1e-9 可能因浮點 reduction 順序假紅；對小尺度/比例特徵又可能太寬或只看 aggregate。  
  建議修法：改成 `abs <= atol OR rel <= rtol`，按指標分開：`nan_ratio` 用 exact 或 ≤1/bar_count；mean/std 用 dtype-aware `atol/rtol`，另用 value-level hash/`max_abs_diff` 捕捉語義漂移。

- [BLOCKING] Phase 1 宣稱無依賴，但 T1.3 依賴 C1 注入機制  
  證據：SPEC Phase 1「無跨 phase 依賴，可先派」（line 73）；T1.3「複用須經注入（同 C1）」(line 102)；Phase 2 才是 C1 注入 registrar（lines 130-146）。  
  問題：執行端 Phase 1 若嚴守 scope，無法安全改 batch service 依賴注入；若自行先做注入，會越界到 C1 設計。  
  建議修法：把共用注入基礎抽成 Phase 0/T1.0，或把 T1.3 移到 C1 後；TODO 必須指定允許修改的 constructor/factory 檔案。

- [BLOCKING] 實施順序互相矛盾  
  證據：TODO 完成順序「Phase 1 → 2 → 3 → 4」（line 4）；診斷建議順序「C1 → 品質 loader → C2 → C3」（line 144）；診斷也說 C3「最後做」（line 128）。  
  問題：SPEC 把 C3 放在 C2 前，違反診斷中「避免一次動 ML 路由 + 並行預算難回歸」的風險控制。  
  建議修法：重排為低爭議非注入項 → C1/id+注入 → quality loader → C2 → C3；若維持現序，需明確說明 C3 降級後為何可早於 C2。

- [MAJOR] C1 browse id 含 hash 的覆蓋語義仍未拍板  
  證據：SPEC T2.0「建議 browse_{symbol}_{timeframe}_{config_hash8}」（line 135），但 §1.x 說「唯一需使用者拍板項」（line 69）；TODO 仍寫「建議」（line 21）。  
  問題：TODO 交給執行端選 hash 或 latest-overwrite，會造成 API/前端/restore/checkpoint 語義分叉。  
  建議修法：Frozen 前直接定案。建議採 full config_hash 或 collision-safe hash，並明列 old `browse_{sym}_{tf}` migration/compat 行為。

- [MAJOR] C1 registrar 介面缺 config_hash 來源  
  證據：SPEC T2.1 呼叫 `register_hdf5_for_browse(symbol, timeframe, manifest_path)`（line 146），T2.0 卻要求同 `(symbol,tf,config)` 產生 id（line 138）。  
  問題：介面沒有明確傳 config_hash；若從 manifest_path 推導，需規定 manifest 欄位、缺失/舊檔 fallback、hash8/full hash 一致性。  
  建議修法：定義 registrar protocol：輸入 `symbol,timeframe,manifest_path,config_hash` 或明確由 manifest loader 回傳 config_hash；加 corrupt/missing config_hash 測試。

- [MAJOR] C2 OOM 驗收只驗 worker 數，不驗記憶體峰值  
  證據：SPEC T4.2 驗收只斷言 16GB concurrency=1→4、=2→2、8GB→1（lines 206-209）；同節承認 `floor(cap/N)`「必要非充分」（line 211）。  
  問題：可能通過單元測試但在 16GB `2 symbols × 2 joblib × BLAS/Numba/Polars threads` 下 OOM；RAM gate 是否涵蓋子進程 slowpath peak 未被驗證。  
  建議修法：加入 16GB 模擬或實測 peak RSS gate：記錄 per-child peak RSS、總 RSS 上限、OOM 降載路徑；明確限制 BLAS/Numba threads 或把它們納入預算。

- [MAJOR] T4 rollback 不完整  
  證據：SPEC 回退「Phase 4 若 16GB 實測 OOM → 回退 T4.2 env 傳遞，保留 T4.1」（line 219）。  
  問題：若 OOM 根因是 T4.1 新簽名被其他 caller 傳入 concurrency 或 env 殘留，僅回退 env 傳遞不保證恢復安全模式。  
  建議修法：回退策略改為 feature flag 包住 T4.1/T4.2 整體，預設 off；OOM 時一鍵回到舊 `FFACT_BATCH_NESTED=1` 行為。

- [MAJOR] G1 baseline 來源不可重現  
  證據：SPEC §1.4「本次實際 config」「L2-6.5 同 0530」（line 46），「路徑記 TODO」（line 45）；TODO T3.0 未記 baseline 路徑或生成命令（line 28）。  
  問題：執行端無法知道 exact config、資料快照、baseline 存放路徑；後續驗收不可重跑。  
  建議修法：TODO 寫死 baseline 目錄、生成命令、config JSON/hash、資料來源快照、comparison script 路徑。

- [MINOR] T1.4 log 驗收模糊  
  證據：SPEC 可測「含子進程來源的關鍵字串」「不產生損毀行」（lines 116-118）。  
  問題：關鍵字與損毀行定義不固定，測試容易變成 brittle smoke test。  
  建議修法：定義結構化 log schema 或 JSONL fields：`symbol,timeframe,pid,layer,peak_rss,duration,status`；驗收解析 JSONL，不靠 substring。

- [MINOR] T2.2 前端驗收不可自動化  
  證據：SPEC T2.2「前端測試或手動」（line 160）；TODO T2.2 無驗收細節（line 25）。  
  問題：容易漏掉 fallback register 仍被觸發、型別未更新、舊 results shape 兼容。  
  建議修法：補 store/page unit test：有 `browse_task_id` 時不 call register；缺欄位時 fallback；更新 TypeScript response type。

## 無

- 過度工程：無明顯新增大型不必要架構。
- fake data / data_cache 修改風險：文件未要求修改 `data_cache/`。
- 明顯弱化 NaN/inf gate：無，但 G1/G2 驗收需補強如上。

HANDOFF_NOT_UPDATED: read-only sandbox and user requested review output only.

STATUS: DONE