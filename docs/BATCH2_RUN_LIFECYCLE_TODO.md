# Batch2 Run 生命週期 TODO V5（DRAFT｜基於 SPEC V5｜2026-06-13）

> 追溯：manifest [B2-1]~[B2-10]；SPEC Task 0.1/0.2/0.3/1.1/2.1/2.2/2.3/3.1/4.1 共 **9 Task**。版本史：V3（deleting 標記/lease_sink/resume requeue/錨點勘誤）→V4（coordinator/resolver 三級）→**V5（鎖=fcntl.flock 終局，舊 lockdir/接管協定全廢）**。

## §0 全域規則與約束
- **刪除安全順序**：lstat 逐 component → resolve → is_relative_to 唯二根（data_cache/features/、data_cache/cgsa_work/）→ 只刪葉層；禁區：feature_klines/、kline_cache.h5、feature_preprocessing/、models/、patterns/、registry.json、.locks/。
- **一致性鐵律**：無 exclusive lease 不 rmtree；**set_alias 同樣先取 lease**；registry mutation 全走 `_locked_mutate`；corrupt → lifecycle fail-closed 且 add 禁落盤覆寫；lease=fcntl.flock（kernel 互斥，lock 檔永不 unlink，無任何接管協定）。
- 解耦：run_paths/run_locks/run_lifecycle 在 momentum/FeatureEngineering/（禁 import api）；factories 工廠；DTO 進 api/models/；`grep -r "from api\." momentum/` → 0。
- 不碰數值：禁改 config_hash 計算/特徵輸出/batch **checkpoint 寫入格式**；第 1 批回歸 bundle **78 passed 維持**。
- 防假綠：禁動既有斷言（唯一例外=browse ID 格式更新，逐條登記）；競態用 threading barrier 禁 sleep；前端 vitest render 禁 grep。
- 紀律：測試全 tmp_path；禁動真 data_cache、根 HANDOFF.md、templates/、docs/*SPEC|TODO|PLAN|MANIFEST|DECISION*；BLOCKED 即停。

## §B 批次執行策略（[B2-10]）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| P0 | 0.1→0.2→0.3 | 無 | identity/lock/registry 基礎 | 中 |
| P1 | 1.1 | P0 | lifecycle 核心 | 中 |
| P2 | 2.1→2.2→2.3 | P1 | lease 接線+API+resume | 大 |
| P3 | 3.1 | P2 | frontend+vitest | 中 |
| P4 | 4.1 | P0-P3 | 整合回歸 | 小 |

- 執行端**不負責 git commit**；每 Phase 完成記交接（檔案清單+測試輸出原文）。P4 總 Gate：兩 pytest 新檔全綠 + vitest 綠 + `npm run build` exit 0 + bundle 78 passed + tests/api 紅數 ≤ 基線 + grep gate。

## Phase 0 — 基礎設施

### Task 0.1 — run_paths.py [B2-1]
- SPEC ref：Task 0.1。
- 輸出：`validate_config_hash(token)`（`re.fullmatch(r"[A-Za-z0-9_.-]{1,64}")` 且非全 `.`→ValueError）；`features_run_dir(root,s,tf,h)`（feature_run_dir 委派，feature_storage.py:698-703）；`cgsa_work_dir(root,s,tf,h)`（逐行搬 feature_factory.py:903-912 default 分支）；**`safe_token(text)`**（=:903-905 的 `re.sub(r"[^A-Za-z0-9_.-]+","_",text)`，cgsa 與 lock 名共用）。feature_factory.py:903-912 改委派（byte 等價）。
- 不可做：禁改 sanitize；禁規則互換；禁 IO。
- 邊界：symbol 含 `/`；全 `.` hash → ValueError；64 上限。
- 驗證：`pytest tests/feature_engineering/test_run_lifecycle.py -k paths -q` 綠——`cfg_batch2d` 合法；`"../x"`/`".."`/`""`/65 字 → `pytest.raises(ValueError)`；3 組病態 (s,tf,h) 抽出前後路徑 ==。

### Task 0.2 — run_locks.py：fcntl.flock per-run lease [B2-2]（V5 終局，Codex r3/r4-N1）
- SPEC ref：Task 0.2（V5）。
- 輸出：
  ```python
  class RunBusyError(RuntimeError): ...
  class RunLease:
      @classmethod
      def acquire(cls, locks_dir, symbol, timeframe, config_hash, timeout: float = 0.0) -> "RunLease"
      def release(self) -> None   # LOCK_UN + close；二次呼叫冪等
  def is_run_active(locks_dir, symbol, timeframe, config_hash) -> bool  # try-flock 探測
  ```
- 實作要點：
  1. lock 檔=`locks_dir/{safe_token(s)}_{safe_token(tf)}_{config_hash}.lock`；`os.open(O_CREAT|O_RDWR)` → `fcntl.flock(fd, LOCK_EX|LOCK_NB)`；`BlockingIOError/OSError(EWOULDBLOCK)` → RunBusyError。
  2. 成功後 truncate 寫 `{"pid":...,"ts":iso}`（純診斷，不參與互斥）；**lock 檔永不 unlink**。
  3. kernel 於進程死亡自動釋放——**無 stale 判定/接管/graveyard 任何邏輯**。
  4. lease 物件可跨執行緒移交（fd 進程級）；release=LOCK_UN+close。
  5. `is_run_active`：open+try LOCK_EX|LOCK_NB → 成功則 LOCK_UN+close 回 False；EWOULDBLOCK 回 True。
- 不可做：禁 unlink lock 檔；禁 mkdir/O_EXCL 混搭協定；禁假設 NFS（本機磁碟前提記 §N）。
- 邊界：lock 檔殘留（前次進程亡）→ 直接 flock 成功；release 連呼 2 次第 2 次 no-op；同 hash 不同 (s,tf) 不互斥。
- 驗證：`pytest -k locks -q` 綠——同進程兩次獨立 open+acquire → 第 2 次 `pytest.raises(RunBusyError)`；**跨進程**：subprocess 持鎖 → 主進程 acquire RunBusyError；subprocess `kill -9` 後 ≤1s 主進程 acquire 成功（kernel 自動釋放）；release 後再取；8 執行緒競取恰 1 勝；is_run_active 回值與 acquire 行為一致（2 案例斷言）。

### Task 0.3 — Registry transaction [B2-3]
- SPEC ref：Task 0.3。
- 實作要點：
  1. `_locked_mutate(fn)`：`registry.json.lock` O_EXCL 自旋（10ms 起 ×2 退避上限 500ms，總 30s）逾時 raise **`RegistryLockTimeout`**；lock 內 `_load()` reload → fn → copy 現檔 `.bak` → atomic persist → unlink lock。
  2. `add` 走 _locked_mutate + merge-preserve（同 key 保留既有非空 `alias/size_bytes/created_at`）；**`self._corrupt` 時：不落盤**（in-memory append + `logger.error`），首次偵測 corrupt 即 copy 原檔 → `registry.json.corrupt-<ts>`。
  3. `set_alias(s,tf,h,alias)`（None/strip 空=除名；同 (s,tf) 重複→ValueError；不存在→KeyError；**entry `deleting:true` → raise RunBusyError**）；`remove(s,tf,h)->bool`；`get(...)->Optional[dict]`（無鎖讀，TOCTOU 由 lease+deleting 標記補，文檔化）；`mark_deleting(s,tf,h)->bool`/`clear_deleting(...)`（_locked_mutate 內）。
  4. `_load` 失敗 → `_corrupt=True`：set_alias/remove/mark_deleting → RegistryCorruptError。
- 不可做：list_all/find 簽名不變；corrupt 下禁 cleanup/禁空表覆寫；禁去 atomic rename。
- 邊界：lock 殘留→RegistryLockTimeout（非 RunBusyError）；alias=""；.bak 寫失敗 log 不阻斷。
- 驗證：`pytest -k registry -q` 綠——雙實例交錯 alias 不丟（==斷言）；rerun add 保 alias/created_at；corrupt：set_alias `pytest.raises(RegistryCorruptError)`、add 後 **registry.json bytes 不變** 且 corrupt-<ts> 副本存在；deleting entry → set_alias `pytest.raises(RunBusyError)`；.bak == 前版 bytes；殘留鎖 → `pytest.raises(RegistryLockTimeout)`。

## Phase 1 — lifecycle 核心

### Task 1.1 — run_lifecycle.py [B2-4][B2-5][B2-8]（Codex N2/Composer #5）
- SPEC ref：Task 1.1。
- 輸出：DeleteResult/CleanupReport（V2 欄位）+ RunLifecycleManager：
  - `_delete_run_locked(s,tf,h,lease)`：**不 acquire**；安全四步→features 葉→cgsa（env `FFACT_CGSA_WORK_DIR` 非空→skip `"work_dir_override"`；`{leaf}/manifest.json` 的 config_hash == full hash 才刪，缺→`"no_manifest"`、異→`"ownership_mismatch"`）→registry.remove。OSError→errors+entry 保留。
  - `delete_run(s,tf,h)`：validate→`RunLease.acquire(timeout=0)`→內核→finally release；冪等（皆無+registry 有→remove 回空 result）。
  - `auto_cleanup(s,tf,keep_latest=5)`：corrupt→raise；進程內 per-(s,tf) singleflight；候選=未命名 created_at 降序第 keep_latest+1 起；逐 run：acquire(busy→skipped_busy)→`registry.mark_deleting`（_locked_mutate 內 re-check alias 為空，否則 skip+clear）→`_delete_run_locked`→（entry 隨 remove 消失）；失敗→`clear_deleting`。
  - `set_run_alias(s,tf,h,alias)`（manager 級）：`RunLease.acquire(timeout=0)`（busy→RunBusyError）→registry.set_alias→release。
- factories：`create_run_lifecycle_manager(features_root=None,cgsa_root=None,locks_dir=None,registry=None)`。
- 不可做：白名單前禁刪 syscall；禁刪中間層/registry.json/.locks；corrupt 下禁 cleanup；禁碰 service 狀態。
- 邊界：cgsa 葉缺→cgsa_deleted=False 無 error；恰 5 no-op；全命名 no-op；deleting 殘留（崩潰）→下次 cleanup 重走（文檔化）。
- 驗證：`pytest -k "delete or cleanup" -q` 綠——V2 全案例（tmp 真樹/4 層 symlink/`"../x"`/ownership mismatch/override/monkeypatch rmtree PermissionError/7+2 清理/busy skip）+（V3）**barrier 卡 mark_deleting 後 rmtree 前**：另執行緒 `set_run_alias` → `pytest.raises(RunBusyError)` 且 run 照刪；alias 先成功（候選選定前）→ 該 run 倖存。

## Phase 2 — service/API

### Task 2.1 — lease_sink 接線 + browse ID 全鏈 [B2-5]（Codex N3/Composer #1/#2/#3）
- SPEC ref：Task 2.1。
- 實作要點：
  1. `feature_factory.py::generate_features`（:209；config_hash 確定 ~:236-243 處）與 **`run_ic_first_pipeline`**（~:1860；resolved_config_hash 確定處）：`RunLease.acquire(timeout=0)`（busy→RunBusyError）；**簽名加 `lease_sink: Optional[list] = None`**——成功且 sink is not None → 不 release、`lease_sink.append(lease)`；失敗/例外 → finally release。
  2. `feature_factory_service.py`（V4）：呼叫處傳 `sink=[]`；result 後啟動**單一 coordinator thread** `_run_warmups_then_release(lease, warmup_fns)`——內部啟動並 `join` 全部實際 warmup（現行兩條：`_start_cgsa_catalog_warmup` + `_start_data_quality_warmup`，service:1410-1474），全部結束後唯一一次 `lease.release()` → `auto_cleanup(s,tf,5)`（try/except）；個別 warmup 函式禁觸碰 lease；無 warmup 路徑 service 直接 release+cleanup；completed event 時點不變（docstring 記順序）。
  3. browse ID：pass2（:3861-3906）+ **`register_hdf5_for_browse`（:609）** + batch adapter（feature_factory_batch_adapters.py 呼叫處）→ `browse_{s}_{tf}_{full_config_hash}`；既有測試 `browse_BTCUSDT_12h` 式斷言更新逐條登記。
- 不可做：禁改 config_hash 計算；禁 release-後-reacquire；禁改 batch checkpoint 寫入格式；bundle 78 維持。
- 邊界：task 失敗 finally release；kill -9 → kernel 自動釋放 flock（0.2 V5）；IC-first 覆蓋；batch worker 不傳 sink 正常自管。
- 驗證：`pytest tests/api/test_run_lifecycle_api.py -k lease -q` 綠——生成持鎖 DELETE→409；同 hash 第二 generate → failed 含 "busy"；**warmup barrier 中 DELETE→409、warmup 畢 DELETE→200，全程 is_run_active(try-flock)==True（無空窗斷言）**；pass2 兩 hash 並存；register_hdf5_for_browse 回 ID 含 full hash。

### Task 2.2 — runs 端點 + reconciliation + completion 契約 [B2-6][B2-7][B2-8]（Composer #4/#7/#9/#12）
- SPEC ref：Task 2.2（契約全文見 SPEC [B2-6]）。
- 實作要點：
  1. DTO：RunInfo（含 `active:bool`）/AliasRequest/DeleteRunResponse；**path=既有 `GET /task/{task_id}`（route :252）**擴充：`get_task_status`（service:554-567）填 `retention_prompt`+`run_identity`（completed+persist 成功）+ FeatureTaskStatusResponse.result 填值。
  2. 新 3 端點 thin→service：list_runs（`active := is_run_active(triple)`；size 缺值 null；created_at：numeric epoch 秒→ISO UTC / ISO 字串 passthrough / 其他→null）；set_run_alias（經 manager lease 版本；RunBusyError→409、ValueError→422 `alias_conflict`、KeyError→404）；delete_run（RunBusyError→409 `run_busy`、404 `run_not_found`、errors 非空→500 `delete_partial` 禁 200、冪等語義對齊 SPEC [B2-6]：磁碟孤兒+registry 有→200 清 entry、**皆無→404 `run_not_found`**）。
  3. size 寫入：task 收尾執行緒 du features+cgsa 一次經 _locked_mutate 寫 entry。
  4. 刪除成功 reconciliation：清 in-memory tasks（result metadata 三元組 + browse full-hash ID 兩來源）+ `_invalidate_task_cache()`。
- 不可做：route 業務邏輯；service 互 import；list 同步全掃；partial 回 200。
- 邊界：registry 空→[]；alias strip 空=除名；同 (s,tf) 多 hash 刪一不影響另一。
- 驗證：`-k api -q` 綠——逐碼+code 字串（409"run_busy"/404/422"alias_conflict"/500"delete_partial"）；`GET /task/{id}` 含 run_identity 三欄；active true 時 DELETE 409、release 後 active false 且 DELETE 200；created_at float 樣本與 `cfg_batch2d` 樣本 → ISO regex match 或 null；刪後兩種 browse task 從 `/browse/available` 消失；auto_cleanup 異常注入 task_status=="completed"；WS 與 polling 同 fixture payload 同欄位斷言。

### Task 2.3 — batch resume completed artifact 驗證 [B2-9]（Codex N4）
- SPEC ref：Task 2.3。
- 實作要點（V4 resolver 三級凍結；completed item 無 run hash——batch_service:519-526 僅 symbol/timeframe/output_paths/browse_task_id/metrics）：
  1. `_resolve_completed_run_hash(item)`：① output_paths 內 match `{features_root}/{s}/{tf}/{hash}/` → 取 path segment hash；② browse_task_id match `browse_{s}_{tf}_{full_hash}` 新格式 → 取 hash；③ 皆否（legacy）→ None。
  2. `resume_batch`（:174-189 一帶）載入後：hash 定位成功 → 驗 features manifest（既有 resolve helper），缺→移回 queued+log；**None → 不重分類、保留 completed + `logger.warning`（禁猜測）**。
  3. checkpoint 寫入格式不變。
- 不可做：禁改 checkpoint 格式；禁對 legacy 猜 hash；禁動 batch 其他流程。
- 邊界：manifest 空檔=缺（沿 helper 語義）；checkpoint 缺欄容錯沿既有。
- 驗證：`-k resume -q` 綠——三分支：①output_paths 含 hash + 刪 run → requeue 且重生成觸發（mock assert_called）；②僅新格式 browse_task_id → 同上；③legacy（`{s}_{tf}_factory.h5` 式路徑）→ 不 requeue + caplog warning；未刪 item 不重跑；全 completed 有效 → 直接 completed（既有斷言保留）。

## Phase 3 — frontend

### Task 3.1 — types/store/dialog/panel + vitest [B2-7]
- SPEC ref：Task 3.1。
- 實作要點：types.ts（RunInfo/DeleteRunResponse；FeatureTask 加 `retention_prompt?`/`run_identity?`，對齊 **`GET /task/{task_id}`** 真實形狀）；store（runs 三態+actions+completionQueue 兩路 push）；`GenerationProgress.tsx:48-74 applyPayload` 擴充+polling 路徑；RunRetentionDialog（queue 驅動三選，關閉=保留未命名）；RunManagerPanel（三態、alias 行內、刪除 confirm 含 total_bytes+cgsa 說明、active 禁刪、409/delete_partial 顯示）；vitest 檔循既有測試慣例。
- 不可做：繞 store；新 UI 依賴；grep 假驗收；改既有面板行為。
- 邊界：queue 連續 2 筆依序；422 行內錯誤不關 dialog；WS 斷線僅 polling 仍開 dialog。
- 驗證：`cd frontend && npm run test -- run_lifecycle` 綠——dialog WS 路+polling 路（與後端同 fixture payload）；loading/empty/error+retry render（`expect(screen.getByText(...))`）；409 → busy 顯示且列表項保留；delete_partial → errors 顯示；`npm run build` exit 0。

## Phase 4 — 整合驗收

### Task 4.1 — 端到端 + 回歸 [B2-9]
- 實作要點：執行前記 `pytest tests/api/ -q --tb=no | tail -1` 基線紅數；resume requeue 端到端；curl smoke 序列入交接。
- 不可做：動既有紅測試；調 bundle 範圍。
- 邊界：基線紅數浮動重跑取穩定值。
- 驗證：兩 pytest 新檔全綠 + vitest 綠 + `npm run build` exit 0 + 第 1 批 bundle **78 passed** + tests/api 紅數 ≤ 基線 + `grep -r "from api\." momentum/` → 0。

## 派工 Prompt（[B2-10]）
> 前置：repo 根、main、venv、frontend 可 build。讀 SPEC V5 + 本 TODO。
> P0→P1→P2→P3→P4；不負責 git commit；每 Phase 記 `handoffs/20260613-batch2-run-lifecycle.md`（檔案清單+測試輸出原文+browse 斷言更新清單+tests/api 基線數+size 寫入函式名）。
> 競態一律 barrier；測試禁碰真 data_cache。禁：§0 全部；BLOCKED 即停。

## 階段 3 自檢（0 FAIL）
1. 追溯：[B2-1]→0.1；[B2-2]→0.2/2.1；[B2-3]→0.3；[B2-4]→1.1/2.2；[B2-5]→1.1/2.1；[B2-6]→2.2；[B2-7]→2.2/3.1；[B2-8]→1.1/2.2；[B2-9]→0.2/1.1/2.3/4.1/§V；[B2-10]→§B。10/10 ✓
2. 深度：9 Task 均 ≥3 要點+函式級+≥2 邊界+可證偽驗證 ✓
3. 語義：lease 介面（lease_sink/caller-holds）跨 Task 0.2/1.1/2.1 一致；deleting 標記由 0.3 提供、1.1 使用；browse full-hash 由 2.1 遷移、2.2 reconcile 依賴 ✓
4. 全棧跨層：後端→API→前端→整合鏈完整 ✓
5. 錨點：§0/§B/9 Task 驗證·邊界·不可做 ✓
