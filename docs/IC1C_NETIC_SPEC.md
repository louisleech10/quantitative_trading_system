# IC Phase 1 — 1c Net IC 量綱正確化 — SPEC

> 來源 PLAN/診斷:docs/ROADMAP.md 1c 節+使用者參數訪談(2026-07-14,commit 89b5853)　|　日期:2026-07-14　|　對應 TODO:docs/IC1C_NETIC_TODO.md(SPEC 凍結後生成)　|　版本:**v1.0 Frozen(2026-07-14)**——r5 閉合:codex APPROVE(R5)+composer/grok delta concur APPROVE,RECONCILE-STAMP 機檢 PASS(三家,body sha256:ab910286)。歷史:(r2:composer/grok APPROVE+STAMP;r3/r4:codex 逐輪 CLOSED 全部舊 BLOCKING;r4 REJECT(2B)=R4-1 cost_bps=0 矛盾+R4-2 三層 validator 無逐層 probe——r5 落:裁 cost_bps=0 非法(無成本唯一表示=cost_enabled=False)三處同步、M10 三層各綁具名 test+同檔 probe(T5=config 層))

## §RISK 風險分級

- **大小**:大。
- **命中高風險原則**:(a) 數值正確性 (b) 跨模組全棧 (d) ML/回測正確性。
- RISK-HIT: a,b,d
- §G 必填、adversarial 已跑 r1(三家 REJECT)→ 本 r2 交閉合重驗。

## §A 假設與待使用者確認

**核心 bug(已驗證,4 條 FACT-RECEIPT,r1 三家複核同意)**:
- FACT-RECEIPT: `sed -n '25,42p' momentum/Analysis/net_ic_analyzer.py` → `net_ic = gross_ic_value - (use_cost / 10000.0) * turnover_value * 2.0`(Claude 實跑 2026-07-14;grok 另以 exec 手算 `compute_net_ic(0.05,1.5,10)→0.047` 複核)。相關係數減報酬率=無意義量;:41 `breakeven_cost_bps` 同病。
- FACT-RECEIPT: `grep -n "net_ic" momentum/Analysis/ic_filter_orchestrator.py` → `:1956 batch_analyze(summary, turnover_data)` 未傳 factor_returns(Claude 實跑 2026-07-14)。
- FACT-RECEIPT(r1 codex 實證): `factor_return_analyzer.py:87-88` `ls_returns` = high/low 分位各自 `reset_index` 後**按位置相減**——timestamp 錯位仍產生有限「報酬」;且僅輸出 mean/抽樣累積,無 `pd.Series` export(codex/composer/grok 三家獨立確認 2026-07-14)。
- FACT-RECEIPT(r1 codex 實證): `turnover_analyzer.py:22-40` `quantile_turnover` = 逐列 binary top-state `abs(diff)`,**每次進出已各計一腿**;現行 `×2` = 四腿重複計費(codex 2026-07-14)。

**待使用者確認**:待確認:無。
**已確認結果**:`2026-07-14 使用者訪談(ROADMAP 1c 節,commit 89b5853)`:① 成本禁寫死→前端輸入+啟用勾選,全棧接線;② 持倉 1h~1w 不定→情境掃描不綁 timeframe;③ capacity 維持現狀標未校準、低優先。
**委員會已裁(2026-07-14 三家 RULING 收斂,RECONCILE)**:RULING-FINAL: **B-strict**——永不從相關係數減報酬率;報告拆 gross IC(無量綱)+成本拖累(報酬空間)+損益平衡點(因子報酬分子);**canonical time-aligned factor-portfolio return series 未建立前(拆票 1c-FR),net_factor_return/breakeven/profitable 一律 `unavailable`+reason,禁以 IC 或現有 `long_short_mean_return`(錯位構造)代填**。
**案 A 封存條件(GROK-10)**:重提 IC 同單位化須另附 σ 估計 PIT 證明+與真實報酬交叉校準,不得混入 1c。

## §T Turnover 與成本語意(r2 新增,CODEX-2)

- `quantile_turnover` 定義=**每 bar 分位成員變動率,已含進出雙腿**(one-way legs summed)。輸出必附 `turnover_semantics: "membership_change_both_legs_per_bar"`。
- 成本模型:`cost_drag_return = (cost_bps/10000) × turnover`——**無 ×2**(×2 即四腿重複計費,M8 mutation 守)。
- `cost_semantics: "per_rebalance_not_annualized"`;禁任何年化、禁跨 timeframe 直比(文件+UI 註記);持有期矩陣依賴 1c-FR canonical series,**不入 1c**。
- **cost_sensitivity 階梯(r4 移入本節,Phase 1 實作)**:`scenarios = {c/2, c, 2c, 5c}`(c=生效 cost_bps),每值 clamp 至 [0.1, 1000] bps 後四捨五入 0.1、去重;舊 `cost_scenarios` 硬編碼 `[1,3,5,10,20]` 同 Phase 刪除。

