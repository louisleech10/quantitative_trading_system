# IC-HC 健檢施工 TODO　（v1.1／狀態 **FROZEN**（R3 三家審 20 findings 全採納修訂＋R4 三家複驗全 CLOSED＋RECONCILE-STAMP 全 APPROVED）／基於 docs/IC_HEALTHCHECK_SPEC.md（frozen）／2026-08-17）

> 執行端＝Claude 主委自任（ORCH §1 現行分工行 2026-08-17 五調）。冷啟動原則：每 Task 不回讀 SPEC 即可寫碼；歧義以 SPEC 為準（衝突標 ⚠️ 矛盾回報，不自行裁決）。

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 解耦：R1 `grep -r "from api\." momentum/` == 0；R7 DTO 不跨界——契約 SoT 在 `momentum/Analysis/contracts/`，api／frontend 各自消費不互 import。
- 不可違反：不弱化 NaN/inf gate；不改輸出大小（Phase 2 數值 exact 不變）；不動 1cfr sanitizer 八出口測試、la1 loud-fallback 測試、1d attribution 三鍵測試之既有斷言。
- 防假綠：不得放寬/刪除既有測試斷言換綠；`tests/api/test_ic_response_v2.py` quantile subroute 斷言隨新契約更新＝新行為對新斷言（diff 審查逐條說明）。
- 資料真實性：golden 一律真實 `data_cache/feature_klines/kline_cache.h5`，禁合成 fixture；`data_cache/*` 絕不 commit。
- 測試紀律（HANDOFF）：優先性質檢驗／真實 kline／第三方對照；golden 僅 Phase 2 窄用。
- 新資料結構鐵律：欄位/枚舉只住 `momentum/Analysis/contracts/ic_report_contract.json`（Task 1.1 產出）；本 TODO 與程式碼註解不得複列枚舉值表。
- Commit：每 Phase 獨立 commit（`feat(ic-hc): Phase N …`）；回退=git revert per-phase；訊息 operational claim 附 `VERIFY:` receipt。

## §T SPEC 索引追溯（100% 覆蓋；原文節錄 ≤30 字）
| SPEC ID | 原文節錄 | TODO 落點 |
|---|---|---|
| Task 1.1 | 「建立單一真相源 schema 檔——capability status 枚舉」 | Task 1.1 |
| Task 2.1 | 「reporter 出口 flatten 至契約形狀…數值不變」 | Task 2.1 |
| Task 3.1 | 「xsec 五欄空殼改 typed status」 | Task 3.1 |
| Task 3.2 | 「前端消費 status＋page wiring…funnel 收口」 | Task 3.2 |
| Task 4.1 | 「insufficient fallback 改 loud…重用 degraded_full_sample」 | Task 4.1 |
| Task 4.2 | 「event_timestamps 接線…analyze() 顯式參數」 | Task 4.2 |
| Task 5.1 | 「掃描器 scripts/ic_wiring_check.sh…三規則機檢」 | Task 5.1 |
| Task 5.2 | 「契約三方一致性測試」 | Task 5.2 |
| Task 5.3 | 「turnover toggle 語意定案…方案 A」 | Task 5.3 |
| Task 6.1 | 「capacity unknown 契約鎖死」 | Task 6.1 |
| Task 6.2 | 「WF/CPCV 現狀誠實標示」 | Task 6.2 |
| Task 6.3 | 「死配置處置…REMOVED_KEYS」 | Task 6.3 |
| Task 6.4 | 「gap registry＋票登記＋白話」 | Task 6.4 |
| §G | 「per-feature 完整 canonical payload」 | Task 2.0（凍結）＋T-G1 |
| §V mutation 1–7 | 「7 條——每條 target→命令→預期紅→復原」 | 各 Phase 測試節 M1–M7 |
| §RISK | 「RISK-HIT: b,d」 | §0 約束＋Phase 2 golden 強制 |
| Phase 依賴 | 「Phase 2/3/4/5 皆僅依賴 Phase 1」 | §B 批次表 |
| 環境/flag | 「不建 runtime flag（§R）」 | §0 Commit 條 |
合計：Task 13、§G 1、mutation 7、RISK 2、依賴 1、flag 宣告 1。

