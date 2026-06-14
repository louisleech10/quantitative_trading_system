# Batch2 Run 生命週期 UX — SPEC V5

> V3→V4（Codex r3）：warmup coordinator 唯一 release；resume resolver 三級。V4→V5（Codex r4-N1 終局）：**鎖機制改 fcntl.flock**——kernel 互斥+進程死亡自動釋放，自製 stale/接管協定（V3 rename/V4 mutex，均存在 successor-race）整段廢除。Composer 已 PASS V3；V4/V5 為 Codex-finding 範圍定點修正。

> V2→V3：Codex r2（`...codex-r2.md`：N1-N4 BLOCKING+7 PARTIAL，FAIL）+ Composer 獨立輪（`...composer.md`：3 BLOCKING/12 MAJOR，FAIL）合併收斂。
> 日期：2026-06-13　|　manifest：`docs/BATCH2_RUN_LIFECYCLE_MANIFEST.md` V3　|　TODO：V3　|　DECISION：`docs/BATCH2_RUN_LIFECYCLE_DECISION.md`（V3 增補）。

## §RISK 風險分級 [B2-10]
- **大**；命中 (b)（factories/registry/factory 入口/API/WS/前端）+(c)（5 Phase+不可逆刪除）。(a)(d) 不命中（lease 僅互斥，禁改計算語義；回歸 bundle 78 passed 維持）。
- 流程：本 V3 經雙家族確認 PASS → Codex 實作 + Composer code review。

## §A 假設與待使用者確認
- **使用者產品決策（兩輪 AskUserQuestion，2026-06-13 已確認共 6 項）**：保留最近 5 個未命名（per symbol+timeframe 各 5）；跑完提示+列表管理；命名永不自動清；刪除=features+對應 cgsa_work（絕不碰 feature_klines/kline_cache.h5/feature_preprocessing）；並發刪除=409。
- **已驗證事實**（Claude 實測+Codex/Composer 各自 rg/sed/nl 覆核；V3 勘誤已修）：
  - V2 既有 10 項（run 目錄/registry 無鎖 upsert/非 hex hash/cgsa override/單筆 task 無三元組/batch 獨立 service/warmup 背景執行緒/pass2 無 hash/resume manifest gate/vitest 存在）——見 manifest 與 r1/r2 報告，不重抄。
  - **V3 勘誤（Composer B1/M4）**：lease 第二掛點真實函式=**`run_ic_first_pipeline`**（feature_factory.py ~:1860；V2 寫 `generate_and_persist(:1890)` 為虛構名）；task status route=**`GET /task/{task_id}`**（api/routes/feature_factory.py:252）；瀏覽註冊第二路徑=**`register_hdf5_for_browse`**（feature_factory_service.py:609 `browse_{s}_{tf}` 無 hash，batch adapter 呼叫）；`get_task_status`=service:554-567 現不回 result。
  - **Codex r2 控制流核實**：batch `resume_batch` 在 queued==0 直接 completed（batch_service:174-189），completed item 不過 factory manifest gate（N4）；warmup 為 result 返回後 daemon thread（service:259-271），factory 方法內 lease 無法自然延伸（N3）。
- **待使用者確認：無**。
- **已確認結果**：兩輪產品決策（2026-06-13）；分級升大為規則強制。

## §C 約束
- **刪除安全順序**（lstat 逐 component→resolve→is_relative_to 唯二根→葉層）與白名單禁區（feature_klines/kline_cache.h5/feature_preprocessing/models/patterns/registry.json/.locks）不變。
- **一致性鐵律（V3 強化）**：無 exclusive lease 不 rmtree；alias 變更同樣需 lease；registry mutation 全走 `_locked_mutate`；corrupt → lifecycle fail-closed 且 **add 禁止落盤覆寫**。
- 解耦/不碰數值/前端 vitest 同 V2。

## §G Golden / Baseline
- N/A — 移 §N（不碰數值；一致性 baseline=§V 競態測試）。

## §P Phase 與依賴 [B2-9]
> P0→P1→P2→P3→P4，各自獨立 commit。

### Phase 0 — 基礎設施
**Task 0.1 — run_paths.py [B2-1]**
- 同 V2 + 新增 `safe_token(text)->str`（=feature_factory.py:903-905 的 re.sub 規則，cgsa 與 lock 名共用）；pass2/browse stable_id 規格改**完整 hash**。
- 驗證：`pytest tests/feature_engineering/test_run_lifecycle.py -k paths -q` 綠——`cfg_batch2d` 合法；`../x`/`..`/空/65字 → ValueError；3 組病態 (s,tf,h) 抽出前後 cgsa 路徑字串 ==。
- 邊界：symbol 含 `/`；hash 8 字短值。不可做：禁改 sanitize 規則；禁 features/cgsa 規則互換。

