# Batch2 Run Lifecycle SPEC/TODO Adversarial Review

- Reviewer: Codex (adversarial, V13)
- Date: 2026-06-13
- Inputs: `docs/BATCH2_RUN_LIFECYCLE_SPEC.md` V1, `docs/BATCH2_RUN_LIFECYCLE_TODO.md`
- Focus: deletion boundary, concurrency, idempotency/registry consistency, API contract, frontend states
- Strictness: MAXIMUM

## Verdict: 有根本缺陷需修補後重審

目前不可派工。文件把不可逆刪除建在「單一 service 記憶體 active task + 多個獨立 FeatureRegistry 實例 + 路徑先 resolve 再查 symlink」上；真實程式另有 batch/resume、背景 warmup、task restore pass2、CGSA root override。這些路徑未被同一把 run lease/registry transaction 保護，足以造成刪除正在生成的 run、alias 遺失、registry lost update、刪後留下可瀏覽的 stale task。

## §0 挑戰前提與已核實事實

親自核實命令：`rg`/`sed`/`nl` 對照 `feature_registry.py`、`feature_factory.py:890-986`、`feature_storage.py:698-703,1390-1394`、`feature_factory_service.py:149-278,577-643,3698-3730,3811-3910`、`feature_factory_batch_service.py:124-265,728-930,1001-1034`、前端 store/types/WS consumer；另唯讀抽查 registry/cgsa_work 與 `du`。

- Fact verified: `FeatureRegistry` 現只有 `add/list_all/find/find_latest`；`add` 以整筆 entry 取代舊 entry，`_persist()` 僅 temp+rename，沒有 thread/process/file lock，也不會寫前 reload。證據：`feature_registry.py:47-99`。
- Fact verified: `FeatureFactory` 自己持有一個 `FeatureRegistry()`，factory/library 也可再建其他實例。證據：`feature_factory.py:194`、`factories.py:280-290,648-652`。規格新增 lifecycle manager 後會再出現一個長壽 registry snapshot。
- Fact verified: 三個生成完成分支呼叫 `_registry.add({...})` 時都不帶 alias/size，整筆 upsert 會清掉既有 metadata。證據：`feature_factory.py:3103-3113,3248-3258,3380-3390`。
- Fact verified: 預設 CGSA 名稱為 `{sanitized_symbol}_{sanitized_tf}_{hash[:8]}`，但 `FFACT_CGSA_WORK_DIR` 存在時完全改用 override 目錄。證據：`feature_factory.py:899-912`。
- Fact verified: features path segment 是 reject `/`, `\\`, `.`, `..`，不是 CGSA 的 `re.sub` normalization。證據：`feature_storage.py:698-703,1390-1394`。
- Fact verified: 單筆 task 建立時只有 task_id/status，尚無 symbol/tf/config_hash；三元組只會在完成 result metadata 出現。證據：`feature_factory_service.py:153-169,206-249`。
- Fact verified: batch/resume 使用獨立 `FeatureFactoryBatchService._tasks` 與 checkpoint，並在 worker 建立另一個 FeatureFactory。證據：`feature_factory_batch_service.py:124-209,728-769,1001-1034`。
- Fact verified: task 完成後會啟動 CGSA catalog/data-quality/stats background warmup，之後才送 completed event。證據：`feature_factory_service.py:251-278`。
- Fact verified: restore pass2 對沒有 task_record 的 manifest 建立 `browse_{symbol}_{timeframe}`，省略 config_hash；同組多 run 只保留掃描遇到的第一個 stable_id。證據：`feature_factory_service.py:3861-3906`。
- Fact verified: 前端 `GenerationProgress.applyPayload` 只消費 stage/progress/message/status，現在會丟掉 retention_prompt 與 run 三元組。證據：`GenerationProgress.tsx:48-74`。
- Fact verified: 實際 registry 是 list[dict] 且 `created_at` 為 epoch seconds；現存 `config_hash` 不全是 32-char hex（例如 `cfg_batch2d`）。實際 `du` 為 features 8.3G、cgsa_work 51M。

