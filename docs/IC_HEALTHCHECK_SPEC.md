# IC-HC 健檢施工（3×P0＋契約 SoT＋wiring 閘門）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260817-ichc-x-consult-r1/synth.md`（C1–C13）＋`handoffs/20260817-ichc-recon-{claude,codex,composer,grok}.md`　|　日期：2026-08-17　|　對應 TODO：待生成

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。
- **命中高風險原則**：(b) 跨模組共用路徑——`ic_filter_orchestrator`（縱向/xsec/deep 三模式共用）＋`ic_reporter`＋api service＋frontend 同一 report 契約；(d) ML/回測正確性——事件 fallback 語意、分位圖呈現直接影響研究結論解讀。
- **RISK-HIT 宣告**：

RISK-HIT: b,d
- 命中 (d) → §G 必填、adversarial review 必跑。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（附 receipt，共 5 條）：
  - FACT-RECEIPT: `sed -n '180,195p' momentum/Analysis/monotonicity_tester.py` → 印出 per-feature 回傳巢狀 `{"quantile_returns":…,"monotonicity_score":…,"long_short":…}`（Claude 實跑 2026-08-17）
  - FACT-RECEIPT: `sed -n '1,30p' frontend/src/components/ic-analysis/QuantileReturnChart.tsx` → 印出 `Object.entries(data.quantile_mean_returns || {})`＝讀頂層鍵，巢狀下恆 `[]`（Claude 實跑 2026-08-17；GROK-R1-P0-01 另有動態 probe `chartData empty=True`）
  - FACT-RECEIPT: `rg -n "ic_decay|quantile_returns|grouped_ic|turnover_analysis|coverage_analysis" momentum/Analysis/ic_filter_orchestrator.py` → 印出 `1486-1496` xsec 分支五欄硬編空 dict（CODEX-R1-P1-02 實跑 2026-08-17；COMPOSER/GROK 同判）
  - FACT-RECEIPT: `sed -n '2705,2716p' momentum/Analysis/ic_filter_orchestrator.py` → 印出 `tier=="insufficient"` 時 `fallback=True` 並回傳未過濾全樣本（GROK-R1-P0-02 實跑 2026-08-17）
  - FACT-RECEIPT: `rg -n "compute_all" momentum/Analysis/ic_filter_orchestrator.py` → 印出 `:3103` stage5 無條件 `self._turnover.compute_all(...)`（CODEX-R1-P1-05 實跑 2026-08-17）
- **待使用者確認**：**待確認：無**
- **已確認結果**：`2026-08-17 使用者核可偵察結論、施工三類切分（施工/登記/defer）與逐票排序（本 session 對話）`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條照常（R1 `grep "from api\." momentum/`→0；R7 DTO 不跨界：契約 SoT 置於 `momentum/Analysis/contracts/`，api/frontend 各自消費不互 import）。
- 本任務特別注意：①`ic_filter_orchestrator` 三模式共用，改 xsec 分支不得影響縱向 golden；②`ic_reporter` 八出口統一 sanitizer（1cfr B1 產物）不得繞過或弱化；③`FactorEquityCurveChart` stopgap 三態（1cfr B2）不得回退；④la1 loud-fallback 先例（root 紅標）為 Phase 4 的既有模式，沿用不另造。
- **新資料結構鐵律**：capability status 枚舉與 report envelope 形狀一律入 **schema 檔單一真相源**（Task 1.1 建 `momentum/Analysis/contracts/ic_report_contract.json`）；本 SPEC 與 TODO **不得**在散文中列舉欄位/枚舉值；下文凡涉及者僅 pointer。
- **SPEC 階段禁寫實作**；委員以「腳本尚不存在」作 BLOCKING 屬 Task 未實作的正常狀態，回應寫進 §V。

