# ICRESULT_PAGING — IC 結果分頁與按需載入 — SPEC

> 來源 PLAN/診斷：UAT 2026-09-09（使用者：「網頁顯示 30K 多的特徵，整個網頁很慢，幾乎不會動」）　|　日期：2026-09-09　|　對應 TODO：`docs/ICRESULT_PAGING_TODO.md`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。
- **命中高風險原則**：(b) 跨模組共用路徑——`GET /result/{task_id}` 為前端、匯出、golden replay、`test_ic1d_baseline`／survivor 契約測試之共用出口；改動面橫跨 `api/routes`＋`api/services`＋`api/models`＋`frontend`。不命中 (a)(d)：**不改任何數值、不改報告落檔、不改 orchestrator**——只改搬運方式。
- **RISK-HIT 宣告**（機檢依據，缺行 FAIL）：
RISK-HIT: b
- 命中 (a) 或 (d) → 否；§G 仍填（改前==改後之位元組級／集合級對照是本票唯一防假綠手段）。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已核實事實**（FACT-RECEIPT 七條如下，主委實跑 2026-09-09）：
  - FACT-RECEIPT: `ls -la data_cache/reports/ic_report_ic_gatekeeper.json` → 印出 `118894891`（118.9 MB；Claude 實跑 2026-09-09）
  - FACT-RECEIPT: `jq -c '{st:(.summary_table|length), rs:(.rolling_ic_series|length)}'` → 印出 `{"st":39346,"rs":39346}`（Claude 實跑 2026-09-09）
  - FACT-RECEIPT: 各段 `jq -c ".<k>" | wc -c` → `turnover_analysis 50938089`、`ic_decay 16436560`、`summary_table 14544874`、`grouped_ic 9745300`、`quantile_returns 8679685`、`metadata 8417776`、`rolling_ic_series 3643397`、`coverage_analysis 3644737`、`filter_log 3282725`、`correlation_matrix 28`（Claude 實跑 2026-09-09）
  - FACT-RECEIPT: `jq -r '.metadata | keys | length'` → 印出 `39398`；前 12 大鍵＝`selection_scope 3273340` 之後全是 per-feature 描述子（`{category,layer,name}` 各 111 bytes × 39,346）（Claude 實跑 2026-09-09）⇒ **metadata 被 per-feature 描述子扁平污染**，光 metadata 就 8.4 MB
  - FACT-RECEIPT: `grep -n 'sortedData.map' frontend/src/components/ic-analysis/ICSummaryTable.tsx` → 印出 `360:                {sortedData.map((item, index) => {`；`selectedFeatures.includes(item.feature_name)` 逐列（Claude 實跑 2026-09-09）⇒ 全量 DOM＋O(n²) 勾選
  - FACT-RECEIPT: `grep -n 'requestJson<ICReport>' frontend/src/hooks/useICAnalysis.ts` → 印出 `103: … /result/${taskId}` 與 `598: … /refilter?task_id=`（Claude 實跑 2026-09-09）⇒ 前端兩處吃整份報告
  - FACT-RECEIPT: `api/services/ic_analysis_service.py:1789` `if not settings.ic_response_v2 or schema_version != 2: return normalized` 且 `api/core/config.py:76` `ic_response_v2: bool = Field(default=False, …)`（Claude 讀碼 2026-09-09）⇒ 既有 `schema_version=2` top-N 路徑**預設關閉且前端從未呼叫**；其回應只有 `top_n_summary`＋`artifact_uri`，不含圖表所需各段 ⇒ 不能直接拿來當本票解
  - FACT-RECEIPT: `grep 'report?\.' frontend/src/app/ic-analysis/page.tsx` → 頁面消費 11 段：`summary_table`／`filter_log`／`metadata`／`ic_decay`／`quantile_returns`／`grouped_ic`／`turnover_analysis`／`rolling_ic_series`／`correlation_matrix`／`marginal_ic`／`cross_sectional_symbol_ic`；per-feature 四段（decay／quantile／turnover／rolling）皆以 `activeFeature` 取單鍵（Claude 實跑 2026-09-09）