## §U 統一佔位契約與輸出 profile(r3 新增,CODEX-6/R2-1+GROK-R2-1/2+COMPOSER-R2-1)

- **conditional metric 統一形狀(discriminated union)**:`net_factor_return`、`breakeven_cost_bps`、`profitable_after_cost` **當其鍵存在於該 profile 時**,一律為物件 `{"status": "ok"|"unavailable", "value": <number|bool|null>, "reason": <string|null>}`;`status=="unavailable"` 時 `value==null` 且 `reason` 非空;`status=="ok"` 時 `reason==null`。**形狀約束只管「存在時長什麼樣」;鍵是否存在由下方 profile 唯一決定**(r4 修 CODEX-R3-1:兩者不再互相矛盾)。HTTP 序列化不改形狀(value 非有限=非法,一律以 unavailable 表示)。TS 型別同構。禁止其他表示(`null`+頂層 reason、裸 number 皆非法)。
- **三套精確鍵集合 profile(§G equality 的唯一 oracle)**:
  - `SCHEMA_SKIPPED` = `{skipped: true, reason}`(觸發條件枚舉:turnover 缺/**非有限**/**負值**(v1.1 補裁:`turnover<0`=上游資料汙染,→SKIPPED reason=`negative_turnover`,**禁 `max(0,·)` 靜默 clamp**——TODO r2 三家共同 finding,交 r3 閉合輪核可)/gross_ic 非有限)
  - `capacity` 允許子鍵(v1.1 明列):`{estimated_capacity_usd: number|null(非有限→null), capacity_tier, calibration:"uncalibrated"}`
  - `SCHEMA_GROSS_ONLY`(cost_enabled=False)= `{gross_ic, turnover, turnover_semantics, capacity, net_factor_return}`——**無** cost_bps/cost_semantics/cost_drag_return/cost_sensitivity/breakeven/profitable 鍵
  - `SCHEMA_COST_ENABLED` = GROSS_ONLY ∪ `{cost_bps, cost_semantics, cost_drag_return, cost_sensitivity, breakeven_cost_bps, profitable_after_cost}`
  - 每 feature 鍵集合必須 == 其 profile 的集合(多/少鍵=FAIL);TODO 生成時三集合抄為測試常數 `tests/momentum/Analysis/test_net_ic_schema_profiles.py::SCHEMA_*`。
- **`cost_enabled`/`cost_bps` 於 Phase 1 進 config schema 與 analyzer**(修 CODEX-R2-1 phase 倒置):Phase 1 即建欄(config 層,default False/None)+analyzer 依 profile 輸出;Phase 2 只做 API request typed 欄+前端接線。G-NEW(Phase 1 後)凍 GROSS_ONLY+SKIPPED+(config 直開 cost 的)COST_ENABLED 三 profile;G-NEW2(Phase 2 後)僅驗 API 傳導,feature 級 schema 不再變。**cost_sensitivity 階梯算法於 §T 定義、Phase 1 實作**(r4 修 CODEX-R3-2:Phase 3 不再改 schema,只剩 UI 註記/文案)。
- **finite/range validator(r4 新增,CODEX-R3-3)**:`cost_bps` 合法域=有限且 `0 < cost_bps ≤ 1000`;三層一致強制:config schema(pydantic validator)、API request(422)、analyzer 直呼(raise ValueError)。`turnover` 非有限→該 feature 落 `SCHEMA_SKIPPED`(reason=`non_finite_turnover`)。故 `cost_bps`/`cost_drag_return` 兩裸數值欄**恒有限**(cost 有限×turnover 有限=有限),與 §G 禁 JSON NaN/inf 相容;此不變式入測試(§V M10)。

## §C 約束與 consumer-map(r2 補全,F8)