**Task 0.2 — run_locks.py：fcntl.flock per-run lease [B2-2]（V5 重設計，Codex r3/r4-N1 終局解）**
- **設計轉向**：放棄自製 stale/接管協定（V3 rename、V4 mutex 均被 Codex 證明存在 successor-race / 無 base case）。改用 **`fcntl.flock(LOCK_EX|LOCK_NB)`**：kernel 保證互斥、**進程死亡自動釋放**——stale 鎖問題在物理上不存在，無接管/graveyard/age 門檻。
- `RunLease.acquire(locks_dir,s,tf,h,timeout=0)`：open(lock 檔 `{safe_token(s)}_{safe_token(tf)}_{h}.lock`, O_CREAT|O_RDWR) → `fcntl.flock(fd, LOCK_EX|LOCK_NB)`；EWOULDBLOCK→RunBusyError；成功後 truncate 寫 `{pid,ts}`（純診斷資訊，不參與互斥）。lock 檔**永不刪除**（避免 unlink/open 競態經典漏洞），數量=run 數量級可接受。
- `release()`：`flock(fd, LOCK_UN)` + close；二次呼叫冪等。lease 物件可跨執行緒移交（fd 為進程級資源，coordinator thread release 合法）。
- `is_run_active(...)`：open + try `LOCK_EX|LOCK_NB`：取到→立即 LOCK_UN+close 回 False；EWOULDBLOCK→True。
- **前提假設（記 §N）**：data_cache 在本機磁碟（macOS/Linux 本地 flock 語義可靠）；若未來搬 NFS 須重新評估。
- 驗證：`pytest -k locks -q` 綠——同進程兩個獨立 open+flock → 第二個 `pytest.raises(RunBusyError)`（macOS flock 以 open file description 為單位）；**跨進程**：subprocess 持鎖期間主進程 acquire → RunBusyError；subprocess `kill -9` 後 ≤1s 內主進程 acquire 成功（**kernel 自動釋放,取代全部 stale 測試**）；release 後再取；8 執行緒競取恰 1 勝；is_run_active 與 acquire 結果一致。
- 邊界：lock 檔已存在（前次殘留）→ 直接 flock 正常；release 連呼 2 次第 2 次 no-op。
- 不可做：禁 unlink lock 檔（unlink/open 競態）；禁混用 O_EXCL/mkdir 協定；禁假設 NFS 可用。

**Task 0.3 — Registry transaction [B2-3]**
- 同 V2 merge-preserve/set_alias/remove/get + V3 變更：(1) 自旋=10ms 起指數退避 ×2 上限 500ms、總 30s，逾時 raise **`RegistryLockTimeout`**（與 RunBusyError 區分，Composer #10）；(2) **corrupt 時 `add` 不落盤**：in-memory append + `logger.error`，且首次偵測 corrupt 即 copy `registry.json` → `registry.json.corrupt-<ts>`（人工救援），禁空表覆寫；(3) entry 支援 `deleting:bool` 標記（[B2-4] 用）；set_alias 對 `deleting:true` entry → raise RunBusyError。
- 驗證：`pytest -k registry -q` 綠——雙實例 alias 不丟；rerun add 保 alias/created_at；corrupt → set_alias raise RegistryCorruptError、add 不 raise 且 **registry.json 檔 bytes 不變**+corrupt 副本存在；deleting entry set_alias → `pytest.raises(RunBusyError)`；.bak == 前版；模擬鎖殘留 → RegistryLockTimeout 非 RunBusyError。
- 邊界：lock 自旋逾時；alias="" 同 None。不可做：list_all/find 簽名不變；corrupt 下禁 cleanup。

### Phase 1 — lifecycle 核心
**Task 1.1 — run_lifecycle.py [B2-4][B2-5][B2-8]（Codex N2/Composer #5 重設計）**
- 內核 `_delete_run_locked(s,tf,h,lease)`（不 acquire，斷言 lease 有效）：安全四步→features 葉→cgsa（override env→skip `"work_dir_override"`；manifest hash 核對 mismatch/缺→skip）→registry remove。OSError→errors、entry 保留。
- `delete_run(s,tf,h)`：validate→acquire(timeout=0)→`_delete_run_locked`→release。冪等同 V2。
- `auto_cleanup(s,tf,keep_latest=5)`：corrupt→raise；singleflight；候選=未命名第 6 起；逐 run：acquire(busy→skipped_busy)→**`_locked_mutate` 內 re-check alias 為空且標記 `deleting:true`**→`_delete_run_locked`→（內含 remove，deleting 標記隨 entry 移除）；失敗回滾 deleting 標記。
- `set_alias` 路徑（service 層呼叫 registry 前）：**先 acquire run lease(timeout=0)**，busy→上拋 RunBusyError（API 409）——alias 與刪除由 lease 完全互斥。
- 驗證：`pytest -k "delete or cleanup" -q` 綠——V2 全部案例 +（V3 新）**barrier 卡在 re-check 標記後、rmtree 前**：另執行緒 set_alias → `pytest.raises(RunBusyError)`（deleting 標記+lease 雙防）且 run 照刪；cleanup 中 lease busy run → skipped_busy；ownership/override/PermissionError/4 層 symlink 同 V2。
- 邊界：恰 5 個 no-op；全命名 no-op；deleting 標記殘留（程序崩潰）→ 下次 cleanup 視為候選重走（標記非永久鎖,文檔化）。
- 不可做：白名單前禁刪除 syscall；禁 unlink lock 檔（V5）；禁 corrupt 下 cleanup；禁本層碰 service 狀態。

