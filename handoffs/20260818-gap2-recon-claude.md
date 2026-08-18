# GAP-2a／2b 偵察 R1 — 主委版（CLAUDE；roster 外，供 reconcile 對照）

> brief：`handoffs/20260818-gap2-recon-BRIEF.md`｜日期 2026-08-18｜read-only 偵察，禁改碼。
> 主委版與三家（codex／composer／grok）平行產出；本檔不進 completeness roster，只作對照與 SPEC 起草輸入。

## Verdict：可進 SPEC 起草（無 BLOCKING）；三項技術取捨交 reconcile 決（見末節）

## CLAUDE-R1-P0-01

**斷言**: 現有正交化輸出無法承載「邊際 IC」——`gram_schmidt` 回傳 QR 的 Q（正交規範化列），逐因子 residual 序列只算 `np.var` 進 metadata 後丟棄，且為 full-sample 單次擬合；任何以它為基底的邊際 IC 都會（a）沒有 residual 可對 label 算相關（b）被 `deny_factor_in_ok_oos` 拒於 ok_oos 報告之外。

**碼證**: `momentum/Analysis/factor_orthogonalizer.py:43-45`（`q_matrix, _ = qr(matrix, mode="economic")`；回傳 `orth = pd.DataFrame(q_matrix, ...)`）、`:52-62`（`residual = target - projection`；僅 `float(np.var(residual))` 存入 `features_meta`）、`:30`（`dropna(axis=0, how="any")` 全樣本）；`momentum/core/contracts.py:1956-1968`（`FactorModuleResult.oos_guarantees: Literal[False]`、`fit_scope: Literal["full_sample"]`）、`:2000-2012`（`deny_factor_in_ok_oos` 拒 `module∈{orthogonalization,exposure}` 且 `oos_guarantees=False`）。RECHECK：`sed -n 43,62p momentum/Analysis/factor_orthogonalizer.py`。

**來源摘要**: `momentum/Analysis/factor_orthogonalizer.py#989b9e4b2101`；`momentum/core/contracts.py#8a1415d6ea01`

修法：邊際 IC 走**自己的** train-fit／test-apply 路徑（新純函式），不改 `factor_orthogonalizer.py` 語意（保留 full-sample research-only）；新結果型別**不得**沿用 `FactorModuleResult`（型別鎖死 False），另定 `MarginalICResult` 帶 `fit_scope∈{train,full_sample}`、`oos_guarantees` 隨 root status。信心度 High。

## CLAUDE-R1-P0-02

**斷言**: 「邊際 IC」在本平台語意（單標的縱向、Spearman IC）下應定義為 **residual IC**：對 candidate f 與已選集合 S，於 train 段以 OLS 擬合 f 對 S（含截距）之投影係數 β̂，於 test 段取 r=f−Sβ̂，`marginal_ic = Spearman(r_test, y_test)`；並以**秩空間**（mask 內 average rank）做投影以與 Spearman IC 一致。此定義（而非「Δ組合 IC」或「label 也殘差化的偏相關」）才直接回答「相對已有集合帶來多少**新**資訊」，因為對互相正交的因子，最佳線性組合之 IC² ＝ Σ marginal_ic²（Grinold & Kahn 之 information-added 加法性）——這條加法性同時是可證偽 oracle。

**碼證**: 平台 IC 為 Spearman：`momentum/Analysis/ic_config_schema.py:78-80`（`methods: list[str] = ["spearman"]`）；平台 IC 為單標的縱向：`docs/IC_QUANT_GAP_REGISTRY.md` 與 memory「1c-FR-FULL P1 canonical」（單 symbol 無橫截面）；投影用秩：與 stage4 Spearman 一致（`ic_filter_orchestrator.py:2906-2916` 用 `global_settings.default_method`）。文獻：Grinold & Kahn, *Active Portfolio Management* 2e, ch.10（IC 加法性／正交因子）；Qian, Hua & Sorensen, *Quantitative Equity Portfolio Management* ch.4（multi-factor IC、factor orthogonalization）。

**來源摘要**: `momentum/Analysis/ic_config_schema.py#69807b668584`；`momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c`

陷阱與處置：①秩空間投影是線性投影套在秩上，非「秩的非線性投影」——接受此近似並在契約標 `projection_space=rank`；②S 順序依賴：報告**兩個視角**——`loo`（S＝倖存者集合去掉自己；order-free，回答「這因子有多少獨一無二的資訊」）與 `sequential`（依 train ICIR 遞減之 Gram-Schmidt 順序；回答「逐個加入還剩多少新資訊」）；③近共線：`lstsq(rcond)`＋回報 `condition_number`，residual 變異 ≤ 閾值 ⇒ `not_computed:residual_degenerate`。信心度 High（定義）／Medium（秩空間投影之選擇，交 reconcile）。

