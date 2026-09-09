# ICRESULT_PAGING TODO　（DRAFT／基於 `docs/ICRESULT_PAGING_SPEC.md`（R3 修訂）／2026-09-09）

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 解耦 7 條；`momentum/` 不 import `api/`；service 不互 import；R7 DTO 不跨界（pydantic 模型只在 `api/models/`，service 回 dict）。
- **紅線（SPEC §C 不變式 1–8）**：①預設 `GET /result/{id}` **raw body** 位元組級不變（G-1 以 `response.content` sha 驗）；⑥light 投影四規則只讀 contract（`drop_sections`／`metadata_keep_keys` 顯式列舉／`collection_to_count_paths` 集合值→`<key>_count`／附加鍵）；⑦`result_revision` 世代戳，不符 ⇒ 409；⑧排序契約 `sort_policy`（缺值兩向沉底、並列以 `feature_name` 升冪），**分頁序取代前端本地序＝有意行為變更**；②orchestrator／reporter／落檔一行不改；③所有投影端點只讀 `task_info["result"]`，不重算、不讀檔、不另存；④排序／篩選欄位白名單來自 `momentum/Analysis/contracts/ic_result_paging_contract.json`（唯一真相源），非白名單 ⇒ 400；⑤前端 light 視圖缺段不補假值。
- 不可違反原則：不擅改輸出大小（落檔）；不弱化任何 gate；`deny_factor_in_ok_oos` 出口守衛在所有視圖前先跑。
- 防假綠：既有 `/result`、golden replay、survivor／contract、`ICSummaryTable.icirNull.test.tsx` 斷言一條不改；新斷言對應新行為；mutation rc=5 計 UNCOVERED。
- 引用 SPEC §A 七條 FACT-RECEIPT（119 MB／39,346 列／各段位元組數／metadata 39,398 鍵），不整段複製。
- 新資料結構：回應 schema 在 `api/models/ic_models.py`；白名單／limit／metadata 保留鍵在 contract JSON；SPEC／TODO 不第二次列舉。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B0 | 0.1 | 無 | golden 凍結＋contract JSON＋mutation 骨架（改前） | 小 |
| B1 | 1.0、1.1、1.2、1.3 | B0 | 世代戳＋三個純函式共用同一 fake-task fixture 與 golden；預設路徑不動 | 中 |
| B2 | 2.1、2.2、2.3 | B1 commit | 前端**單批 cutover**（R2 `CODEX-R2-P1-05`：light 已開而圖表仍讀已刪段＝功能退化中間態；page 整合測試為 gate） | 中 |
| B3 | 3.1 | B2 commit | 實機 UAT B34 | 小 |
- 批次 Gate：B0 ⇒ `tests/golden/icresult_paging/full_report_projection.json` 存在且 `handoffs/<date>-probe-icresult-golden.py --check` rc=0；B1 ⇒ `pytest tests/api/test_icresult_paging.py` rc=0＋G-1～G-4／G-6～G-8（repo fixture）＋G-5 探針唯一文法 `SIZE_GATE=PASS|FAIL|BLOCKED`（gate：FAIL ⇒ rc=1；BLOCKED ⇒ 轉印不改 rc；缺行／未知 ⇒ rc=1）＋`pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_survivor_contract.py` rc=0＋mutation P1–P14 紅／C0 綠（`scripts/icresult_paging_phase_gate.sh 1`）；B2 ⇒ vitest（含 page 整合）rc=0＋tsc `error TS` == 8；B3 ⇒ 使用者簽 B34＋`SIZE_GATE=PASS`。
- 派工：實作＝Claude 主委自任（ORCH §1）；review＝codex＋composer＋grok 全員 adversarial；SPEC/TODO 先過三家審查再開 B0。

## Phase 0 — Golden 與骨架（完成後：改前投影對照可機檢）

