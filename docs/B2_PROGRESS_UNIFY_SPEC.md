# B2 — 進度契約統一 (E-progress-normalize + Q3) — SPEC

> 來源：handoffs/20260619-ffconsist-FINAL.md(E P0c + Q3 P1)｜日期：2026-06-19｜對應 TODO：docs/B2_PROGRESS_UNIFY_TODO.md

## §RISK 風險分級
- **大小**：中-大（委員會升級:跨棧 progress 契約,命中 (b)）。**不命中 (a)/(d)**——純觀測,不碰特徵值。
- → §G N/A;以 parity 5 條 + byte 不變 驗證。

## §A 假設與待使用者確認
- **已驗證事實**(grep/Read,附行號):
  - 單 symbol:`feature_factory_service.py:188 progress_callback(payload)`→`:198 task_info["current_stage"]=stage`,經 notification_callback 推 WS;**已有 current_stage,缺 RSS**(Q3 gap)。
  - 批次:T2 layer_metrics.jsonl→tick→`_apply_layer_metrics_to_task`(concurrent>1 已 skip,coarse)。
  - WS mapper `feature_factory_ws.py:132-134`:current_stage/stage_progress/**current_rss_mb**(T2 共用欄)。
  - 前端 `types.ts:465-467` + `featureFactoryStore.ts:356-367` 已消費三欄(`'key' in payload` 權威清除,B1/T2 已修 stale)。
  - `_report_progress`(feature_factory.py:3492)送 dict `{stage,progress,message}`(B1 期間確認 dict 形)。
- **待確認**:無。**已確認**(2026-06-19):做 B2(E P0c+Q3)。

## §C 約束
- 解耦:normalize 函式放共用處(api 或 momentum 中性);不新增跨域依賴。
- **不可違反**:不改特徵值;normalize/RSS 失敗 fail-open 不中斷生成;WS 向後相容(舊前端收到新欄不爆、新前端收不到舊欄退化)。
- 注意:**單一 normalize 出口**(兩路徑都經它,防漂移);RSS 互斥分欄;concurrent>1 不輸出假單一 current_stage。

## §G Golden / Baseline
- N/A(移 §N)。行為不變:`python scripts/build_l65_golden_baseline.py --check` PASS(progress 不污染數值)。

## §P Phase 與依賴

### Phase 1 — 共用 schema + normalize(依賴:無)
**Task 1.1 — FeatureProgressEvent schema + error enum + normalize_progress_event()**
- 目標:定義共用 TypedDict `FeatureProgressEvent{stage,progress,message,process_rss_mb?,worker_rss_mb?,current_rss_mb?(legacy雙寫),symbol?,timeframe?,schema_version:int}` + error-class enum;單一薄 `normalize_progress_event(...)`。
- 檔案:新 `api/utils/ff_progress.py`。
- 改法:薄函式,無 lifecycle/runner 抽象。**(adv#2 單一邊界)**:定義唯一邊界=`raw event → normalize_progress_event() → normalized event`;**jsonl row / REST / WS 全部只搬 normalized event,不再各自手組**。
- **(adv#3 schema_version)**:`schema_version` 為 **int**,初始 `1`;legacy-absent(舊 payload 無此欄)視為 0/pre-version;TS 對齊 int(現為 string optional 須改)。
- **(adv#1 BLOCKING 雙寫)**:normalize 同時填 `process_rss_mb`/`worker_rss_mb`(新)**與** `current_rss_mb`(legacy,=當前路徑那個 RSS) → 一版內雙寫,不移除 legacy。
- 驗證:同輸入→固定 schema/version/error-class + 雙寫 legacy 欄;`pytest tests/api/ -k ff_progress_normalize`。
- 邊界:缺 RSS→欄 None;非法 stage→不拋(歸 error-class)。　不可做:不做 Sink 類/runner;不移除 current_rss_mb。

### Phase 2 — 兩路徑接 normalize + 單補 RSS(依賴:Phase 1)
**Task 2.1 — 單 symbol 補 RSS + 經 normalize**
- 目標:單 symbol progress_callback 經 normalize,補 `process_rss_mb`(psutil 同進程 RSS)。
- 檔案:feature_factory_service.py:188-198。
- 改法:callback 內 psutil RSS→normalize_progress_event(...,process_rss_mb=rss)→task_info+WS;全包 try/except fail-open。
- 驗證:單 symbol 進度含 process_rss_mb;`pytest tests/api/ -k single_progress_rss`。
- 邊界:psutil 失敗→RSS None 不中斷。
**Task 2.2 — 批次經同 normalize**
- 目標:batch layer_metrics→tick 映射經同 normalize,填 `worker_rss_mb`(子進程 RSS)。
- 檔案:feature_factory_batch_service.py(_apply_layer_metrics_to_task/tick 映射)。
- 改法:走 normalize_progress_event(...,worker_rss_mb=...);concurrent>1 維持 coarse(不填單一 current_stage)。
- 驗證:batch 進度含 worker_rss_mb;concurrent>1 不輸出假 current_stage;`pytest tests/api/ -k batch_progress_normalize`。

### Phase 3 — RSS 分欄四層 + 前端(依賴:Phase 2)
**Task 3.1 — RSS 分欄穿 4 層(雙寫 legacy)**
- 目標:互斥新分欄 process_rss_mb/worker_rss_mb 穿 Pydantic+WS mapper+TS+Zustand+UI;**current_rss_mb 一版內雙寫保留**(不 deprecate-removal)。
- 檔案:api/models、feature_factory_ws.py:132-134、frontend types.ts:465-467、featureFactoryStore.ts:356-367、BatchProgressPanel/單 symbol 元件。
- 改法:WS payload 帶 process_rss_mb XOR worker_rss_mb **+ current_rss_mb(legacy 同值)**;前端**優先讀新欄、退 legacy current_rss_mb**;各標籤「(單)行程 RSS」/「(批)worker RSS」**不跨路徑比較**;`'key' in payload` 權威清除。
- **(adv#5 語意進契約)**:`process_rss_mb` API 欄 docstring/註解明定「single = API 行程整體 RSS(含 API/browse 噪音),observational,非該 symbol 獨佔」;UI tooltip 同。
- 驗證:`cd frontend && npm run build` 綠;mapper/store/types 測新欄+legacy 雙寫;**legacy 消費者(舊 current_rss_mb tests)仍綠**;`pytest tests/api/ -k progress_rss_fields`。
- 邊界:舊 payload 無新欄→讀 legacy/退化 running;兩新欄不同時填;legacy 與新欄同值。

## §V 驗證策略與邊界測試目錄
- 測試層級:單元(normalize/RSS)/整合(單+批真實小 run 各帶對的 RSS 欄)/前端(渲染+空值退化)/行為不變(byte)。
- **防假綠**:不放寬既有測試;**legacy current_rss_mb tests 須仍綠**(雙寫);新斷言 parity 5 條 + RSS 互斥 + byte 不變。
- **parity 5 條(可證偽,adv#4 改實質,去空洞)**:①單 symbol REST+WS 帶 `process_rss_mb`+`schema_version`(int);②批次 REST+WS 帶 `worker_rss_mb`+`schema_version`;③**legacy `current_rss_mb` 兩路徑仍存在(雙寫,向後相容)**;④`process_rss_mb` XOR `worker_rss_mb`(同 event 互斥);⑤concurrent>1 不輸出假單一 current_stage。
- **行為不變 + diff scope(adv minor)**:`build_l65_golden_baseline.py --check` PASS;**diff 只允許 progress payload/normalize/RSS/前端/測試——碰 generation params/cache/config_override → BLOCK**。
- **邊界目錄**:psutil 失敗 RSS None/concurrent>1 coarse/舊 payload 讀 legacy 退化/兩新 RSS 欄互斥/legacy 雙寫同值/schema_version legacy-absent=0/normalize 非法 stage 不拋。

## §R 回退
- 每 Phase 獨立 commit。normalize 函式集中→回退單點。`schema_version` 供前端演進。byte 變=立即 revert。

## §N N/A 登記
- §G Golden:**N/A — 純觀測不碰數值**;改以 `python scripts/build_l65_golden_baseline.py --check` PASS(abs≤1e-6)+ parity 5 條 驗證。