- **待使用者確認**：`待確認：無`（技術取捨依 `feedback_delegate_technical_decisions` 交委員會；使用者已於 2026-09-09 白話段知悉方向：「後端只回摘要層、表格分頁、點到才拉、落檔不動」）。
- **已確認結果**：`2026-09-09 使用者提出 UAT 症狀並要求修正；方向由 Claude 白話說明，未否決`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條；R4 服務不互 import；R7 DTO 不跨界（新回應模型放 `api/models/ic_models.py`，service 只回 dict）。
- **不變式（本票紅線）**：
  1. `GET /result/{task_id}`（無 `view` 參數）**位元組級不變**——golden replay、`test_ic1d_baseline`、survivor／contract 測試、匯出皆走此路，不得動。
  2. 落檔 `ic_report_*.json` 與 orchestrator／reporter **一行不改**（`RISK-HIT: b` 不含 a/d 的憑據）。
  3. 分頁／單特徵端點回的值必須是**同一份** `task_info["result"]` 的投影（不重算、不讀檔、不另存）；重組後與全量報告 **集合相等**（§G）。
  4. 排序／篩選欄位**白名單**（封閉集合，機檢），非白名單 ⇒ 400；禁 eval／getattr 動態欄位。
  5. 前端**不得**在 light 視圖下靜默補值：缺段 ⇒ 顯示「按需載入中／不適用」，不填 0／[]。
- 既有 caller／下游：`useICAnalysis.fetchResult`（`:103`）、`refilter`（`:598`）、`ExportButtons`（吃 `report.module_statuses`＋`summaryTable` prop）、`ScanCubeBrowser`（獨立端點，不動）、deep-analysis（獨立端點，不動）。
- **新資料結構單一真相源**：分頁回應 schema 與白名單放 `api/models/ic_models.py`（pydantic）＋ `momentum/Analysis/contracts/ic_result_paging_contract.json`（白名單欄位、預設 `limit`、上限）；SPEC 只 pointer，不在散文列舉欄位。

## §G Golden / Baseline
- **feature/kline 條件**：不涉 feature／kline 生成計算——略過三方 kline 簽核（§N）。
- **凍結時機 / reference 設定**：動工前以 `tests/momentum/helpers/ichc_run.run_analyze`（ETHUSDT 12h la0 fixture）產一份全量報告存進 service 之 `task_info["result"]`（測試用 fake task），並以 `tests/golden/icresult_paging/full_report_projection.json` 凍結：`summary_table` 列數＋`feature_name` 集合 sha256＋各段鍵集 sha256＋整份 canonical sha（沿 `ichc_run.canonical_sha`）。
- **baseline 內容**：
  - B-1 預設 `/result` 回應 canonical sha（改前）；
  - B-2 per-feature 四段＋`coverage_analysis` 之 `{feature: canonical sha(value)}` 對照表（抽樣 200 特徵＋全量 feature 集合 sha）。
- **通過條件（可證偽）**：
  - G-1 改後預設 `/result` canonical sha == B-1（位元組級不變）。
  - G-2 `/result/{id}/summary` 以 `limit=max` 逐頁抓完並依 `feature_name` 排序 == 全量 `summary_table` 依同鍵排序（列數、每列 dict 相等）。
  - G-3 對 B-2 每個抽樣特徵，`/result/{id}/feature/{name}` 回的各段 == 全量報告該段 `[name]`（canonical sha 相等）。
  - G-4 `view=light` 回應：`summary_table` 缺席或僅含首頁、per-feature 四段與 metadata per-feature 描述子缺席；其餘段（`filter_log`／`metadata` 非描述子鍵／`grouped_ic` 摘要／`marginal_ic`／`correlation_matrix`／`cross_sectional_*`／`module_statuses`／`analysis_status`／`oos_guarantees`）與全量報告**逐鍵相等**。
  - G-5 尺寸：對 39,346 特徵之實機報告（`data_cache/reports/ic_report_ic_gatekeeper.json` 載入為 fake task），`view=light` 回應 canonical JSON ≤ **2 MB**；`summary?limit=50` ≤ 100 KB；`feature/{name}` ≤ 2 MB。超出即 FAIL 並列出最大段。