## Findings

### 前提 / 風險分級

1. **[BLOCKING][High] 任務被錯分為不命中 (b)(c)，低估不可逆跨層一致性風險。**
   - 證據：SPEC §RISK:7 稱「(a)(b)(c)(d) 不命中」；同文件卻要求改 `factories.py`、共享 registry、API、WebSocket、frontend，並執行不可逆雙樹刪除。
   - 失敗：按中型粒度派工會把 registry transaction、batch/resume lease、task restore reconciliation 分散到 P1/P2，沒有共同原子性設計。
   - 修法：至少按命中 (b)(c) 的高風險流程重分級；先凍結 run identity/ownership/lease/registry transaction，再展開 TODO。

### 1. 矛盾 / 互斥

2. **[BLOCKING][High] registry「add 行為不變」與 alias 永久保留互相矛盾。**
   - 證據：SPEC Task 1.1:43「既有 add/find 行為不變」；產品決策 §A:15「已命名 run 永不自動清理」。真實 `add` 在同 key 時整筆替換；生成 caller 不傳 alias/size。
   - 失敗：同 config rerun/cache regeneration 後 alias 消失，run 立刻重新成為 auto-cleanup 候選；size 也回退為 unknown。
   - 修法：明定 upsert 為 merge-preserve lifecycle metadata，或把 lifecycle metadata 放獨立 keyed store；新增「先 alias，再同 key add，alias/size/created_at 語義保持」回歸測試。

3. **[MAJOR][High] features 與 CGSA 的 segment 規則被 TODO 誤寫為可共用同一 safe_*。**
   - 證據：TODO Task 1.2:53 要「沿用 feature_storage `_safe_path_segment`/factory 的 re.sub 規則」；前者拒絕非法 segment，後者會替換為 `_`。
   - 失敗：同一 API identity 可能算出不同 features/cgsa 路徑；兩個原值也可能 normalize 到同一 CGSA 名稱。
   - 修法：分別使用 canonical producer 的 exact resolver，禁止模糊「二選一」；對 normalization collision 加拒絕測試。

4. **[MAJOR][High] SPEC 宣稱 resume/checkpoint N/A，但刪除會直接改變 restore/resume 可見狀態。**
   - 證據：SPEC §N:88「resume/checkpoint: N/A」；同 SPEC §A:21 已承認 task_record/pass2；CGSA resume gate 依賴 features manifest（`feature_factory.py:923-960`）。
   - 失敗：刪 run 後 batch checkpoint 仍可宣稱 completed/resumable；task restore 與 browse task 仍指向已刪資產。
   - 修法：把 checkpoint/task restore reconciliation 納入 scope 與驗收，不得列 N/A。

### 2. 漏項 / 端到端

5. **[BLOCKING][High] active-task gate 只覆蓋單筆 service，漏掉 batch、resume、背景 warmup，且單筆 running task 當下沒有 config_hash 可比。**
   - 證據：SPEC §C:32、Task 2.1:59 只說「service 內存 task 狀態」；真實單筆 task 初始資料無三元組，batch 有獨立 `_tasks`/checkpoint/worker factory，完成後還啟動背景讀檔 warmup。
   - 失敗：DELETE/auto-cleanup 可在 batch worker 寫 parquet/manifest、resume 讀 CGSA shard、或 warmup 掃檔時 rmtree；409 測試仍會假綠，因只 mock 單一 `_tasks`。
   - 修法：建立所有 producer/consumer 共用的 per-run lease（single、batch、resume、warmup、browse/export），delete 取得 exclusive lease 後再重查；run identity 必在工作開始前可取得並持久化。新增真實競態測試：delete vs single write、batch write、resume、warmup。