## §B 批次執行策略（依賴拓撲 → 最少批次；執行端=主委自任，批次=實作順序）
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1 | 無 | 契約 SoT 是一切前置 | 小 |
| B2 | 2.0（golden 凍結）+2.1 | B1 | 同一出口單點；凍結必先於改碼 | 中 |
| B3 | 3.1+3.2 | B1 | 後端 status 與前端消費同一契約，分開會出現中間態假紅 | 中 |
| B4 | 4.1+4.2 | B1 | 同為事件誠實化，共用測試檔 | 中 |
| B5 | 5.1+5.2+5.3 | B1（5.3 另依 B2 之 report 契約已落） | 閘門三件一起收口 | 中 |
| B6 | 6.1+6.2+6.3+6.4 | B1–B5 | 收尾誠實契約＋登記，6.3 的 allowlist lifecycle 依 5.1 | 中 |
- **批內順序（R3 修訂：CODEX-R3-P1-03/GROK-R3-P2-01 寫死）**：B2＝2.0（凍結）→2.1（改碼）；B3＝3.1（producer）→3.2（consumer）；**B4＝4.2（簽名＋timestamps 下鑽）→4.1（loud fallback＋root）**——兩 Task 同改 `_stage3_event_filter`（:2682-2716），先接線後加語意，同函式改動合為單一 commit 檢視；B5＝5.3→5.1→5.2（5.1 allowlist 須含 5.3 後的最終 key 面）；B6＝6.3→6.1→6.2→6.4（6.3 動 allowlist，先做讓 6.x 後續驗證都在最終態上跑）。
- 批次間 Gate：前批全部 Test ID 綠（命令見各 Phase 測試節）→ 才進下批。
- 派工 prompt：不適用（主委自任）；每批開工前狀態＝上批 commit 已落＋`pytest tests/momentum/Analysis/ tests/api/ -k ichc` 綠。

---

## Phase 1 — 契約 SoT（目標：schema 檔成為唯一真相源；完成後系統狀態：runtime 行為零變化，新契約可被載入驗證）

### Task 1.1 — report/capability 契約 schema 檔（`票 —`：量化主線 epic 契約基線，不對單一治理票）
- SPEC ref：Task 1.1　目標：建 `ic_report_contract.json`＋pydantic 載入驗證＋types.ts 對應段。
- 輸入/輸出：輸入=SPEC §P 各 Task 之狀態需求；輸出=`momentum/Analysis/contracts/ic_report_contract.json`（新檔）＋`ic_config_schema.py` 之 loader 函式＋`types.ts` 對應型別段。
- 實作要點（R3 修訂：CODEX-R3-P1-01 刪枚舉散文、GROK-R3-P1-01 補 validator API）：
  1. schema 檔頂層三節，**節名如下、值一律只住檔內（本 TODO 不列任何枚舉值）**：`capability_status`（各節狀態枚舉）、`report_sections`（分位/衰減/分組/換手/coverage/net_ic 各節 envelope 形狀＋status 欄）、`reasons`（NetIC 停用原因、event fallback 原因、split_method 枚舉、timestamps epoch 語意註記）。
  2. `ic_config_schema.py` 新增兩個具名 API：`load_report_contract() -> dict`（讀檔＋`json.loads`；語法錯→raise fail-closed）＋`contract_enum(name) -> frozenset[str]`。
  3. **具名 validator**：`validate_report_against_contract(report: Mapping) -> None`——report 各節 status 不在契約枚舉、或必要節缺席→raise `ValidationError`；此函式即 SPEC「契約 validator 唯一邊界」的實體，Task 2.1 於 `generate_json_report` 出口呼叫。
  4. `types.ts` 新增對應段（手寫，與檔一致性由 Task 5.2 機檢；不做 codegen）。
- 修改檔案：`momentum/Analysis/contracts/ic_report_contract.json`（新）；`momentum/Analysis/ic_config_schema.py::load_report_contract/contract_enum/validate_report_against_contract`（新函式×3）；`frontend/src/lib/types.ts`（新型別段）。既有 caller：無（消費者在 B2–B6 接入）。
- 不可做：不改任何 runtime 行為；不動既有 report 輸出；不在 SPEC/TODO/註解複列枚舉值。
- 邊界：schema 檔語法錯→載入 raise 非靜默；`contract_enum` 查不存在節→KeyError（測試斷言）。
- 風險緩解：⊘（無 runtime 變更）。
- **存活至**：永久（SoT）。　**覆蓋風險**：無。
- 驗證：`jq empty momentum/Analysis/contracts/ic_report_contract.json` rc=0；`pytest tests/momentum/Analysis/test_ichc_contract_load.py` 全綠——T-1a 載入成功；T-1b `validate_report_against_contract` 對「status 不在枚舉」與「缺節」各 raises ValidationError（針對 validator API，非裸 loader）；T-1c 壞 JSON raises。

### Phase 1 測試
- 單元：`test_ichc_contract_load.py`（T-1a 載入、T-1b 未知值、T-1c 壞檔 fail-closed）。邊界：空節。效能：⊘（一次性載入）。
- Phase Gate：T-1a/b/c 全綠。

## Phase 2 — 分位圖 envelope 修復（目標：前端讀得到、數值一個不變；完成後狀態：QuantileReturnChart 有圖，golden exact）

