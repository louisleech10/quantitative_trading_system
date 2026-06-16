# Batch Alias Design Consultation

## Scope
- 讀取型設計諮詢；未改 production code，未 commit。
- 問題：批次生成 N 個 symbol 會產生 N 個 run，現行 alias per-run，100 symbols 需改 100 次。

## 已驗證現況
- Run registry key 是 `(symbol, timeframe, config_hash)`；`FeatureRegistry.add()` 以此 upsert。
- `FeatureRegistry.set_alias()` 只改單一 run，且 alias 唯一性是同一 `symbol/timeframe` 內不得重複。
- API 只有 `PATCH /api/v1/features/runs/{symbol}/{timeframe}/{config_hash}/alias`，沒有 bulk/batch alias endpoint。
- `RunInfo` 回傳 `alias`，沒有 `batch_id` / `batch_alias` 欄位；前端 `RunInfo` 型別相同。
- Feature Explorer 選擇器以 `runKey = symbol|timeframe|config_hash` 選 run；顯示 label 是 `alias || symbol/timeframe/hash`。
- Batch checkpoint 有 `batch_id`、`request_payload`、`completed_items[]`、`browse_task_id`、`output_paths`；`completed_items` 沒有獨立 `config_hash` 欄位，但可由 `browse_task_id` 或 path 間接解析。
- 實際 registry 樣本 `data_cache/features/registry.json` 沒有 `batch_id` / `batch_alias`；實際 checkpoint 樣本存在於 `data_cache/feature_preprocessing/batch_state_*.json`。

## Batch 與 Run 關聯判斷
- 目前可以從 batch checkpoint 反查該批完成的 symbol runs，但這是 checkpoint 衍生能力，不是 registry 的穩定一等關聯。
- 反查路徑：`batch_id -> checkpoint.completed_items[] -> browse_task_id/path -> symbol/timeframe/config_hash -> registry run`。
- 風險：checkpoint 是 resumable/operational artifact，不等於長期 metadata model；若 checkpoint 被清理或 browse id 格式改變，batch/run 關聯會弱化。
- 結論：若要支援「批次命名」成為產品能力，應把 `batch_id` 寫入每個 completed run 的 registry entry；只靠 checkpoint 不夠穩。

## 方案比較

### A. 批次層級 alias，套用到所有 symbol runs
- 做法：每個 run registry entry 增加 `batch_id`、`batch_alias`；顯示名用 `batch_alias:{symbol}` 或 `batch_alias / symbol`。
- 優點：使用者只命名一次；保留 per-run key 不變；Feature Explorer 可用 batch 名搜尋/分組；很貼近「同一批 config」心智模型。
- 缺點：如果實作成每個 run 寫同一 `alias=batch_alias`，會撞現有同 `symbol/timeframe` alias 唯一性；因此應新增 `batch_alias` 欄位，不要覆寫 per-run `alias`。
- 適用：批次生成後主要以「這批實驗」管理，而不是每個 symbol 各自命名。

### B. Alias 模板批次套用
- 做法：新增 bulk rename，使用模板如 `{batch_alias}_{symbol}` 或 `{alias}_{symbol}` 寫入每個 run 的現有 `alias`。
- 優點：最小後端模型變動；沿用 per-run alias、auto cleanup named protection、現有 UI label。
- 缺點：仍產生 N 個 alias 實體；日後改批次名稱仍需批量改 N 筆；模板錯誤可能造成部分成功/衝突，需要 transaction/preview。
- 適用：想快速止痛，且接受 alias 最終仍是 per-run materialized 值。

### C. 引入 batch entity 分組
- 做法：建立 batch registry/entity，例如 `data_cache/features/batches.json` 或 registry 子模型；batch 有 `batch_id`、`batch_alias`、request hash、symbols、timeframe、created_at、status，run entry 只存 `batch_id`。
- 優點：語義最乾淨；支援批次列表、批次品質、批次刪除/保留、批次 rename、Feature Explorer 分組；避免把 operational checkpoint 當產品 metadata。
- 缺點：範圍最大；需 migration/backfill、API model、frontend grouping、測試面較大。
- 適用：若未來會把 batch 當一等研究實驗管理，這是正解。

### D. 後端 bulk-rename endpoint
- 做法：新增 `PATCH /runs/aliases` 或 `PATCH /batch/{batch_id}/aliases`，一次更新多個 `(symbol,timeframe,config_hash)->alias`。
- 優點：很小、直覺；可先只做 endpoint + UI template；不必先設計 batch entity。
- 缺點：只解「少點幾次」；不解 batch/run 關聯與分組；若沒有 `batch_id` in registry，`/batch/{id}` 仍依賴 checkpoint 反查。
- 適用：作為 Phase 1 或 B 的基礎能力。

