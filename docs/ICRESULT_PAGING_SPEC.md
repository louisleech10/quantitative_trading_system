# ICRESULT_PAGING — IC 結果分頁與按需載入 — SPEC（R3 修訂）

> 來源 PLAN/診斷：UAT 2026-09-09（使用者：「網頁顯示 30K 多的特徵，整個網頁很慢，幾乎不會動」）　|　日期：2026-09-09（R1 修訂）　|　對應 TODO：`docs/ICRESULT_PAGING_TODO.md`
> R1 修訂來源：`handoffs/reconcile/20260909-icresultpaging-x-review-r1/synth.md`（Z1–Z7）。R2 修訂來源：`handoffs/reconcile/20260909-icresultpaging-x-review-r2/synth.md`（Y1–Y6）。R3 修訂來源：`handoffs/reconcile/20260909-icresultpaging-x-review-r3/synth.md`（守衛計數矛盾、`SIZE_GATE` 單一文法、feature-count dict `count` 語意＋funnel 先於計數＋stage3、G-7b sentinel、B2 page 表格斷言、參數名對齊 Feature Factory）。

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。
- **命中高風險原則**：(b) 跨模組共用路徑——`GET /result/{task_id}` 為前端、匯出、golden replay、`test_ic1d_baseline`、survivor 契約測試之共用出口；改動面橫跨 `api/routes`＋`api/services`＋`api/models`＋`frontend`。不命中 (a)(d)：**不改任何數值、不改報告落檔、不改 orchestrator**——只改搬運方式。
- **RISK-HIT 宣告**（機檢依據，缺行 FAIL）：
RISK-HIT: b
- 命中 (a) 或 (d) → 否；§G 仍填（改前==改後之位元組級／集合級對照是本票唯一防假綠手段）。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已核實事實**（FACT-RECEIPT 十條如下，主委實跑 2026-09-09）：
  - FACT-RECEIPT: `ls -la data_cache/reports/ic_report_ic_gatekeeper.json` → 印出 `118894891`（118.9 MB）
  - FACT-RECEIPT: `jq -c '{st:(.summary_table|length), rs:(.rolling_ic_series|length)}'` → 印出 `{"st":39346,"rs":39346}`
  - FACT-RECEIPT: 各段 `jq -c ".<k>" | wc -c` → `turnover_analysis 50938089`、`ic_decay 16436560`、`summary_table 14544874`、`grouped_ic 9745300`、`quantile_returns 8679685`、`metadata 8417776`、`rolling_ic_series 3643397`、`coverage_analysis 3644737`、`filter_log 3282725`、`correlation_matrix 28`
  - FACT-RECEIPT: `jq -r '.metadata | keys | length'` → 印出 `39398`；`selection_scope 3273340` bytes（鍵 `base_universe_hash,evaluated_features,method,n_tests,scope_id,split_label,universe_features`，兩 list 各 ~39k），其餘全是 per-feature 描述子（`{category,layer,name}` × 39,346）
  - FACT-RECEIPT: `jq -c '[.filter_log[] | to_entries[] | select(.value|type=="object" or type=="array") | .key] | unique'` → 印出 `["consumed_event_labels","output_features","per_bar_validity","removed_features","removed_nan_features","skipped_winsorization","split_mask","winsorized_features"]`（`winsorized_features` array 1637874 bytes）
  - FACT-RECEIPT: `venv/bin/python handoffs/_light_size_probe.py`（刪七段含 `grouped_ic`、metadata 顯式保留鍵、`selection_scope`／`filter_log` 集合值→計數、`summary_page` 首頁 50 列）→ 印出 `light_bytes 28019`（`summary_page 19446`、`metadata 7932`、`marginal_ic 1208`）
  - FACT-RECEIPT: `grep -rhoE 'metadata[?]?\.[a-zA-Z_]+' frontend/src`（排除 test）→ IC 相關鍵：`oos_downgrade`、`period_alignment`、`isolation`、`ic_window_disclosure`、`event_filter`、`n_timestamps`、`n_symbols`、`mode`、`ic_train_test_split`、`survivor_output`、`compute_warnings`；後端 `survivor_contract.py:598,615` 讀 `selection_scope.scope_id`；service 讀 `symbol`／`timeframe`／`config_hash`／`period_alignment`／`isolation`／`ic_train_test_split`
  - FACT-RECEIPT: `grep -n 'task_info\["result"\] =' api/services/ic_analysis_service.py` → `:1623`／`:2339`／`:2631`（refilter）⇒ completed 後 result **會被替換**，需世代戳
  - FACT-RECEIPT: `frontend/src/components/ic-analysis/ICSummaryTable.tsx:91-106` `getSortValue` 非有限值→`-Infinity`、tie 回 0 無次鍵；`jq '[.summary_table[].icir]|map(select(.!=null))|length'` → `0`（39k run icir 全 null）⇒ 現行前端首列＝輸入序首列
  - FACT-RECEIPT: `api/routes/ic_analysis.py:649-687` 既有 `GET /export/{task_id}/{format}`（`json`／`ai_json`／`csv_summary`／`csv_detailed`／`markdown`／`hdf5`），`ExportButtons.tsx:47-66` 已組該 URL；`summaryTable` prop 只用於 PNG 按鈕 disable