### Task 2.0 — §G golden 凍結（`票 —`：§G 前置，不對單一票）
- SPEC ref：§G　目標：動工前凍結 per-feature 完整 canonical payload。
- 輸入/輸出：真實 `data_cache/feature_klines/kline_cache.h5` → `handoffs/run_receipts/ichc_p2_golden_pre.json`。
- **Frozen inputs（R3 修訂：COMPOSER-R3-P1-02 釘死）**：symbol=`ETHUSDT`、timeframe=`12h`（沿用 `tests/golden/la1/` 既有基準慣例）；config＝repo 預設 `ICConfig()` 不帶 override，凍結時將 `config_hash`（config canonical JSON 之 sha256）寫入 receipt 檔頭；entrypoint＝與 T-G1 測試同一條 orchestrator 主流程呼叫（腳本與測試共用同一 helper，禁兩套組裝）。
- **Canonical serialization spec（R3 修訂：COMPOSER-R3-P1-03/GROK-R3-P1-04 定死）**：①數值位 NaN 一律寫 `null`，另存平行 bool 陣列 `nan_mask`（與值陣列等長、同序）；②`json.dumps(..., sort_keys=True, separators=(',',':'), allow_nan=False)`——出現裸 NaN 即 ValueError（fail-closed）；③float 以 `format(x,'.17g')` 正規化後回寫；④凍結範圍＝`report["quantile_returns"]` 子樹全量＋feature 名集合 sha256，不含 `generated_at`；⑤腳本與 T-G1 共用同一序列化 helper（單一實作，禁測試側重寫）。
- 實作要點：①寫 `scripts/ichc_freeze_p2_golden.py`：跑主流程 report，抽 `quantile_returns` 全樹；②per-feature dict＝key set＋`quantile_mean_returns` 全值＋`cumulative_returns` 全值與長度＋`long_short` 全 scalar（含 `spread`/`long_short_tstat`）＋`monotonicity_score`＋`nan_mask`＋per-feature canonical sha256；③檔頭＝feature 名集合 sha256＋config_hash＋symbol/timeframe。
- 修改檔案：`scripts/ichc_freeze_p2_golden.py`（新）＋共用 helper（建議同檔可 import）。既有 caller：無。
- 不可做：不動產品碼；不用合成資料；不在測試側另寫序列化。
- 邊界：kline 缺檔/symbol 缺→腳本 loud fail 指路；重跑兩次輸出 byte 相同（決定性斷言）。
- 風險緩解：⊘。　**存活至**：epic 完工後保留於 run_receipts（§P 自檢句）。　**覆蓋風險**：無。
- 驗證：receipt 檔存在且 `jq empty` rc=0；重跑 diff == 0 bytes。

### Task 2.1 — reporter 出口 flatten（`票 —`：修 GROK-R1-P0-01 靜默空圖）
- SPEC ref：Task 2.1　目標：出口依映射表攤平，數值 exact 不變。
- 輸入/輸出：輸入=Task 1.1 契約＋Task 2.0 golden；輸出=`ic_reporter.py` 出口新 envelope＋前端型別對齊。
- 實作要點：
  1. 映射（SPEC 定死）：內層 `quantile_returns.*` 全鍵上提 feature 根層；`long_short.spread`→`long_short_spread`；`monotonicity_score` 留根層；**不丟鍵**（含 `cumulative_returns`）。
  2. 落點=`generate_json_report`（`ic_reporter.py:334` 一帶）單點 flatten＋出口處呼叫 `validate_report_against_contract`（Task 1.1 具名 validator）；CSV 側（:469-471）**現碼已讀 `long_short_spread` 鍵**——確認 flatten 後鍵名一致並補「該欄有值」斷言即可，勿做無意義 diff（GROK 建議採納）。
  3. `QuantileReturnChart.tsx` 型別對齊（讀取語意不變：`data.quantile_mean_returns`——攤平後即命中）。
  4. 出口矩陣測試：同一 report fixture 走 `get_result`／`export_all`／`save_report`／summary CSV／`GET /quantile/{feature_name}` 五路，逐路斷言形狀＋數值＋NaN。
- 修改檔案：`momentum/Analysis/ic_reporter.py::generate_json_report`＋CSV 讀鍵處；`frontend/src/components/ic-analysis/QuantileReturnChart.tsx`（型別）；`frontend/src/lib/types.ts`（QuantileReturnData 對契約）。既有 caller（全列）：`page.tsx:751-752,800`；`api/routes/ic_analysis.py:234-245`；`tests/api/test_ic_response_v2.py:245-246`（斷言更新）；`tests/golden/la0/gen_baseline.py:1019`（同步確認）；export_all 五出口；`_persist_outputs`（orchestrator:3748-3758）；service `get_result`（:333-352）。
- 不可做：不改 `MonotonicityTester` 計算；不動 `long_short` 數值語意；不改分位數個數；不弱化 factor_return_sanitizer 測試。
- 邊界：feature 無分位資料→契約空態非裸 `{}`；全 NaN→mask 保留＋前端空態文案。
- 風險緩解：golden（T-G1）＋mutation M1。　**存活至**：永久。　**覆蓋風險**：無（Phase 3 只動 xsec 分支）。
- 驗證：T-G1=`pytest tests/momentum/Analysis/test_ichc_p2_golden.py` 全綠（逐 feature 逐 path exact，atol=0）；出口矩陣測試綠；`QuantileReturnChart.test.tsx` `chartData.length == 分位數 n`；CSV `long_short_spread` 欄有值。