## §G Golden / Baseline（RISK-HIT 含 d → 必填）
- **適用範圍**：僅 Phase 2（分位圖 envelope 修復）＝**行為不變型**——數值/NaN/數量不變，只改封裝形狀。Phase 3/4/5 為行為變更或新建，golden 不適用（§N 登記）。
- **feature/kline 條件**：以真實 `data_cache/feature_klines/kline_cache.h5` 跑，禁合成 fixture。
- **凍結時機 / reference**（R1 修訂：CODEX-R1-P1-02/GROK-R1-P2-02 全 payload 凍結）：Phase 2 動工前，以單 symbol＋固定 config 跑主流程 report，存 `handoffs/run_receipts/ichc_p2_golden_pre.json`：feature 名集合 sha256＋**per-feature 完整 canonical payload**——key set、分位鍵數量、`quantile_mean_returns` 全值、`cumulative_returns` 全值＋每條長度、`long_short` 全部 scalar（含 `spread`/`long_short_tstat`）、`monotonicity_score`、NaN/finite mask——並存 per-feature canonical sorted serialization sha256。
- **通過條件（可證偽）**：修後同 config 重跑，逐 feature 逐 path 對照：數值 exact（atol=0）、NaN mask exact、key set 經映射表換名後集合相等、cumulative 長度相等、feature 集合 sha 相等；唯一允許差異＝映射表明列的 envelope 路徑換名。任一差→列出 feature＋path＋diff＝FAIL、不 merge（逐 feature 對照，禁只比 aggregate hash——CODEX-R1-P1-02）。
- **測試紀律**（HANDOFF 定）：新測試優先性質檢驗/真實 kline/第三方對照；golden 僅此窄用。

## §P Phase 與依賴

### Phase 1 — 契約 SoT（依賴：無）
**Task 1.1 — report/capability 契約 schema 檔**
- 目標：建立單一真相源 schema 檔——capability status 枚舉＋IC report 各節（分位/衰減/分組/換手/coverage）envelope 形狀與狀態欄。　檔案：`momentum/Analysis/contracts/ic_report_contract.json`（新建）＋`momentum/Analysis/ic_config_schema.py` 載入驗證＋`frontend/src/lib/types.ts` 對應段。　既有 caller：無（新建；消費者於 Phase 2/3/5 接入）。
- 改法：schema 檔定義（形狀＋status 枚舉）；pydantic 側由檔載入建 validator；前端 types 与檔的一致性由 Task 5.2 機檢。
- **驗證**：schema 檔 `jq empty` rc=0；`pytest tests/momentum/analysis/test_ichc_contract_load.py` 全綠（載入成功＋枚舉未知值 raises ValidationError 兩斷言）。
- **邊界（≥2）**：schema 檔語法錯→載入 fail-closed（啟動即錯非靜默）；schema 缺必要節→validator 拒絕。
- **存活至**：永久（SoT）。
- **覆蓋風險**：無。
- 不可做：本 Task 不改任何 runtime 行為、不動既有 report 輸出。