- 解耦 7 條/AST scanner 全綠不得破;config 單源;DTO 不跨界。
- **完整 consumer manifest(改動必逐點附 red-on-break)**:
  1. `momentum/Analysis/net_ic_analyzer.py`(本體)
  2. `momentum/Analysis/ic_filter_orchestrator.py:1942-1956`(runner)+:70/:1613/:1648/:1720/:1749-1750(模組註冊)
  3. `momentum/Analysis/turnover_analyzer.py:125-137` **`compute_net_ic_proxy` 同病孿生→納入 1c scope 刪除或正名為報酬空間**(禁雙重標準)
  4. `momentum/Analysis/ic_reporter.py:150/:209/:570/:631-634/:773`(CSV 欄+alias+inject)
  5. `momentum/Analysis/ic_config_schema.py:266-271`(`default_cost_bps=5.0`、幽靈 `slippage_bps=2.0`、`cost_scenarios` 硬編碼)
  6. `config/ic_config.yaml:181-186`(5bps YAML 回退)
  7. `momentum/factories.py:505` `create_net_ic_analyzer`
  8. `api/models/ic_models.py:18-35`(`net_ic_analysis: bool=True`、自由 `config_override`)
  9. `api/services/ic_analysis_service.py:1140`(僅傳 enabled)+:628-665(背景套 config)+:1198-1213(NaN→null 轉換)
  10. `api/routes/ic_analysis.py:107-118`(先回 200 後背景驗證→422 須在 HTTP 邊界)
  11. `frontend/src/components/ic-analysis/NetICChart.tsx:13,20-26,36-37,44,57`(硬編 useState(5)、`[1,3,5,10,20]`、**turnover fallback 0.1 假值**、Net IC 軸)
  12. `frontend/src/components/ic-analysis/DeepAnalysisConfigPanel.tsx:28`+`FeatureTierPanel.tsx:39`(「淨 IC」文案)
  13. `frontend/src/app/ic-analysis/page.tsx:419-428,823`+`hooks/useICAnalysis.ts:320-331`(request wiring)
  14. `frontend/src/lib/types.ts:2451-2474` `NetICAnalysisData` 全型別
  15. `frontend/src/store/icAnalysisStore.ts`(module toggle+新成本欄)
  16. tests:`tests/phase25/test_net_ic_analyzer.py`、`tests/momentum/Analysis/test_net_ic_analyzer.py`(近重複)、`tests/phase24/test_deep_analysis_config.py:23,70-74`(斷言 default==5,**舊斷言固化寫死成本=錯**)、`tests/momentum/test_turnover_analyzer.py:60-66`(proxy)、`tests/momentum/test_export_formats.py:73-75,107-113`、`tests/phase26/*`、`tests/api/test_ic_deep_analysis.py`
- 既有測試斷言會改:見 §V「新建 vs 改寫」表,逐條附為何舊斷言錯,禁靜默放寬。

## §G Golden / Baseline(r2 重設計,F7)

- 資料:真-kline fixture(`tests/fixtures/ic_api_real_kline.py`,源自 `data_cache/feature_klines/kline_cache.h5`);禁合成 fixture。
- **G-OLD(Phase 0)**:改前全量輸出 JSON(features 全 dict+summary)+sha256 凍 `handoffs/ic1c_baseline/`。含 skipped 路徑(turnover 空/gross_ic NaN)。
- **G-NEW(Phase 1 後)**:
  1. **全鍵集合 equality**:每 feature 輸出鍵集合 == §U 三 profile 之一的精確集合(依該 feature 的 skipped/cost_enabled 狀態選集;多鍵/少鍵=FAIL);conditional metric 形狀==§U union(shape 驗證,非只鍵名);
  2. **canonical 重算**:驗證腳本以獨立實作(直接 numpy 算 `cost_drag=(bps/1e4)×turnover`)重算**全量 feature**(非抽 3)比對 value+NaN mask,`atol=1e-12`;
  3. 不變欄:`gross_ic`/`turnover` 對 G-OLD byte 級等值;G-NEW 以 config 直開 cost(固定測試值 10bps)產 COST_ENABLED profile 樣本;G-NEW2(Phase 2 後)僅驗 API 傳導等值,feature 級 schema 凍結不變;
  4. 必變欄 diff 表:全部列出+機器可驗規則(如 `net_ic` 鍵**不存在**、summary 新欄依 §P 契約),未列欄位變動=FAIL;
  5. JSON 禁 `inf`/`NaN` 字面值——非有限值一律 `null`+`reason`(CODEX-6)。
- mutation 綁 golden:恢復混減公式 → canonical 重算必紅;`gross_ic` 來源欄改錯(:1947)→ 不變欄比對必紅。

## §P Phase 與依賴