### Phase 2 測試
- 單元：contract validator 拒巢狀舊形。整合：出口矩陣五路。Golden：T-G1。前端：chart contract test。
- Mutation M1：flatten 映射任一鍵改名→T-G1 FAIL 列 feature+path→revert。
- Phase Gate：T-G1＋矩陣＋M1 實跑紅一次後綠。

## Phase 3 — xsec capability status（目標：空殼變誠實狀態；完成後狀態：xsec 模式五節帶 status，funnel 不再吃錯形狀）

### Task 3.1 — xsec 五欄改 typed status（`票 —`：修 COMPOSER-R1-P0-02/H 空殼）
- SPEC ref：Task 3.1　目標：`ic_filter_orchestrator.py:1481-1497` 五個硬編 `{}` 改契約 status 物件。
- 輸入/輸出：輸入=Task 1.1 契約；輸出=xsec 分支 `ic_decay/quantile_returns/grouped_ic/turnover_analysis/coverage_analysis` 各＝`{status: 模式不適用值, reason: …}`（值取自契約檔）。
- 實作要點：①以 `contract_enum` 取值建構 status 物件替換空 dict；②縱向分支零改動；③新測試檔斷言五節皆帶 status 非裸空。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::_run_cross_sectional_analysis`（:1481-1497 一帶）。既有 caller：xsec 消費端（page mode switch、export——Task 3.2 收口）。
- 不可做：不在 xsec 補算五類分析；不改 xsec IC 計算；不動 `filter_log`（funnel 由 3.2 前端收口）。
- 邊界：xsec＋deep 全關→五節 status 仍完整；單 symbol 退化輸入→status 非 KeyError。
- 風險緩解：mutation M4。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`ASSERT pytest tests/momentum/Analysis/test_ichc_xsec_capability.py WHEN mode=cross_sectional THEN rc=0`——斷言五節 status **值 ∈ 契約枚舉（經 `contract_enum` 取值比對）且 reason 欄非空**，非只「帶 status」（CODEX-R3-P1-04 修訂）；既有縱向測試全綠斷言不改。

### Task 3.2 — 前端 status 消費＋page wiring（`票 —`：同上，前端半）
- SPEC ref：Task 3.2　目標：五類圖 xsec 顯契約文案；型別改 discriminated union；xsec 不渲染 funnel。
- 輸入/輸出：輸入=3.1 之 status 形狀；輸出=五 component＋page 分流。
- 實作要點：①`types.ts` 五節型別改 union（status 形｜legacy 數值形）；②各 component 讀 status 分流文案，無 status（legacy）→現行文案；③`page.tsx:736-742` xsec 模式不渲染 `FilterFunnelChart`、顯 capability 說明；④4 類 page 級 fixture：xsec（含 funnel 不渲染）／legacy／unknown status fallback＋console warn／縱向回歸。
- 修改檔案（R3 修訂：COMPOSER-R3-P2-05 依 SPEC 具名）：`QuantileReturnChart.tsx`、`ICDecayChart.tsx`、`GroupedICBarChart.tsx`、`TurnoverTimeSeriesChart.tsx`、coverage＝現無 UI consumer→僅 `types.ts` 型別＋allowlist 註記（GROK-R2-P2-04 孤兒欄既判）；`FilterFunnelChart.tsx`（型別防衛）；`frontend/src/app/ic-analysis/page.tsx`；`frontend/src/lib/types.ts`。既有 caller：page 兩模式。
- 不可做：不重排版面；不為 xsec 造 funnel payload；不動縱向 funnel 行為。
- 邊界：unknown status→通用空態＋console warn；縱向有值→圖＋funnel 正常（回歸）。
- 風險緩解：⊘（純前端顯示）。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`npm test -- ic-analysis` 全綠，4 類 fixture 皆 page 級斷言（文案 exact／funnel 不渲染／warn 呼叫 expect）。

### Phase 3 測試
- 單元：3.1 status 物件。整合：雙模式 orchestrator。前端：4 fixture 矩陣。
- Mutation M4：xsec 任一節改回裸 `{}`→`test_ichc_xsec_capability.py` FAIL→revert。
- Phase Gate：M4 紅過＋全綠。

## Phase 4 — 事件誠實化（目標：不再靜默騙人；完成後狀態：insufficient loud、timestamps 真生效）

### Task 4.1 — insufficient fallback 改 loud（`票 —`：修 GROK-R1-P0-02；R3 修訂：COMPOSER-R3-P1-01/P1-04＋GROK-R3-P1-02 落點鏈路重寫）
- SPEC ref：Task 4.1　目標：tier=insufficient 回全樣本時 root `analysis_status=degraded_full_sample`＋metadata 事件資訊；banner 副文案。
- **落點鏈路（定案，勿在 stage3 寫 root）**：
  1. stage3（:2705-2716）只負責 `event_info["fallback"]=True`＋`event_info["reason"]`（值入契約檔）——現碼已設 fallback，補 reason。
  2. `_build_report_metadata`（:3631 一帶）已寫 `metadata["event_filter"]=event_info`——**事件資訊的單一路徑定案＝`report.metadata.event_filter`**（不新增 root `event_info` 欄；契約檔訂其形狀）。
  3. root 紅標：擴 `_resolve_root_status`（:1128-1146）——`metadata.event_filter.fallback` 為真→回 `degraded_full_sample`（重用既有值；normalizer `ic_reporter.py:50-65` 不動）；stage7（:3342-3348）annotate 鏈自然帶出。
  4. `DegradedBanner.tsx` 擴讀 `report.metadata.event_filter` 顯副文案（主文案不變）；`types.ts` 補 `metadata.event_filter` 型別。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`（:2705-2716 reason、:1128-1146 `_resolve_root_status`）；`frontend/src/components/ic-analysis/DegradedBanner.tsx`；`frontend/src/lib/types.ts`。既有 caller：event 請求鏈；split-fallback 既有 degraded 路徑（回歸：banner 主文案不變）；`_resolve_root_status` 既有三條件（回歸：不動）。