### Phase 2 — P0-1 分位圖 envelope 修復（依賴：Phase 1）
**Task 2.1 — reporter 出口 flatten 至契約形狀（R1 修訂：GROK-R1-P1-03 映射表＋COMPOSER-R1-P1-01 caller 補齊＋CODEX-R1-P1-07 validator 邊界定案）**
- 目標：`report.quantile_returns[feature]` 依契約輸出，數值不變。定案＝**改後端出口單點**（Grok 已核：主報告經 `generate_json_report` 單點組裝，export/save/get_quantile 讀同一 report；內部 `_monotonicity_cache` 巢狀不出口）。
- **欄位映射表（source→target，契約檔為權威、此處為施工摘要）**：內層 `quantile_returns.*`（含 `quantile_mean_returns`、`cumulative_returns`、`long_short_tstat` 等全部鍵）上提為 feature 根層；`long_short.spread`→`long_short_spread`（CSV reporter:469-471 之 `_safe_nested` 期望鍵）；`monotonicity_score` 維持 feature 根層；**不丟任何鍵**（`cumulative_returns` 保留——stopgap 圖雖不繪，envelope 承諾不變）。
- **契約 validator 唯一邊界＝report 組裝點**（`ic_reporter.py` 之 `generate_json_report` 出口，共 1 個邊界）；所有下游（export_all 5 種、save_report、API get_result、`GET /quantile/{feature_name}`）讀已驗證 report，不各自再驗——但各出口測試斷言形狀（見驗證欄之出口矩陣）。
- 檔案：`momentum/Analysis/ic_reporter.py`（:334 出口＋:469-471 CSV 讀鍵）＋`QuantileReturnChart.tsx` 型別對齊。　既有 caller（**完整清單**）：`page.tsx:751-752,800`；`api/routes/ic_analysis.py:234-245`（`GET /quantile/{feature_name}` 直回 `result.quantile_returns[feature]`）；`tests/api/test_ic_response_v2.py:245-246`（subroute baseline——**斷言須隨契約更新，屬新行為對新斷言，非放寬**）；`tests/golden/la0/gen_baseline.py:1019`（讀 envelope，需同步確認）；`ic_reporter.export_all` 五出口＋`_persist_outputs`/`save_report`（orchestrator:3748-3758）＋API `get_result`（service:333-352）。
- 改法：出口處依映射表重排 envelope；過契約 validator。
- **驗證**：§G golden 全數值 exact（atol=0）；`pytest tests/momentum/analysis/test_ichc_p2_golden.py` 全綠；出口矩陣測試——同一 report fixture 逐一走 `get_result`／`export_all`／`save_report`／summary CSV／`GET /quantile/{feature_name}`，逐路徑斷言契約形狀＋數值＋NaN（CODEX-R1-P1-07 RECHECK 形態）；前端 contract test（`QuantileReturnChart.test.tsx`）——`chartData.length == 分位數 n`；CSV `long_short_spread` 欄有值斷言（COMPOSER-R1-P2-02）。
- **邊界（≥2）**：feature 無分位資料→輸出契約空態（status 欄）非裸 `{}`；全 NaN 分位→NaN mask 保留、前端顯空態文案。
- **存活至**：永久。
- **覆蓋風險**：無（Phase 3 只動 xsec 分支，不觸此出口；對照 §P 自檢通過）。
- 不可做：不改 `MonotonicityTester` 計算本體；不動 `long_short` 數值語意；不改分位數個數；不弱化 `factor_return_sanitizer` 既有八出口測試（其保護標的是 factor_returns，不得誤當 quantile 覆蓋）。

### Phase 3 — P0-2 xsec capability status（依賴：Phase 1）
**Task 3.1 — xsec 五欄空殼改 typed status**
- 目標：xsec 分支 `ic_decay/quantile_returns/grouped_ic/turnover_analysis/coverage_analysis` 由硬編空 dict 改為契約 status（區分「模式不適用/尚未產生/算失敗」，值域見契約檔）＋reason。　檔案：`momentum/Analysis/ic_filter_orchestrator.py:1481-1497` 一帶。　既有 caller：xsec 消費端（page mode switch、export）。
- 改法：以契約 status 物件替換空 dict；縱向分支不動。
- **驗證**：`ASSERT pytest tests/momentum/analysis/test_ichc_xsec_capability.py WHEN mode=cross_sectional THEN rc=0`（斷言五節皆帶 status 非裸空）；縱向模式對照——既有縱向測試全綠不改斷言。
- **邊界（≥2）**：xsec＋deep 模組全關→各節 status 仍完整；單 symbol 退化輸入→status 而非 KeyError。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不在 xsec 分支補算這五類分析（那是能力擴張，屬 gap 票）；不改 xsec IC 計算。