- **待使用者確認**：`待確認：無`（技術取捨依 `feedback_delegate_technical_decisions` 交委員會；使用者已於 2026-09-09 白話段知悉方向：「後端只回摘要層、表格分頁、點到才拉、落檔不動」）。
- **已確認結果**：`2026-09-09 使用者提出 UAT 症狀並要求修正；方向由 Claude 白話說明，未否決`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條；R4 服務不互 import；R7 DTO 不跨界（新回應模型放 `api/models/ic_models.py`，service 只回 dict）。
- **不變式（本票紅線）**：
  1. `GET /result/{task_id}`（無 `view` 參數）**原始 HTTP body 位元組級不變**（G-1 以 raw bytes sha 驗，canonical sha 只作輔助；R1 `CODEX-R1-P1-04`）。
  2. 落檔 `ic_report_*.json` 與 orchestrator／reporter **一行不改**。
  3. 分頁／單特徵／light 端點回的值必須是**同一份** `task_info["result"]` 的投影（不重算、不讀檔、不另存）；重組後與全量報告 **集合相等**（§G）。
  4. 排序／篩選欄位**白名單**（封閉集合，機檢），非白名單 ⇒ 400；禁 eval／getattr 動態欄位。
  5. 前端**不得**在 light 視圖下靜默補值：缺段 ⇒ 顯示「按需載入中／不適用」，不填 0／[]。
  6. **light 投影規則為封閉集合，全部住 contract JSON**（R1 P0）：(i) `drop_sections`（七段：`summary_table`／`ic_decay`／`quantile_returns`／`turnover_analysis`／`coverage_analysis`／`rolling_ic_series`／`grouped_ic`——`grouped_ic` 由 Task 1.2 單特徵投影供圖；R1 `GROK-R1-P2-02`）；(ii) `metadata` 只保留 `metadata_keep_keys`（**顯式列舉**＝前端＋後端消費者聯集，見 §A receipt；**不得**由 fixture 推導；R1 `CODEX-R1-P1-02`／`GROK-R1-P1-01`）；(iii) `collection_to_count_paths`＝顯式路徑規格清單，每條 `{path: ["filter_log", "*"]}` 或 `{path: ["metadata", "selection_scope"]}`：`*` **只匹配該層的直接子鍵**（一層，不遞迴），目標節點須為 dict，對其**直接子鍵**之 list／dict 值改為 `<key>_count`（int），標量原樣，更深層不動；目標缺席或非 dict ⇒ no-op（不拋、不補）；未知 stage 名同規則（R2 `CODEX-R2-P2-06`）；(iv) `funnel_stage_adapter`（R2 `CODEX-R2-P1-04`／`GROK-R2-P2-01`）：對 `filter_log` 每個 stage 依 contract 之「input 候選鍵序」`[input_features, feature_count_original]` 與「output 候選鍵序」`[output_features, feature_count_filtered]` 取第一個存在者：int 原樣；**dict 含 `count` 鍵（int）⇒ 取 `count`**（實機 `stage5_thresholds.output_features={"count":0,"pass_class":"oos"}` ⇒ 0，非 `len`=2；R3 `CODEX-R3-P1-03`）；其他 dict／list ⇒ `len`；兩者皆缺 ⇒ `null`（`stage3_event_filter` ⇒ `{null,null}`，不由前一 stage 推導；R3 `GROK-R3-P2-01`）。**funnel 必須對計數前的原始 `filter_log` 計算**（先算 `filter_log_funnel`，再對 light 的 `filter_log` 做 (iii) 計數；R3 `GROK-R3-P1-01`）；light 另寫 `filter_log_funnel: {stage: {input: int|null, output: int|null}}`，`FilterFunnelChart` 改讀此鍵（`null` ⇒ 顯示不適用，不補 0）；(v) 加 `view`、`total_features`、`result_revision`、`summary_page`。
  7. **結果世代戳**（R1 `CODEX-R1-P1-03`／`COMPOSER-R1-P1-02`／`GROK-R1-P2-01`）：service 對 `task_info["result"]` 每次寫入（完成／refilter／其他寫點）經單一 helper 遞增 `task_info["result_revision"]`（int，從 1 起）；light／summary／feature 回應皆帶 `result_revision`；summary／feature 請求可帶 `revision`，不符 ⇒ 409（回 `{current_revision}`）。**投影一律對 lock 內取出的不可變 snapshot `(report, revision)` 進行**，回應之 `result_revision` 為該 snapshot 的值（投影中途 refilter 不影響已取 snapshot；R2 `CODEX-R2-P1-02`）。**refilter handshake**：`POST /refilter?task_id=&view=light` 回 light 視圖（含新 `result_revision`）；無 `view` ⇒ 既有全量回應**不變**。前端：refilter 成功 ⇒ 以回應 `result_revision` 更新 store、abort 所有進行中 summary／feature 請求；任何 summary／feature 回應之 `result_revision != store.resultRevision` ⇒ **丟棄**不套用。
  8. **排序契約**（R1 `CODEX-R1-P1-04`／`COMPOSER-R1-P1-01`／`GROK-R1-P1-03`）：住 contract `sort_policy`——數值欄 comparator：缺值（None／NaN／±inf）**兩方向皆沉底**；主鍵依 `sort_order`；並列 ⇒ 次鍵 `feature_name` 升冪（字串）；`sort_by=feature_name` 純字串比較。**明文宣告：分頁序取代前端本地序，允許與舊前端 stable 序不同**（含 icir 全 null 時首列改變）；`get_top_features`／`_sort_artifact_rows` 不動。
