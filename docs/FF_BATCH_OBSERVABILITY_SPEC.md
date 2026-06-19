# FF 批次 layer 觀測性 (T2) — SPEC

> 來源：docs/FF_OBSERVABILITY_COMMITTEE_BRIEF.md（三方 reconcile）｜日期：2026-06-19｜對應 TODO：docs/FF_BATCH_OBSERVABILITY_TODO.md

## §RISK 風險分級
- **大小**：中。
- **命中高風險原則**：**(b) 跨模組共用路徑**（batch service websocket + factory progress_callback + 前端面板）。**不命中 (a)/(d)**——純觀測性，**不碰任何特徵值/數值計算**。
- → §G Golden N/A（不改數值；行為不變型，以「特徵輸出 byte 不變」+「新增 jsonl/WS 欄位」為主）。

## §A 假設與待使用者確認
- **已驗證事實**（grep/Read 實測，附行號）：
  - `FeatureFactory._report_progress(stage,progress,message)`（feature_factory.py:3492）呼叫 `self._progress_callback`（:3494）；**已在每個 layer 邊界觸發**（:540 start / :677,:705,:616 done / :556,:614,:682 failed）。
  - `progress_callback` 經 generate_features 串接（:232,:270,:282,:316）。
  - **gap**：`_compute_single`（feature_factory_batch_service.py:1036）呼叫 `factory.generate_features`（:1062）**未傳 progress_callback** → layer 事件發了無人收。
  - `_append_child_metrics_jsonl`（:698，O_APPEND 安全）+ `child_metrics.jsonl`（:695）；現有 `peak_rss_mb`（:1076）是 **run 結束快照非真峰值**。
  - `_notify_progress`（:1131）**只在 item submit/finish 觸發**（:321,343,381,391,449,513）→ **長 layer 進行中不會更新 WS**（adversarial #4）→ 需週期 tail。
  - WS schema 實況（adversarial #2）：`BatchTaskStatusResponse`（feature_factory_models.py:242）只有 `current_symbol/current_timeframe/concurrent_symbols`,**無 per-symbol stage**；`feature_factory_ws.py`(:194-200) 有**白名單 mapper** 重包 payload。新欄位須穿 Pydantic model + WS mapper 白名單 + TS type + Zustand normalize 四層,非「只加欄位」。
  - 多 TF 實況（adversarial #3）：multi-TF generator 另有 `multi_tf/persist/complete` stages + CGSA 並行 TF workers → 事件數非無條件 16-30;**使用者跑 2 tf 即 multi-TF**。
  - **回呼 fail-open 位置（adversarial #1）**：`_report_progress`(:3494) **直接呼叫** callback,例外會穿回 layer 執行使子進程 future 失敗 → fail-open 必須在 `_report_progress` 自身(包 callback 呼叫)+ callback wrapper 雙層。
  - 批次經 ProcessPoolExecutor 子進程（:442）→ 子進程 log 不回父（F1 根因）。
- **待使用者確認**：無（使用者已拍板做 T1+T2，2026-06-19）。
- **已確認**：T1+T2 做、T3 擱置（使用者 2026-06-19）。

## §C 約束
- 解耦：momentum 不 import api；progress_callback 是注入點（factory 不知 api）。
- **不可違反**：不改特徵值/不弱化 NaN·inf gate/不改輸出大小；callback 失敗不得中斷或拖慢生成（fail-open，包 try/except）。
- 本任務注意：高頻 callback 不得洗版（layer 邊界粒度，**非 per-row/per-column heartbeat**）；多 worker 寫同檔須 O_APPEND（複用既有）。

## §G Golden / Baseline
- N/A（移 §N）。行為不變型驗證：開啟 T2 前後，**同 config 的特徵輸出 byte 一致**（`build_l65_golden_baseline.py --check` 或既有 golden）→ 證明觀測性不污染數值。

## §P Phase 與依賴（自檢：無 forward dependency）

### Phase 1 — _report_progress fail-open + worker 寫 layer_metrics（依賴：無）
**Task 1.1 — _report_progress fail-open（adversarial #1 BLOCKING）**
- 目標：callback 例外不得穿回 layer 執行/使子進程 future 失敗。
- 檔案：feature_factory.py `_report_progress`(:3492-3494)。
- 改法：`if self._progress_callback: try: self._progress_callback(stage,progress,message) except Exception: logger.debug(...)`（吞所有例外，fail-open 在源頭）。
- 驗證：注入 raise 的 callback → generate_features 仍完成、layer 不 fail；`pytest tests/feature_engineering/ -k progress_failopen`。
- 邊界：callback raise / callback=None / 正常 3 情境。　不可做：不改 progress 觸發點/數值。