**Task 3.2 — 前端消費 status＋page wiring（R1 修訂：CODEX-R1-P1-04 型別閉合＋funnel 收口移入本 Task）**
- 目標：五類圖在 xsec 顯示契約化文案而非通用「暫無數據」；**五節型別改 discriminated union**（status/reason｜legacy 數值形狀，`types.ts` 同步）；**FilterFunnelChart 收口**：xsec 之 `filter_log` 為 `mode`/`n_timestamps` 形狀、不符 `FilterLogStage` 之 `input/output` 數值契約（`FilterFunnelChart.tsx:12-23` 直讀 `.input/.output` 會產 NaN）——定案＝`page.tsx` 於 xsec 模式**不渲染 funnel**、顯示 capability 說明（不造新 payload）。　檔案（具名五 component）：`QuantileReturnChart.tsx`、`ICDecayChart.tsx`、`GroupedICBarChart.tsx`、`TurnoverTimeSeriesChart.tsx`（或現行 turnover 消費 component，實作時以 grep 定名）、coverage 消費點＋`FilterFunnelChart.tsx`＋`frontend/src/lib/types.ts`＋`page.tsx`（mode 分流，:736-742 funnel props 一帶）。　既有 caller：`page.tsx` 兩模式。
- 改法：union 型別分流文案；page 於 xsec gate funnel；無 status（legacy）→維持現行文案（相容）。
- **驗證**：`npm test -- ic-analysis` 全綠，fixture 矩陣（CODEX-R1-P1-04 RECHECK 形態）＝xsec page fixture（含 funnel 不渲染斷言）／legacy report fixture（現行「暫無」文案 exact）／unknown status fallback／縱向正常資料（回歸）——4 類 fixture 皆須有 page 級測試，非只孤立 component。
- **邊界（≥2）**：status 未知值→fallback 通用空態＋console warn；縱向模式有值→圖正常渲染＋funnel 正常渲染（回歸）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不重排版面；不為 xsec 造 funnel payload（能力擴張屬 gap 票）；不動縱向 funnel 行為。

### Phase 4 — P0-3 事件誠實化（依賴：Phase 1）
**Task 4.1 — insufficient fallback 改 loud（R1 修訂：GROK-R1-P2-04 枚舉對接定案）**
- 目標：`tier=insufficient` 回退全樣本時 loud；禁 silent。**枚舉定案＝重用既有 `degraded_full_sample`**（不擴 `normalize_analysis_status` 二元枚舉——`ic_reporter.py:50-65` fail-closed normalizer 不動），區分資訊放 `event_info.fallback=True`＋`event_info.reason`（值入契約檔），DegradedBanner 讀之顯示副文案。　檔案：`momentum/Analysis/ic_filter_orchestrator.py:2705-2716`＋`frontend/src/components/ic-analysis/DegradedBanner.tsx`＋`frontend/src/lib/types.ts`（event_info 型別）。　既有 caller：event 模式請求鏈；既有 split-fallback 的 degraded 路徑（回歸——banner 主文案不變）。
- 改法：fallback 發生→root `analysis_status=degraded_full_sample`＋`event_info` 帶 reason；banner 副文案分流。
- **驗證**：性質測試——構造小事件集（tier=insufficient）→root status 斷言＋banner 前端測試；`ASSERT pytest tests/momentum/analysis/test_ichc_event_honesty.py WHEN tier=insufficient THEN rc=0`。
- **邊界（≥2）**：事件數恰於 tier 邊界→不誤標；零重疊 timestamps→既有 `AlignmentViolationError` 行為不變（回歸斷言）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不做 case-control/matching（gap 票）；不改 tier 判準本身。