6. **[BLOCKING][High] alias、manual delete、auto-cleanup、generation add 未在同一 transaction/lock domain。**
   - 證據：SPEC 只要求 cleanup-cleanup singleflight；TODO Task 1.1:32 沿用無鎖 `_persist()`；現有多個 FeatureRegistry 實例各自持有 `_entries` snapshot。
   - 失敗：A 實例 set_alias 後，B 實例用舊 snapshot remove/add 並 atomic rename，alias 或整個新 entry lost update；cleanup 選候選後，使用者剛命名仍會被刪。
   - 修法：所有 mutation 使用同一 registry transaction（process lock + cross-process file lock + lock 內 reload/validate/write）；cleanup 在 exclusive run lock 內重新確認 alias 與 generation lease。測試兩實例交錯 add/set_alias/remove 與 alias-vs-cleanup barrier。

7. **[BLOCKING][High] 刪除只移除磁碟與 registry，未清除 task_record 對應的 in-memory task/caches/pass2 browse task。**
   - 證據：SPEC Task 1.2:50 只列兩目錄+registry；restore pass2 建 `browse_{symbol}_{timeframe}` 且 metadata 不含 hash；service 有多個 per-task cache，現有 `_invalidate_task_cache()` 但 TODO 未要求使用。
   - 失敗：刪後 `/browse/available` 仍列出 completed task，browse/export 指向不存在檔；stable browse task 無 hash，可能錯刪/錯清另一 run；重啟前後 API 結果不一致。
   - 修法：定義 run-to-task index（含 config_hash），刪除 commit 後移除所有指向該 run 的 task/caches；pass2 ID 必能區分 hash 或明確選 latest 並可重建。新增「pass1 task_record」「pass2 無 task_record」「多 hash 同 s/tf」刪除測試。

8. **[MAJOR][High] `FFACT_CGSA_WORK_DIR` 使 §A 的 CGSA 對應事實只在無 override 時成立。**
   - 證據：SPEC §A:20 把預設路徑寫成一般事實；真實 code `feature_factory.py:899-902` 優先採任意 override 目錄。
   - 失敗：API 顯示「含 cgsa_work」但實際未刪 override 資產；若 lifecycle 擅自跟隨任意 override，又違反唯二白名單根。
   - 修法：明定 override 模式政策：只管理 canonical root，或把經核准的 root 注入同一 storage descriptor；非白名單 override 必 fail closed 並回報未刪，不可靜默成功。

### 3. 不可測驗收

9. **[MAJOR][High] 競態驗收全是靜態/mocked active 409，沒有可證偽 interleaving。**
   - 證據：SPEC §V:80 把「並發」等同 active task 409；TODO API test:73 僅 mock active 與 auto_cleanup call。
   - 失敗：最危險的 check-then-delete、alias-after-candidate-selection、writer-after-delete 均不會被測到。
   - 修法：以 Event/barrier 控制真實 filesystem writer 與 delete interleaving，斷言 delete 阻塞/409、檔案不部分消失、registry 最終單一一致狀態。

10. **[MAJOR][High] 前端三態驗收是 grep/build 假 gate。**
   - 證據：TODO Task 3.1:89 只要求 `grep "isLoading|error"`；無 render test、mutation failure test、dialog payload test。
   - 失敗：變數存在但 UI 不 render、error 無 retry、delete 失敗卻從列表移除仍可過 build/grep。
   - 修法：加 component/store tests，逐一驗 loading、empty、error+retry、success、delete pending、409、partial delete/error；completed WS payload 必真的開 dialog。

### 4. 可疑 quant 假設

- 無數值公式、leakage、NaN/inf gate 變更。風險是刪除正在生成的真實 artifact，已由 Findings 5-7 覆蓋。

### 5. 過度工程

- 無。lifecycle manager 本身合理；但在缺少共享 lease/transaction 時先做 UI 會形成錯誤抽象，應先補一致性模型。

### 6. OOM / 並行

11. **[MINOR][Medium] list 時逐 run 計算 du 的成本與一致性未定義。**
   - 證據：TODO Task 2.1:67 要 size 缺值現算並回寫，只說 thread executor；現有 features 8.3G。
   - 失敗：首次 GET 可能長時間掃描，掃描同時生成/刪除得到 stale size；多請求可重複掃描。
   - 修法：限制單次 scan concurrency、標記 `size_exact/as_of` 或接受 approximate；size 應明定是否為 features+CGSA 合計。