- 不可做：不做 case-control/matching；不改 tier 判準；不擴 normalizer 枚舉；不在 stage3 觸碰 report root。
- 邊界：事件恰於 tier 邊界→不誤標；零重疊 timestamps→既有 `AlignmentViolationError` 不變（回歸斷言）。
- 風險緩解：mutation M2（反例矩陣見下）。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`pytest tests/momentum/Analysis/test_ichc_event_honesty.py` 全綠，**測試矩陣必含 `holdout=ON × tier=insufficient`**（GROK-R3-P1-02：holdout OFF 時 root 本已 degraded，只測該格＝廉價綠燈）——斷言該格 root==degraded_full_sample ∧ metadata.event_filter.fallback==True ∧ reason ∈ 契約枚舉；banner 前端測試（副文案 exact）。

### Task 4.2 — event_timestamps 接線（`票 —`：修 CODEX-R1-P1-01）
- SPEC ref：Task 4.2　目標：`analyze(event_timestamps=None)` 顯式參數貫通 service→stage3。
- **完整呼叫鏈（R3 修訂：GROK-R3-P1-03/COMPOSER-R3-P2-01 五節點寫死，缺一節 timestamps 即恒 None）**：
  1. `orchestrator.analyze()` 簽名（:860-868）末端加 **keyword-only** `event_timestamps: list | None = None`（不破壞既有 positional caller）。
  2. analyze 內呼叫點（:963-965）下傳 `_stage3_event_filter(..., event_timestamps=event_timestamps)`。
  3. `_stage3_event_filter` 簽名（:2669-2676）加同名參數；:2682 以參數取代 `timestamps = None` 寫死。
  4. service 側：`_run_analysis`（:229-237 一帶）與 `_run_full_analysis` 的 `analyzer.analyze(...)` kwargs 各加 `event_timestamps=request.event_timestamps or None`。
  5. 刪 :1232-1233 之「not supported」warning（`_build_config_override` 不經手 timestamps——per-request 資料不入 config）。