**Task 4.2 — `event_timestamps` 接線（R1 修訂：GROK-R1-P1-02 通道定案＋CODEX-R1-P1-03 oracle 定案）**
- 目標：API 收的 `event_timestamps` 由「warning 後忽略」改為真傳遞至 stage3。**傳輸通道定案**：`orchestrator.analyze()` 新增顯式參數 `event_timestamps`（預設 None），service 由 request 欄位傳入，stage3 以該參數取代寫死的 `timestamps = None`；**不走** `EventFilterConfig` 塞欄（config 是宣告性設定，per-request 資料走參數）。**單位契約**：與 features index 同一 epoch 語意，秒/毫秒判別沿用 `ic_engine.py:1070-1077` 既有自動偵測原語（契約檔註記）；**空 list ≡ 未帶**。　檔案：`api/services/ic_analysis_service.py:1232-1233`＋`momentum/Analysis/ic_filter_orchestrator.py:2682-2706`（analyze 簽名＋stage3）。　既有 caller：API `analyze` 請求鏈；`analyze()` 其他呼叫點（預設參數，不受影響——實作時逐點回歸）。
- 改法：見通道定案；「not supported」warning 移除（已支援即不 warning）。
- **驗證**：`pytest tests/api/test_ichc_event_timestamps.py` 全綠——帶 timestamps 請求→`event_info` 反映生效且 `n_obs <=` 全樣本 n（性質不等式斷言）；未帶 timestamps→**canonical 等值 oracle**：報告排除 `generated_at`（唯一排除鍵，寫死於測試、禁實作擴充）後之 canonical sorted JSON sha256 相等。
- **邊界（≥2）**：空 timestamps 清單→等同未帶（同 canonical oracle 斷言）；全部 timestamps 落在 features index 外→`AlignmentViolationError`（沿用既有）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不新增事件 API 欄位；不做事件前窗/matching；不把 per-request timestamps 塞進 config schema。

### Phase 5 — wiring 閘門（依賴：Phase 1；與 Phase 2–4 並行開發、收口在後）
**Task 5.1 — 掃描器 `scripts/ic_wiring_check.sh`**
- 目標：三規則機檢：①前端 toggle/config key ⊆ 後端可消費 key（`getEffectiveConfig`/`STAGE_OVERRIDE_PATHS`/deep module 名）②後端 schema 欄位須有 consumer 或於豁免檔具名 ③report 各節須帶契約 status（禁裸空 dict）。　檔案：`scripts/ic_wiring_check.sh`（新建）＋豁免檔 `scripts/ic_wiring_allowlist.json`（新建；初始內容＝本輪已知殘留：FeatureTierPanel 五鍵、`max_features_for_correlation`、`ShapleyConfig`、coverage 孤兒欄等，逐條附來源 finding ID）。　既有 caller：無（新建；pytest 包一層跑）。
- 改法：靜態掃描（AST/grep 混合）；allowlist 白名單機械卡（封閉集合，不做散文判斷）。
- **驗證**：`ASSERT bash scripts/ic_wiring_check.sh WHEN allowlist=present THEN rc=0`；`ASSERT bash scripts/ic_wiring_check.sh WHEN allowlist=absent THEN rc!=0`（fail-closed）；mutation——測試 fixture 注入一條新幽靈 key→rc!=0。
- **邊界（≥2）**：掃描目標檔被移動→路徑存在性檢查先失敗（loud）；allowlist 含未知欄位名→視為過期、rc!=0。
- **存活至**：永久（隨 pytest 常駐）。　**覆蓋風險**：無。
- 不可做：不掛治理 hook 鏈（治理不擴建）；以 pytest 常駐測試承載強制性。

**Task 5.2 — 契約三方一致性測試**
- 目標：schema 檔 ↔ pydantic ↔ `types.ts` 三方一致（性質檢驗）。　檔案：`tests/momentum/analysis/test_ichc_contract_sync.py`（新建）。
- 改法：解析三源比對節名/枚舉值集合。
- **驗證**：`pytest tests/momentum/analysis/test_ichc_contract_sync.py` 全綠（三源集合 `==` 斷言）；mutation——測試內建 tamper fixture：任一側增刪一鍵→該測試 FAIL（斷言存在且可證偽）。
- **邊界（≥2）**：types.ts 註解干擾解析→解析器忽略註解（fixture 涵蓋）；schema 空節→FAIL。
- **存活至**：永久。　**覆蓋風險**：無。　不可做：不做 codegen（超scope）。