### Phase 0 — Baseline 凍結(依賴:無)
**Task 0.1**:真-kline fixture 跑 net_ic 模組凍 G-OLD JSON+sha256 至 handoffs/ic1c_baseline/。驗證:重跑 sha256 一致;skipped 路徑入 baseline。

### Phase 1 — 核心量綱修復(依賴:Phase 0;修法=B-strict 已裁)
**Task 1.1 — net_ic_analyzer 改寫**
- 檔案:`compute_net_ic` 刪除(整個混減公式);新 `compute_cost_drag(cost_bps, turnover) -> float`(§T 公式,無 ×2);`cost_sensitivity_analysis` 改產 `scenarios[].cost_drag_return`;`batch_analyze` 輸出=§U 三 profile(鍵集合+形狀為唯一 oracle);`compute_net_factor_return` 標 deprecated 且 `batch_analyze` 於 1c 內**忽略** factor_returns 注入、conditional metrics 恒 `{status:"unavailable"}`(GROK-R2-3)。
- **config schema 同 Phase 建欄(修 CODEX-R2-1)**:`ic_config_schema.py` 本 Task 即刪 `default_cost_bps`/`slippage_bps`、新 `cost_enabled: bool=False`+`cost_bps: float|None=None`;`config/ic_config.yaml:181-186` 同步。
- **`net_ic` 鍵禁止輸出,含任何別名**(F6 裁死)。
- **summary 契約(F5)**:`total_analyzed`/`evaluable_count`(有報酬序列者,1c 恒 0)/`profitable_count`(只計 evaluable)/`avg_cost_drag_return`(取代 `avg_ic_loss_pct`)/`rank_correlation_gross_vs_net`→刪除(1c-FR 恢復,以報酬序列版)。
- 驗證:`pytest tests/momentum/Analysis/test_net_ic_analyzer.py` 手算對照 cost=10bps,turnover=1.5 → `cost_drag_return==0.0015`(§T 無 ×2);輸出斷言 `"net_ic" not in result`。
- 邊界:turnover=0(cost_drag=0,breakeven unavailable)、gross_ic NaN(skipped)、**cost_bps=0 非法**(r5 裁決 CODEX-R4-1:「無成本」唯一表示=`cost_enabled=False`;0 在 enabled 語意下無意義,三層一致拒絕,與 §U 域 `0<cost_bps≤1000` 同步)、cost_enabled=False(無 cost 子樹)。
- 不可做:不得實作 IC→報酬轉換;不得以 `long_short_mean_return` 餵 breakeven(錯位構造,F1)。

**Task 1.2 — orchestrator fail-closed(r2 改寫,F1/F2)**
- `_run_net_ic` 不傳 factor_returns(**canonical time-aligned series 未建立**,GROK-R2-4:`FactorReturnAnalyzer` 模組本身存在且不動,勿誤刪);輸出依 §U:`net_factor_return={"status":"unavailable","value":null,"reason":"canonical_factor_return_series_not_built (1c-FR)"}`。模組依賴矩陣:net_ic_analysis 不依賴 factor_return 模組(1c 內)。
- 驗證:`pytest tests/api/test_ic_deep_analysis.py -k net_ic`(新建)斷言 `net_factor_return.status=="unavailable"` 且 reason 非空;斷言全輸出樹無 `"net_ic"` 鍵。

**Task 1.3 — turnover proxy 同病清除(r2 新增,F8)**
- `turnover_analyzer.compute_net_ic_proxy`(:125-137)刪除或改名 `cost_drag_proxy`(報酬空間,§T 公式);`tests/momentum/test_turnover_analyzer.py:60-66` 同步改寫(舊斷言 `0.1-0.01×2=0.08` 固化四腿計費=錯)。
- 驗證:`grep -rn "net_ic_proxy" momentum/ tests/` == 0 或全部新語意;mutation M8 綁此。

