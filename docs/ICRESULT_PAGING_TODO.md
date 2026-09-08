# ICRESULT_PAGING TODO　（DRAFT／基於 `docs/ICRESULT_PAGING_SPEC.md`／2026-09-09）

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 解耦 7 條；`momentum/` 不 import `api/`；service 不互 import；R7 DTO 不跨界（pydantic 模型只在 `api/models/`，service 回 dict）。
- **紅線（SPEC §C 不變式 1–5）**：①預設 `GET /result/{id}` 位元組級不變；②orchestrator／reporter／落檔一行不改；③所有投影端點只讀 `task_info["result"]`，不重算、不讀檔、不另存；④排序／篩選欄位白名單來自 `momentum/Analysis/contracts/ic_result_paging_contract.json`（唯一真相源），非白名單 ⇒ 400；⑤前端 light 視圖缺段不補假值。
- 不可違反原則：不擅改輸出大小（落檔）；不弱化任何 gate；`deny_factor_in_ok_oos` 出口守衛在所有視圖前先跑。
- 防假綠：既有 `/result`、golden replay、survivor／contract、`ICSummaryTable.icirNull.test.tsx` 斷言一條不改；新斷言對應新行為；mutation rc=5 計 UNCOVERED。
- 引用 SPEC §A 七條 FACT-RECEIPT（119 MB／39,346 列／各段位元組數／metadata 39,398 鍵），不整段複製。
- 新資料結構：回應 schema 在 `api/models/ic_models.py`；白名單／limit／metadata 保留鍵在 contract JSON；SPEC／TODO 不第二次列舉。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B0 | 0.1 | 無 | golden 凍結＋contract JSON＋mutation 骨架（改前） | 小 |
| B1 | 1.1、1.2、1.3 | B0 | 三個純函式共用同一 fake-task fixture 與 golden；預設路徑不動 | 中 |
| B2 | 2.1、2.2、2.3 | B1 commit | 前端一次切換到投影（切一半會出現 light 缺段又沒分頁的中間態） | 中 |
| B3 | 3.1 | B2 commit | 實機 UAT B34 | 小 |
- 批次 Gate：B0 ⇒ `tests/golden/icresult_paging/full_report_projection.json` 存在且 `handoffs/<date>-probe-icresult-golden.py --check` rc=0；B1 ⇒ `pytest tests/api/test_icresult_paging.py` rc=0＋G-1～G-5＋`pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_survivor_contract.py` rc=0＋mutation P1–P6 紅／C0 綠（`scripts/icresult_paging_phase_gate.sh 1`）；B2 ⇒ vitest rc=0＋tsc `error TS` == 8；B3 ⇒ 使用者簽 B34。
- 派工：實作＝Claude 主委自任（ORCH §1）；review＝codex＋composer＋grok 全員 adversarial；SPEC/TODO 先過三家審查再開 B0。

## Phase 0 — Golden 與骨架（完成後：改前投影對照可機檢）