**Task 5.3 — turnover toggle 語意定案（含 NetIC 跨模組契約；R1 三家同判修訂：CODEX-R1-P0-01/COMPOSER-R1-P1-02/GROK-R1-P1-01）**
- 目標：`turnover.enabled=false` → stage5 **不算**、report turnover 節輸出契約 status=disabled。**NetIC 跨模組政策定案＝方案 A**：`turnover.enabled=false ∧ net_ic_analysis.enabled=true` → NetIC 輸出 **typed unavailable，reason=`turnover_disabled`**（這是明示的行為變更，NetIC 依賴 stage5 `turnover_analysis` 之 per-feature `quantile_turnover`——orchestrator:2322-2335、`net_ic_analyzer.py:359-369` 空輸入即 skip；禁再寫「不受影響」）。　檔案：`momentum/Analysis/ic_filter_orchestrator.py:3099-3103`（gate）＋`:2322-2335`（NetIC 輸入端 typed reason）＋契約檔補 `turnover_disabled` reason 值。　既有 caller：stage5 消費端、summary_table `turnover_rate` 欄（:3515，disabled 時該欄行為＝顯式缺席入契約）、NetIC deep runner。
- 改法：stage5 加 enabled gate；disabled 時寫 status 節；`_run_net_ic` 輸入缺席時輸出 typed unavailable（reason 值取自契約檔），非既有裸 `turnover_not_available` 字串（正名入契約枚舉）。
- **驗證**：`pytest tests/momentum/analysis/test_ichc_turnover_gate.py` 全綠，測試矩陣＝`turnover∈{true,false} × net_ic∈{true,false}` 四格：`ASSERT pytest tests/momentum/analysis/test_ichc_turnover_gate.py WHEN turnover_enabled=false net_ic_enabled=true THEN rc=0`（斷言 NetIC status=unavailable ∧ reason==turnover_disabled ∧ 無數值節）；`WHEN turnover_enabled=true net_ic_enabled=true` →現行輸出 byte 等值（回歸，排除 `generated_at`）。
- **邊界（≥2）**：預設 config→兩者皆 ON（回歸 exact）；turnover off ∧ net_ic off→兩節皆 status 化、無殘留數值鍵。
- **存活至**：永久。　**覆蓋風險**：無。　不可做：不動 NetIC 計算公式本體；不採方案 B（net_ic on 時偷算 turnover——違反「不算即不跑」語意）；不採方案 C（config 互斥 422——把研究組合擋死屬過度限制）。