- 其他要點：單位=features index epoch 語意（ms/s 自動偵測沿用 `ic_engine.py:1070-1077` 原語）；空 list≡未帶（第 4 節點之 `or None` 即正規化）；canonical oracle 測試＝排除 `generated_at`（唯一排除鍵，測試內寫死）後 canonical sorted JSON sha256 相等。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::analyze/_stage3_event_filter`；`api/services/ic_analysis_service.py::_run_analysis/_run_full_analysis`＋刪 warning 處。既有 caller：`analyze()` 其他呼叫點（keyword-only 預設參數；逐點 grep 回歸）。
- 不可做：不新增 API 欄位；不做前窗/matching；不塞 config schema。
- 邊界：空 list→等同未帶（同 oracle 斷言）；全部落 index 外→`AlignmentViolationError`（沿用）。
- 風險緩解：mutation M3。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`pytest tests/api/test_ichc_event_timestamps.py` 全綠——帶 timestamps fixture 用**嚴格真子集**（覆蓋 < 全樣本的 timestamps）→斷言 `n_obs < full_n`（嚴格小於，CODEX-R3-P1-04：`<=` 在斷線時仍成立＝假綠）∧ `metadata.event_filter` 反映生效；未帶→canonical sha256 相等。

### Phase 4 測試
- 單元：參數正規化。整合：API 帶/不帶/空 list 三態。
- Mutation M2：移除 `_resolve_root_status` 之 event fallback 分支→`test_ichc_event_honesty.py` 於 **holdout=ON×insufficient** 反例 FAIL（root 仍 ok_oos）→revert。M3：stage3 強制 `timestamps=None`→`test_ichc_event_timestamps.py` FAIL（**嚴格 `n_obs < full_n` 不成立**）→revert。
- Phase Gate：M2/M3 紅過＋全綠。

## Phase 5 — wiring 閘門（目標：幽靈永久防復發；完成後狀態：三規則機檢常駐 pytest）

### Task 5.1 — `scripts/ic_wiring_check.sh`（`票 —`：C5 幽靈群機械閘）
- SPEC ref：Task 5.1　目標：三規則靜態掃描＋fail-closed allowlist。
- 實作要點：①規則一：前端 toggle/config key（`getEffectiveConfig`／`featureToggles` 解析）⊆ 後端可消費 key（`STAGE_OVERRIDE_PATHS`∪deep module 名）；②規則二：後端 schema 欄位須有 consumer（AST/grep 命中 schema 欄位名於 momentum/api/frontend 任一消費點）或 allowlist 具名；③規則三：report 節須帶契約 status（禁裸空 dict——掃 orchestrator 字面 `: {}` 賦值於 report 節鍵）；④`scripts/ic_wiring_allowlist.json` 初始內容（具名，CODEX-R3-P1-05 修訂）＝FeatureTierPanel 五鍵 `ic_method_selection`/`winsorization_method`/`ic_autocorrelation`/`redundancy_method_selection`/`vif_filter`（來源 GROK-R1-P1-01）＋coverage 孤兒欄 `coverage_analysis` UI 缺席（GROK-R2-P2-04）＋`max_features_for_correlation`/`ShapleyConfig`（GROK-R2-P2-02；**於 Task 6.3 移除時同步剔除**）；每條目欄位＝key/所在檔/來源 finding ID/處置狀態；⑤allowlist 缺檔→rc!=0；allowlist 含現碼不存在的欄位→rc!=0（過期即紅）。
- 修改檔案：`scripts/ic_wiring_check.sh`（新）＋`scripts/ic_wiring_allowlist.json`（新）＋pytest 包裝 `tests/momentum/Analysis/test_ichc_wiring_check.py`（subprocess 跑腳本斷 rc）。既有 caller：無（pytest 常駐承載強制性）。
- 不可做：不掛治理 hook 鏈；不做散文/語意判斷（封閉集合機械比對）。
- 邊界：掃描目標檔移動→路徑存在性先 fail loud；動態組 key（模板字串）→保守列 allowlist 註記。
- 風險緩解：mutation M5。　**存活至**：永久。　**覆蓋風險**：allowlist 兩條目由 6.3 移除（lifecycle 設計內，非白工）。
- 驗證：`ASSERT bash scripts/ic_wiring_check.sh WHEN allowlist=present THEN rc=0`；`ASSERT bash scripts/ic_wiring_check.sh WHEN allowlist=absent THEN rc!=0`；pytest 包裝綠。

### Task 5.2 — 契約三方一致性測試（`票 —`：契約防漂移）
- SPEC ref：Task 5.2　目標：schema 檔↔pydantic↔types.ts 三源集合一致。
- 實作要點：①解析 schema 檔節名/枚舉值集合；②pydantic 側由 `load_report_contract` 取；③types.ts 側正則抽對應段（忽略註解）；④三源 set `==` 斷言；⑤tamper fixture：複製任一源增/刪一鍵→斷言 FAIL（測試測試自己）。
- 修改檔案：`tests/momentum/Analysis/test_ichc_contract_sync.py`（新）。既有 caller：無。
- 不可做：不做 codegen；不放寬為子集比較。
- 邊界：types.ts 註解干擾→解析器忽略註解（fixture 涵蓋）；schema 空節→FAIL。
- 風險緩解：mutation M6。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`pytest tests/momentum/Analysis/test_ichc_contract_sync.py` 全綠（含 tamper fixture 兩形態）。

### Task 5.3 — turnover toggle 語意＋NetIC 契約（`票 —`：C1 三家同判項）
- SPEC ref：Task 5.3　目標：方案 A 落地。
- 實作要點：①stage5 turnover 呼叫（orchestrator **:3103 該行**——:3099-3102 為 quantile/coverage `compute_all`，勿誤 gate；COMPOSER-R3-P2-03）加 `turnover.enabled` gate，disabled→report turnover 節＝status 物件（已停用值）；②NetIC 輸入端（orchestrator:2322-2335）：turnover_data 空且 turnover disabled→`_run_net_ic` 輸出 typed unavailable、reason=`turnover_disabled`（契約枚舉；既有裸字串 `turnover_not_available` 正名入契約——`net_ic_analyzer.py:359-369` 一帶）；③summary_table `turnover_rate` 欄（:3515）disabled 時顯式缺席（契約註記）；④2×2 測試矩陣。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`（:3099-3103、:2322-2335、:3515）；`momentum/Analysis/net_ic_analyzer.py`（reason 正名處）。既有 caller：stage5 消費端、NetIC deep runner、summary 消費端。
- 不可做：不動 NetIC 計算公式；不採方案 B（偷算）/C（互斥 422）；預設 config 兩者皆 ON 不變。
- 邊界：預設→ON×ON byte 等值回歸（排除 `generated_at`）；off×off→兩節 status 化無殘留數值鍵。
- 風險緩解：mutation M7。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`pytest tests/momentum/Analysis/test_ichc_turnover_gate.py` 全綠，矩陣四格各斷言；`ASSERT pytest tests/momentum/Analysis/test_ichc_turnover_gate.py WHEN turnover_enabled=false net_ic_enabled=true THEN rc=0`（NetIC status=unavailable ∧ reason==turnover_disabled）。