### Phase 2 — service/API
**Task 2.1 — lease 接線（lease_sink 介面凍結）+ browse ID 全鏈遷移 [B2-5]（Codex N3/Composer #2/#3）**
- `feature_factory.py`：`generate_features`（:209，config_hash 確定 ~:236-243）與 `run_ic_first_pipeline`（~:1860，resolved_config_hash 確定處）acquire(timeout=0)；**新參數 `lease_sink: Optional[list] = None`**：成功且 sink is not None → 不 release、`sink.append(lease)`；任何失敗/例外 → finally release。busy → raise RunBusyError（同 config 並發生成被拒，DECISION #16）。
- `feature_factory_service.py`（V4，Codex r3-N3：現行有**兩條**並行 warmup——`_start_cgsa_catalog_warmup` 與 `_start_data_quality_warmup`，service:1410-1474）：**單一 coordinator thread** `_run_warmups_then_release(lease, warmup_fns)`——啟動/join 全部實際要跑的 warmup thread，全部結束後**唯一一次** `lease.release()` → `auto_cleanup(s,tf,5)` try/except；個別 warmup 禁觸碰 lease。completed event 時點不變（docstring 記順序）。無 warmup 路徑 → service 直接 release+cleanup。
- browse ID 全鏈（Composer #3）：pass2（:3861-3906）與 **`register_hdf5_for_browse`（:609）** 與 batch adapter 一律 `browse_{s}_{tf}_{full_config_hash}`；既有測試 `browse_BTCUSDT_12h` 斷言更新逐條登記；刪除 reconciliation 按 full hash 清兩種來源 task。
- 驗證：`pytest tests/api/test_run_lifecycle_api.py -k lease -q` 綠——生成持鎖 DELETE→409；同 hash 第二 generate → failed 含 "busy"；**warmup barrier 期間 DELETE→409 且 warmup 結束後 DELETE→200**（無 release/reacquire 空窗：barrier 全程斷言 `is_run_active`==True，即 flock 連續持有）；pass2 兩 hash 並存；`register_hdf5_for_browse` 回 ID 含 full hash；batch worker（不傳 sink）正常 release。
- 邊界：task 失敗 finally release；kill -9 → kernel 自動釋放 flock（V5）；IC-first 路徑同樣覆蓋。
- 不可做：禁改 config_hash 計算/batch checkpoint 格式；禁 release-後-reacquire 模式；回歸 bundle 78 維持。

**Task 2.2 — runs 端點 + reconciliation + completion 契約落地 [B2-6][B2-7][B2-8]（Composer #4/#7/#9/#12）**
- 同 V2 契約 + V3 修正：path=`GET /task/{task_id}`（:252）；`get_task_status`（:554-567）擴充填 `retention_prompt`+`run_identity`（completed 且 persist 成功）+ FeatureTaskStatusResponse.result 填值；`RunInfo.active := is_run_active(triple)`（**try-flock 探測**，檔案存在不代表活性），list 與 DELETE 409 一致性測試；created_at 轉換規則：numeric epoch 秒→ISO UTC、ISO 字串 passthrough、其他→null（float 與 `cfg_batch2d` 樣本測試）；alias 端點 service 先 acquire lease（Task 1.1 規則）。
- 刪除 reconciliation：lifecycle 成功後清 in-memory tasks（result metadata 三元組+browse full-hash ID 兩來源）+`_invalidate_task_cache()`；batch `_tasks`/checkpoint 可見性=**out-of-scope 已知限制**（§N，Composer #8——resume 端由 Task 2.3 收斂）。
- 驗證：`-k api -q` 綠——逐碼+code 字串；`GET /task/{id}` 含 run_identity；active==true 時 DELETE 409、release 後 active==false 且 DELETE 200（一致性）；created_at 兩樣本斷言 ISO 格式 regex；刪後兩種 browse task 皆消失；auto_cleanup 異常不改 task_status；WS 與 polling 用**同一 fixture payload** 斷言同欄位。
- 邊界/不可做：同 V2 + 禁回 release/reacquire。