### Phase 2 — 成本參數全棧接線(依賴:Phase 1)
**Task 2.1 — config/API fail-closed(r2 強化,F4/F9/F12)**
- config schema 欄位已於 Task 1.1 建立(本 Task 不重複)。
- `api/models/ic_models.py`:typed nested `NetICAnalysisRequest{cost_enabled, cost_bps}`(非 config_override 自由 dict);Pydantic model validator:`cost_enabled=True 且 cost_bps None → ValidationError`——**422 在 HTTP 邊界**(route 回 200 前,`ic_analysis.py:107-118` 同步路徑),非背景;`config_override` 對 `net_ic_analysis` 節**整節 reject**(含 `cost_enabled`/`cost_bps`/`default_cost_bps`/`slippage_bps`/`cost_scenarios` 及任何未知鍵——白名單空集,成本相關一律走 typed 欄,修 CODEX-3 殘留)。
- analyzer:`cfg.get("default_cost_bps", 5.0)` fallback 刪除;enabled 缺 cost → raise(防 direct factory 呼叫繞過)。
- DTO:conditional metrics 一律 §U discriminated union(types.ts 同構,唯一合法形狀;禁 `number|null` 裸表示)。
- 驗證:`pytest tests/api/test_ic_deep_analysis.py -k cost` 斷言 (i) enabled+缺 cost→HTTP 422(同步回應);(ii) 舊 request 不帶成本欄→`cost_enabled=False` 路徑,輸出無 cost 子樹且無任何 5bps 痕跡:`grep -rn "5\.0" 於 net_ic 路徑==0`(schema/YAML/analyzer 三處)。
**Task 2.2 — 前端(F8 補全)**
- DeepAnalysisConfigPanel:成本 bps 輸入欄+啟用勾選;NetICChart:刪 `useState(5)`/硬編 `[1,3,5,10,20]`/**turnover fallback 0.1**(缺 turnover→顯示「無資料」,禁假值);軸與標題改 `cost_drag_return`(不再稱 Net IC);FeatureTierPanel:39 文案改「成本拖累(報酬空間)」;page.tsx/useICAnalysis/store/types 全同步。
- 驗證:`npm run build` 綠+wiring 測試:UI 送 cost_bps=7 → 後端 artifact 記 7(M4);`grep -n "0.1" NetICChart.tsx` 無 turnover fallback。

### Phase 3 — UI 語意註記(依賴:Phase 2;r4 縮:階梯與 semantics 欄已移 §T/Phase 1,本 Phase **零 schema 變更**)
**Task 3.1**:前端 UI 註記禁年化/禁跨 TF 直比(NetICChart 說明文字+tooltip);文件同步。驗證:`npm run build` 綠;`grep -n "per_rebalance" frontend/src/components/ic-analysis/NetICChart.tsx` ≥1;G-NEW2 對本 Phase 前後 feature 級輸出 byte 等值(證零 schema 變更)。
(階梯/semantics 驗證隨 Phase 1:`pytest tests/momentum/Analysis/test_net_ic_analyzer.py -k scenario` 斷言 `cost_semantics=="per_rebalance_not_annualized"`+階梯值符 §T 公式。)

### 拆票(不入 1c)
- **1c-FR**:canonical time-aligned factor-portfolio gross-return+turnover series(修 ls_returns 錯位、模組間資料通道、net_factor_return/breakeven/profitable 實值、持有期矩陣、rank_correlation 恢復)。RISK-HIT a,d,另走完整管線。

## §V 驗證策略(r2 重寫,F10)

**Property→Oracle→Test→Mutation 矩陣**(依 docs/TEST_DESIGN_CHARTER.md **B4 類別+B1.1 自證 probe**;r3 依 CODEX-7 補「測試檔:函式」與自證機制):

主測試檔:`tests/momentum/Analysis/test_net_ic_analyzer.py`(=T1,合併 phase25 重複本)/`tests/api/test_ic_deep_analysis.py`(=T2)/`tests/momentum/test_turnover_analyzer.py`(=T3)/`frontend` vitest `NetICChart.test.tsx`(=T4)/`tests/phase24/test_deep_analysis_config.py`(=T5,config schema 層,R 改寫)。

| # | Property | 章程類別 | Oracle | 測試檔:函式(N 新建/R 改寫) | 自證 mutation probe(同檔 `test_mutation_*`,基線綠→注入紅→還原綠) |
|---|----------|----------|--------|------------------------------|------------------|
| M1 | 禁混量綱減法 | 契約/負向 | 全樹遞迴無 `net_ic` 鍵+canonical 重算 | N T1:`test_no_net_ic_key_anywhere` | T1:`test_mutation_m1_restore_mixed_subtraction` |
| M2 | cost_drag 公式無 ×2 | 數值 oracle | 手算 `10bps×1.5=0.0015` | N T1:`test_cost_drag_hand_calc` | T1:`test_mutation_m2_reinstate_x2` |
| M3 | breakeven fail-closed | 契約 | §U unavailable 物件,禁 IC 分子 | N T1:`test_breakeven_unavailable_1c` | T1:`test_mutation_m3_ic_numerator_backfill` |
| M4 | 成本 wiring 非幽靈 | 整合 wiring | request cost_bps=7→artifact 記 7 | N T2:`test_cost_bps_fullstack_wiring`+T4:`sends_cost_bps` | T2:`test_mutation_m4_drop_cost_passthrough`+**T4 同檔 `test_mutation_m4_frontend_drop_cost`**(vitest:mock 掉 request builder 的 cost 欄→`sends_cost_bps` 必紅;r4 修 CODEX-7 殘留) |
| M10 | 裸數值欄恒有限+域 (0,1000](含拒 0) | 邊界/不變式 | **三層各自具名 test**(r5 修 CODEX-R4-2):analyzer=T1:`test_finite_invariants`;API=T2:`test_cost_bps_range_422`(含 0/NaN/inf/1000.1);config schema=T5(R `tests/phase24/test_deep_analysis_config.py`):`test_net_ic_cost_validator` | 三層各自同檔 probe:T1:`test_mutation_m10_drop_finite_guard`+T2:`test_mutation_m10_api_drop_validator`+T5:`test_mutation_m10_config_drop_validator` |
| M5 | 5bps fallback 拔淨 | 負向/靜態 | schema+YAML+analyzer grep==0;enabled 缺 cost raise | N T1:`test_no_default_cost_fallback` | T1:`test_mutation_m5_revive_cfg_get_default` |
| M6 | summary 契約 | 契約 | `avg_ic_loss_pct`/`rank_correlation_gross_vs_net` 不存在;profitable 只計 evaluable | N T1:`test_summary_contract_b_strict` | T1:`test_mutation_m6_ic_vs_ic_rankcorr` |
| M7 | override 繞過封死 | 邊界/安全 | `config_override.net_ic_analysis` 任何鍵→422 | N T2:`test_config_override_net_ic_rejected` | T2:`test_mutation_m7_allow_override_key` |
| M8 | proxy 同病清除 | 負向 | `net_ic_proxy` 語意消失 | R T3:`test_cost_drag_proxy` | T3:`test_mutation_m8_restore_proxy_subtraction` |
| M9 | §U 形狀唯一 | schema | conditional metric 三欄物件形狀驗證 | N T1:`test_unavailable_union_shape` | T1:`test_mutation_m9_bare_null_placeholder` |

- probe 實作=章程 B1.1:monkeypatch/參數注入模擬 mutant,斷言目標測試 FAIL,還原後 PASS;Python 側驗收跑 `scripts/mutation_probe_check.sh`(已確認存在,僅掃 `test_*.py`);**前端 probe(T4)不在該腳本範圍,驗收=`npm run test -- NetICChart` 明列 `test_mutation_m4_frontend_drop_cost` 通過**(TODO 須列此為獨立驗收命令,不得只跑 Python checker 即稱 M4 閉合)。

**改寫測試表(舊斷言為何錯)**:phase25+momentum/Analysis 兩份 `test_net_ic_analyzer.py`(斷言 `net_ic` 鍵=固化錯 API;近重複→合併一份)/phase24 `default_cost_bps==5`(固化寫死成本)/export_formats fixture(舊 schema)/turnover proxy(四腿計費)。phase26 factories/integration 預期綠(模組名不變)。
**防假綠**:所有改寫逐條 diff+理由;golden 綁 mutation(§G)。API 測試離線環境 `api.main` import 觸發 Binance ping 之 collection error(codex r1 實測)→ 測試須可在無網環境 collect(fixture 層隔離,不得弱化)。
邊界目錄:☑ 空 DF ☑ 全 NaN ☑ turnover=0 ☑ **cost_bps=0→三層拒絕**(r5 裁非法) ☑ cost_enabled=False ☑ 舊 request 相容 ☐ 並發 ☐ OOM。

## §R 回退

- 每 Phase 獨立 commit 可 revert;Phase 2 API additive+`cost_enabled` default=False(舊 request 語意=不啟成本,**與 `modules.net_ic_analysis=True` 相容**:模組照跑但輸出 gross-only,無 5bps 幽靈);golden FAIL→不 merge。cost_enabled 是功能開關(使用者語意)非逃生口。

## §N N/A 登記

- 三方數據正確性簽核鐵律全文:N/A——非 feature 生成/merge/split;但走三家 adversarial+閉合重驗(已跑 r1,本 r2 交閉合)。
- capacity 校準:N/A——使用者裁定僅標 `uncalibrated`。
- net_factor_return/持有期矩陣/rank_correlation:N/A(1c 內)——拆 1c-FR 票,fail-closed 佔位。