- 既有 caller／下游：`useICAnalysis.fetchResult`（`:103`）、`refilter`（`:598`）、`ExportButtons`（匯出走 `/export/{id}/{format}` **不改**；R1 `CODEX-R1-P1-05`／`COMPOSER-R1-P1-03`／`GROK-R1-P1-02`）、`ScanCubeBrowser`（獨立端點，不動）、deep-analysis（獨立端點，不動）、`schema_version=2`（`IC_RESPONSE_V2`）並存：`view=light` 與 `schema_version=2` 同時給 ⇒ 400；flag on／off × view 有／無之四格矩陣測試。
- **效能與體驗預算（使用者 2026-09-09 裁定：「不只要可用，還要效率，包括載入或讀取時間，還有使用者體驗」）**：
  9. **後端延遲預算**（對 39,346 特徵實機報告、本機、暖機後單請求 p50／p95）：`view=light` ≤ 150／300 ms；`summary?limit=50`（任意 `sort_by`／`search`）≤ 100／200 ms；`feature/{name}` ≤ 50／100 ms。`paginate_summary` 對 39k 列每次請求 O(n log n) 排序須快取：同一 `(result_revision, sort_by, sort_order, pass_class, search)` 之排序索引在 service 內以 LRU（上限 8 組／task）快取，第二次請求 ≤ 20 ms；revision 變更即失效。
  10. **前端體驗預算**（B34 實機）：首屏可互動 ≤ 3 s（light ≤ 262 KB＋首頁 50 列）；翻頁／排序 ≤ 1 s 且顯示 skeleton 列（不閃白、不清空舊列直到新列到達）；點特徵 ⇒ 圖表 ≤ 2 s，切換期間保留舊圖並加 loading 遮罩；搜尋 300 ms 去抖；翻頁保留勾選（Set 跨頁）；頁碼／每頁筆數／排序狀態寫進 URL query（重整不丟）；請求失敗顯示可重試按鈕而非空白。
- **參數命名對齊 Feature Factory**（使用者建議 2026-09-09；FF `/browse/{task}/features` 已用 `offset`／`limit`／`sort_by`／`sort_order`／`search`）：本票 summary 端點採 `sort_by`／`sort_order`（`asc|desc`）／`search`／`offset`／`limit`；前端分頁表格與 Set 勾選照 FF explorer（`FeatureTimeSeriesChart.tsx` `browseFeatures` 模式）實作。
- **新資料結構單一真相源**：`momentum/Analysis/contracts/ic_result_paging_contract.json`（`sort_fields`、`sort_order_values`、`limit_default`、`limit_max`、`drop_sections`、`metadata_keep_keys`、`collection_to_count_paths`、`per_feature_sections`、`sort_policy`）＋`api/models/ic_models.py`（pydantic 回應模型，由 contract 載入常數）；SPEC／TODO 只 pointer，不在散文第二次列舉。