### Phase 5 測試
- Mutation M5：fixture 注入新幽靈 key→`ic_wiring_check.sh` rc!=0→移除 fixture。M6：三源任一側增/刪鍵→sync 測試 FAIL→revert。M7：刪 enabled gate→turnover_gate 測試 FAIL→revert。
- Phase Gate：M5/M6/M7 紅過＋`pytest -k ichc` 全綠。

## Phase 6 — 誠實契約＋登記收口（目標：缺口顯式化＋六票落 ROADMAP；完成後狀態：epic 可收）

### Task 6.1 — capacity unknown 契約鎖死（`票 —`：C8 契約面）
- SPEC ref：Task 6.1　目標：現行為契約化＋測試釘住（`net_ic_analyzer.py:239-252` 已 unknown，防回退）。
- 實作要點：①契約檔註記 capacity tier 枚舉含 unknown；②測試：無 ADV／ADV=0／負值→`capacity_tier == "unknown"`；ADV 正常→tier 計算（回歸）；③前端定案（COMPOSER-R3-P2-04 實查：`NetICChart.tsx` **無** `capacity_tier`/badge 消費，僅測試 fixture 有）→**前端本 Task N/A**——現無 UI 顯示 tier 即無「誤顯可交易 tier」風險；於契約檔註記「前端若未來消費 capacity_tier 須經契約」，不新增 UI。
- 修改檔案：`tests/momentum/Analysis/test_ichc_capacity_contract.py`（新）；產品碼原則零改（若現行為與契約不符才改，改動需列 diff 說明）。既有 caller：無 UI consumer（實查證據見上）。
- 不可做：不接真 volume 管線（gap 票⑤）。
- 邊界：ADV=0/負→unknown；正常→回歸。
- 風險緩解：⊘。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`pytest tests/momentum/Analysis/test_ichc_capacity_contract.py` 全綠（三態 unknown＋正常回歸四斷言）。

