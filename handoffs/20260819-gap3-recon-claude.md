# GAP-3 偵察 R1 — 主委版（CLAUDE；roster 外，供 reconcile 對照）

> brief：`handoffs/20260819-gap3-recon-BRIEF.md`｜日期 2026-08-19｜read-only 偵察，禁改碼。
> 主委版與三家（codex／composer／grok）平行產出；本檔不進 completeness roster，只作對照與白話整理／SPEC 起草輸入。

## Verdict：可進 SPEC 起草（無 BLOCKING），前提＝使用者先裁三題產品語意（Q1 進場點、Q2 反例來源、Q4 標籤規則歸屬）；其餘為技術題由 reconcile 定案。現雛形（case 路由→`xgboost_batch_service`）**不改殼、不沿用其對齊邏輯**；新線＝契約＋純函式核心。

## CLAUDE-R1-P0-01

**斷言**: 現雛形的案例→特徵對齊在三處違反 IC 主線標準，不得作為 GAP-3 基底：(a) `timestamp_sec == case_ts` 精確相等匹配，無 TF 邊界正規化、無 as-of；(b) 找不到 bar／特徵含 NaN 皆 `warning` 後**靜默跳過**（樣本組成無聲改變，report 無揭露）；(c) 特徵取 t₀ **同根** bar 列，而契約無「決策時點」欄 ⇒ t₀ 語意（open／close）由呼叫端默契決定。

**碼證**: `api/services/xgboost_batch_service.py:618`（`idx = features_df[features_df['timestamp_sec'] == case_ts].index`）、`:621`（`找不到對應的 K 線數據` → `continue`）、`:651`（`特徵包含 NaN，跳過` → `continue`）、`:641`（`features_df.loc[row_idx, shared_feature_names]`）；`api/models/case_models.py:16-26`（`CaseRecord` 欄位無 decision_time／horizon／label_rule）。

**來源摘要**: api/services/xgboost_batch_service.py#0d11f275806e；api/models/case_models.py#61f72fca0397

影響：同一份匯入檔在不同 kline 快取狀態下得到不同樣本集而不自知；與 IC 主線「loud fallback＋契約 reason」原則（ICHC R5 A′、`capability_status`）不一致。修法＝新 `event_import` 契約＋`align_events` 純函式：每事件回傳對齊 receipt（`matched_bar_open_time`／`drop_reason∈枚舉`），被剔除者計入報告 `n_dropped_by_reason`，禁靜默。信心度 High。

## CLAUDE-R1-P0-02

**斷言**: PIT 正確時間軸（以使用者原例為準）＝①觸發**觀測**時點＝觸發根 **close**（漲≥5% 只有收盤才成立）②**決策時點**＝觸發根 close（或下一根 open，若要含成交延遲）③特徵截止＝決策時點當時**已收盤**之最後一根 1h／4h 子 bar（含觸發根內的子 bar——這是合法且有資訊的）④label 起算價＝決策價（t₀ close 或 next open）⑤label 終點＝決策時點＋24／36／48h 之 close。把 t₀ 定義為「該根 open」只是**時間戳命名慣例**（kline `open_time`），不是決策時點；若契約不顯式區分，兩種錯各一半：特徵用到觸發根 close 卻宣稱決策在 open ⇒ look-ahead；label 從 open 價起算 ⇒ 把觸發根 +5% 算進績效。

**碼證**: 平台 kline 時間戳＝open_time 慣例：`api/services/xgboost_batch_service.py:574-590`（`timestamp`／`open_time` 欄並列，`timestamp_sec` 由 `timestamp` 派生）；IC 主線 label horizon 以 bars 計且 purge≥horizon：`momentum/Analysis/ic_filter_orchestrator.py:255-290`（`_resolve_effective_label_horizon`）、`:365-372`（`purge_gap < effective_horizon` ⇒ raise）；`AlignmentSpec(lag=horizon)` `:228-232`。文獻：López de Prado, *AFML* ch.3（triple-barrier／t₁ 事件終點）、ch.4（sample uniqueness）。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#fa7b795aaea8；api/services/xgboost_batch_service.py#0d11f275806e

建議契約欄：`t0`（epoch ms UTC，**觸發根 open_time**，與 kline 對齊）、`decision_time_rule∈{trigger_bar_close, next_bar_open}`（v1 只准這兩值；`trigger_bar_open` **禁止**——觸發事實在 open 時不存在）、`label_horizon_bars`（以 t0 所屬 TF 計）或 `label_horizon_seconds`、`label_ref_price∈{decision_price}`（v1 單值）。對齊函式據此算出 `decision_ts` 與 `feature_cutoff_ts`，特徵列＝`features_df[ts ≤ feature_cutoff_ts].iloc[-1]`（per-TF）。現雛形 :641 在「決策＝close」語意下**不是** look-ahead，但因無欄位可證，報告不得宣稱 PIT。**[Q1 使用者裁的只有一句：你是在觸發根收盤確認後才進場（預設）還是下一根開盤；PIT 機制本身＝委員會定]**。信心度 High。