## §G Golden / Baseline
- **feature/kline 條件**：不涉 feature／kline 生成計算——略過三方 kline 簽核（§N）。
- **凍結時機 / reference 設定**：動工前以 `tests/momentum/helpers/ichc_run.run_analyze`（ETHUSDT 12h la0 fixture，14 特徵）產全量報告存進 fake task，凍結 `tests/golden/icresult_paging/full_report_projection.json`：`summary_rows`、`feature_set_sha256`、`section_key_sha256{段:sha}`、**全部**特徵之 `feature_samples{name:{段:sha}}`（fixture 小，不抽樣；R1 必答 6）、`raw_body_sha256`（TestClient `response.content`）、`report_canonical_sha`、`sort_golden`（`icir` desc／asc 前 5 列 `feature_name`＋人工構造 4 列並列 fixture 之雙向序）、`filter_log_light`（投影後全文）。
- **通過條件（可證偽）**：
  - G-1 改後預設 `/result` **raw body sha256 == golden `raw_body_sha256`**；canonical sha 亦相等（輔助）。
  - G-2a 無篩選：`/summary` 以 `limit=limit_max` 逐頁抓完（同一 `result_revision`）並依 `feature_name` 排序 == 全量 `summary_table` 依同鍵排序（列數、每列 dict 相等）。G-2b 有篩選（`search`／`pass_class`）：逐頁串接 == 對同參數一次 `paginate_summary(limit=10**9)` 之結果（同 revision）。
  - G-3 對 golden 每個特徵，`/feature/{name}` 各段 == 全量報告該段 `[name]`（canonical sha 相等）；`grouped_ic` 投影為 `{group: value_for_feature}`。
  - G-4 `view=light`：(a) `drop_sections` 各段**缺席**；(b) `metadata` 鍵集 ⊆ `metadata_keep_keys` 且對 fixture 中存在者逐鍵相等（`selection_scope` 依 (iii) 投影後相等）；(c) `filter_log` == golden `filter_log_light`；(d) 其餘頂層段（`marginal_ic`／`correlation_matrix`／`cross_sectional_*`／`module_statuses`／`analysis_status`／`oos_guarantees`／`version`／`diversification_metrics`）逐鍵相等；(e) `summary_page` == `paginate_summary(sort_by=icir, sort_order=desc, offset=0, limit=limit_default)`。
  - G-5 尺寸（受控 artifact；**不在 pytest 內**，R2 `CODEX-R2-P1-03`）：獨立探針 `handoffs/<date>-probe-icresult-size.py` 對 `data_cache/reports/ic_report_ic_gatekeeper.json` 載入 fake task，light canonical JSON ≤ **262144 bytes**（實測 28019）、`summary?limit=50` ≤ 102400、任一 `feature/{name}` ≤ 2097152；stdout **唯一文法**（R3 `CODEX-R3-P1-02`）：恰一行 `SIZE_GATE=PASS`／`SIZE_GATE=FAIL`／`SIZE_GATE=BLOCKED`（原因寫在其後另行 `SIZE_REASON=…`），rc 對應 0／1／2；receipt `handoffs/run_receipts/icresult_size_budget.log`。`scripts/icresult_paging_phase_gate.sh 1` 對 G-1～G-4／G-6～G-8（repo fixture）要求 rc=0；對 G-5 嚴格解析該一行（R3 `GROK-R3-P2-02`）：`FAIL` ⇒ gate rc=1；`BLOCKED` ⇒ 轉印 `SIZE_GATE=BLOCKED` 且不改 rc；`PASS` ⇒ 轉印並繼續；缺行／多行／未知值 ⇒ rc=1。B3 收案要求 `SIZE_GATE=PASS`。pytest 內另有 shape 測試：以 repo 內 **結構 fixture** `tests/golden/icresult_paging/shape_fixture.json`（六 stage 鍵名＋型別，由實機 `jq` receipt 抄錄，無數值）驗 `filter_log_light`／`filter_log_funnel` 形狀。
  - G-6 排序：fixture `icir` desc／asc 首 5 列 `feature_name` == golden `sort_golden`；4 列並列 fixture（A、B 同有限值且 A<B 名序；C、D 為 None）：desc 序 == `[A,B,C,D]`、asc 序 == `[A,B,C,D]`（缺值兩向沉底、並列以名升冪）；另 3 列 fixture（A=0.5、B=0.9、C=None）：desc == `[B,A,C]`、asc == `[A,B,C]`。
  - G-7 世代：(a) TestClient 交錯（取 page1 → refilter → 取 page2 帶舊 `revision`）⇒ 409；不帶 `revision` ⇒ 回新 revision 且 `total` 為新值；(b) 投影中途 refilter（monkeypatch `paginate_summary` 在投影中觸發 `_set_result` 寫入**含 sentinel 的新報告**：新 `summary_table` 全部 `feature_name` 加前綴 `NEW__`、`total` 不同）⇒ 回應 `result_revision`、`total`、每列 `feature_name` **全部**屬舊世代（無 `NEW__`）；`feature/{name}` 同法斷言各段 sha 屬舊世代（R3 `CODEX-R3-P1-04`）；(c) `POST /refilter?view=light` 回應含 `view=="light"` 且 `result_revision` 遞增。
  - G-9 延遲（受控 artifact，與 G-5 同探針、同三態文法）：對 39k 實機報告以 TestClient 量 20 次取 p50／p95，`light`／`summary`（`sort_by=icir`、`sort_by=feature_name`、`search=close` 三組）／`feature`：皆 ≤ §C-9 預算；快取命中第二次 `summary` ≤ 20 ms；receipt `handoffs/run_receipts/icresult_latency.log` 寫 `LATENCY_GATE=PASS|FAIL|BLOCKED`＋各項 p50／p95。
  - G-8 漏斗：shape fixture 六 stage 經 `funnel_stage_adapter` ⇒ `filter_log_funnel` == golden（`stage0_ingestion {input:int, output:null}`、`feature_filter {input,output}` 皆 int、`stage1_preprocessing {null,null}`、`stage3_event_filter {null,null}`、`stage5_thresholds {input:int, output:0}`（dict 含 `count`=0 ⇒ 0）、`stage6_redundancy {int,int}`）；六 stage 全鎖。

