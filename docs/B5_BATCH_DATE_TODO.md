# B5 批次特徵生成日期 bug 修復 TODO v2
> 版本：v2(Codex adversarial 修正,跨棧大任務)｜基於 SPEC：docs/B5_BATCH_DATE_SPEC.md｜日期：2026-06-21

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | BatchGenerateRequest 加 date 欄 | Phase1 |
| Task | 1.2 | 前端 batch 分支送 date | Phase1 |
| Task | 2.1 | threading _compute_single→generate_features | Phase2 |
| Task | 2.2 | checkpoint 存 date 供 resume | Phase2 |
| Task | 3.1 | 8 個 _compute_single mock 同步 | Phase3 |
| 不變量 | NODATE | 無 date=今日全史不變 | §G/§V |
| 不變量 | DATEAPPLIED | date 生效列數=strict 區間 | §V |
| 不變量 | HASH | config_hash 與單 path 一致 | §V |
| 不變量 | RESUME | resume 保留 date | §V |
| 風險 | (b)(d) | 批次共用+日期資料正確性 | §RISK |
- 合計：Task=5、不變量=4、風險=1。
- **Codex adversarial reconcile**:v1 §A 誤認 BatchGenerateRequest 有 date→實無(176-184)→跨棧加(Pydantic+前端+threading+resume+8mock);warmup 留 B6(strict-window)。

## §0 全域規則
- **無 date(None)=今日全史行為完全不變**(向後相容核心;golden+spy)。
- **date 進 config_hash**(已驗:241)→ 批次與單 path cache 一致無 stale。
- **不改數值計算**(只改「用哪段資料」入口)。
- **B5 strict-window=Option2**(止血);**warmup(Option1)留 B6**(動工前明示此邊界)。
- **更新全部 8 個 _compute_single mocks**(漏更 TypeError 假綠)。
- **防假綠**:新斷言碰真實 generate_features date 參數+真實列數;不放寬既有。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B5a | 1.1+1.2 | 無 | 中(Pydantic+前端送 date) |
| B5b | 2.1+2.2 | B5a | 中(threading+resume) |
| B5c | 3.1 | B5b | 中(8 mock 同步) |
- Gate:B5a model 接受 date+前端 vitest 送 date;B5b date 生效列數=strict+resume 帶 date+無date golden不變;B5c 8 檔全綠無 TypeError+config_hash 一致。

## Phase 1 — 契約層
### Task 1.1 — BatchGenerateRequest 加 date
- SPEC ref：1.1　目標:加 start_date/end_date Optional=None(比照 :225-226)。
- 實作要點:api/models/feature_factory_models.py:176-184 加兩欄。
- 修改檔案:feature_factory_models.py。不可做:不改其他欄位。
- 邊界:None 預設向後相容。
- 驗證:model 接受 date;`pytest tests/api/ -k batch_request_date`。
### Task 1.2 — 前端 batch 送 date
- SPEC ref：1.2　目標:batch 生成送 startDate||undefined/endDate||undefined(比照單 path:259)。
- 實作要點:page.tsx batch 分支 + types.ts batch payload + store/api。
- 修改檔案:frontend page.tsx、lib/types.ts、相關。不可做:不破單 path。
- 邊界:空 date→undefined。
- 驗證:`npm run build` + **vitest 2 案例**(帶 date/空 date undefined);`*.test.tsx`。

## Phase 2 — threading + resume
### Task 2.1 — threading date
- SPEC ref：2.1　目標:date 經 run_in_executor→_compute_single→generate_features。
- 實作要點:_compute_single(:1282)簽名加 date;run_in_executor(:581-590)傳 request.start_date/end_date;generate_features(:~1340)補 date。
- 修改檔案:feature_factory_batch_service.py。不可做:不改數值;不做 warmup。
- 邊界:None→全史。
- 驗證:spy date 收對;date 批次列數=strict 區間(167天~4009列非20352);`pytest tests/api/ -k "batch_date_threading or batch_date_applied"`。
### Task 2.2 — checkpoint resume 帶 date
- SPEC ref：2.2　目標:date 經 model_dump 入 checkpoint,resume 帶 date。
- 實作要點:確認/補 checkpoint 保存+resume 重建路徑帶 date。
- 修改檔案:feature_factory_batch_service.py。不可做:不破舊 checkpoint 相容。
- 邊界:舊 checkpoint 無 date→None→全史。
- 驗證:resume date 批次列數=strict 區間;`pytest tests/api/ -k batch_date_resume`。

## Phase 3 — mocks
### Task 3.1 — 8 個 _compute_single mock 同步
- SPEC ref：3.1　目標:全部 8 檔 mock 簽名加 date,免 TypeError。
- 實作要點:rg 全掃確認;改 test_feature_factory_batch_step4/test_batch_retention/test_batch_layer_metrics/test_batch_progress_normalize/test_worker_logging/test_feature_factory_batch_resume/test_multi_symbol_ic_first/test_multi_window_rolling 的 _compute_single mock;加 1 spy 測證 date 參數順序。
- 修改檔案:上述 8 檔。不可做:不放寬既有斷言。
- 邊界:mock 簽名與真實一致。
- 驗證:`pytest tests/api/ -k batch -q` 全綠無 TypeError。

### Phase 測試 + Gate
- 無 date:`build_l65_golden_baseline.py --check` PASS + spy 驗 None。
- date 生效列數=strict;config_hash 與單 path 一致;resume 帶 date;8 mock 綠。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B5_BATCH_DATE_SPEC.md TODO=docs/B5_BATCH_DATE_TODO.md FOCUS=無date不變/date生效strict列數/config_hash一致/resume帶date/8mock同步/不做warmup(B6)`
→ **雙家族 adversarial(大任務,Codex+Composer)** reconcile → Composer 實作(Phase1→3) + Codex review。