**Task 1.2 — _compute_single 接 callback → layer_metrics.jsonl**
- 目標：worker 每 layer 邊界寫 `{artifact_dir}/layer_metrics.jsonl`。
- 檔案：feature_factory_batch_service.py `_compute_single`(:1036)；新 env `FFACT_LAYER_METRICS_PATH`（仿 FFACT_CHILD_METRICS_PATH 設/還原+checkpoint）。
- 改法：cb `(stage,progress,message)` 內捕 `psutil rss//MB`，append `{symbol,timeframe,stage,progress,message,rss_mb,ts,elapsed,schema_version:1}`（複用 `_append_child_metrics_jsonl` O_APPEND）；cb 全包 try/except；`generate_features(...,progress_callback=cb)`。
- 驗證：跑 1 symbol×1tf → jsonl 每 layer ~2 行；rss_mb **存在/非負/合理範圍（非要求單調，adversarial #6）**；`pytest tests/api/ -k batch_layer_metrics`。
- 邊界：① 寫檔失敗→生成完成(fail-open)；② **cache-hit(force_regenerate=False)→可能無 layer 事件→不報錯、jsonl 可空(adversarial #5)**；③ multi-TF→含 multi_tf/persist/complete stages(adversarial #3)；④ layer failed 也記。
- 不可做：不改 generate_features 數值；不加 per-row heartbeat。

### Phase 2 — 父週期 tail → batch status WS 四層串接（依賴：Phase 1）
**Task 2.1 — 週期 tick + schema 四層（adversarial #2,#4）**
- 目標：父**週期性**讀 jsonl（非只 item 邊界，否則長 layer 中不更新）→ 併入 status → WS；新欄位穿 4 層。
- 檔案：feature_factory_batch_service.py `_notify_progress`(:1131) + 批次迴圈加**週期 tick**（asyncio task 每 ~2-3s tail+notify，batch 結束取消）；api/models/feature_factory_models.py `BatchTaskStatusResponse`(:242)；api/websocket/feature_factory_ws.py mapper 白名單(:194-200)。
- 改法：concurrent=1（單 running symbol）→ status 直接加 `current_stage/stage_progress/current_rss_mb`（**非 per_symbol list**）；tail 限讀尾 N KB/offset cache；Pydantic model + WS mapper 白名單同步加欄位。
- 驗證：長 layer 進行中 WS 有更新（週期 tick）；payload 含 `current_stage`；`pytest tests/api/ -k batch_status_layer`（含 WS mapper + response model）。
- 邊界：① jsonl 不存在(舊task)→退 symbol 級；② 半行 JSONDecodeError→跳過不 crash；③ batch 結束→tick 取消不洩漏 task。
- 不可做：不改既有 symbol 級 progress 語義（只增欄位）；不新建 WS channel。

### Phase 3 — 前端顯示（依賴：Phase 2）
**Task 3.1 — BatchProgressPanel 顯示當前 layer + rss**
- 目標：running symbol 下顯示「當前 layer/stage + rss_mb」。
- 檔案：BatchProgressPanel.tsx + lib/types.ts + Zustand store normalize + BatchProgressPanel.test.tsx。
- 改法：types 加 `current_stage?/stage_progress?/current_rss_mb?`；Zustand normalize 收新欄位；running symbol 列下加一行；空值優雅退回。
- 驗證：`cd frontend && npm run build` 綠；test 斷言新欄位渲染 + 空值退回；真實 2 symbol×2tf batch UI 看到 layer 推進。
- 邊界：① 後端沒給新欄位 → 顯示 running（向後相容）；② rss 缺 → 不顯示該段。
- 不可做：不改既有逐標的狀態結構（只加一行）。

## §V 驗證策略與邊界測試目錄
- 測試層級：單元（_report_progress fail-open / callback 寫 jsonl / 父 tail 合併 / WS mapper / Pydantic response model / Zustand normalize）/ 整合（**真實 1-2 symbol × 多 TF** batch e2e → layer_metrics.jsonl + WS payload，adversarial #5）/ 前端（BatchProgressPanel 渲染 + 空值退回）/ 行為不變（特徵 byte）。
- **防假綠**：不得放寬既有 batch 測試；新斷言「jsonl 有 per-layer rss（**存在/非負/範圍,非單調**,adversarial #6）」「WS 真帶 current_stage」「callback raise 仍生成完成」「特徵 byte 不變」。
- **行為不變（核心）**：T2 前後 `python scripts/build_l65_golden_baseline.py --check` PASS（abs≤1e-6；觀測不污染數值）。
- **不洗版（multi-TF 上限,adversarial #3）**：layer 邊界粒度；單(symbol,tf) jsonl 行數量級數十（multi-TF 含 multi_tf/persist/complete 額外 stages，**驗證 ≤ 上限 N（如 ≤200/symbol）非數千**）。
- **邊界目錄**：_report_progress callback raise(1.1)/寫檔失敗 fail-open(1.2)/**cache-hit 無事件 jsonl 可空(1.2,adversarial #5)**/multi-TF stages(1.2)/半行 JSONDecodeError(2.1)/舊 task 無檔(2.1)/週期 tick 取消不洩漏(2.1)/前端空值向後相容(3.1)/layer failed 事件(1.2)。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert。callback 不傳即回舊行為（layer_metrics 不寫、WS 不帶新欄位、前端退回 symbol 級）——天然 feature-flag。
- 特徵 byte 變 = 立即 revert（觀測性絕不該改數值）。

## §N N/A 登記
- §G Golden：**N/A — 本任務純觀測性,不碰特徵值/數值計算**；改以行為不變替代：`python scripts/build_l65_golden_baseline.py --check` PASS（T2 前後特徵 byte 一致,abs≤1e-6）。