## §P Phase 與依賴

### Phase 1 — 後端投影端點（依賴：無）
**Task 1.0 — `result_revision` 世代戳**
- 目標：`task_info["result"]` 每個寫點經單一 helper 遞增 `result_revision`；`/task/{id}` 回該值。　檔案：`api/services/ic_analysis_service.py::_set_result(task_info, report) -> int`（三寫點 `:1623`／`:2339`／`:2631` 改經 helper）；`api/models/ic_models.py::ICTaskStatusResponse.result_revision: Optional[int]`。　既有 caller：三寫點。
- 改法：源碼守衛測試以 AST 鎖「對 `task_info["result"]` 之 Assign／Subscript 賦值：`_set_result` 函式體內恰 1 處、函式體外 0 處」（R3 `CODEX-R3-P1-01`；不用註記排除）。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k revision THEN rc=0`；G-7；AST 守衛：helper 內 == 1、helper 外 == 0。
- **邊界**：①未完成 ⇒ `result_revision=None`；②refilter 失敗不遞增；③兩次 refilter ⇒ 3。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不做 ETag／Cache-Control；不持久化 revision。

**Task 1.1 — summary 分頁端點**
- 目標：`GET /result/{task_id}/summary?sort_by=&sort_order=&offset=&limit=&pass_class=&search=&revision=` 回 `{total, offset, limit, sort_by, sort_order, result_revision, rows}`（命名對齊 FF browse）。　檔案：`api/services/ic_result_projection.py::paginate_summary`（純函式）、`api/services/ic_analysis_service.py::get_result_summary_page`、`api/routes/ic_analysis.py::get_result_summary_page`、`api/models/ic_models.py::ICSummaryPageResponse`。　既有 caller：新建無 caller。
- 改法：白名單驗 `sort_by`／`sort_order` → `sort_policy` comparator（§C-8）→ `pass_class` 精確／`search` 子字串不分大小寫 → 切片；`revision` 不符 ⇒ 409；排序索引 LRU 快取（§C-9，key 含 revision，上限 8 組／task）。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k summary_page THEN rc=0`；G-2a／G-2b／G-6／G-9；TestClient `sort_by=evil` ⇒ 400；`limit=99999` ⇒ 回 `limit == limit_max`；快取：同參數第二次不重排（spy `sorted` 呼叫次數 == 1）、revision 變更後重排。
- **邊界**：①running ⇒ 404；②`offset ≥ total` ⇒ `rows=[]`；③`limit>limit_max` ⇒ clamp；④`icir` 全 None ⇒ 全部並列 ⇒ 依 `feature_name` 升冪（**有意行為變更**）；⑤`search` 無命中 ⇒ `total=0`；⑥`sort_by=feature_name` 字串序；⑦`revision` 不符 ⇒ 409。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不讀 parquet artifact、不重算、不快取到檔、不做游標。