### 7. Cache / Registry 正確性

12. **[MAJOR][High] registry 損壞「starting fresh」與自動清理組合是 fail-open。**
   - 證據：SPEC Task 1.1:45 要保持損壞後空 registry；auto_cleanup 完全以 registry entries 決定保留集合。
   - 失敗：損壞後列表為空，磁碟孤兒永不管理；若後續用磁碟 fallback 補掃又可能把 alias 全視為未命名而誤刪。
   - 修法：lifecycle mutation 遇 registry parse/corruption 必 fail closed；提供顯式 reconciliation/backup，不可在「starting fresh」狀態自動清理。

13. **[MAJOR][Medium] 8-char CGSA ownership collision 未處理。**
   - 證據：SPEC/TODO 以 `config_hash[:8]` 直接映射刪除；registry key 是完整 hash，且現存值不保證 hex/固定長度。
   - 失敗：兩 full hashes 同 prefix 時刪 A 會刪 B 共用/覆寫的 CGSA 目錄；短 hash 也可能形成含義不明的 leaf。
   - 修法：刪前檢查同 s/tf 下 prefix 唯一，並用 work manifest/ownership marker 核對完整 hash；無法證明 ownership 時只刪 features，CGSA 回報 conflict。

### 8. API / 型別 / 相容

14. **[MAJOR][High] API contract 尚未寫死，Agent 被允許自行選 400/422 與 payload。**
   - 證據：SPEC:60「422/400」；TODO:73「400 or 422（與實作一致寫死）」；DTO 未定義 errors、partial success、error code。
   - 失敗：前端無法可靠區分 duplicate alias、active lease、unsafe path、partial filesystem failure；`DeleteRunResponse` 甚至漏掉 Task 1.2 的 errors。
   - 修法：SPEC 先固定每種狀態碼與 machine-readable error code；DELETE 對 partial failure 不得 200；定義 idempotency、404/200、409、422、500/507 類型與 response schema。

15. **[MAJOR][High] `created_at` 單位與 `size_bytes` 含義未定，Pydantic/TS 對齊不可驗。**
   - 證據：RunInfo 只列欄名；實際 registry `created_at` 是 epoch seconds float，而 task timestamps 是 ISO string；UI 要顯示時間與「將釋放大小」。
   - 失敗：TS 若直接 `new Date(created_at)` 會把 seconds 當 milliseconds；confirm 顯示的 size 可能不含 CGSA，與文案不符。
   - 修法：API 統一輸出 ISO-8601 UTC 或 epoch milliseconds；明定 `features_bytes/cgsa_bytes/total_bytes`、nullable 與 scan timestamp。

16. **[MAJOR][High] completed payload 的前端接線缺少明確資料流。**
   - 證據：TODO:82 說 dialog「監聽完成訊息」；現有 `GenerationProgress.applyPayload` 丟掉 result 與新增欄位，`FeatureTask`/`FeatureGenerationProgress` 也沒有 retention/run identity 欄位。
   - 失敗：後端即使送 payload，dialog 不會開；HTTP polling fallback 也只取 status/progress/current_stage，WS 斷線時永遠收不到 prompt。
   - 修法：定義 typed completion event 並存入 Zustand queue；HTTP task status 同樣返回 retention identity，確保 WS/polling 等價；加兩路測試。

### 9. 測試品質

17. **[MAJOR][High] symlink 測試不足以驗證文件指定順序，且缺 symlink ancestor/TOCTOU。**
   - 證據：TODO:53 明列「resolve→is_relative_to→is_symlink」；`resolve()` 後 leaf 已是 target，對 resolved path 做 `is_symlink()` 通常看不到原 symlink。
   - 失敗：測試只放 leaf symlink 可能因 is_relative_to 偶然拒絕；白名單內 symlink ancestor、check 後替換 parent 的競態未覆蓋。
   - 修法：對 lexical path 每一 existing component 先用 lstat 拒 symlink，再 resolve containment；刪除時用可抵抗 path swap 的方式或至少持有受控 root/run lock。測 leaf、symbol parent、tf parent、root symlink、swap race。