## CLAUDE-R1-P0-03

**斷言**: OOS 紀律可用現有 `split_context`（`train_mask`／`test_mask`）＋`pit_stats.pit_train_fit`（mask 內 fit → 全段 transform）達成，不需新增切分機制；`fit_mode=full_sample` fallback 下輸出必須標 `oos_guarantees=False`＋`pass_class=full_sample_research_only`；無 holdout（`ic_train_test_split=False`）時邊際 IC 應為 `not_applicable:no_holdout_split`，**不得**靜默退化為 full-sample 擬合。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:920-928`（`split_context` 含 `train_mask/test_mask/train_plan/test_plan/effective_horizon`）、`:1097-1101`（fallback 強制 `fit_mode="full_sample"`＋`ic_train_test_split=False`）、`:2616-2618`（split off ⇒ `pit_expanding`）；`momentum/Analysis/pit_stats.py:551-576`（`pit_train_fit(df, fit_mask, transform_fn)`「統計參數只得來自 fit_df」）；rolling warm-up 守衛 `:2917-2934` 只在 stage4 rolling 觸發，新 stage 不用 rolling 故不新增 fallback 觸發面。

**來源摘要**: `momentum/Analysis/pit_stats.py#b9bc1a10da59`；`momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c`

補充：新 stage 需自己的樣本下限（例 `n_test ≥ max(30, 5·|S|)`），不足 ⇒ `not_computed:insufficient_test_rows`；cross-sectional 路徑 ⇒ `not_applicable:cross_sectional_mode`（既有 reason 枚舉可複用）。信心度 High。

## CLAUDE-R1-P1-04

**斷言**: 多因子組合於單標的縱向 IC 語意下，只有「訊號合成」有意義（無橫截面持倉權重）：composite_t = Σ w_i · s_i · z_i(t)，s_i＝train 段 IC 符號、z_i＝mask 內秩→z（或 z-score）、w∈{等權, |train ICIR| 加權}；`composite_ic`＝Spearman(composite_test, y_test)。OLS／Ridge 權重屬 ML 層邊界之外（成熟度地圖）。`composite_ic` 對 `best_single_ic` 的增量須附 block bootstrap CI（IC 序列自相關）。

**碼證**: 單標的縱向：`ic_filter_orchestrator.py:2240-2243`（factor_exposure 之 `equal_time_weights` 明註「時間軸等權，非交易持倉」）；F-IC-4／F-IC-8：`docs/TEST_DESIGN_CHARTER.md:100`；成熟度地圖：memory `project_platform_maturity_map`（ML／回測不完整層）。

**來源摘要**: `docs/TEST_DESIGN_CHARTER.md#e9be08bb5d5f`；`momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c`

oracle：①單因子集合 ⇒ composite_ic ＝ 該因子 IC（`atol=1e-12`）；②兩正交因子等 IC ⇒ composite_ic ≈ √2·單因子 IC（Pearson 情形精確；Spearman 容差）；③label 置亂 ⇒ |composite_ic| < 2/√n。信心度 High。

## CLAUDE-R1-P1-05

**斷言**: 落點應為 `analyze()` 之 **stage 6b**（吃 stage6 `filtered_df` 為 S、`passed_features∖S` 為「被冗餘移除者」次要候選），結果寫入報告新節 `marginal_ic`（`report_sections` 新增；`status/reason` 物件契約同五節），**非** deep-analysis 模組——因 2b 倖存者契約在 stage7 `_persist_outputs` 產出，須能同時攜帶邊際 IC 快照；deep 模組為 opt-in、cache-hit 路徑無 series owner，會使契約缺欄。

**碼證**: `ic_filter_orchestrator.py:1039-1063`（stage6→stage7 順序）、`:3789-3852`（`_persist_outputs`）、`:1854`（cache hit 無 owner ⇒ net_ic unavailable 之先例）；`ic_report_contract.json:27-43`（`report_sections` 五節＋net_ic 之 `status_object_keys`）；`scripts/ic_wiring_check.py:29-35`（R3 五節鍵禁裸空 dict）；`tests/momentum/Analysis/test_ichc_contract_sync.py:43-62`（report_sections 鍵須在 orchestrator 組裝面出現）。

**來源摘要**: `momentum/Analysis/contracts/ic_report_contract.json#6937da262f34`；`scripts/ic_wiring_check.py#bdf0f75f427b`