**Task 1.2 — 單特徵詳情端點**
- 目標：`GET /result/{task_id}/feature/{feature_name}?revision=` 回 contract `per_feature_sections` 各段（`grouped_ic`→`{group: value}`）＋`summary_row`＋`result_revision`。　檔案：`api/services/ic_result_projection.py::project_feature`；route／service／模型 `ICFeatureDetailResponse`。　既有 caller：新建無 caller。
- 改法：SectionStatus 物件透傳；缺 ⇒ `null`；`name` 不存在 ⇒ 404。
- **驗證**：G-3；`ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k feature_detail THEN rc=0`。
- **邊界**：①特殊字元名精確匹配；②段為 SectionStatus ⇒ 透傳；③三窗皆空 ⇒ 空陣列；④`revision` 不符 ⇒ 409。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不做批次；不回整份 grouped_ic。

**Task 1.3 — `view=light` 摘要視圖**
- 目標：`GET /result/{task_id}?view=light` 依 §C-6 四條規則投影；無 `view` ⇒ G-1。　檔案：`api/services/ic_result_projection.py::project_light_view(report, contract)`；service `get_result(task_id, schema_version, view)`；route `get_result(view: Optional[Literal["light"]] = Query(None))`。　既有 caller：`useICAnalysis.fetchResult`／`refilter`（Phase 2a 改）。
- 改法：`deny_factor_in_ok_oos` 先跑；`{"raw":…}` ⇒ 400；`view=light`＋`schema_version=2` ⇒ 400；投影純函式只讀 contract；snapshot `(report, revision)` 於 lock 內取；`filter_log_funnel` 依 (iv)；`POST /refilter` 加 `view` 參數（`light` ⇒ 回 light；無 ⇒ 不變）。
- **驗證**：G-1、G-4、G-7c、G-8；`ASSERT venv/bin/python -m pytest tests/api/test_icresult_paging.py -k light_view THEN rc=0`；`ASSERT venv/bin/python handoffs/<date>-probe-icresult-size.py THEN rc=0`（印 `SIZE_GATE=PASS`；artifact 缺席 ⇒ rc=2 印 `BLOCKED`）；`ASSERT venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_survivor_contract.py -q THEN rc=0`；v2 矩陣：`ASSERT TestClient GET /result/{id} WHEN IC_RESPONSE_V2=true schema_version=2 view=light THEN rc=400`；`ASSERT TestClient GET /result/{id} WHEN IC_RESPONSE_V2=false schema_version=2 view=none THEN rc=200`（回全量，既有行為）。
- **邊界**：①`{"raw":…}` ⇒ 400；②保留鍵缺席不補；③`summary_table` 空 ⇒ `summary_page.total=0`；④`filter_log` 某 stage 無集合鍵 ⇒ 原樣。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改預設回應一個 byte；不把 light 設預設；不在 light 內補值。

### Phase 2 — 前端一次切換（依賴：Phase 1；R2 `CODEX-R2-P1-05`：B2 不拆——light 已開而圖表仍讀已刪段＝功能退化的中間態，須同批 cutover＋page 整合測試）
**Task 2.1 — hook／store／types 改 light＋分頁＋單特徵**
- 目標：`fetchResult`／`refilter` 改 `view=light`；新增 `fetchSummaryPage`／`fetchFeatureDetail`（帶 `revision`）；store 持 `reportLight`、`summaryPage`、`featureDetail`、`resultRevision`、`selectedFeatureSet: Set<string>`。　檔案：`frontend/src/hooks/useICAnalysis.ts`、`frontend/src/store/icAnalysisStore.ts`、`frontend/src/lib/types.ts`。　既有 caller：`page.tsx`、`ExportButtons`、`ICSummaryTable`。
- 改法：回應 `view !== 'light'` ⇒ `setError('後端版本過舊')` 不吃全量；refilter 成功 ⇒ abort 全部進行中 summary／feature 請求、`resultRevision` 更新、offset 歸 0；409 ⇒ 以回應 `current_revision` 重拉一次，再 409 ⇒ 顯示錯誤不迴圈。
- **驗證**：`ASSERT (cd frontend && npx vitest run src/hooks src/store) THEN rc=0`；`npx tsc --noEmit -p tsconfig.json` 之 `error TS` 計數 == 8。
- **邊界**：①切換特徵時前請求未回 ⇒ abort；②detail 404 ⇒ 「此特徵無詳情」；③409 重拉一次上限。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不在前端排序／篩選；不保留整份報告；不 polyfill 舊後端。