## 對既有行為影響
- Registry key 不應改：`(symbol,timeframe,config_hash)` 是 browse、delete、lease、Feature Explorer selection 的穩定身份。
- Alias 唯一性：現有 `alias` 在同 `symbol/timeframe` 內唯一。批次名若寫入 `alias`，同一 symbol 多批同名會衝突；不同 symbol 不衝突但仍不代表 batch。建議新增 `batch_alias`，唯一性改為 `batch_id` 唯一、`batch_alias` 可全域唯一或允許重名但顯示時間/hash disambiguation。
- Auto cleanup：目前 named run 不會被清。若只新增 `batch_alias`，需明確決策：有 `batch_alias` 的 run 是否等同 named/protected。建議 yes，否則「命名批次」卻被 cleanup 清掉會違反使用者預期。
- Feature Explorer：短期只需 `RunInfo` 增加 `batch_id/batch_alias/display_alias`，`formatRunLabel()` 改成 `alias || batch_alias + ':' + symbol || fallback`；selection key 不變。
- Run Manager：應分組顯示 batch，提供「重命名整批」；per-run rename 仍保留作 override。
- BatchQualityOverview/batch service：已有 `batch_id` 與 completed symbol list，可作為 rename entry point，但應在 registry 補寫關聯後再依 registry 查，避免 checkpoint 缺失導致 UI 不一致。

## 推薦方案
- 推薦採「A 的使用者體驗 + C 的最小資料模型骨架 + D 的 bulk endpoint」，分階段做。
- 不推薦把同一批直接 materialize 成 N 個相同 `alias`；這會混淆 per-run alias 語義，也容易踩唯一性與 rename 維護成本。

## 分階段
- Phase 1（最小一致止痛）：batch completed 時把 `batch_id` 寫入每個 registry entry；新增 `batch_alias` 欄位與 `PATCH /api/v1/features/batch/{batch_id}/alias`。endpoint 根據 registry `batch_id` 更新同批 runs 的 `batch_alias`，回傳 affected runs。Feature Explorer label 顯示 `alias || batch_alias:{symbol} || fallback`，搜尋加入 `batch_alias`。
- Phase 2（管理體驗）：Run Manager 按 `batch_alias/batch_id` 分組；批次 rename 一次生效；per-run alias 作 override；auto cleanup 把 `alias` 或 `batch_alias` 視為 protected。
- Phase 3（一等 batch entity）：若批次研究工作流繼續擴大，再新增 batch registry/entity，保存 request hash、config hash、symbols、quality summary、status、created_at；checkpoint 只做 resume，不再當 metadata source。

## 挑戰 Claude 傾向
- 「registry run 存 batch_id+batch_alias，顯示 batch_alias:{symbol}」方向正確。
- 需要補兩點避免後續債務：`batch_alias` 不應覆寫 `alias`；以及批次/run 關聯應在生成完成時寫進 registry，而不是每次從 checkpoint 推導。
- 更精確的最小方案是：run entry 存 `batch_id` + `batch_alias`，per-run `alias` 保持 override；顯示名優先序 `alias > batch_alias:{symbol} > symbol/timeframe/hash`。

## 驗證建議
- 後端：registry 同批兩個 symbol 設 batch alias 後皆回傳 `batch_id/batch_alias`；同一 symbol/timeframe 兩個不同 batch 可使用相同或不同 batch_alias 的決策需測清。
- 後端：per-run alias 仍維持既有唯一性；batch alias 不觸發 per-run alias conflict。
- Batch：completed checkpoint 中的 runs 可 backfill `batch_id`；新生成時 registry entry 直接帶 `batch_id`。
- 前端：Feature Explorer default selection key 不變；搜尋 batch alias 可找到所有同批 runs；per-run alias 覆蓋 batch label。

ASSUMPTIONS_VERIFIED: 已用 rg/sed/json.tool 驗證 registry alias、batch checkpoint、Feature Explorer selector、RunInfo 型別與實際 data_cache 樣本。
TESTS_RUN: 未跑測試；本任務為讀取型設計諮詢，只新增報告。
FAILURES_SEEN: none
SCOPE_CHANGES: none；未改 production code，未 commit。
NUMERIC_OR_SCHEMA_IMPACT: 本次無；建議方案未來會新增 metadata/API schema 欄位 `batch_id/batch_alias`，不影響數值輸出。
STATUS: DONE — 推薦 Phase 1 先做 run entry `batch_id+batch_alias` + batch alias endpoint，顯示 `alias > batch_alias:{symbol} > fallback`，保留 per-run alias 作 override。