## §P Phase 與依賴

### Phase 1 — 後端投影端點（依賴：無）
**Task 1.1 — summary 分頁端點**
- 目標：`GET /result/{task_id}/summary?sort_by=&order=&offset=&limit=&pass_class=&q=` 回 `{total, offset, limit, sort_by, order, rows}`，只投影 `task_info["result"]["summary_table"]`。　檔案：`api/routes/ic_analysis.py::get_result_summary_page`、`api/services/ic_analysis_service.py::ICAnalysisService.get_result_summary_page`、`api/models/ic_models.py::ICSummaryPageResponse`、`momentum/Analysis/contracts/ic_result_paging_contract.json`（`sort_fields` 白名單、`limit_default=50`、`limit_max=500`、`q` 為 `feature_name` 子字串不分大小寫）。　既有 caller：新建無 caller。
- 改法：service 讀 result → 白名單驗 `sort_by`（預設 `icir`）→ 排序 key 用既有 `_finite_or_neg_inf` 語意（None／NaN 沉底，與 `get_top_features` 一致）→ `pass_class`／`q` 篩選 → 切片。全程純函式 `paginate_summary(rows, params) -> page`（可單測，不碰 lock 以外狀態）。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k summary_page THEN rc=0`；G-2；`ASSERT curl /result/<id>/summary?sort_by=evil WHEN task=completed THEN rc=400`（以 TestClient 斷言 status 400）。
- **邊界**：①result 尚未產生（running）⇒ 404 同 `/result`；②`offset ≥ total` ⇒ `rows=[]`、`total` 正確；③`limit>limit_max` ⇒ clamp 至 `limit_max` 並在回應 `limit` 回真值；④`icir` 全 None（事件路徑）⇒ 排序不拋、順序穩定（次鍵 `feature_name`）；⑤`q` 無命中 ⇒ `total=0`。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不讀 parquet artifact、不重算任何指標、不快取到檔案、不加 offset 以外的游標機制。

**Task 1.2 — 單特徵詳情端點**
- 目標：`GET /result/{task_id}/feature/{feature_name}` 回該特徵之 `ic_decay`／`quantile_returns`／`turnover_analysis`／`coverage_analysis`／`rolling_ic_series`／`grouped_ic`（若為 per-feature map 則取該鍵；若為 SectionStatus 物件則原樣透傳）＋`summary_row`。　檔案：同 1.1 之 route／service；模型 `ICFeatureDetailResponse`。　既有 caller：新建無 caller。
- 改法：純函式 `project_feature(report, name) -> dict`；`name` 不存在 ⇒ 404；段缺席 ⇒ 該鍵 `null`（不填 `{}`）。
- **驗證**：G-3；`ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k feature_detail THEN rc=0`。
- **邊界**：①特徵名含 URL 特殊字元（`-`／`_`／`.`／空白）⇒ path 解碼後精確匹配；②段為 SectionStatus（xsec 不適用）⇒ 透傳物件；③`rolling_ic_series[name]` 三窗皆空（1h fallback）⇒ 回空陣列不拋。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不做多特徵批次端點（前端一次只看一個）；不回整份 grouped_ic。

**Task 1.3 — `view=light` 摘要視圖**
- 目標：`GET /result/{task_id}?view=light` 回全量報告**去除** per-feature 四段＋`coverage_analysis`＋`summary_table`（改為 `summary_page`＝1.1 首頁，`limit=50`，`sort_by=icir`）＋ metadata per-feature 描述子（只保留 `ic_result_paging_contract.json::metadata_keep_keys` 白名單鍵——封閉集合，機檢），並加 `view:"light"`、`total_features`。無 `view` ⇒ 行為不變（G-1）。　檔案：route `get_result`（加 `view: Optional[Literal["light"]]`）、service `project_light_view(report) -> dict`。　既有 caller：`useICAnalysis.fetchResult`／`refilter`（Phase 2 改）。
- 改法：純函式；`deny_factor_in_ok_oos` 仍先跑（出口守衛不變）；`schema_version=2` 與 `view=light` 互斥（同時給 ⇒ 400）。
- **驗證**：G-1、G-4、G-5；`ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k light_view THEN rc=0`；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_survivor_contract.py -q THEN rc=0`（既有出口不變）。
- **邊界**：①report 為 `{"raw": …}` 非 dict ⇒ light 回 400（不猜）；②metadata 白名單鍵缺席 ⇒ 不補；③`summary_table` 空 ⇒ `summary_page.total=0`。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改預設回應一個 byte；不把 light 設為預設。