### Task 0.1 — 凍結全量報告投影 golden＋contract JSON＋mutation 骨架（`SPEC §G`／`§V`）
- 目標：改前產出 §G golden（raw body sha＋全部特徵各段 sha＋sort_golden＋filter_log_light）；建 contract（白名單、投影規則、排序契約皆顯式）；建 mutation／gate 骨架（phase 1 條目先 SKIP 計 UNCOVERED）。
- 檔案：`handoffs/<date>-probe-icresult-golden.py`（`--write`／`--check`；以 `tests/momentum/helpers/ichc_run.run_analyze` 產全量報告 → `tests/golden/icresult_paging/full_report_projection.json`：`summary_rows`、`feature_set_sha256`、`section_key_sha256{段:sha}`、`report_canonical_sha`、`feature_samples{name: {段: sha}}`（fixture **全部**特徵，不抽樣）、`raw_body_sha256`（TestClient `GET /result/{id}` 之 `response.content`）、`sort_golden`、`filter_log_light`）；`momentum/Analysis/contracts/ic_result_paging_contract.json`（`sort_fields`、`sort_order_values`、`limit_default=50`、`limit_max=500`、`drop_sections`（七段）、`metadata_keep_keys`（**顯式**＝SPEC §A receipt 之前端＋後端消費者聯集，另加 `symbol`／`timeframe`／`config_hash`／`fit_mode`／`fit_mode_source`／`conditional_ic`／`alpha_source`／`significance`／`baseline_subset`／`scope`／`tiebreaker_effective`／`n_samples`；**禁由 fixture 推導**）、`collection_to_count_paths`＝`[{"path":["filter_log","*"]},{"path":["metadata","selection_scope"]}]`（`*` 只匹配該層直接子鍵、一層不遞迴、目標須為 dict、缺席／非 dict ⇒ no-op）、`funnel_stage_adapter`＝`{"input_keys":["input_features","feature_count_original"],"output_keys":["output_features","feature_count_filtered"],"dict_count_key":"count"}`（值為 int 原樣；dict 含 `count` ⇒ 取之；其他 dict／list ⇒ len；皆缺 ⇒ null）、`per_feature_sections`、`sort_policy`）；`tests/golden/icresult_paging/shape_fixture.json`（實機六 stage 鍵名＋型別，由 SPEC §A receipt 抄錄，無數值）；`handoffs/<date>-icresult-paging-mutate.py`（沿 `20260908-evtwarmup-mutate.py` 型：rc=5 計 UNCOVERED、紅只認 rc=1、目標檔須與 HEAD 一致）；`scripts/icresult_paging_phase_gate.sh <1>`。
- 實作要點：①golden 產生用 `ichc_run.canonical_sha` 同一 scrub 集合，另存 raw body sha；②`metadata_keep_keys` 為顯式清單（見檔案欄），測試斷言「SPEC §A receipt 列出的前端／後端消費鍵 ⊆ keep_keys」且「keep_keys ∩ fixture `summary_table.feature_name` == ∅」；③contract 由 `api/models/ic_models.py::load_ic_result_paging_contract()` 載入為常數，測試斷言模型欄位 == contract；④`sort_golden` 由 contract comparator 產生（非由改前前端序推導），含 4 列並列 fixture 三向序；⑤`filter_log_light`／`filter_log_funnel` 由投影規則對 fixture 與 shape fixture 產生（G-8 golden）；⑥`handoffs/_light_size_probe.py` 改讀 contract 之 `metadata_keep_keys`（單一來源；R2 `COMPOSER-R2-P2-01`）並更名為 `handoffs/<date>-probe-icresult-size.py`（G-5 三態探針：stdout 恰一行 `SIZE_GATE=PASS|FAIL|BLOCKED`＋`SIZE_REASON=`，rc 0／1／2）；⑦`scripts/icresult_paging_phase_gate.sh` 偽碼：`line=$(grep -c '^SIZE_GATE=' out)`；`!= 1` ⇒ rc=1；值 `FAIL` ⇒ rc=1；`BLOCKED` ⇒ echo 轉印、rc 不變；`PASS` ⇒ 繼續；其他 ⇒ rc=1（R3 `GROK-R3-P2-02`／`CODEX-R3-P1-02`）。
- 修改檔案：新建三檔＋一 golden；`api/models/ic_models.py::load_ic_result_paging_contract()`。　既有 caller：新建無。
- 路徑：
  handoffs/*-probe-icresult-golden.py
  handoffs/*-icresult-paging-mutate.py
  scripts/icresult_paging_phase_gate.sh
  momentum/Analysis/contracts/ic_result_paging_contract.json
  tests/golden/icresult_paging/full_report_projection.json
  tests/golden/icresult_paging/shape_fixture.json
  handoffs/*-probe-icresult-size.py
  api/models/ic_models.py
- 不可做：不用 39k 實機報告當 golden（不進 repo；只做 G-5 尺寸 receipt）；不由 fixture 推導白名單；不抽樣。
- 邊界：①fixture 報告 `correlation_matrix` 為空 ⇒ sha 照算；②`metadata` 中同名鍵既是特徵名又是保留鍵（不可能，斷言互斥）⇒ 建 contract 時 FAIL。
- 風險緩解：⊘。
- 驗證：`venv/bin/python handoffs/<date>-probe-icresult-golden.py --check` rc=0；`jq '.sort_fields|length' contract` ≥ 5 且含 `icir`、`ic_mean`、`p_value`、`feature_name`；`jq '.metadata_keep_keys' contract` ⊇ {`event_filter`,`oos_downgrade`,`isolation`,`ic_window_disclosure`,`period_alignment`,`ic_train_test_split`,`n_timestamps`,`n_symbols`,`mode`,`survivor_output`,`compute_warnings`,`selection_scope`,`symbol`,`timeframe`,`config_hash`} 且與 fixture `feature_name` 交集 == 0；`jq '.drop_sections|length' contract` == 7；`venv/bin/python handoffs/<date>-probe-icresult-size.py` 印恰一行 `SIZE_GATE=` 三態之一（改前投影函式尚不存在 ⇒ `SIZE_GATE=BLOCKED`＋`SIZE_REASON=projection missing`，rc=2）。
- **存活至**：永久。
- **覆蓋風險**：無。

## Phase 1 — 後端投影端點（完成後：三個端點可用，預設路徑一 byte 不變）

### Task 1.0 — `result_revision` 世代戳（`SPEC Task 1.0`）
- 目標：`task_info["result"]` 每個寫點經單一 helper 遞增 `result_revision`；`/task/{id}` 回該值。
- 檔案：`api/services/ic_analysis_service.py::_set_result(task_info: dict, report: Any) -> int`（寫 `result`＋`result_revision = (task_info.get("result_revision") or 0) + 1`，回新值）；三既有寫點 `:1623`／`:2339`／`:2631` 改呼叫 helper；`get_task_status` 回 `result_revision`；`api/models/ic_models.py::ICTaskStatusResponse.result_revision: Optional[int] = None`。
- 實作要點：①helper 在既有 lock 內呼叫（不另加鎖）；⓪`_snapshot_result(task_id) -> tuple[dict, int] | None` 於 lock 內同時取 `(result, result_revision)`，所有投影只吃 snapshot（R2 `CODEX-R2-P1-02`）；②源碼守衛測試以 `ast` 走訪 `ic_analysis_service.py`：對 `task_info["result"]` 之 Subscript 賦值，位於 `_set_result` 函式體內者 == 1、其餘 == 0（不用註記排除；R3 `CODEX-R3-P1-01`）；③refilter 失敗路徑不呼叫 helper。
- 修改檔案：如上兩檔。　既有 caller：三寫點。
- 路徑：
  api/services/ic_analysis_service.py
  api/models/ic_models.py
  tests/api/test_icresult_paging.py
- 不可做：不做 ETag／Cache-Control；不持久化；不改 deep-analysis 結果欄位語意。
- 邊界：①未完成 ⇒ `result_revision=None`；②refilter 失敗不遞增；③兩次 refilter ⇒ 3。
- 風險緩解：SPEC §C-7。
- 驗證：`venv/bin/python -m pytest tests/api/test_icresult_paging.py -k revision -q` rc=0；G-7a（TestClient：page1 → refilter → page2 帶舊 `revision` ⇒ status == 409 且 body `current_revision` == 2；不帶 revision ⇒ 200 且 `result_revision` == 2）；G-7b（monkeypatch `paginate_summary` 於投影中觸發 `_set_result` 寫入 sentinel 新報告（`feature_name` 前綴 `NEW__`、不同 total）⇒ 回應 `result_revision` == 1 且 `total` == 舊值且所有列 `feature_name` 不含 `NEW__`；`feature/{name}` 同法各段 sha == 舊世代）；AST 守衛 helper 內 == 1、外 == 0。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 1.1 — summary 分頁端點（`SPEC Task 1.1`）
- 目標：`GET /result/{task_id}/summary` 回分頁；純函式 `paginate_summary`。
- 檔案：`api/services/ic_result_projection.py`（**新模組**，純函式：`paginate_summary(rows: list[dict], *, sort_by: str, sort_order: str, offset: int, limit: int, pass_class: str|None, search: str|None, contract: dict) -> dict`（命名對齊 FF `/browse/{task}/features`）；`sort_key(row, field, sort_order)` 依 contract `sort_policy`：缺值（None／NaN／±inf）**兩向沉底**（回 `(1, 0, name)`），主鍵 `(0, ±value, name)`，`feature_name` 純字串序；`revision` 參數不符 ⇒ `RevisionMismatch` → route 409）；`api/services/ic_analysis_service.py::ICAnalysisService.get_result_summary_page(task_id, **params)`（lock 內取 `result`，lock 外投影）；`api/routes/ic_analysis.py::get_result_summary_page`（Query 驗證：`limit` clamp、`sort_by` 非白名單 ⇒ `HTTPException(400)`）；`api/models/ic_models.py::ICSummaryPageResponse`。
- 實作要點：⓪排序索引 LRU 快取：key `(task_id, result_revision, sort_by, sort_order, pass_class, search)` → 已排序 index list，上限 8 組／task，`_set_result` 時整 task 失效（SPEC §C-9）；①`sort_order` 只准 contract `sort_order_values`；②`pass_class` 精確匹配、`search` 為 `feature_name.lower()` 子字串；③`total` 為篩選後列數；④`rows` 為原 dict 不裁欄（前端表格已消費全部欄）；⑤不用 `_finite_or_neg_inf`（它是單向 `-inf`，asc 會置頂）；comparator 自 contract 產生；⑥回應含 `result_revision`。
- 修改檔案：如上四檔。　既有 caller：新建無。
- 路徑：
  api/services/ic_result_projection.py
  api/services/ic_analysis_service.py
  api/routes/ic_analysis.py
  api/models/ic_models.py
  tests/api/test_icresult_paging.py
- 不可做：不讀 parquet；不快取；不做游標；不在 route 內排序。
- 邊界：①running ⇒ 404；②`offset ≥ total` ⇒ `rows=[]`；③`limit > limit_max` ⇒ clamp；④`icir` 全 None ⇒ 全並列 ⇒ `feature_name` 升冪（首列＝名最小，**有意變更**）；⑤`search` 無命中 ⇒ `total=0`；⑥`sort_by=feature_name` 字串序；⑦`revision` 不符 ⇒ 409。
- 風險緩解：SPEC §C-4 白名單。
- 驗證：`venv/bin/python -m pytest tests/api/test_icresult_paging.py -k summary_page -q` rc=0；G-2a（無篩選逐頁 `limit=limit_max` 串接後依 `feature_name` 排序 == golden 全量列，列數 == `summary_rows`）；G-2b（`search=close` 逐頁 == 單次 `paginate_summary(limit=10**9)`）；G-6（desc／asc 首 5 列 == `sort_golden`；4 列並列 fixture desc == `[A,B,C,D]`、asc == `[A,B,C,D]`（缺值兩向沉底、並列以名升冪）；3 列 fixture desc == `[B,A,C]`、asc == `[A,B,C]`）；TestClient `sort_by=evil` ⇒ status == 400；`limit=99999` ⇒ 回應 `limit == limit_max`；快取：同參數第二次 `sorted` spy 呼叫 == 1、refilter 後 == 2；G-9（探針 `--latency` 對 39k：light ≤ 150／300 ms、summary ≤ 100／200 ms、feature ≤ 50／100 ms p50／p95，快取命中 ≤ 20 ms；artifact 缺席 ⇒ `LATENCY_GATE=BLOCKED`）。
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
- 邊界：①名含 `-`／`.`／空白 ⇒ 精確匹配；②段為 SectionStatus ⇒ 透傳；③三窗皆空 ⇒ 空陣列；④name 不存在 ⇒ 404；⑤`revision` 不符 ⇒ 409。
- 風險緩解：⊘。
- 驗證：`venv/bin/python -m pytest tests/api/test_icresult_paging.py -k feature_detail -q` rc=0；G-3（golden `feature_samples` **全部**特徵各段 canonical sha == 端點回值 sha；`grouped_ic` 投影 `{group: value}`）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 1.3 — `view=light` 摘要視圖（`SPEC Task 1.3`）
- 目標：`GET /result/{id}?view=light` 依 SPEC §C-6 四規則投影（刪 `drop_sections` 七段含 `grouped_ic`；`metadata` 只留 `metadata_keep_keys`；`filter_log.*`／`metadata.selection_scope` 集合值→`<key>_count`；加 `view`／`total_features`／`result_revision`／`summary_page`）；無 `view` raw body 位元組不變。
- 檔案：`api/services/ic_result_projection.py::project_light_view(report: dict, contract: dict) -> dict`（`drop_sections` 各段 pop；`metadata={k: m[k] for k in keep_keys if k in m}`；`_collections_to_counts(node)`＝對 `collection_to_count_paths` 每個節點，list／dict 值改 `f"{k}_count": len(v)`、標量原樣；**先**算 `filter_log_funnel=funnel_from_filter_log(report["filter_log"], contract["funnel_stage_adapter"])`（對**原始** filter_log；每 stage `{input, output}`：候選鍵序取第一存在者，int 原樣、dict 含 `count` 取之、其他 dict／list 取 len、皆缺 ⇒ null；R3 `GROK-R3-P1-01`），**再**對 light 的 `filter_log` 做計數；`summary_page=paginate_summary(rows, sort_by="icir", sort_order="desc", offset=0, limit=limit_default)`）；`api/routes/ic_analysis.py::refilter` 加 `view: Optional[Literal["light"]]`（`light` ⇒ 回 `project_light_view(snapshot)`；無 ⇒ 既有全量不變）；`ic_analysis_service.get_result(task_id, schema_version, view)`（`view=="light"` 且 `schema_version==2` ⇒ `ValueError` → route 400）；route `get_result(view: Optional[Literal["light"]] = Query(None))`。
- 實作要點：①`deny_factor_in_ok_oos(normalized)` 在投影**之前**；②`{"raw": …}` 非 dict ⇒ 400；③`marginal_ic`／`correlation_matrix`／`cross_sectional_*`／`module_statuses`／`analysis_status`／`oos_guarantees`／`version`／`diversification_metrics` 原樣；④`view=light`＋`schema_version=2` ⇒ 400；v2 flag on／off × view 有／無 四格矩陣測試（IP-RESID-3 並存契約）；⑤`_collections_to_counts` 依 contract 路徑規格：`*` 一層、目標須 dict、非 dict／缺席 no-op、更深層不動。
- 修改檔案：如上三檔。　既有 caller：`useICAnalysis.fetchResult`／`refilter`（Phase 2 改）；既有 `/result` 測試不改。
- 路徑：
  api/services/ic_result_projection.py
  api/services/ic_analysis_service.py
  api/routes/ic_analysis.py
  tests/api/test_icresult_paging.py
- 不可做：不改預設回應；不把 light 設預設；不在 light 內補任何值。
- 邊界：①`{"raw":…}` ⇒ 400；②保留鍵缺席不補；③`summary_table` 空 ⇒ `summary_page.total == 0`；④`view=light&schema_version=2` ⇒ 400；⑤`filter_log` 某 stage 無集合鍵 ⇒ 原樣。
- 風險緩解：SPEC §G G-1。
- 驗證：`venv/bin/python -m pytest tests/api/test_icresult_paging.py -k light_view -q` rc=0；G-1（預設回應 **raw body sha256** == golden `raw_body_sha256`，canonical 亦 ==）；G-4a–e（七段缺席；`metadata` ⊆ keep_keys 且逐鍵 ==；`filter_log` == golden `filter_log_light`；其餘頂層段逐鍵 ==；`summary_page` == `paginate_summary(icir,desc,0,50)`）；G-7c（`POST /refilter?task_id=&view=light` ⇒ 200、`view=="light"`、`result_revision` 遞增；無 `view` ⇒ 回應 raw body 與改前既有 refilter 測試斷言一致）；G-8（shape fixture 六 stage 全鎖：`stage0_ingestion {input:int,output:null}`、`feature_filter {int,int}`、`stage1_preprocessing {null,null}`、`stage3_event_filter {null,null}`、`stage5_thresholds {input:int, output:0}`（dict `count`=0）、`stage6_redundancy {int,int}`）；G-5 **不在 pytest**：`venv/bin/python handoffs/<date>-probe-icresult-size.py` ⇒ 恰一行 `SIZE_GATE=PASS`（light ≤ 262144、summary50 ≤ 102400、feature ≤ 2097152）或 artifact 缺席 ⇒ `SIZE_GATE=BLOCKED` rc=2；receipt `handoffs/run_receipts/icresult_size_budget.log`；`venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py tests/api/test_survivor_contract.py -q` rc=0。
- **存活至**：永久。
- **覆蓋風險**：無。

### Phase 1 測試＋Gate
- 單元：`paginate_summary`／`project_feature`／`project_light_view` 純函式（合成 5 列小報告：含 `icir=None`、SectionStatus 段、特殊字元名）。
- 整合：TestClient＋fake task（`ic_analysis_service._tasks[task_id] = {"status":"completed","result": <ichc_run 報告>}`）。
- Golden：G-1～G-5。
- mutation（`handoffs/<date>-icresult-paging-mutate.py --phase 1`）：P1 切片 off-by-one ⇒ `-k summary_page` 紅；P2 白名單放寬 ⇒ `-k sort_by_whitelist` 紅；P3 `project_feature` 段錯位 ⇒ `-k feature_detail` 紅；P4 light 忘刪 `turnover_analysis` ⇒ `-k size_budget or light_view` 紅；P5 light 誤刪 `marginal_ic` ⇒ `-k light_view` 紅；P6 預設 `/result` 誤套 light ⇒ `-k default_unchanged` 紅；P7 comparator 缺值置頂 ⇒ `-k sort_golden` 紅；P8 `_set_result` 不遞增 ⇒ `-k revision` 紅；P9 `filter_log` 集合值未轉計數 ⇒ `-k light_view` 紅；P10 snapshot 改為投影中重讀 `task_info["result"]` ⇒ `-k revision_mid` 紅；P11 funnel 候選鍵序反轉 ⇒ `-k funnel` 紅；P12 funnel 改在計數後算 ⇒ `-k funnel` 紅（stage5 output 變 null）；P13 dict 含 `count` 改取 len ⇒ `-k funnel` 紅（stage5 output 變 2）；P14 快取 key 去掉 revision ⇒ `-k cache` 紅；C0 註解 ⇒ 綠。Gate：`bash scripts/icresult_paging_phase_gate.sh 1` rc=0（skip=0、UNCOVERED=0；`SIZE_GATE=FAIL` ⇒ rc=1；`BLOCKED` 轉印不影響 rc；缺行 ⇒ rc=1）。

## Phase 2 — 前端單批 cutover（完成後：39k run 首屏可互動，DOM 列數 ≤ 每頁 limit，六圖吃 featureDetail，漏斗讀 funnel）

### Task 2.1 — hook／store／types（`SPEC Task 2.1`）
- 目標：`fetchResult`／`refilter` 改 `view=light`；新增 `fetchSummaryPage`／`fetchFeatureDetail`；store 持 `reportLight`、`summaryPage`、`featureDetail`、`resultRevision`、`selectedFeatureSet`。
- 檔案：`frontend/src/hooks/useICAnalysis.ts`（`fetchResult`：`requestJson<ICReportLight>(`/result/${taskId}?view=light`)`；回應 `view !== 'light'` ⇒ `setError('後端版本過舊：未回 light 視圖')` 不 setReport；`fetchSummaryPage(params: SummaryPageParams)`／`fetchFeatureDetail(name)` 皆帶 `revision=resultRevision`、去抖 150 ms＋`AbortController`；409 ⇒ 以 `current_revision` 更新 store 後重拉一次，再 409 ⇒ setError 不迴圈）；`frontend/src/store/icAnalysisStore.ts`（`report: ICReportLight|null`、`summaryPage`、`summaryParams`、`featureDetail`、`selectedFeatureSet: Set<string>`；`setSelectedFeature` 觸發 detail 拉取由 hook 做）；`frontend/src/lib/types.ts`（`ICReportLight = Omit<ICReport, per-feature 四段|'coverage_analysis'|'summary_table'> & {view:'light'; total_features:number; summary_page: ICSummaryPage}`、`ICSummaryPage`、`ICFeatureDetail`、`SummaryPageParams`）。
- 實作要點：①`activeFeature` 變更 ⇒ effect 呼叫 `fetchFeatureDetail`，前一請求 abort；②refilter 改打 `?view=light`，成功 ⇒ 以回應 `result_revision` 更新 store、abort 全部進行中 summary／feature 請求、`summaryParams.offset=0` 重拉首頁；③任何 summary／feature 回應 `result_revision !== store.resultRevision` ⇒ 丟棄不套用；④`selectedFeatures: string[]` 對外 API 保留，內部以 Set 實作。
- 修改檔案：如上三檔。　既有 caller：`page.tsx`、`ExportButtons`、`ICSummaryTable`、各圖表。
- 路徑：
  frontend/src/hooks/useICAnalysis.ts
  frontend/src/store/icAnalysisStore.ts
  frontend/src/lib/types.ts
  frontend/src/hooks/*.test.ts
  frontend/src/store/*.test.ts
- 不可做：不在前端排序／篩選；不保留整份報告；不 polyfill 舊後端。
- 邊界：①切換特徵時前請求未回 ⇒ abort；②detail 404 ⇒ `featureDetail={status:'missing'}`；③後端舊版 ⇒ 錯誤文案不吃全量；④409 重拉一次上限。
- 風險緩解：⊘。
- 驗證：`(cd frontend && npx vitest run src/hooks src/store)` rc=0（新測：light 回應 setReport、`view` 不符 ⇒ setError、detail abort 舊請求、refilter 重置 offset＋abort＋revision 更新、409 重拉一次）；`npx tsc --noEmit -p tsconfig.json` 之 `error TS` 計數 == 8。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.2 — 表格伺服器分頁（`SPEC Task 2.2`）
- 目標：`ICSummaryTable` 只畫當頁列；排序／搜尋／pass_class 走 API；勾選 O(1)。
- 檔案：`frontend/src/components/ic-analysis/ICSummaryTable.tsx`（props 改 `page: ICSummaryPage`、`params`、`onParamsChange`；移除 `sortedData` useMemo；`SortButton` ⇒ `onParamsChange({sort_by, order, offset:0})`；分頁列：上一頁／下一頁／每頁 50|100|200／「第 x–y 列，共 total」；勾選 `selectedFeatureSet.has`）；`frontend/src/app/ic-analysis/page.tsx`（`summaryTable` 消費者改 `summaryPage.rows`；全選＝當頁）。
- 實作要點：①`limit` 選項 ≤ contract `limit_max`；②搜尋框 300 ms 去抖 → `search`；③`activeFeature` 預設＝首頁第一列；④翻頁時 skeleton 列覆蓋、舊列保留到新列到達（不閃白）；⑤勾選 Set 跨頁保留；⑥`page`／`limit`／`sort_by`／`sort_order`／`search` 同步到 URL query（`useSearchParams`），重整還原；⑦請求失敗 ⇒ 列內錯誤＋重試按鈕（SPEC §C-10）。
- 修改檔案：如上兩檔。　既有 caller：`page.tsx`。
- 路徑：
  frontend/src/components/ic-analysis/ICSummaryTable.tsx
  frontend/src/components/ic-analysis/ICSummaryTable.*.test.tsx
  frontend/src/app/ic-analysis/page.tsx
- 不可做：不加虛擬捲動依賴；不在前端保留全量列。
- 邊界：①`total=0` 空狀態；②末頁不足；③排序切換 offset 歸 0；④`icir` null 顯示 `--`（既有測試不改）。
- 風險緩解：⊘。
- 驗證：`(cd frontend && npx vitest run src/components/ic-analysis/ICSummaryTable)` rc=0（新測：`total=39346, rows=50` ⇒ `<tr>` == 51；`Array.prototype.includes` spy 在 200 次勾選中呼叫次數 == 0；排序點擊 ⇒ `onParamsChange` 收到 `offset:0`；翻頁 loading 中舊列仍在 DOM 且 skeleton 出現；跨頁勾選回前頁仍勾；URL query 含 `page`＝2 後重掛 ⇒ 請求 `offset=50`）；`ICSummaryTable.icirNull.test.tsx` 斷言不改仍 rc=0。
- **存活至**：永久。
- **覆蓋風險**：無。

### Task 2.3 — 圖表改吃 featureDetail；漏斗讀 `filter_log_funnel`；匯出不動（`SPEC Task 2.3`）
- 目標：per-feature 圖表由 `featureDetail` 餵；其餘讀 `report` 的元件 props 放寬為 `ICReportLight | ICReport`；`ExportButtons` **維持** `/export/{task_id}/{format}`（R1 三家一致：既有後端匯出讀全量 result，受 G-1 保護）。
- 檔案：`frontend/src/app/ic-analysis/page.tsx::sectionSplit`（改讀 `featureDetail.{ic_decay,quantile_returns,grouped_ic,turnover_analysis}`；SectionStatus 透傳語意不變）；`ICDecayChart`／`QuantileReturnChart`／`TurnoverTimeSeriesChart`／`RollingICChart`／`GroupedICBarChart`／`RegimeRadarChart` props 改單特徵資料；`FilterFunnelChart`／`DegradedBanner`／`IsolationNote`／`PeriodAlignmentBanner`／`MarginalICTable`／`CorrelationHeatmap`／`CrossSectionalICHeatmap`／`CrossSymbolValidationPanel`／`EventTablesPanel`／`EventBatchDisclosurePanel` props 型別放寬；`ExportButtons.tsx` 之 `summaryTable` prop（僅 PNG disable）改 `hasRows: boolean`＝`summaryPage.total > 0`。
- 實作要點：①`featureDetail` 未到 ⇒ 圖表「載入中」不填空陣列；②`FilterFunnelChart` 改讀 `reportLight.filter_log_funnel`（`null` ⇒ 該 stage 顯示「不適用」，不補 0；`types.ts::FilterLogStage` 改 `{input: number|null, output: number|null}`）；③匯出邏輯零改動；④page 整合測試（`frontend/src/app/ic-analysis/page.test.tsx`；fixture＝**不含 `summary_table`** 之 light＋`summary_page{total:39346, rows:50}`）：①`<tr>` == 51；②點排序 ⇒ `fetchSummaryPage` 收 `{sort_by, sort_order, offset:0}`；③點列 ⇒ `fetchFeatureDetail(name)`；④`featureDetail=null` ⇒ 六圖「載入中」不 throw；⑤golden detail ⇒ 六圖渲染；⑥funnel 含 null ⇒ 不適用（R3 `CODEX-R3-P1-05`）；表格與勾選照 FF explorer（`FeatureTimeSeriesChart.tsx` `browseFeatures`）模式。
- 修改檔案：如上。　既有 caller：`page.tsx`。
- 路徑：
  frontend/src/app/ic-analysis/page.tsx
  frontend/src/components/ic-analysis/*.tsx
  frontend/src/lib/types.ts
- 不可做：不改匯出格式／端點；不做逐頁匯出；不動 `ScanCubeBrowser`／deep-analysis；不在圖表補假資料。
- 邊界：①`featureDetail` 未到 ⇒ 載入中；②light 缺 `marginal_ic`（不應發生，G-4d）⇒ `SectionStatusNotice` 不適用；③`grouped_ic` 投影 `{group: value}` 之 `RegimeRadarChart` 輸入形狀。
- 風險緩解：⊘。
- 驗證：`(cd frontend && npx vitest run src/components/ic-analysis src/app)` rc=0（既有斷言不改）；新測：page 整合六案例（表格 51 列／排序 callback／detail 呼叫／載入中／六圖渲染／漏斗不適用）；`npx tsc --noEmit -p tsconfig.json` `error TS` == 8；後端 `venv/bin/python -m pytest tests/api -k "export" -q` rc=0（匯出既有測試不改）。
- **存活至**：永久。
- **覆蓋風險**：無。

### Phase 2 測試＋Gate
- vitest：hooks／store／表格／圖表／page 整合；tsc 不增錯。Gate：`(cd frontend && npx vitest run)` rc=0 且 `error TS` == 8。

## Phase 3 — 實機驗收（完成後：使用者簽 B34；依賴 B2）

### Task 3.1 — UAT B34（`SPEC Task 3.1`）
- 目標：使用者以 39,346 特徵 run 驗：首屏 ≤ 3 秒可互動、翻頁／排序 ≤ 1 秒（skeleton、不閃白）、點特徵圖表 ≤ 2 秒（舊圖保留＋遮罩）、重整不丟頁碼／排序；後端 G-9 延遲 receipt PASS。
- 檔案：`白話說明/GAP-3驗收清單.md`（B34 段＋進度列）；`白話說明/現在做到哪.md`。
- 實作要點：①白話寫「要先重啟後端」；②寫「後端版本過舊」錯誤的含義；③寫 G-5 實跑數字（light 幾 MB）。
- 修改檔案：兩份白話。　既有 caller：無。
- 路徑：
  白話說明/GAP-3驗收清單.md
  白話說明/現在做到哪.md
- 不可做：不以縮小特徵數當通過；HANDOFF／白話依 claim guard 規則措辭。
- 邊界：①後端未重啟 ⇒ 前端顯示「後端版本過舊」（Task 2.1 邊界③）；②使用者用舊 run（task 已不在記憶體）⇒ 404 文案。
- 風險緩解：⊘。
- 驗證：使用者實機簽 B34（`blocked-by:使用者`）；Claude 端 `venv/bin/python handoffs/<date>-probe-icresult-size.py` rc=0 印恰一行 `SIZE_GATE=PASS`；`--latency` 印 `LATENCY_GATE=PASS`（receipt `handoffs/run_receipts/icresult_latency.log`） 且 receipt `handoffs/run_receipts/icresult_size_budget.log` 含 `light_bytes=` ≤ 262144。
- **存活至**：永久。
- **覆蓋風險**：無。

## 追溯（SPEC ID → TODO）
Task 1.0→1.0；1.1→1.1；1.2→1.2；1.3→1.3；2.1→2.1；2.2→2.2；2.3→2.3；3.1→3.1；§G G-1～G-7→0.1＋1.0～1.3；§C-6～8（投影規則／世代戳／排序契約）→0.1 contract＋1.0／1.1／1.3；§C-6(iv) 漏斗 adapter→0.1 contract＋1.3＋2.3（G-8）；§V P1–P14／C0→Phase 1 Gate；§C-9／10（效能與體驗預算）→1.1 快取＋2.2 UX＋3.1 G-9；§N IP-RESID-1～4→不入 Task（登記處 `docs/IC_QUANT_GAP_REGISTRY.md`，由 B3 收案時同步；原 IP-RESID-4 漏斗已收回為 Task）。合計：Task 8／Golden 9／mutation 15／殘留 4。