影響面：`refilter`（:1691）與 `analyze_full`（:1770）重跑 stage5-7 ⇒ 6b 須在兩處同步；`analyze_cross_sectional` ⇒ `not_applicable`。`REPORT_SECTIONS` 常數（wiring check）與契約 `report_sections` 目前不同步（五 vs 六），新節加入時應以契約檔為唯一來源。信心度 Medium（deep 模組 vs 主 stage 交 reconcile）。

## CLAUDE-R1-P1-06

**斷言**: 2b 倖存者輸出契約應為**新 JSON SoT** `momentum/Analysis/contracts/survivor_output_contract.json`＋獨立輸出檔 `data_cache/reports/ic_survivors_{case_id}.json`；欄位集合（只在契約檔列舉一次）最小需：`schema_version`、`generated_at`、`symbol`、`timeframe`、`label`（horizon／return_type）、`sample_scope`（結構：`kind∈{full,event}`＋`event_definition_hash`＋`n_samples`＋`row_mask_source`）、`split`（`split_method`＋`train/test time_bounds`＋`base_universe_hash`＋`selection_scope_id`）、`provenance`（`config_hash`、`features_source_hash`、`pit_stats_version`、`fit_mode`、`report_ref`）、`analysis_status`／`pass_class`／`oos_guarantees`、`survivors[]`（`feature_name`＋IC 快照＋`marginal_ic_loo`＋`redundancy_kept`）、`composite`（method／`composite_ic`／`best_single_ic`）。`sample_scope.kind` 應與 `RowMaskPlan.source` 對齊（已有 `event` 成員），非另造枚舉。

**碼證**: `momentum/core/contracts.py:682-700`（`RowMaskPlan.source ∈ {split,event,feature_filter,full}`）、`:726-748`（`SelectionScope`）、`:324-338`（`ICArtifactSchema` 10 欄）、`:340-348`（`FilteredFeatureSet`）；`ic_filter_orchestrator.py:3690-3747`（現 metadata 無 provenance／config_hash 獨立欄）、`:3831-3843`（`filtered_features_path` 於空結果被 pop）；`_stage3_event_filter` `:2715-2790`（事件 fallback 時 `info["fallback"]=True`）；ML 消費面 `api/services/xgboost_batch_service.py:221-243`（`selected_features: Optional[List[str]]`）。GAP-1 provenance 先例 `momentum/Analysis/strategy_validation/report.py:47-56,118-119`。

**來源摘要**: `momentum/core/contracts.py#8a1415d6ea01`；`api/services/xgboost_batch_service.py#0d11f275806e`；`momentum/Analysis/strategy_validation/report.py#4f3bb6c386cb`

要點：①事件型倖存者 `sample_scope.kind=event` ⇒ 消費端只能在事件樣本訓練（契約 `_doc` 明寫，resolver fail-closed）；②事件 fallback（`insufficient_events`）⇒ `sample_scope.kind=full` 且 `degraded=true`（禁把 fallback 全量誤標事件）；③`capability_status` 以 ref 複用 `ic_report_contract.json#capability_status`（GAP-1 Task 2.1 resolver 模式）；④本票**不寫**消費端，僅附 conformance test（讀檔→驗欄位→fail-closed）。信心度 High（欄位集合開放三家補漏）。

## CLAUDE-R1-P1-07

**斷言**: 測試策略須含四類可證偽 oracle（皆用合成**因子／label 序列**，非合成價格；符合章程 §F 註）：(i) `f ∈ span(S)` ⇒ `|marginal_ic| < 1e-8`（秩空間下改為「f 為 S 單元素之嚴格單調函數 ⇒ marginal_ic≈0（atol 1e-6）」）；(ii) `f ⟂ S` 且 `corr(f,y)=ρ` ⇒ `marginal_ic ≈ gross_ic`（atol 依 n）；(iii) label 置亂 ⇒ `|marginal_ic| < 2/√n_test`（MR-L1）；(iv) `f×c`（c>0）／單調變換 ⇒ 秩不變（`atol=1e-12`）；加 train-tail 刪除不改 test 側 β̂ 以外之值（MR-L2 變體：test 值只經 β̂ 影響）；契約 round-trip＋tamper fail-closed；mutation：改壞投影（用 test 段擬合 β）須被「train-tail 刪除改變 β̂ 但 test 端資料不變」之測試抓到。