**Task 2.3 — batch resume 驗證 completed artifact（Codex N4；V4 凍結 run 定位 resolver）[B2-9]**
- 前提事實（Codex r3 核實）：completed item 僅有 symbol/timeframe/output_paths/browse_task_id/metrics（batch_service:519-526），**無 run config_hash**；top-level config_hash 是 request override 16 字 hash 非 run identity。
- **run 定位 resolver（優先序凍結，V4）**：① `output_paths` 中含 `{features_root}/{s}/{tf}/{hash}/` 形式者 → 從路徑 segment 取 hash；② 否則 `browse_task_id` 為新格式 `browse_{s}_{tf}_{full_hash}` → 取 hash；③ 都不行（legacy 路徑如 `{s}_{tf}_factory.h5`）→ **不重分類、保留 completed + logger.warning**（保守：禁猜測,legacy checkpoint 不支援刪除後自動重生成,記 §N 已知限制）。
- 定位成功者驗 features manifest 存在（既有 resolve helper 語義）；缺 → 移回 queued + log；checkpoint **寫入格式不變**。
- 驗證：`-k resume -q` 綠——三分支各一測：①路徑含 hash 的 completed+刪 run → requeue 且重生成被觸發（mock assert_called）；②僅 browse_task_id 新格式 → 同上；③legacy → 不 requeue + caplog warning；未刪 item 不重跑；全 completed 有效 → 直接 completed（既有行為斷言）。
- 邊界：manifest 空檔=缺；checkpoint 缺欄容錯沿既有。
- 不可做：禁改 checkpoint 寫入格式；禁對 legacy 猜 hash；禁動 batch 其他流程。

### Phase 3 — frontend
**Task 3.1 — types/store/dialog/panel + vitest [B2-7]**
- 同 V2 + 依 Task 2.2 落地後的真實契約（`GET /task/{task_id}` 形狀）對齊 types.ts；兩路測試用與後端相同 fixture payload（Composer #13）。
- 驗證：`cd frontend && npm run test -- run_lifecycle` 綠（dialog WS+polling 兩路/三態 render/409 保留項/delete_partial errors）；`npm run build` exit 0。
- 邊界/不可做：同 V2。

### Phase 4 — 整合驗收
**Task 4.1 — 端到端 + 回歸**
- 同 V2 +（V3）resume requeue 端到端納入；交接記 tests/api 基線紅數、pass2/browse 斷言更新清單、curl smoke。
- 驗證：兩 pytest 新檔全綠 + vitest 綠 + `npm run build` exit 0 + 第 1 批 bundle 78 passed + tests/api 紅數 ≤ 基線 + `grep -r "from api\." momentum/` → 0。

## §V 驗證策略與邊界測試目錄 [B2-9]
- 一致性核心（V5）：跨進程 flock 互斥 + kill -9 自動釋放（取代全部 stale/接管測試）；alias 卡 re-check 後（deleting 標記+lease 雙防）；warmup coordinator 全程持鎖（flock 連續持有斷言）；resume requeue 真 checkpoint 三分支。
- 其餘層級/防假綠/真實路徑/邊界目錄同 V2（雙實例、4 層 symlink、PermissionError monkeypatch、corrupt fail-closed、override、非 hex hash、WS/polling 等價、kill -9 自動釋放）。
- 競態一律 threading barrier 禁 sleep；唯一允許的既有斷言更新=browse ID 格式（逐條登記）。

## §R 回退
- P0-P4 各自 commit；lease_sink 為新增選填參數（預設 None=現行為，向後相容）；resume 驗證為載入時重分類（checkpoint 格式不變）；前端新增組件。

## §N N/A 登記與已知限制
- §G Golden：N/A — 不碰數值；一致性 baseline=§V 競態 pytest。
- 多 symbol OOM/tier：N/A。
- **已知限制（評審後接受）**：symlink parent-swap TOCTOU（內部進程皆守 lease，無不可信本地行為者威脅模型，Composer #14）；factory 內 registry 實例記憶體陳舊（磁碟一致由 _locked_mutate reload 保證；factory 僅 add，Composer #11）；batch `_tasks` 面板可見性不隨刪除即時更新（resume 正確性由 Task 2.3 保證，Composer #8）；cleanup `deleting` 標記於崩潰後殘留 → 下次 cleanup 重走（非永久鎖）；**flock 前提=data_cache 在本機磁碟**（NFS 須重評，V5）；legacy batch checkpoint（無法定位 run hash）刪除後 resume 不自動重生成，僅 warning（V4，Task 2.3 ③）。
