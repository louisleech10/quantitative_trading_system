# FF 批次 layer 觀測性 (T2) TODO
> 版本：DRAFT｜基於 SPEC：docs/FF_BATCH_OBSERVABILITY_SPEC.md｜日期：2026-06-19

## 階段 1：SPEC ID 覆蓋（已納 Codex adversarial 6 findings,SPEC 為權威）
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | _report_progress fail-open(callback 例外不穿回 layer) | Phase1(adv#1 BLOCKING) |
| Task | 1.2 | _compute_single 接 callback → layer_metrics.jsonl | Phase1 |
| Task | 2.1 | 週期 tick + schema 四層(Pydantic+WS mapper+TS+Zustand) | Phase2(adv#2,#4) |
| Task | 3.1 | BatchProgressPanel 顯示 layer+rss | Phase3 |
| 不變量 | BYTE | 特徵輸出 byte 不變(觀測不污染數值) | §G/§V |
| 風險 | (b) | 共用路徑 websocket+factory+前端 | §RISK |
| flag | callback 不傳=回舊行為 | 天然 feature-flag | §R |
- 合計：Task=4、不變量=1、風險=1。
- **Codex adversarial reconcile**(handoffs/20260619-t2-adv-codex.md):#1 fail-open 移到 _report_progress(新Task1.1);#2 schema 穿4層(非只加欄位);#3 multi-TF 額外 stages(行數上限 ≤N 非 16-30);#4 父需週期 tick(非只 item 邊界);#5 cache-hit 無事件/驗證擴端到端;#6 rss 非單調(存在/非負/範圍)。詳見 SPEC。

## §0 全域規則
- **解耦**：momentum 不 import api；callback 是注入點(factory 不知 api)。
- **fail-open 鐵律**：callback 寫檔失敗**不得中斷或拖慢生成**(包 try/except,吞例外只 log debug)。
- **不改數值**：純觀測;T2 前後特徵 byte 一致(`build_l65_golden_baseline.py --check`)。
- **不洗版**：layer 邊界粒度,禁 per-row/per-column heartbeat(1 symbol ~16-30 行)。
- **O_APPEND**：多 worker 寫同檔複用既有 `_append_child_metrics_jsonl`,不自造寫檔。
- **防假綠**：不放寬既有 batch 測試;新斷言對應新行為(jsonl 有 per-layer rss / WS 帶 current_stage / byte 不變)。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B1 | 1.1, 1.2 | 無 | 小(factory fail-open + 後端 worker) |
| B2 | 2.1 | B1 | 中(後端父週期 tick + schema 4 層) |
| B3 | 3.1 | B2 | 小(前端 + Zustand) |
- Gate:B1 後 callback raise 仍生成完成 + layer_metrics.jsonl 有 per-layer rss(非單調);B2 後長 layer 中 WS 帶 current_stage;B3 後 npm build + UI 看到 layer 推進 + `build_l65_golden_baseline.py --check` byte 不變。

## Phase 1 — _report_progress fail-open + worker 寫 layer_metrics
### Task 1.1 — _report_progress fail-open (adv#1 BLOCKING)
- SPEC ref：1.1　目標：callback 例外不穿回 layer 執行/使子進程 future 失敗。
- 實作要點:`feature_factory.py:3494` 包 `try: callback(...) except Exception: logger.debug(...)`(吞所有例外,源頭 fail-open)。
- 修改檔案:momentum/FeatureEngineering/feature_factory.py `_report_progress`。
- 不可做:不改 progress 觸發點/數值。
- 邊界:callback raise / None / 正常 3 情境。
- 驗證:注入 raise callback → generate_features 完成、layer 不 fail;`pytest tests/feature_engineering/ -k progress_failopen`。

### Task 1.2 — _compute_single 接 callback → layer_metrics.jsonl
- SPEC ref：1.2　目標：worker 每 layer 邊界寫 jsonl。
- 實作要點:
  1. `_compute_single`(:1036) `def cb(stage,progress,message)` 捕 `psutil rss//MB`,append `{symbol,timeframe,stage,progress,message,rss_mb,ts,elapsed,schema_version:1}`(複用 `_append_child_metrics_jsonl` O_APPEND)。
  2. cb 全包 try/except(fail-open)。
  3. `generate_features(...,progress_callback=cb)`;路徑用新 env `FFACT_LAYER_METRICS_PATH`(仿 FFACT_CHILD_METRICS_PATH 設/還原+checkpoint)。
- 修改檔案:feature_factory_batch_service.py `_compute_single`。
- 不可做:不改 generate_features 數值;不加 per-row heartbeat;不改 child_metrics.jsonl 語義。
- 邊界:寫檔失敗→完成(fail-open);**cache-hit→可能無事件、jsonl 可空(adv#5)**;multi-TF→multi_tf/persist/complete 額外 stages(adv#3);layer failed 也記。
- 驗證:跑 1 symbol×1tf→jsonl 每 layer ~2 行;rss_mb **存在/非負/範圍(非單調,adv#6)**;`pytest tests/api/ -k batch_layer_metrics`。

## Phase 2 — 父週期 tick → WS 四層串接
### Task 2.1 — 週期 tick + schema 4 層 (adv#2,#4)
- SPEC ref：2.1　目標:父**週期**讀 jsonl(非只 item 邊界)→ status → WS;新欄位穿 Pydantic+mapper+TS+Zustand。
- 實作要點:
  1. 批次迴圈加 asyncio **週期 tick**(每 ~2-3s tail+`_notify_progress`,batch 結束取消)——否則長 layer 中 WS 不更新。
  2. concurrent=1 單 running symbol → status 直接加 `current_stage/stage_progress/current_rss_mb`(非 per_symbol list)。
  3. tail 限讀尾 N KB/offset;同步 `BatchTaskStatusResponse`(feature_factory_models.py:242) + `feature_factory_ws.py` mapper 白名單(:194-200)。
- 修改檔案:feature_factory_batch_service.py(`_notify_progress`+迴圈 tick)、feature_factory_models.py、feature_factory_ws.py。
- 不可做:不改既有 symbol 級 progress 語義(只增欄位);不新建 WS channel。
- 邊界:jsonl 不存在(舊task)→退 symbol 級;半行 JSONDecodeError→跳過不 crash;batch 結束→tick 取消不洩漏。
- 驗證:長 layer 中 WS 有更新;payload 含 `current_stage`;`pytest tests/api/ -k batch_status_layer`(含 mapper+response model)。

## Phase 3 — 前端
### Task 3.1 — BatchProgressPanel 顯示 layer+rss
- SPEC ref：3.1　目標：running symbol 下顯示當前 layer+rss。
- 實作要點：
  1. types 加 `current_stage?/stage_progress?/rss_mb?`。
  2. lib/types.ts 加 `current_stage?/stage_progress?/current_rss_mb?`;Zustand store normalize 收新欄位;BatchProgressPanel.tsx running symbol 列下加一行(layer + rss);pending/done 不顯示;空值優雅退回。
- 修改檔案：BatchProgressPanel.tsx + lib/types.ts + Zustand store + BatchProgressPanel.test.tsx。
- 不可做：不改既有逐標的狀態結構(只加一行)。
- 邊界：後端無新欄位→顯示 running(向後相容);rss 缺→不顯示該段。
- 驗證：`cd frontend && npm run build` 綠;test 加斷言;UI 真實 batch 看到 layer 推進。

### Phase 測試 + Gate
- 行為不變:`python scripts/build_l65_golden_baseline.py --check` PASS(T2 不污染數值)。
- 不洗版:1 symbol jsonl 行數量級 16-30(非數千)。

## 階段 4：Frozen 前 handoff
`SPEC=docs/FF_BATCH_OBSERVABILITY_SPEC.md TODO=docs/FF_BATCH_OBSERVABILITY_TODO.md FOCUS=fail-open不拖慢/byte不變/不洗版/WS向後相容`
→ 一家 adversarial(Codex,作者非自審)reconcile 後過 gate → Composer 實作 + Codex review。