**Task 2.2 — 表格伺服器分頁**
- 目標：`ICSummaryTable` 只畫當頁列；排序／搜尋／pass_class 走 API；勾選 O(1)。　檔案：`frontend/src/components/ic-analysis/ICSummaryTable.tsx`、`page.tsx`。　既有 caller：`page.tsx`（全選＝當頁）。
- 改法：移除 `sortedData`／`getSortValue`；分頁列 50|100|200；搜尋 300 ms 去抖；翻頁時 skeleton 列覆蓋、舊列保留到新列到達；勾選 Set 跨頁保留；頁碼／每頁／排序／搜尋同步到 URL query；失敗顯示重試（§C-10）。
- **驗證**：vitest：`total=39346, rows=50` ⇒ DOM `<tr>` == 51；`Array.prototype.includes` spy 於 200 次勾選呼叫 == 0；排序點擊 ⇒ `onParamsChange` 收 `offset:0`；翻頁期間舊列仍在 DOM 且出現 skeleton；跨頁勾選後回到前頁仍勾；URL query 含 `page`／`limit`／`sort_by`；`ICSummaryTable.icirNull.test.tsx` 斷言不改。
- **邊界**：①`total=0` 空狀態；②末頁不足；③排序切換 offset 歸 0。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不加虛擬捲動依賴；不在前端保留全量列。

**Task 2.3 — 圖表改吃 featureDetail；漏斗改讀 `filter_log_funnel`；匯出不動**
- 目標：per-feature 圖表（`ICDecayChart`／`QuantileReturnChart`／`TurnoverTimeSeriesChart`／`RollingICChart`／`GroupedICBarChart`／`RegimeRadarChart`）由 `page.tsx` 餵 `featureDetail`；其餘讀 `report` 的元件 props 型別放寬為 `ICReportLight | ICReport`；`ExportButtons` **維持** `/export/{id}/{format}`，只把 `summaryTable` prop（PNG disable）改 `summaryPage.total > 0`。　檔案：`page.tsx`、各元件。　既有 caller：`page.tsx`。
- **驗證**：`ASSERT (cd frontend && npx vitest run src/components/ic-analysis src/app) THEN rc=0`（既有斷言不改；新增 page 整合測試（fixture＝**不含 `summary_table`** 之 light 報告＋`summary_page{total:39346, rows:50}`）：①表格 `<tr>` == 51 且不讀 `report.summary_table`（fixture 無此鍵仍渲染 50 列）；②點排序 ⇒ `fetchSummaryPage` 收 `{sort_by, sort_order, offset:0}`；③點列 ⇒ `fetchFeatureDetail(name)` 被呼叫；④`featureDetail=null` ⇒ 六圖區「載入中」不 throw；⑤`featureDetail`＝golden 單特徵 ⇒ 六圖渲染；⑥`filter_log_funnel` 含 `null` ⇒ 漏斗該 stage 不適用；R3 `CODEX-R3-P1-05`）；`npx tsc --noEmit -p tsconfig.json` `error TS` == 8；後端 `ASSERT venv/bin/python -m pytest tests/api -k export THEN rc=0`（匯出既有測試不改）。
- **邊界**：①`featureDetail` 未到 ⇒ 圖表「載入中」；②light 缺 `marginal_ic`（不應發生，G-4d）⇒ `SectionStatusNotice`。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不改匯出格式；不做逐頁匯出；不動 `ScanCubeBrowser`／deep-analysis。

