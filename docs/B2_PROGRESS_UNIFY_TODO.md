# B2 進度契約統一 (E-progress + Q3) TODO
> 版本：DRAFT｜基於 SPEC：docs/B2_PROGRESS_UNIFY_SPEC.md｜日期：2026-06-19

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | FeatureProgressEvent schema+error enum+normalize 薄函式 | Phase1 |
| Task | 2.1 | 單 symbol 補 process_rss_mb 經 normalize | Phase2 |
| Task | 2.2 | 批次經同 normalize 填 worker_rss_mb | Phase2 |
| Task | 3.1 | RSS 分欄穿 Pydantic+WS+TS+Zustand+UI | Phase3 |
| 不變量 | BYTE | progress 不污染特徵值 | §G/§V |
| 不變量 | PARITY | parity 5 條 | §V |
| 風險 | (b) | 跨棧 progress 契約 | §RISK |
- 合計：Task=4、不變量=2、風險=1。
- **Codex adversarial reconcile**(handoffs/20260619-b2-adv-codex.md):#1 BLOCKING current_rss_mb **一版內雙寫**(不移除)+#2 normalize 唯一邊界(raw→normalized,jsonl/REST/WS 只搬不重組)+#3 schema_version **int** legacy-absent=0(TS 對齊 int)+#4 parity 5 條實質化(單REST/WS、批REST/WS、legacy雙寫、互斥、concurrent>1 coarse)+#5 process_rss_mb 語意進 API 契約+diff-scope guard。詳見 SPEC。

## §0 全域規則
- **不改數值(核心)**:純觀測;B2 前後 `build_l65_golden_baseline.py --check` PASS。
- **normalize 單一出口**:兩路徑都經 `normalize_progress_event()`,不各自手組(防漂移);薄函式,**不做 Sink 類/runner 抽象**。
- **WS 向後相容**:舊前端收新欄不爆;新前端收不到舊欄退化顯示 running。
- **RSS 互斥分欄**:單填 process_rss_mb、批填 worker_rss_mb,同 event 只一個;deprecate current_rss_mb(過渡)。
- **fail-open**:normalize/psutil 失敗不中斷生成。
- **防假綠**:不放寬既有測試;新斷言 parity 5 條 + RSS 互斥 + byte 不變。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B2a | 1.1 | 無 | 小(schema+normalize 函式) |
| B2b | 2.1+2.2 | B2a | 中(兩路徑接 normalize+RSS) |
| B2c | 3.1 | B2b | 中(RSS 分欄 4 層+前端) |
- Gate:B2a normalize 單元綠;B2b 單帶 process_rss/批帶 worker_rss+concurrent>1 coarse;B2c npm build+RSS 分欄穿 4 層+byte PASS。

## Phase 1 — schema + normalize
### Task 1.1 — FeatureProgressEvent + normalize_progress_event
- SPEC ref：1.1　目標:共用 schema+error enum+薄 normalize。
- 實作要點:① 新 `api/utils/ff_progress.py`:TypedDict 含 process_rss_mb?/worker_rss_mb?/**current_rss_mb?(legacy雙寫)**/`schema_version:int=1` + `ProgressErrorClass` enum;② `normalize_progress_event(**fields)` 薄函式=**唯一邊界**(raw→normalized;jsonl/REST/WS 只搬此 normalized 不重組,adv#2)+填 version+**雙寫 current_rss_mb=當前路徑 RSS**(adv#1);③ 無 lifecycle/Sink 類;④ schema_version int,legacy-absent=0(adv#3)。
- 修改檔案:api/utils/ff_progress.py(新)。
- 不可做:不做 Sink 類/runner;不改數值。
- 邊界:缺 RSS→None;非法 stage→歸 error-class 不拋。
- 驗證:同輸入→固定 schema/version;`pytest tests/api/ -k ff_progress_normalize`。

## Phase 2 — 兩路徑接 normalize
### Task 2.1 — 單 symbol 補 RSS
- SPEC ref：2.1　目標:單 progress_callback 經 normalize 補 process_rss_mb。
- 實作要點:feature_factory_service.py:188-198 callback 內 psutil RSS→`normalize_progress_event(...,process_rss_mb=rss)`→task_info+WS;try/except fail-open。
- 修改檔案:feature_factory_service.py。不可做:不改既有 current_stage 語義(只增 RSS+走 normalize)。
- 邊界:psutil 失敗→RSS None 不中斷。
- 驗證:單 symbol 進度含 process_rss_mb;`pytest tests/api/ -k single_progress_rss`。
### Task 2.2 — 批次經同 normalize
- SPEC ref：2.2　目標:batch tick/_apply_layer_metrics 走同 normalize 填 worker_rss_mb。
- 實作要點:feature_factory_batch_service.py 映射處走 `normalize_progress_event(...,worker_rss_mb=...)`;concurrent>1 維持 coarse。
- 修改檔案:feature_factory_batch_service.py。不可做:不改 concurrent>1 coarse 行為。
- 邊界:concurrent>1 不輸出假 current_stage。
- 驗證:batch 含 worker_rss_mb;`pytest tests/api/ -k batch_progress_normalize`。

## Phase 3 — RSS 分欄 4 層 + 前端
### Task 3.1 — process_rss_mb/worker_rss_mb 穿 4 層
- SPEC ref：3.1　目標:互斥分欄穿 Pydantic+WS mapper+TS+Zustand+UI;deprecate current_rss_mb。
- 實作要點:① api/models 加 process_rss_mb/worker_rss_mb(**current_rss_mb 保留雙寫**);② feature_factory_ws.py:132-134 mapper 加新欄+續送 legacy;③ frontend types.ts(schema_version int)+featureFactoryStore.ts(**優先讀新欄退 legacy**,`'key' in payload` 權威)+ panel 各標籤;④ **process_rss_mb docstring 明定 single=API 行程 RSS observational 非該 symbol 獨佔**(adv#5)。
- 修改檔案:api/models、feature_factory_ws.py、frontend types/store/panel。
- 不可做:不破既有 current_stage/stage_progress;**不移除 current_rss_mb**;兩新 RSS 欄不同時填;不碰 generation params(diff-scope)。
- 邊界:舊 payload 無新欄→退化 running;互斥。
- 驗證:`cd frontend && npm run build` 綠;mapper/store/types 測;`pytest tests/api/ -k progress_rss_fields`;byte PASS。

### Phase 測試 + Gate
- 行為不變:`python scripts/build_l65_golden_baseline.py --check` PASS。
- parity 5 條(progress 適用前 4 + RSS 互斥)。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B2_PROGRESS_UNIFY_SPEC.md TODO=docs/B2_PROGRESS_UNIFY_TODO.md FOCUS=normalize單一出口/RSS互斥分欄/parity5條/byte不變/WS向後相容`
→ 一家 adversarial(Codex,中-大從嚴)reconcile → Composer 實作 + Codex review。