### Phase 6 — 誠實契約＋登記收口（依賴：Phase 1–5）
**Task 6.1 — capacity unknown 契約鎖死**
- 目標：無 `avg_daily_volume_usd` → `capacity_tier=unknown` 為契約保證，前端禁顯示可交易 tier。　檔案：`net_ic_analyzer.py:239-252` 現行為已如此——本 Task＝契約化＋測試釘住（防回退），前端消費斷言。
- **驗證**：`pytest tests/momentum/analysis/test_ichc_capacity_contract.py` 全綠——無 ADV fixture→`capacity_tier == "unknown"` 斷言；前端測試斷言 tier 徽章不渲染。　**邊界（≥2）**：ADV=0／負值→unknown；ADV 正常→tier 計算（回歸）。　**存活至**：永久。　**覆蓋風險**：無。　不可做：不接真 volume 管線（gap 票⑤）。
**Task 6.2 — WF/CPCV 現狀誠實標示**
- 目標：report metadata 標 `split_method=holdout`（值入契約檔）；`docs/API_SPECIFICATION.md` 補「無 CPCV/WF 於 IC 主路徑」節。
- **驗證**：`pytest tests/momentum/analysis/test_ichc_split_metadata.py` 全綠（`split_method == "holdout"` 斷言）；`grep -c "^## IC 主路徑切分現狀（holdout-only）" docs/API_SPECIFICATION.md` == 1（specific 節標題，非任意 CPCV 字樣——CODEX 必答 1 指正）。　**邊界（≥2）**：fallback 全樣本時 split_method 值顯式定義（枚舉入契約檔）；未來加 CPCV 時枚舉可擴充（schema 檔單點）。　**存活至**：永久。　**覆蓋風險**：無。　不可做：不實作 WF/CPCV。
**Task 6.3 — 死配置處置（R1 修訂：CODEX-R1-P1-05 遷移機制定案；funnel 面已移入 Task 3.2）**
- 目標：`max_features_for_correlation`/`ShapleyConfig` 死配置移除。**遷移機制定案**：①schema 側維護顯式 `REMOVED_KEYS` 清單（值入契約檔），loader 邊界（`ic_config_schema.py:472-488` deep-merge 後、`model_validate` 前）偵測命中→發 warning（固定 code `ICHC-REMOVED-KEY`）——不可依賴 pydantic `extra=ignore`（其為靜默吞鍵，CODEX 實測 receipt）；②同 Task 清理 `config/ic_config.yaml:114,220` 兩處死鍵＋`api/routes/ic_analysis.py:285-290` config dump 不再回傳該欄；③**allowlist lifecycle**：Task 5.1 之 allowlist 中此二欄目於本 Task 同 commit 移除（wiring check 的「allowlist 含未知欄位→rc!=0」規則即為此 lifecycle 的機械強制——兩者同步否則紅）。
- **驗證**：`grep -c "max_features_for_correlation\|ShapleyConfig" momentum/Analysis/ic_config_schema.py config/ic_config.yaml api/routes/ic_analysis.py` == 0；`pytest tests/momentum/analysis/test_ichc_config_compat.py` 全綠——舊 config 帶二移除鍵→載入成功＋warning code `ICHC-REMOVED-KEY` exact 斷言；非 REMOVED_KEYS 的未知鍵→行為不變（現狀 ignore，回歸斷言）；`bash scripts/ic_wiring_check.sh` rc=0（allowlist 已同步）。
- **邊界（≥2）**：舊 config 檔帶已移除鍵→載入不爆＋warning；API override 帶已移除鍵→同 warning 路徑。　**存活至**：永久。　**覆蓋風險**：無。　不可做：不實作 correlation cap 本體（gap 票⑥/IC-PERF）；不把 REMOVED_KEYS 偵測擴成全面 strict mode（行為變更超 scope）。
**Task 6.4 — gap registry＋票登記＋白話（文檔收口）**
- 目標：`docs/IC_QUANT_GAP_REGISTRY.md`（六缺口：DSR/PBO/MinBTL、IC↔ML 橋＋多因子/邊際 IC、事件 case-control 真套件、pooled IC、容量 ADV 接線、430K cap；逐條附來源 finding ID＋觸發條件）；ROADMAP 狀態表六票列（pointer 至 registry）；`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md` 檔頭加 pointer 註記（不改內文）；`白話說明/IC健檢偵察結果.md` 加排程對照節。
- **驗證**：commit 時死連結 delta == +0（既有 hook 輸出）；plain_docs_sync rc=0；`grep -c "^| " docs/IC_QUANT_GAP_REGISTRY.md` >= 6（六缺口列存在）且六條各含來源 finding ID（`grep -c "R1-P" docs/IC_QUANT_GAP_REGISTRY.md` >= 6）。　**邊界（≥2）**：ROADMAP 生成區塊不受影響；白話檔非檔尾追加（no_append_only rc=0）。　**存活至**：永久。　**覆蓋風險**：無。　不可做：不改 phasing CONVERGED 內文（provenance）。