18. **[MINOR][High] PermissionError 測試用 chmod 000 在常見環境不可靠。**
   - 證據：TODO:58 指定 chmod 000。
   - 失敗：root/CI/macOS 權限行為可使刪除仍成功，測試不穩定。
   - 修法：patch 最底層 unlink/rmtree syscall 抛 PermissionError，另保留一個平台條件式整合測試。

### 10. Agent 可執行性

19. **[BLOCKING][High] Task 2.1 把關鍵決策留給實作者，且 scope 宣稱不改 batch contract，實際上無法完成並發安全。**
   - 證據：TODO:69 要實作端自行定位完成掛點；:70 du 策略「擇一」；:73 status「400 or 422」；:85 dialog consumer「實作端定位」；同時 SPEC:62 禁改既有 batch endpoint contract。
   - 失敗：Agent 可做出局部綠測但漏 batch/resume；不同選擇導致 API/前端不一致。
   - 修法：SPEC 先指定共享 lease provider、batch service 查詢/註冊介面、completion event schema、du semantics、status codes、pass2 reconciliation；TODO 再精確到函式與測試。

## 範本錨點與空殼

- §RISK/§A/§C/§G/§P/§V/§R/§N 均存在。
- §G=N/A 對「不碰數值」合理，但不能取代不可逆 filesystem/registry consistency baseline。
- 無純標題空殼；但「並發=active 409」、「三態=grep」、「resume=N/A」屬貌似完整、邏輯未覆蓋的實質空殼，已列 BLOCKING/MAJOR。

## 被當成事實的未驗證假設

1. **[High]** 「CGSA 對應目錄固定在 data_cache/cgsa_work」只是無 `FFACT_CGSA_WORK_DIR` 時的 fact；有 override 時為 false。
2. **[High]** 「service 內存 task 狀態足以判 active run」為 false；single task 起始無 hash，batch/resume 在另一 service，warmup 不是 running task。
3. **[High]** 「atomic rename 等於 registry 一致性」為 false；它只避免半檔，不能避免多實例 lost update。
4. **[High]** 「pass2 自動註冊不影響刪除」為 false；stable_id 不含 hash且刪除未清 task/cache。
5. **[High]** 「config_hash 可直接視為 canonical hash segment」未成立；實際 registry 有 `cfg_batch2d`，格式未被 schema 約束。
6. **[Medium]** 「per (symbol,timeframe) 保留 5」是 Claude 補充產品決策，不是已確認使用者事實；文件已標可否決，但又寫「待使用者確認：無」，內部狀態矛盾。

## 修補後最低重審 Gate

- 明定 run identity 與 canonical path resolver，覆蓋 default/override、非 hex hash、hash8 collision。
- 所有 single/batch/resume/warmup/browse 使用共享 per-run lease；delete/cleanup 取得 exclusive lease。
- registry mutation 具跨實例 transaction，add 保留 alias；corrupt registry 對 cleanup fail closed。
- delete 同步 reconcile registry、task_record/pass2 task、所有 in-memory caches、batch checkpoint 可見性。
- API status/error/time/size/completion event schema 固定；WS 與 polling 等價。
- 新增真實 interleaving、multi-instance registry、pass1/pass2、多 hash、symlink ancestor、frontend render/store tests。

ASSUMPTIONS_VERIFIED: 已以 rg/sed/nl 與唯讀 registry/cgsa_work/du 核實上述程式路徑；未假設未讀 code 行為
TESTS_RUN: read-only adversarial review；未執行 pytest/npm（本任務只產 review 報告）
FAILURES_SEEN: none
SCOPE_CHANGES: none；僅新增本 handoff，未改 docs/momentum/api/frontend/data_cache
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: FAIL — registry/lease/task-restore 一致性與刪除並發安全未定義，現況不可派工