### Task 0.1 — 凍結全量報告投影 golden＋contract JSON＋mutation 骨架（`SPEC §G`／`§V`）
- 目標：改前產出 B-1／B-2 golden；建白名單 contract；建 mutation／gate 骨架（phase 1 條目先 SKIP 計 UNCOVERED）。
- 檔案：`handoffs/<date>-probe-icresult-golden.py`（`--write`／`--check`；以 `tests/momentum/helpers/ichc_run.run_analyze` 產全量報告 → `tests/golden/icresult_paging/full_report_projection.json`：`summary_rows`、`feature_set_sha256`、`section_key_sha256{段:sha}`、`report_canonical_sha`、`feature_samples{name: {段: sha}}`（等距抽 200））；`momentum/Analysis/contracts/ic_result_paging_contract.json`（`sort_fields`、`order_values`、`limit_default`、`limit_max`、`metadata_keep_keys`、`per_feature_sections`）；`handoffs/<date>-icresult-paging-mutate.py`（沿 `20260908-evtwarmup-mutate.py` 型：rc=5 計 UNCOVERED、紅只認 rc=1、目標檔須與 HEAD 一致）；`scripts/icresult_paging_phase_gate.sh <1>`。
- 實作要點：①golden 產生用 `ichc_run.canonical_sha` 同一 scrub 集合；②`metadata_keep_keys` 初值＝`metadata` 中非 per-feature 描述子之鍵（以「值為 dict 且鍵集 == {category,layer,name}」判為描述子，**但 contract 存的是保留鍵白名單，不存判別規則**）；③contract 由 `api/models/ic_models.py` 載入為常數（單一來源），測試斷言模型 `sort_fields` == contract。
- 修改檔案：新建三檔＋一 golden；`api/models/ic_models.py::load_ic_result_paging_contract()`。　既有 caller：新建無。
- 路徑：
  handoffs/*-probe-icresult-golden.py
  handoffs/*-icresult-paging-mutate.py
  scripts/icresult_paging_phase_gate.sh
  momentum/Analysis/contracts/ic_result_paging_contract.json
  tests/golden/icresult_paging/full_report_projection.json
  api/models/ic_models.py
- 不可做：不用 39k 實機報告當 golden（不進 repo；只做 G-5 尺寸 receipt）；不把判別規則寫進 contract。
- 邊界：①fixture 報告 `correlation_matrix` 為空 ⇒ sha 照算；②`metadata` 中同名鍵既是特徵名又是保留鍵（不可能，斷言互斥）⇒ 建 contract 時 FAIL。
- 風險緩解：⊘。
- 驗證：`venv/bin/python handoffs/<date>-probe-icresult-golden.py --check` rc=0；`jq '.sort_fields|length' contract` ≥ 5 且含 `icir`、`ic_mean`、`p_value`、`feature_name`；`jq '.metadata_keep_keys' contract` 不含任何 `summary_table` 之 `feature_name`（集合交集 == 0）。
- **存活至**：永久。
- **覆蓋風險**：無。

## Phase 1 — 後端投影端點（完成後：三個端點可用，預設路徑一 byte 不變）

### Task 1.1 — summary 分頁端點（`SPEC Task 1.1`）
- 目標：`GET /result/{task_id}/summary` 回分頁；純函式 `paginate_summary`。
- 檔案：`api/services/ic_result_projection.py`（**新模組**，純函式：`paginate_summary(rows: list[dict], *, sort_by: str, order: str, offset: int, limit: int, pass_class: str|None, q: str|None, contract: dict) -> dict`；`sort_key(row, field)`＝`_finite_or_neg_inf` 語意，次鍵 `feature_name`）；`api/services/ic_analysis_service.py::ICAnalysisService.get_result_summary_page(task_id, **params)`（lock 內取 `result`，lock 外投影）；`api/routes/ic_analysis.py::get_result_summary_page`（Query 驗證：`limit` clamp、`sort_by` 非白名單 ⇒ `HTTPException(400)`）；`api/models/ic_models.py::ICSummaryPageResponse`。
- 實作要點：①`order` 只准 contract `order_values`；②`pass_class` 精確匹配、`q` 為 `feature_name.lower()` 子字串；③`total` 為篩選後列數；④`rows` 為原 dict 不裁欄（前端表格已消費全部欄）；⑤`_finite_or_neg_inf` 從 `momentum/Analysis/ic_reporter.py` import（不複製）。
- 修改檔案：如上四檔。　既有 caller：新建無。
- 路徑：
  api/services/ic_result_projection.py
  api/services/ic_analysis_service.py
  api/routes/ic_analysis.py
  api/models/ic_models.py
  tests/api/test_icresult_paging.py
- 不可做：不讀 parquet；不快取；不做游標；不在 route 內排序。
- 邊界：①running ⇒ 404；②`offset ≥ total` ⇒ `rows=[]`；③`limit > limit_max` ⇒ clamp；④`icir` 全 None ⇒ 穩定序；⑤`q` 無命中 ⇒ `total=0`；⑥`sort_by=feature_name` 字串序。
- 風險緩解：SPEC §C-4 白名單。
- 驗證：`venv/bin/python -m pytest tests/api/test_icresult_paging.py -k summary_page -q` rc=0；G-2（逐頁 `limit=limit_max` 串接後依 `feature_name` 排序 == golden 全量列，列數 == `summary_rows`）；TestClient `sort_by=evil` ⇒ status == 400；`limit=99999` ⇒ 回應 `limit == limit_max`。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 1.2 — 單特徵詳情端點（`SPEC Task 1.2`）
- 目標：`GET /result/{task_id}/feature/{feature_name}` 回該特徵各段＋`summary_row`。
- 檔案：`api/services/ic_result_projection.py::project_feature(report: dict, name: str, contract: dict) -> dict|None`（None ⇒ route 404；段清單來自 contract `per_feature_sections`；SectionStatus 物件透傳；缺 ⇒ `null`）；service `get_result_feature_detail`；route `get_result_feature_detail`（`feature_name: str = Path(...)`，FastAPI 已解碼）；模型 `ICFeatureDetailResponse`。
- 實作要點：①`grouped_ic` 為 `{group: {feature: …}}` 時投影為 `{group: value_for_feature}`；②`rolling_ic_series[name]` 原樣（含三窗空陣列）；③`summary_row` 由 `summary_table` 線性找一次（39k 可接受；不建索引）。
- 修改檔案：同 1.1 三檔＋模型。　既有 caller：新建無。
- 路徑：
  api/services/ic_result_projection.py
  api/services/ic_analysis_service.py
  api/routes/ic_analysis.py
  api/models/ic_models.py
  tests/api/test_icresult_paging.py
- 不可做：不做批次；不回整份 grouped_ic；不對 name 做模糊匹配。
- 邊界：①名含 `-`／`.`／空白 ⇒ 精確匹配；②段為 SectionStatus ⇒ 透傳；③三窗皆空 ⇒ 空陣列；④name 不存在 ⇒ 404。
- 風險緩解：⊘。
- 驗證：`venv/bin/python -m pytest tests/api/test_icresult_paging.py -k feature_detail -q` rc=0；G-3（golden `feature_samples` 200 個特徵各段 canonical sha == 端點回值 sha）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 1.3 — `view=light` 摘要視圖（`SPEC Task 1.3`）
- 目標：`GET /result/{id}?view=light` 回去除 per-feature 段之報告＋`summary_page` 首頁＋`total_features`＋`view`；無 `view` 位元組不變。
- 檔案：`api/services/ic_result_projection.py::project_light_view(report: dict, contract: dict) -> dict`（刪 `per_feature_sections` 各段＋`summary_table`；`metadata` 只留 `metadata_keep_keys`；加 `summary_page=paginate_summary(rows, sort_by="icir", order="desc", offset=0, limit=limit_default)`）；`ic_analysis_service.get_result(task_id, schema_version, view)`（`view=="light"` 且 `schema_version==2` ⇒ `ValueError` → route 400）；route `get_result(view: Optional[Literal["light"]] = Query(None))`。
- 實作要點：①`deny_factor_in_ok_oos(normalized)` 在投影**之前**；②`{"raw": …}` 非 dict ⇒ 400；③`filter_log`／`grouped_ic` 摘要（非 per-feature 部分）／`marginal_ic`／`correlation_matrix`／`cross_sectional_*`／`module_statuses`／`analysis_status`／`oos_guarantees` 原樣。
- 修改檔案：如上三檔。　既有 caller：`useICAnalysis.fetchResult`／`refilter`（Phase 2 改）；既有 `/result` 測試不改。
- 路徑：
  api/services/ic_result_projection.py
  api/services/ic_analysis_service.py
  api/routes/ic_analysis.py
  tests/api/test_icresult_paging.py
- 不可做：不改預設回應；不把 light 設預設；不在 light 內補任何值。
- 邊界：①`{"raw":…}` ⇒ 400；②保留鍵缺席不補；③`summary_table` 空 ⇒ `summary_page.total == 0`；④`view=light&schema_version=2` ⇒ 400。
- 風險緩解：SPEC §G G-1。
- 驗證：`venv/bin/python -m pytest tests/api/test_icresult_paging.py -k light_view -q` rc=0；G-1（預設回應 canonical sha == golden `report_canonical_sha`）；G-4（light 之保留段逐鍵 == 全量）；G-5（fake task 載入 `data_cache/reports/ic_report_ic_gatekeeper.json` 時 light canonical JSON ≤ 2097152 bytes、`summary?limit=50` ≤ 102400 bytes、任一 `feature/{name}` ≤ 2097152 bytes；此測試在檔案缺席時 `pytest.skip`，並在 receipt `handoffs/run_receipts/icresult_size_budget.log` 留實跑值）；`venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_survivor_contract.py -q` rc=0。
- **存活至**：永久。
- **覆蓋風險**：無。

### Phase 1 測試＋Gate
- 單元：`paginate_summary`／`project_feature`／`project_light_view` 純函式（合成 5 列小報告：含 `icir=None`、SectionStatus 段、特殊字元名）。
- 整合：TestClient＋fake task（`ic_analysis_service._tasks[task_id] = {"status":"completed","result": <ichc_run 報告>}`）。
- Golden：G-1～G-5。
- mutation（`handoffs/<date>-icresult-paging-mutate.py --phase 1`）：P1 切片 off-by-one ⇒ `-k summary_page` 紅；P2 白名單放寬 ⇒ `-k sort_by_whitelist` 紅；P3 `project_feature` 段錯位 ⇒ `-k feature_detail` 紅；P4 light 忘刪 `turnover_analysis` ⇒ `-k size_budget or light_view` 紅；P5 light 誤刪 `filter_log` ⇒ `-k light_view` 紅；P6 預設 `/result` 誤套 light ⇒ `-k default_unchanged` 紅；C0 註解 ⇒ 綠。Gate：`bash scripts/icresult_paging_phase_gate.sh 1` rc=0（skip=0、UNCOVERED=0）。

## Phase 2 — 前端改吃投影（完成後：39k run 首屏可互動，DOM 列數 ≤ 每頁 limit）

### Task 2.1 — hook／store／types（`SPEC Task 2.1`）
- 目標：`fetchResult`／`refilter` 改 `view=light`；新增 `fetchSummaryPage`／`fetchFeatureDetail`；store 持 `reportLight`、`summaryPage`、`featureDetail`、`selectedFeatureSet`。
- 檔案：`frontend/src/hooks/useICAnalysis.ts`（`fetchResult`：`requestJson<ICReportLight>(`/result/${taskId}?view=light`)`；回應 `view !== 'light'` ⇒ `setError('後端版本過舊：未回 light 視圖')` 不 setReport；`fetchSummaryPage(params: SummaryPageParams)`；`fetchFeatureDetail(name)` 去抖 150 ms＋`AbortController`）；`frontend/src/store/icAnalysisStore.ts`（`report: ICReportLight|null`、`summaryPage`、`summaryParams`、`featureDetail`、`selectedFeatureSet: Set<string>`；`setSelectedFeature` 觸發 detail 拉取由 hook 做）；`frontend/src/lib/types.ts`（`ICReportLight = Omit<ICReport, per-feature 四段|'coverage_analysis'|'summary_table'> & {view:'light'; total_features:number; summary_page: ICSummaryPage}`、`ICSummaryPage`、`ICFeatureDetail`、`SummaryPageParams`）。
- 實作要點：①`activeFeature` 變更 ⇒ effect 呼叫 `fetchFeatureDetail`，前一請求 abort；②refilter 成功 ⇒ `summaryParams.offset=0` 重拉首頁；③`selectedFeatures: string[]` 對外 API 保留（ExportButtons 用），內部以 Set 實作。
- 修改檔案：如上三檔。　既有 caller：`page.tsx`、`ExportButtons`、`ICSummaryTable`、各圖表。
- 路徑：
  frontend/src/hooks/useICAnalysis.ts
  frontend/src/store/icAnalysisStore.ts
  frontend/src/lib/types.ts
  frontend/src/hooks/*.test.ts
  frontend/src/store/*.test.ts
- 不可做：不在前端排序／篩選；不保留整份報告；不 polyfill 舊後端。
- 邊界：①切換特徵時前請求未回 ⇒ abort；②detail 404 ⇒ `featureDetail={status:'missing'}`；③後端舊版 ⇒ 錯誤文案不吃全量。
- 風險緩解：⊘。
- 驗證：`(cd frontend && npx vitest run src/hooks src/store)` rc=0（新測：light 回應 setReport、`view` 不符 ⇒ setError、detail abort 舊請求、refilter 重置 offset）；`npx tsc --noEmit -p tsconfig.json` 之 `error TS` 計數 == 8。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.2 — 表格伺服器分頁（`SPEC Task 2.2`）
- 目標：`ICSummaryTable` 只畫當頁列；排序／搜尋／pass_class 走 API；勾選 O(1)。
- 檔案：`frontend/src/components/ic-analysis/ICSummaryTable.tsx`（props 改 `page: ICSummaryPage`、`params`、`onParamsChange`；移除 `sortedData` useMemo；`SortButton` ⇒ `onParamsChange({sort_by, order, offset:0})`；分頁列：上一頁／下一頁／每頁 50|100|200／「第 x–y 列，共 total」；勾選 `selectedFeatureSet.has`）；`frontend/src/app/ic-analysis/page.tsx`（`summaryTable` 消費者改 `summaryPage.rows`；全選＝當頁）。
- 實作要點：①`limit` 選項 ≤ contract `limit_max`；②搜尋框 300 ms 去抖 → `q`；③`activeFeature` 預設＝首頁第一列。
- 修改檔案：如上兩檔。　既有 caller：`page.tsx`。
- 路徑：
  frontend/src/components/ic-analysis/ICSummaryTable.tsx
  frontend/src/components/ic-analysis/ICSummaryTable.*.test.tsx
  frontend/src/app/ic-analysis/page.tsx
- 不可做：不加虛擬捲動依賴；不在前端保留全量列。
- 邊界：①`total=0` 空狀態；②末頁不足；③排序切換 offset 歸 0；④`icir` null 顯示 `--`（既有測試不改）。
- 風險緩解：⊘。
- 驗證：`(cd frontend && npx vitest run src/components/ic-analysis/ICSummaryTable)` rc=0（新測：`total=39346, rows=50` ⇒ `<tr>` == 51；`Array.prototype.includes` spy 在 200 次勾選中呼叫次數 == 0；排序點擊 ⇒ `onParamsChange` 收到 `offset:0`）；`ICSummaryTable.icirNull.test.tsx` 斷言不改仍 rc=0。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.3 — 匯出與其餘消費者（`SPEC Task 2.3`）
- 目標：所有讀 `report` 的元件改吃 `ICReportLight`；匯出改逐頁串接。
- 檔案：`frontend/src/components/ic-analysis/ExportButtons.tsx`（`summaryTable` prop 改由內部 `fetchSummaryPage(limit=limit_max)` 逐頁拉齊，進度文案「匯出中 x/total」）；`FilterFunnelChart`／`DegradedBanner`／`IsolationNote`／`PeriodAlignmentBanner`／`MarginalICTable`／`CorrelationHeatmap`／`CrossSectionalICHeatmap`／`CrossSymbolValidationPanel`／`EventTablesPanel`／`EventBatchDisclosurePanel` props 型別放寬為 `ICReportLight | ICReport`；圖表（`ICDecayChart`／`QuantileReturnChart`／`TurnoverTimeSeriesChart`／`RollingICChart`／`GroupedICBarChart`／`RegimeRadarChart`）改由 `page.tsx` 餵 `featureDetail`。
- 實作要點：①`page.tsx::sectionSplit` 改讀 `featureDetail`（SectionStatus 透傳語意不變）；②`deep_analysis_enabled` 等 root 鍵 light 已含；③匯出 79 頁請求序列化（不併發）。
- 修改檔案：如上。　既有 caller：`page.tsx`。
- 路徑：
  frontend/src/components/ic-analysis/*.tsx
  frontend/src/app/ic-analysis/page.tsx
- 不可做：不改匯出檔格式；不動 `ScanCubeBrowser`／deep-analysis 端點。
- 邊界：①匯出中途失敗 ⇒ 顯示失敗頁碼、不輸出半份；②light 缺 `marginal_ic`（不應發生，G-4）⇒ `SectionStatusNotice` 顯示不適用。
- 風險緩解：⊘。
- 驗證：`(cd frontend && npx vitest run src/components/ic-analysis)` rc=0（既有斷言不改）；新測：匯出 fake `total=120, limit_max=50` ⇒ 3 次請求、輸出列數 == 120；`npx tsc --noEmit -p tsconfig.json` `error TS` == 8。
- **存活至**：永久。
- **覆蓋風險**：無。

### Phase 2 測試＋Gate
- vitest：hooks／store／表格／匯出；tsc 不增錯。Gate：`(cd frontend && npx vitest run)` rc=0 且 `error TS` == 8。

## Phase 3 — 實機驗收（完成後：使用者簽 B34）

### Task 3.1 — UAT B34（`SPEC Task 3.1`）
- 目標：使用者以 39,346 特徵 run 驗：首屏 ≤ 3 秒可互動、翻頁／排序 ≤ 1 秒、點特徵圖表 ≤ 2 秒。
- 檔案：`白話說明/GAP-3驗收清單.md`（B34 段＋進度列）；`白話說明/現在做到哪.md`。
- 實作要點：①白話寫「要先重啟後端」；②寫「後端版本過舊」錯誤的含義；③寫 G-5 實跑數字（light 幾 MB）。
- 修改檔案：兩份白話。　既有 caller：無。
- 路徑：
  白話說明/GAP-3驗收清單.md
  白話說明/現在做到哪.md
- 不可做：不以縮小特徵數當通過；HANDOFF／白話依 claim guard 規則措辭。
- 邊界：①後端未重啟 ⇒ 前端顯示「後端版本過舊」（Task 2.1 邊界③）；②使用者用舊 run（task 已不在記憶體）⇒ 404 文案。
- 風險緩解：⊘。
- 驗證：使用者實機簽 B34（`blocked-by:使用者`）；Claude 端 `venv/bin/python -m pytest tests/api/test_icresult_paging.py -k size_budget -q` rc=0 且 receipt `handoffs/run_receipts/icresult_size_budget.log` 含 `light_bytes=` ≤ 2097152。
- **存活至**：永久。
- **覆蓋風險**：無。

## 追溯（SPEC ID → TODO）
Task 1.1→1.1；1.2→1.2；1.3→1.3；2.1→2.1；2.2→2.2；2.3→2.3；3.1→3.1；§G B-1／B-2／G-1～G-5→0.1＋1.1～1.3；§V P1–P6／C0→Phase 1 Gate；§N IP-RESID-1～3→不入 Task（登記處 `docs/IC_QUANT_GAP_REGISTRY.md`，由 B3 收案時同步）。合計：Task 7／Golden 7／mutation 7／殘留 3。