**§P 自檢**：無 forward dependency——Phase 2/3/4/5 皆僅依賴 Phase 1；Phase 6 收口依賴前五。Phase 2 產出（golden receipt）存活至 epic 完工後保留於 run_receipts。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**（RISK-HIT 含 d；R1 修訂補至 7 條——CODEX-R1-P1-06/COMPOSER-R1-P2-03/GROK-R1-P2-03；每條格式＝target→實跑命令→預期紅→復原=revert mutation）：
  1. Phase 2：flatten 映射任一鍵改名→`pytest tests/momentum/analysis/test_ichc_p2_golden.py`→FAIL 列出 feature+path→revert。
  2. Phase 4.1：移除 loud 標記寫入→`pytest tests/momentum/analysis/test_ichc_event_honesty.py`→FAIL（root status 斷言）→revert。
  3. Phase 4.2：stage3 強制回 `timestamps=None`→`pytest tests/api/test_ichc_event_timestamps.py`→FAIL（n_obs 不等式）→revert。
  4. Task 3.1：xsec 任一節改回裸 `{}`→`pytest tests/momentum/analysis/test_ichc_xsec_capability.py`→FAIL→revert。
  5. Task 5.1：fixture 注入新幽靈 key→`bash scripts/ic_wiring_check.sh`→rc!=0→移除 fixture。
  6. Task 5.2：三源任一側增/刪一鍵（各算一形態、同條宣告）→`pytest tests/momentum/analysis/test_ichc_contract_sync.py`→FAIL→revert。
  7. Task 5.3：刪除 enabled gate→`pytest tests/momentum/analysis/test_ichc_turnover_gate.py`→FAIL（enabled=false 仍有數值節）→revert。
  設計依 `docs/TEST_DESIGN_CHARTER.md`；驗收時逐條實跑，禁以刪斷言/放寬門檻取綠。
- 測試層級：單元（schema/status/gate）、整合（orchestrator 縱向+xsec 雙模式）、Golden（僅 Phase 2）、前端 contract/文案測試。全部可獨立 `pytest tests/momentum/...`＋前端 `npm test`，不需 run_api.py。
- **防假綠**：不放寬/刪除既有斷言（diff 審查）；1cfr sanitizer 出口測試、la1 loud-fallback 測試、1d attribution 三鍵測試不得動。
- **邊界目錄**：空DF ✓(3.1)／全NaN列 ✓(2.1)／Inf —（不涉新數值計算，N/A）／std=0 —（N/A 同前）／重複·亂序 timestamp ✓(4.2 邊界)／API重啟 —（無狀態改動，N/A）／並發寫 —（N/A，無新寫入路徑）／OOM降載 —（N/A，規模屬 IC-PERF）。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert，**回退機制＝git revert per-phase commit，不建 runtime flag**（R1 修訂：COMPOSER-R1-P2-01/GROK-R1-P2-01 指出原 `ic_healthcheck_compat` flag 群無任何 Task 建立＝空承諾；且本 epic 行為變更皆為誠實化契約、有測試釘住，flag 機構屬過度工程——CODEX scope 節同判）。Golden FAIL→不 merge。Task 6.3 移除死配置附相容載入（warning 非爆），revert 僅還原 schema 欄與 yaml 鍵。

## §N N/A 登記
- §G 已填（Phase 2 行為不變型窄 golden，含凍結路徑與 exact 通過條件）；行為變更型 Task（3.1/4.1/4.2/5.3）無「改前==改後」可比，其正確性義務由 §V 之性質檢驗＋mutation 承擔，此為 §G 的適用範圍界定而非豁免。
- §V 邊界目錄之 Inf/std=0/API重啟/並發寫/OOM：N/A——本 epic 不新增數值計算路徑、無新持久化寫入、規模防護屬 IC-PERF epic（見上表逐項標註）。
- 三方數據正確性簽核鐵律之「生成→計算→merge→split」全鏈：N/A——本 epic 不動 Feature Factory 資料生成鏈；涉及之 IC 語意正確性由 RISK-HIT d 之 adversarial＋golden＋性質檢驗覆蓋。