## CLAUDE-R1-P0-03

**斷言**: 反例必須與正例**同觸發母體**（same-trigger controls）：研究問題是「已觸發者中，誰續漲」，對照組若取未觸發任意 bar，模型／IC 學到的是「有沒有觸發」（廢答案；且 base rate 被人為稀釋、AUC 虛高）。使用者原例之標法（所有 ≥5% 的 t₀ 依 3% 續漲分正反）**本身就是 same-trigger**，故 v1 契約＝使用者**同時**提供正反例；平台不產反例。現雛形 `_select_negative_timestamps`（正例 ± separation_days 的未觸發點）屬廢答案設計，不沿用。

**碼證**: `api/services/search_task_service.py:788-820`（候選＝`pos_time ± separation_delta`，只檢查與其他正例距離，不檢查是否滿足觸發條件）；使用者原意見 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 開發前討論題」首段。文獻：case-control 設計中 control 須來自同一 source population（Rothman, *Modern Epidemiology* ch.8）；AFML ch.3 meta-labeling（先有 primary trigger，再學 side/size）。

**來源摘要**: api/services/search_task_service.py#c8357d2a7c12

建議契約：`control_kind∈{user_labeled_same_trigger, user_labeled_other, platform_random_bars}` 必填且進報告 `sample_scope.event.control_kind`；v1 平台只實作 `user_labeled_*`（匯入檔須**同時含 label=1 與 label=0**，否則 fail-closed `reason=missing_control_group`）；`platform_random_bars` 留枚舉位、v1 `not_implemented`（需觸發規則＝事件產生器，等 Q0 第二版）。**[Q2 使用者裁：反例你自己標（預設，符合原意）vs 要平台幫你產；後果＝委員會定]**。信心度 High。

## CLAUDE-R1-P1-04

**斷言**: 連續觸發（例：相鄰數根 12h 皆漲≥5%）各為合法事件但 label 窗重疊（48h＝4 根 12h）⇒ 樣本非獨立；正確處置不是丟事件，而是 (i) 保留全部事件＋計算每事件 **uniqueness 權重**（AFML ch.4 平均唯一性）供 IC／AUC 加權與 bootstrap 分塊；(ii) 切分＝per-symbol 時間切＋purge ≥ label_horizon＋embargo，複用 `SplitPlan`／rows purge 守衛；(iii) 去重策略作 config（`dedupe_policy∈{none_with_uniqueness, first_in_cluster, min_gap}`，預設 `none_with_uniqueness`），每種在報告揭露 `n_events_raw/n_events_effective`。

**碼證**: `momentum/core/contracts.py:362-388`（`SplitPlan` 含 `purge_gap/embargo/purge_semantic/symbol/base_universe_hash`）、`:390-400`（跨 symbol／不連續／pair 洩漏三例外）、`:506`（`validate_split_integrity`）；`momentum/Analysis/ic_filter_orchestrator.py:360-380`（`_build_holdout_split_plan`：`effective_purge=max(purge_gap, horizon)`＋embargo）；現 IC 主線 `RowMaskPlan.source∈{split,event,feature_filter,full}` `contracts.py:682`。文獻：AFML ch.4（uniqueness、sequential bootstrap）、ch.7（purged k-fold／embargo）。

**來源摘要**: momentum/core/contracts.py#8a1415d6ea01；momentum/Analysis/ic_filter_orchestrator.py#fa7b795aaea8

陷阱：事件樣本稀疏 ⇒ 單次 holdout 的 test 段事件數可能 < tier 下限（`check_sample_size` :128 `low_confidence=30`）⇒ 須 loud `insufficient_events_in_test` 而非 fallback 全樣本；per-symbol 切後再 pool 報告須標 `split_method=per_symbol_holdout`。**[Q3 委員會定；只向使用者說明「連續觸發都算、但會降權」]**。信心度 High（方向）／Medium（uniqueness 權重是否進 v1 vs 記殘留）。

## CLAUDE-R1-P1-05