### Phase 2 — 前端改吃投影（依賴：Phase 1）
**Task 2.1 — hook／store 改 light＋分頁＋單特徵**
- 目標：`fetchResult`／`refilter` 改打 `view=light`；新增 `fetchSummaryPage(params)`／`fetchFeatureDetail(name)`；store 加 `summaryPage`、`featureDetail`、`selectedFeatureSet: Set<string>`。　檔案：`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`、`frontend/src/lib/types.ts`（`ICReportLight`、`ICSummaryPage`、`ICFeatureDetail`）。　既有 caller：`page.tsx`、`ExportButtons`、`ICSummaryTable`。
- 改法：`activeFeature` 變更 ⇒ 拉 `feature/{name}`（去抖 150 ms、AbortController 取消前一請求）；圖表 props 改讀 `featureDetail`；`summaryTable` 消費者改讀 `summaryPage.rows`。
- **驗證**：`ASSERT (cd frontend && npx vitest run src/hooks src/store) THEN rc=0`；`npx tsc --noEmit` 錯誤數 == 既有 8（不增）。
- **邊界**：①切換特徵時上一請求未回 ⇒ 取消，不覆蓋新特徵；②`feature` 404 ⇒ 圖表區顯示「此特徵無詳情」不填假資料；③refilter 後 `summaryPage` 重置到第 1 頁。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不在前端做任何排序／篩選（全交後端）；不保留整份報告在 store。

**Task 2.2 — 表格分頁化**
- 目標：`ICSummaryTable` 改為伺服器分頁（每頁 50，可切 100／200），排序按鈕改觸發 API `sort_by/order`，搜尋框接 `q`，`pass_class` 篩選接 API；勾選改 `Set`。　檔案：`frontend/src/components/ic-analysis/ICSummaryTable.tsx`、`page.tsx`。　既有 caller：`page.tsx`（`onSelectFeatures` 全選＝當頁全選，並顯示「已選 N／共 total」）。
- 改法：移除 `sortedData` 全量排序；DOM 列數 ≤ `limit`。
- **驗證**：vitest：render 39,346 列 fake page 回應（`total=39346, rows=50`）⇒ DOM `<tr>` 數 == 51（含表頭）；勾選 200 次 ⇒ 每次 O(1)（以 `Set.has` spy 斷言不呼叫 `Array.includes`）；`ICSummaryTable.icirNull.test.tsx` 既有斷言不變。
- **邊界**：①`total=0` ⇒ 空狀態文案；②最後一頁不足 50 列；③排序切換時 offset 歸 0。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不引入虛擬捲動套件（分頁已足；`package.json` 無 tanstack-virtual，禁為此加依賴）。

**Task 2.3 — 匯出與其餘消費者**
- 目標：`ExportButtons` 匯出改走後端既有匯出端點或 `summary?limit=limit_max` 逐頁串接（不用 store 的整份報告）；`FilterFunnelChart`／`DegradedBanner`／`IsolationNote`／`PeriodAlignmentBanner`／`MarginalICTable`／`CorrelationHeatmap`／xsec 面板改讀 light 報告（這些段 light 已含，G-4）。　檔案：各元件 props 型別由 `ICReport` 放寬為 `ICReportLight`。
- **驗證**：`ASSERT (cd frontend && npx vitest run src/components/ic-analysis) THEN rc=0`（既有元件測試斷言不改）；`npx tsc --noEmit -p tsconfig.json` 之 `error TS` 計數 == 8（既有值，不增）；匯出 39,346 列 fake page 串接 ⇒ 匯出列數 == 39346。
- **邊界**：匯出 39,346 列時逐頁 79 次請求 ⇒ 顯示進度，不凍 UI。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改匯出檔格式。