### Task 6.2 — WF/CPCV 現狀誠實標示（`票 —`：C7 誠實面）
- SPEC ref：Task 6.2　目標：metadata `split_method=holdout`＋文件節。
- 實作要點：①report metadata 寫 `split_method`（值自契約檔枚舉；fallback 全樣本時值同樣顯式——枚舉內定）；②`docs/API_SPECIFICATION.md` 加節 `## IC 主路徑切分現狀（holdout-only）`；③metadata writer 落點定案（CODEX-R3-P1-05 修訂）＝`_build_report_metadata`（:3631 一帶，與 Task 4.1 同一 metadata 組裝函式）——split plan 資訊由 `_build_holdout_split_plan` 產物讀出，寫入鍵置於 metadata 頂層。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py::_build_report_metadata`；`docs/API_SPECIFICATION.md`。既有 caller：report metadata 消費端（前端未消費則僅後端＋文件）。
- 不可做：不實作 WF/CPCV。
- 邊界：fallback 時 split_method 顯式；未來擴枚舉走 schema 檔單點。
- 風險緩解：⊘。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`pytest tests/momentum/Analysis/test_ichc_split_metadata.py` 全綠（`split_method == "holdout"`）；`grep -c "^## IC 主路徑切分現狀（holdout-only）" docs/API_SPECIFICATION.md` == 1。

### Task 6.3 — 死配置處置（`票 —`：C5 死配置＋C7 遷移）
- SPEC ref：Task 6.3　目標：移除二死配置＋REMOVED_KEYS 遷移警告＋allowlist lifecycle。
- 實作要點：①schema 刪 `max_features_for_correlation`（:172）與 `ShapleyConfig`（:330,440）；②`REMOVED_KEYS` 顯式清單（契約檔）＋loader 邊界（`ic_config_schema.py:472-488` deep-merge 後 validate 前）偵測→`logger.warning` code `ICHC-REMOVED-KEY`（不依賴 pydantic extra=ignore）；③清 `config/ic_config.yaml:114,220`；④`api/routes/ic_analysis.py:285-290` config dump 不回傳該欄；⑤同 commit 剔除 allowlist 二條目（wiring check 未知欄位規則即機械強制同步）。
- 修改檔案：`momentum/Analysis/ic_config_schema.py`；`config/ic_config.yaml`；`api/routes/ic_analysis.py`；`scripts/ic_wiring_allowlist.json`。既有 caller：config 載入鏈、API config 端點消費者。
- 不可做：不實作 correlation cap（gap 票⑥）；不擴成全面 strict mode。
- 邊界：舊 config 帶移除鍵→載入成功＋warning；API override 帶移除鍵→同路徑；非 REMOVED_KEYS 未知鍵→現狀 ignore（回歸）。
- 風險緩解：相容載入測試。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證：`grep -c "max_features_for_correlation\|ShapleyConfig" momentum/Analysis/ic_config_schema.py config/ic_config.yaml api/routes/ic_analysis.py` == 0；`pytest tests/momentum/Analysis/test_ichc_config_compat.py` 全綠（warning code exact＋未知鍵回歸）；`bash scripts/ic_wiring_check.sh` rc=0。

### Task 6.4 — gap registry＋票登記＋白話收口（`票 —`：文檔收口）
- SPEC ref：Task 6.4　目標：六缺口 registry＋ROADMAP 六票＋phasing pointer＋白話排程節。
- 實作要點：①`docs/IC_QUANT_GAP_REGISTRY.md`：六缺口（DSR/PBO/MinBTL、IC↔ML 橋＋多因子/邊際 IC、事件 case-control、pooled IC、容量 ADV、430K cap）逐條＝一行定義＋來源 finding ID＋觸發條件＋對應 phasing Phase 編號；②ROADMAP 狀態表加六列 pointer 至 registry；③`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md` 檔頭加一行 pointer（不改內文）；④`白話說明/IC健檢偵察結果.md` 加排程對照節（非檔尾追加）；README 索引同步。
- 修改檔案：`docs/IC_QUANT_GAP_REGISTRY.md`（新）；`docs/ROADMAP.md`；`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`（僅檔頭 pointer）；`白話說明/IC健檢偵察結果.md`；`白話說明/README.md`。既有 caller：ROADMAP 讀者。
- 不可做：不改 phasing CONVERGED 內文；不在 registry 寫演算法設計（票開了才寫 SPEC）。
- 邊界：ROADMAP 生成區塊不動；白話檔 no_append_only rc=0。
- 風險緩解：⊘。　**存活至**：永久。　**覆蓋風險**：無。
- 驗證（CODEX-R3-P1-05 補可執行命令）：`grep -c "^| " docs/IC_QUANT_GAP_REGISTRY.md` >= 6 且 `grep -c "R1-P" docs/IC_QUANT_GAP_REGISTRY.md` >= 6；`grep -c "IC_QUANT_GAP_REGISTRY" docs/ROADMAP.md` >= 1（六票 pointer 落點）；`grep -c "健檢" handoffs/20260624-ic-roadmap-phasing-CONVERGED.md` >= 1（檔頭 pointer 已加）；死連結 delta==+0 與 plain_docs_sync rc=0＝commit 當下由既有 pre-commit hook 輸出判讀（觀察其 stdout 行，非本 Task 另跑腳本——hook 名與輸出格式見本檔 §0 Commit 條之既有慣例）。

### Phase 6 測試
- 單元：config compat、capacity contract、split metadata。文件：grep 斷言三條。
- Phase Gate：全部 Test ID 綠＋`bash scripts/ic_wiring_check.sh` rc=0＋前端 `npm test -- ic-analysis` 綠＋`npm run build` 綠（前端有改動）。

---

## 自檢（階段 3；0 FAIL）
1. 追溯：§T 表 13 Task＋§G＋M1–M7＋RISK＋依賴＋flag 宣告全對應，合計數一致。
2. 深度：13 Task 皆有 ≥3 實作要點（含落點/簽名）、檔案到函式、邊界 ≥2、可證偽驗證。
3. 語義：Cross-Task 同檔（orchestrator 被 3.1/4.1/4.2/5.3/6.2 改）→批次序 B3→B4→B5→B6 序列化無並行衝突；golden 前置（Task 2.0）先於 2.1；Task 5.1 allowlist 與 6.3 之 lifecycle 已互指。
4. 全棧：Phase 2/3/4 皆有 後端→API→前端→測試 鏈；Phase 5/6 為閘門與契約（純層標註於各 Task）。
5. 錨點：`## §0`、`## §B`、每 Task 驗證/邊界/存活至/覆蓋風險/不可做 皆在。

## Frozen handoff
SPEC=docs/IC_HEALTHCHECK_SPEC.md TODO=docs/IC_HEALTHCHECK_TODO.md FOCUS=完整審查（已完成）
狀態=**FROZEN**（2026-08-17）：R3 三家 adversarial 20 findings→全採納修訂→R4 三家原提出方複驗 20/20 CLOSED→RECONCILE-STAMP codex/composer/grok 全 APPROVED（`handoffs/reconcile/20260817-ichc-x-review-r3/synth.md`，`reconcile_stamps_check` rc=0）。