**碼證**: `docs/TEST_DESIGN_CHARTER.md:23-27`（MR-L1/L2/L3）、`:50-59`（B1 mutation、B4 追溯矩陣、B6 統計預註）、`:100-105`（F-IC-1..9、F-MC-1..3、合成 IC 序列非合成價格）；mutation 慣例 `scripts/mutation_probe_check.sh:12-18`、`scripts/gap1_b1_mutation_probe.sh:7-25`（備份還原、rc==1 非 2、mutex）。

**來源摘要**: `docs/TEST_DESIGN_CHARTER.md#e9be08bb5d5f`

信心度 High。

## CLAUDE-R1-P2-08

**斷言**: 分批建議＝B1 邊際 IC 純函式＋oracle（獨立可用、零接線）；B2 組合 IC 純函式＋bootstrap CI；B3 契約 JSON＋resolver＋conformance test（2b 交付物）；B4 orchestrator stage 6b 接線＋報告節＋持久化＋wiring／contract-sync 綠＋前端 types 鏡像最小集合。B1／B3 各自單獨上線即有價值（B1 回答產品問題；B3 讓 ML 層將來有可讀契約）。

**碼證**: GAP-1 四批切法先例 `docs/GAP1_STRATEGY_OVERFIT_TODO.md:48`（§B 批次表）；接線面在 `ic_filter_orchestrator.py`（4098 行、三入口 analyze/refilter/analyze_full）為最大風險故置最後。

**來源摘要**: `momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c`

信心度 Medium。

## CLAUDE-R1-P2-09

**斷言**: 前端不需新圖表；但 `report_sections` 新節必須（a）在 orchestrator 組裝面出現（contract-sync 測試）、（b）`types.ts` ICHC 契約段之 `CapabilityStatus` 不變即可（新節不加枚舉值）、（c）若前端 report 型別列舉節鍵則須加 optional 欄避免幽靈；wiring check `REPORT_SECTIONS` 常數需納入新節（否則 R3 禁裸空不覆蓋新節＝守衛漏洞）。

**碼證**: `scripts/ic_wiring_check.py:29-35`；`tests/momentum/Analysis/test_ichc_contract_sync.py:35-62`；`frontend/src/lib/types.ts:2036-2059`。

**來源摘要**: `scripts/ic_wiring_check.py#bdf0f75f427b`

信心度 High。

## 必答逐條 verdict

1. **定義**：residual IC（train-fit β̂、test-apply、秩空間投影、Spearman 對 label），雙視角 `loo`＋`sequential`；加法性 oracle。非 Δcomposite（那是 B2 的驗證量），非 label 殘差化偏相關（回答的是相對量）。→ P0-02。
2. **OOS**：`split_context` masks＋`pit_train_fit`；fallback ⇒ `oos_guarantees=False`；無 holdout ⇒ `not_applicable`；不踩 rolling 守衛；新型別勿沿用 `FactorModuleResult`。→ P0-01／P0-03。
3. **組合**：訊號合成（等權／|ICIR| 加權、train 符號對齊）；`composite_ic` vs `best_single_ic`＋block bootstrap CI。→ P1-04。
4. **落點**：stage 6b（主流程）、報告新節、`refilter`／`analyze_full` 同步、xsec `not_applicable`。→ P1-05。
5. **契約**：新 JSON SoT＋獨立輸出檔；`sample_scope` 為結構且 `kind` 對齊 `RowMaskPlan.source`；provenance 最小集合；conformance test；不寫消費端。→ P1-06。
6. **測試**：四類 oracle＋契約 round-trip／tamper＋mutation 針對「β 用 test 擬合」。→ P1-07。
7. **scope**：B1–B4；B1／B3 單獨即有價值。→ P2-08。
8. **可進 SPEC**：是；無 BLOCKING。

## 交 reconcile 之技術取捨（主委立場＋為何）
- T1 秩空間 vs 原值空間投影：主委傾向**秩空間**（與 Spearman 一致、抗離群）；若三家碼證原值空間更標準且 oracle 更乾淨，可改。
- T2 落點主流程 stage 6b vs deep 模組：主委傾向**主流程**（2b 契約需要）；反方＝主流程改動面大。
- T3 無 holdout 時 `not_applicable` vs PIT expanding 擬合：主委傾向 **not_applicable**（誠實、零新機制）；expanding 版列 needs-research 殘留候選。

## 未查（具名，不當阻塞）
- `analyze_cross_sectional`（:1215-1550）內部細節未逐行讀；只確認其為獨立路徑。
- `api/services/ic_analysis_service.py` 是否重塑 `summary_table` 未查（影響 2b 契約是否需經 service 層轉出）。
- `tests/phase25/` 是否仍被 pytest 收集未查。