### Phase 3 — 實機驗收（依賴：Phase 2）
**Task 3.1 — 39k 實機 UAT B34**
- 目標：使用者以同一份 39,346 特徵 run 開頁面：首屏 ≤ 3 秒可互動、翻頁／排序 ≤ 1 秒（有 skeleton、不閃白）、點特徵圖表 ≤ 2 秒（舊圖保留＋遮罩）、重整不丟頁碼／排序；後端 G-9 延遲 receipt PASS。　檔案：`白話說明/GAP-3驗收清單.md` B34。
- **驗證**：使用者實機（`blocked-by:使用者`）；Claude 端 `ASSERT venv/bin/python handoffs/<date>-probe-icresult-size.py THEN rc=0`（`SIZE_GATE=PASS`，receipt `light_bytes=` ≤ 262144）；`ASSERT venv/bin/python handoffs/<date>-probe-icresult-size.py --latency THEN rc=0`（G-9 `LATENCY_GATE=PASS`）。
- **邊界**：後端未重啟 ⇒ 前端「後端版本過舊」而非靜默吃全量。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不以縮小特徵數當通過。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：RISK-HIT 不含 a/d，但 G-1～G-7 為正確性主張 ⇒ 附 mutation（`handoffs/<date>-icresult-paging-mutate.py --phase 1`）：P1 切片 off-by-one ⇒ G-2a 紅；P2 白名單放寬 ⇒ 400 測試紅；P3 `project_feature` 段錯位 ⇒ G-3 紅；P4 light 忘刪 `turnover_analysis` ⇒ G-4a／G-5 紅；P5 light 誤刪 `marginal_ic` ⇒ G-4d 紅；P6 預設 `/result` 誤套 light ⇒ G-1 紅；P7 缺值置頂（comparator 改）⇒ G-6 紅；P8 revision 不遞增 ⇒ G-7 紅；P9 `filter_log` 集合值未轉計數 ⇒ G-4c 紅；P10 snapshot 改為投影中重讀 `task_info["result"]` ⇒ G-7b 紅；P11 funnel adapter 候選鍵序反轉 ⇒ G-8 紅；P12 funnel 改在計數後計算 ⇒ G-8 stage5 紅；P13 dict 含 `count` 改取 `len` ⇒ G-8 stage5 紅；P14 排序快取 key 不含 revision ⇒ 快取測試紅；C0 只改註解 ⇒ 綠。
- 測試層級：單元（純函式）、整合（TestClient＋fake task）、Golden（G-1～G-4／G-6～G-8，repo fixture）、尺寸（G-5 獨立探針三態，不進 pytest）、前端 vitest（含 page 整合）。
- **防假綠**：既有 `/result` 測試斷言一條不改；`ICSummaryTable.icirNull.test.tsx` 斷言不改；`sort_golden` 由 contract comparator 產生並經三家 R2 審（**不**由改前前端序推導；分頁序是新契約）。
- **邊界目錄**：空 summary_table ✓；`icir` 全 None ✓；特殊字元名 ✓；SectionStatus 段 ✓；running ✓；後端舊版 ✓；refilter 交錯 ✓(G-7)；大尺度 39k ✓(G-5)；v2 flag 矩陣 ✓(1.3)。

## §R 回退
- Phase 1 純新增端點＋`view`／`revision` 參數，預設路徑不變，可單獨 revert；Phase 2 單一 commit revert 即回全量模式。無 feature flag。

## §N N/A 登記
- §G 三方 kline 簽核子項：N/A — 不碰 feature／kline／IC 計算；golden 為報告投影對照。
- 殘留：`IP-RESID-1` metadata 被 39,346 個 per-feature 描述子扁平污染（reporter 寫入面）— `為何現在不做: blocked-by:改 reporter 會動落檔格式與 gap2／ic1d golden（命中 a），須另票走三方簽核`；觸發：下一次 reporter 改版；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`。
- 殘留：`IP-RESID-2` `turnover_analysis` 每特徵含全長 `time_series`（51 MB 主因）落檔量 — `為何現在不做: blocked-by:同 IP-RESID-1（落檔格式）`；觸發：同上。
- 殘留：`IP-RESID-4` `metadata_keep_keys` 清單須以 contract 為唯一來源，`handoffs/_light_size_probe.py` 之 `KEEP_META` 為草稿— `為何現在不做: blocked-by:contract 於 Task 0.1 才建；建後探針改讀 contract（R2 `COMPOSER-R2-P2-01`）`；觸發：Task 0.1 完成即收。
- 殘留：`IP-RESID-3` 既有 `schema_version=2`（`IC_RESPONSE_V2`）top-N 路徑與 light 並存 — `為何現在不做: user-ruling:2026-06-25 IC Phase1 決策「API 現在版本化（top-N＋artifact URI）」為既定契約；R1 三家裁「並存＋precedence 矩陣測試」（Task 1.3），不合併亦不刪`；觸發：v2 契約消費者出現時統一。
- （R2 收回為 Task）原 `IP-RESID-4` 漏斗鍵名錯配：三家碼證確認為可重現契約缺陷，非 needs-research ⇒ 併入 §C-6 (iv) `funnel_stage_adapter`＋Task 1.3／2.3＋G-8（採較嚴版 `CODEX-R2-P1-04`）。