**斷言**: 標籤規則（24∧36∧48 皆≥3% vs 任一 vs 連續值）是**使用者的外部標定**，平台 v1 只收 `label∈{0,1}`＋可選 `label_value`（連續）＋`label_rule_id`（字串＋sha256，平台不解讀），並在報告強制揭露 `label_provenance=external`、正反比例、`n_pos/n_neg`；**不**在 v1 內建 label 重算器（規則空間無界、重算＝另一個事件產生器）。但應提供**一致性探針**：若匯入檔附 `label_rule` 結構（v1 只支援 `price_return_threshold` 一族：ref∈{decision_price}、horizons[]、agg∈{all,any,majority}、threshold），平台重算並報 `label_mismatch_count`，不一致 ⇒ fail-closed（使用者標錯或 kline 版本不同）。

**碼證**: 現雛形 label 純吃 `positive_case`（`xgboost_batch_service.py:655`），無任何規則／provenance；survivor 契約 event object 只有 `mode/definition_hash/timestamps_hash`（`momentum/Analysis/contracts/ic_survivor_contract.json:260-275, 287-305`）。

**來源摘要**: momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073；api/services/xgboost_batch_service.py#0d11f275806e

後果說明（給使用者）：AND 三窗 ⇒ 正例少、不平衡（可能 <20%）、統計力低但「續漲」語意乾淨；OR ⇒ 正例多但雜；連續值（min 報酬）⇒ 可同時做 IC（不需二分）且資訊最多，建議匯入檔**同時**給二元 label 與連續 `label_value`。**[Q4 使用者裁：規則本身；平台是否重算＝委員會定（建議：不重算、只探針）]**。信心度 Medium-High。

## CLAUDE-R1-P1-06

**斷言**: 「共通 pattern 非運氣」的最小可證偽管線＝ (i) 事件子樣本**條件 IC**（特徵 vs 事件後連續報酬 `label_value`，複用 stage3 timestamps 模式＋stage4＋stage5 BH-FDR，`sample_scope.kind=event`）；(ii) 二元 label 之逐特徵 **AUC／Mann-Whitney**（等價 rank-biserial）＋BH-FDR＋per-symbol 時間切 OOS；(iii) 規則抽取沿用 `pattern_extractor.extract_decision_rules`（`SplitPlan` fail-closed 已在）＋規則候選數 N 入 GAP-1 DSR/PBO ledger（規則＝策略候選）；oracle：label 置亂 ⇒ AUC 95% CI 含 0.5 且 IC≈0；特徵截止人為後移一根 ⇒ PIT 守衛必 raise；事件數減半 ⇒ `tier` 降級可觀測。

**碼證**: stage3 timestamps 模式 `momentum/Analysis/event_filter.py:55-105`；stage4／5 `ic_filter_orchestrator.py:2963`／`:3059`；`pattern_extractor.py:77-110`（`split` 必填、`oot_split` 可選）；GAP-1 `momentum/Analysis/strategy_validation/`（DSR/PBO；ledger 見 `docs/GAP1_STRATEGY_OVERFIT_SPEC.md`）。

**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c；momentum/Analysis/pattern_extractor.py#4c088024827a

量級提醒：數千～數萬事件、特徵數百 ⇒ BH-FDR 必要；跨標的 pooled 屬 registry #4（不在本票）但 per-symbol 結果可並列報告。**[Q5 委員會定]**。信心度 High。

## CLAUDE-R1-P1-07

**斷言**: 事件類型可化約為統一匯入契約 `(symbol, timeframe, t0, label[, label_value], decision_time_rule, label_horizon, control_kind, label_rule_id[, label_rule], event_type_tag, source, meta)`；類型差異只在 **t₀ 由誰產生**與**對照組是否天然存在**：①價格／量行為觸發（使用者原例；對照＝同觸發未達標）②技術形態（同①，t₀ 由形態辨識器產）③波動／regime 切換（t₀ 稀疏、對照＝前一 regime）④衍生品微結構（需外部源：資金費率／OI／清算）⑤日曆／排程（t₀ 已知、無觸發不確定性；對照＝非事件日）⑥新聞（最像 event study；需外部源）⑦純人工標定。v1 支援＝①②⑦（皆可由使用者外部標好匯入）；④⑥ 登記待資料源；③⑤ 契約可容但不示範。平台 v1 **不做事件產生器**（使用者已自標）；第二版再做 ①類規則產生器供「平台產同觸發對照」。

**碼證**: 使用者裁決與原例：`docs/IC_QUANT_GAP_REGISTRY.md` #3 與「GAP-3 開發前討論題」Q0 列；外部源現況：`grep -rn "funding_rate\|open_interest" momentum api --include='*.py' | wc -l`（Claude 未跑，標 UNVERIFIED，交三家）。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#333ed10fd833

