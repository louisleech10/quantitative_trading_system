# B5 批次特徵生成日期範圍 bug 修復 TODO
> 版本：DRAFT｜基於 SPEC：docs/B5_BATCH_DATE_SPEC.md｜日期：2026-06-21

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | _compute_single 接收+傳 date 給 generate_features | Phase1 |
| Task | 1.2 | run_in_executor 傳 request.start_date/end_date | Phase1 |
| Task | 1.3 | 更新所有 _compute_single test mocks(防假綠) | Phase1 |
| 不變量 | NODATE | 無 date=今日全史不變(golden+spy) | §G/§V |
| 不變量 | DATEAPPLIED | date 生效列數=選定範圍 | §V |
| 不變量 | HASH | config_hash 與單 path 一致 | §V |
| 風險 | (b)(d) | 批次 worker 共用+日期資料正確性 | §RISK |
- 合計：Task=3、不變量=3、風險=1。

## §0 全域規則
- **無 date(None)=今日全史行為完全不變**(向後相容核心;golden+spy 驗)。
- **date 進 config_hash**(已驗 :241 含 date)→ 批次與單 path cache 一致,無 stale。
- **不改數值計算**(只改「用哪段資料」入口,不碰特徵公式/NaN gate)。
- **更新所有 patch _compute_single 的 mocks**(B1/B2/B3 加 batch_id 前例:漏更 TypeError 假綠)。
- **防假綠**:新斷言碰真實 generate_features date 參數+真實列數,非 smoke;不放寬既有斷言。
- date 改變輸出是**目的**(批次該尊重 date);非 date 路徑零變動。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| 單批 | 1.1+1.2+1.3 | 1.2→1.1;1.3 隨 1.1 | 中-大(threading+mocks 同 PR 驗) |
- Gate:無 date golden+spy 不變 + date-selected 列數=選定範圍 + config_hash 一致 + 既有 batch 測試綠(mocks 更新)。

## Phase 1 — threading date
### Task 1.1 — _compute_single 接收+傳 date
- SPEC ref：1.1　目標:`_compute_single` 加 start_date/end_date 傳 generate_features。
- 實作要點:簽名(:1282)加 `start_date: Optional[str]=None, end_date: Optional[str]=None`(位置與 run_in_executor 對齊);`factory.generate_features(...)`(:~1340)補 `start_date=start_date, end_date=end_date`。比照單 path(feature_factory_service.py:251-272)。
- 修改檔案:feature_factory_batch_service.py。
- 不可做:不改特徵公式/數值;None 時不傳(今日行為)。
- 邊界:None→全史(今日)。
- 驗證:date 傳入時 generate_features 收對 date(spy);`pytest tests/api/ -k batch_date_threading`。
### Task 1.2 — run_in_executor 傳 date
- SPEC ref：1.2　目標:`run_in_executor`(:581-590)補 request.start_date/end_date。
- 實作要點:compute_fn args 加 request.start_date/request.end_date(位置對齊 _compute_single 簽名)。
- 修改檔案:feature_factory_batch_service.py:581-590。
- 不可做:不改其他 args 順序語意。
- 邊界:request 無 date→None→全史。
- 驗證:整合 date-selected 批次生成列數=選定範圍(167天≈4009列1h,非20352);`pytest tests/api/ -k batch_date_applied`。
### Task 1.3 — 更新 test mocks(防假綠)
- SPEC ref：1.3　目標:所有 patch _compute_single 的 mock 簽名同步加 date,免 TypeError。
- 實作要點:掃 tests/api/test_batch_retention.py / test_worker_logging.py / test_batch_*.py 的 _compute_single mock(如 `_compute_success`),簽名加 start_date/end_date。
- 修改檔案:上述 test 檔。
- 不可做:不放寬既有斷言。
- 邊界:mock 簽名與真實一致。
- 驗證:`pytest tests/api/ -k batch -q` 全綠無 TypeError。

### Phase 測試 + Gate
- 無 date:`python scripts/build_l65_golden_baseline.py --check` PASS + spy 驗 call 參數 None。
- date 生效:列數=選定範圍。config_hash 與單 path 一致。既有 batch 測試綠。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B5_BATCH_DATE_SPEC.md TODO=docs/B5_BATCH_DATE_TODO.md FOCUS=無date不變/date生效列數/config_hash一致/mocks同步/不改數值`
→ 一家 adversarial(中-大從嚴,作者非自審)reconcile → Composer 實作 + Codex review。