### Phase 3 — 實機驗收（依賴：Phase 2）
**Task 3.1 — 39k 實機 UAT B34**
- 目標：使用者以同一份 39,346 特徵 run 開頁面：首屏 ≤ 3 秒可互動、翻頁／排序 ≤ 1 秒、點特徵圖表 ≤ 2 秒。　檔案：`白話說明/GAP-3驗收清單.md` B34。
- **驗證**：使用者實機（`blocked-by:使用者`）；Claude 端 `ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k size_budget THEN rc=0`（以 `data_cache/reports/ic_report_ic_gatekeeper.json` 載入 fake task，light ≤ 2097152 bytes、summary?limit=50 ≤ 102400 bytes）。
- **邊界**：後端未重啟 ⇒ 前端打 `view=light` 得整份（舊碼忽略 query）⇒ 前端偵測 `view!=="light"` 顯示「後端版本過舊」而非靜默吃全量。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以縮小特徵數當通過。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：RISK-HIT 不含 a/d，但 G-1～G-4 宣稱「投影＝全量」屬正確性主張 ⇒ 附 mutation（`handoffs/<date>-icresult-paging-mutate.py`）：P1 分頁切片 off-by-one（`rows[offset:offset+limit]`→`rows[offset+1:…]`）⇒ G-2 紅；P2 白名單放寬（`sort_by` 任意）⇒ 400 測試紅；P3 `project_feature` 取錯段（`ic_decay`←`quantile_returns`）⇒ G-3 紅；P4 light 忘刪 `turnover_analysis` ⇒ G-5 紅；P5 light 誤刪 `filter_log` ⇒ G-4 紅；P6 預設 `/result` 誤套 light ⇒ G-1 紅；C0 只改註解 ⇒ 綠。
- 測試層級：單元（純函式 `paginate_summary`／`project_feature`／`project_light_view`）、整合（TestClient 路由＋fake task）、Golden（G-1～G-5）、前端 vitest。可獨立 `pytest tests/api/test_icresult_paging.py`。
- **防假綠**：既有 `/result` 測試斷言一條不改；`ICSummaryTable.icirNull.test.tsx` 斷言不改。
- **邊界目錄**：空 summary_table ✓(1.1⑤／1.3③)；`icir` 全 None ✓(1.1④)；特殊字元特徵名 ✓(1.2①)；SectionStatus 段 ✓(1.2②)；running 未完成 ✓(1.1①)；後端舊版 ✓(3.1)；大尺度 39k ✓(G-5)。

## §R 回退
- Phase 1 純新增端點＋`view` 參數，預設路徑不變，可單獨 revert；Phase 2 單一 commit revert 即回全量模式。無 feature flag（正確化＋預設不變，符合 `feedback_no_default_off_after_validation`）。

## §N N/A 登記
- §G 三方 kline 簽核子項：N/A — 不碰 feature／kline／IC 計算；golden 為報告投影對照。
- 殘留：`IP-RESID-1` metadata 被 39,346 個 per-feature 描述子扁平污染（reporter 寫入面）— `為何現在不做: blocked-by:改 reporter 會動落檔格式與 gap2／ic1d golden（命中 a），須另票走三方簽核`；觸發：下一次 reporter 改版；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`。
- 殘留：`IP-RESID-2` `turnover_analysis` 每特徵含全長 `time_series`（51 MB 主因）落檔量 — `為何現在不做: blocked-by:同 IP-RESID-1（落檔格式）`；觸發：同上。
- 殘留：`IP-RESID-3` 既有 `schema_version=2`（`IC_RESPONSE_V2`）top-N 路徑與本票 light 視圖並存 — `為何現在不做: user-ruling:2026-06-25 IC Phase1 決策「API 現在版本化（top-N＋artifact URI）」為既定契約，本票不合併亦不刪`；觸發：v2 契約消費者出現時統一。