**[Q0 使用者裁：第一版要支援哪幾類（建議 ①②⑦）與示範哪一類（建議 ①＝原例）；分類完備性＝委員會定]**。信心度 Medium。

## CLAUDE-R1-P2-08

**斷言**: 共用／不共用面：**共用**＝kline 載入與特徵計算（Feature Factory）、stage3 timestamps 遮罩（`event_filter.apply_filter`）、stage4 IC／stage5 FDR、`SplitPlan`＋rows purge 守衛、bootstrap／tier、`capability_status` 枚舉與 survivor 契約；**新寫**＝`event_import_contract.json`＋validator、`align_events`（t₀→決策時點→特徵列 receipt）、`dedupe/uniqueness`、二元統計（AUC／rank-biserial＋FDR）、事件報告節（`event_analysis`）與 `sample_scope.event` 擴欄（`control_kind/decision_time_rule/label_horizon/label_rule_hash`）⇒ `ic_survivor_contract.json` `version` bump（additional_properties:false，不能靜默加鍵）。

**碼證**: `momentum/Analysis/survivor_contract.py:278-286, 407`（`sample_scope` 驗證與 kind 判定）；`ic_survivor_contract.json:3`（每層 `additional_properties:false`）。

**來源摘要**: momentum/Analysis/survivor_contract.py#736d8a8cf2a5；momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073

**[Q6 委員會定]**。信心度 High。

## CLAUDE-R1-P2-09

**斷言**: 分批建議（每批單獨上線即有價值）：**B1** 匯入契約＋`align_events`＋dedupe/uniqueness 純函式＋對齊 receipt＋oracle（PIT 後移必 raise／缺反例 fail-closed／靜默跳過歸零）；**B2** 事件樣本統計＝條件 IC（stage3/4/5 複用）＋二元 AUC/FDR＋報告節＋`sample_scope.event` 擴欄（契約 bump）；**B3** 切分＋規則抽取接 `SplitPlan`＋規則候選入 DSR/PBO；**B4** 持久化＋API 輸入面（新路由或 `case.py` 換 schema，**不動** `xgboost_batch_service` 殼）＋前端占位殼（`/pending-features` 條目）。現雛形處置＝**保留殼、棄用其對齊／反例邏輯、不遷移舊 cases.json**（面向未來不溯及既往）。

**碼證**: 成熟度地圖（memory 2026-08-17）；前端占位規則（commit aded5574）；`api/routes/case.py:34-70`。

**來源摘要**: api/models/case_models.py#61f72fca0397

**[Q7 委員會定；使用者只需知道「前端最後一批、UAT 等事件型完整」]**。信心度 Medium-High。

## CLAUDE-R1-P2-10

**斷言**: 無 BLOCKING。Kline 層「可能變更」之風險以契約隔離：匯入契約只綁 `(symbol, timeframe, epoch ms UTC open_time)`，不綁 HDF5 佈局；對齊函式吃 `features_df`（Feature Factory 輸出）而非 raw kline。事件樣本量風險（per-symbol 切後 test 段 < 30）＝loud reason 而非 BLOCKING。

**碼證**: `momentum/Analysis/event_filter.py:128-144`（tier 下限）；`docs/IC_QUANT_GAP_REGISTRY.md`「IC 主路徑切分現狀」節。

**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c

**[Q8 委員會定]**。

## 未查清單（不當阻塞）
- 外部源（資金費率／OI）現有程式面：未 grep（CLAUDE-R1-P1-07 標 UNVERIFIED）。
- `pattern_extractor` 之 `oot_split` 與 DSR/PBO ledger 實際接點：未讀 `strategy_validation/` 全文。
- Feature Factory 多 TF 對齊（1h／4h 子 bar 至 12h 決策時點）的既有 as-of 工具：未查 `momentum/FeatureEngineering/` 是否已有可複用之 merge-asof。

## 給白話整理的三題草稿（使用者裁）＋兩題資訊（使用者知）
- 使用者裁 Q1：進場點＝觸發根收盤確認後（預設）／下一根開盤。
- 使用者裁 Q2：反例自己標（同觸發未續漲；預設）／要平台幫產（v1 做不到，列第二版）。
- 使用者裁 Q4：標籤規則由你定（AND／OR／連續值），建議同時給連續值；平台不重算、只做一致性探針。
- 使用者裁 Q0：第一版支援 ①價量觸發②技術形態⑦人工標定；示範＝你的 12h 例。
- 使用者知 Q3／Q5：連續觸發都算但降權＋時間切分／防運氣＝FDR＋OOS＋DSR/PBO（技術，委員會定）。
