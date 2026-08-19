# GAP-3 consult R2 — 主委版（CLAUDE；roster 外，供 reconcile 對照）

> brief：`handoffs/20260819-gap3-consult-r2-BRIEF.md`｜審查標的：`白話說明/GAP-3事件型討論.md`（第 6 版，#685405d0daf9）｜read-only。
> 主委版與三家平行產出；不進 completeness roster。

## Verdict：可進 SPEC 起草（使用者 U1–U11 已定；K1–K10 有提案；無 BLOCKING）。最大風險＝J1 case-control 之「全樣本驗證」若被省略，整票結論不可信（列 P0 風險，非反對）。

## CLAUDE-R2-P0-01

**斷言**: A／B 情境（t₀ open 決策、依 t₀ 結果挑樣本）之學習樣本為 outcome-selected（case-control），其內之 AUC／勝率／基率**不可**外推為部署時（每根 bar open）之精確率；若 SPEC 未把「全樣本驗證」（對驗證期每根 bar 之 open 打分）列為必備產出，GAP-3 之「pattern 有效」結論不可證偽。

**碼證**: 現雛形 `/search` 以 t₀ 那根 `price_change`（`case_search_engine.py:1228-1233`：`OPEN_TO_CLOSE=(close-open)/open` 或 `close.pct_change()`）與未來欄（`:336,651-658` `future_*_max_drawdown`）挑樣本；`xgboost_batch_service.py:655` label＝`positive_case`；**無任何路徑**在非案例 bar 上評估模型（`grep -n "all_bars\|full_universe\|every bar" api/services/xgboost_batch_service.py` → 0，Claude 實跑）。文獻：Rothman & Greenland, *Modern Epidemiology*, ch.8（case-control 只識別 odds ratio，不識別絕對風險）；AFML ch.3（事件抽樣後須於全序列上回測）。

**來源摘要**: momentum/DataExtraction/case_search_engine.py#98d2ede5f5f5；api/services/xgboost_batch_service.py#0d11f275806e

處置：K8 最小集合（見下）列為 B1／B2 必備產出；報告強制欄 `sample_design=case_control`＋`train_base_rate` vs `universe_base_rate` 並列。信心度 High。

## CLAUDE-R2-P1-02

**斷言**: A／B 之 label 起算價應為 **決策對應之進場價（t₀ open）**，而 IC 主線 label 為 close-to-close 前瞻報酬（`return_N` 由 `_resolve_label_horizon_from_column` 解析，起算＝該列 close）；直接把「t₀ 前一根 1h close」當作事件列餵 IC 主線，其 label 起算＝前一根 close ≈ t₀ open（同一時點、不同價），**可接受但須在契約標明 `label_ref_price=prev_close≈open`**，且 12h t₀ 之 horizon 以 1h 根數表達時須保證 1h 序列無缺根（否則 h 根 ≠ h 小時）。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:255-290`（horizon 由 labels 欄名解析、以 bars 計）、`:330-348`（rows purge 要求連續時間軸 `expected_freq`；缺根 ⇒ raise）；`pit_stats.py`（current-inclusive）。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#fa7b795aaea8；momentum/Analysis/pit_stats.py#b9bc1a10da59

處置：K2 對齊收據須含 `decision_ts`／`feature_row_ts`／`entry_price_semantic`；對 1h 序列缺根事件列入失敗清單 `reason=gap_in_feature_tf`。信心度 High。

## CLAUDE-R2-P1-03

**斷言**: 完整版事件產生器（G1–G6）之條件引擎應落在 `momentum/` 純函式（輸入＝Feature Factory 特徵表＋K 線結果欄，輸出＝合規事件列），API 只包殼；可直接擴充 `momentum/Analysis/event_filter.py` 之 `df.eval` 安全子集（`validate_query` 白名單）為條件語法，**但須把欄位分為 `feature_cols`（受 PIT 守衛：只准 ≤ 決策時點）與 `outcome_cols`（允許未來；用於依結果挑樣本與 label）兩類**，引擎拒絕在 feature 條件中引用 outcome 欄以外的未來資訊。

**碼證**: `event_filter.py:55-105`（query／timestamps 兩模式；`validate_query` :107-126 白名單＋blocklist）；現雛形 `FilterConditionRequest.validate_parameter_for_filtering` 只准 `price_change`（`api/models/requests.py:50`）；`case_search_engine._add_calculated_columns` 產 `price_change/closing_strength/recent_high/low/price_position` 與 `future_*`（`:1228-1260,651-658`）。

**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c；api/models/requests.py#938ff6900fed；momentum/DataExtraction/case_search_engine.py#98d2ede5f5f5

處置：K9；`SearchConfiguration`（`case_search_engine.py:126-245`）升級為新契約之 `rule_snapshot`（U7 不翻掉：沿用其 `to_dict/from_dict` 作規則摘要序列化）。信心度 Medium-High。

## CLAUDE-R2-P2-04

**斷言**: 變化類特徵缺口具名：`RollingAggregator` 現有 `slope/std/mean/rank/zscore/min/max`（窗內統計），**缺** 窗內 `argmax/argmin` 位置（幾根前達極值）、`bars_since(condition)`（距上次交叉／突破幾根）、`streak`（連續 N 根同號）、`count(condition in window)`；這四類是使用者 S3.4「訊號在窗內任何位置」需求的直接載體。

**碼證**: `momentum/FeatureEngineering/operators/rolling_aggregator.py:45-80`（aggregator 表）；grep `argmax|bars_since|streak` in `momentum/FeatureEngineering/` → 0（Claude 實跑）。

**來源摘要**: momentum/FeatureEngineering/operators/rolling_aggregator.py#249714e91213

處置：K7；新增 operator 須過 Feature Factory 既有因果／golden 紀律（三方簽核鐵律）。信心度 High。

---

## A. 逐項對應表

| ID | 表態 | 一句理由 | 建議 | 證據 |
|---|---|---|---|---|
| U2-1 | 技術可行 | /search→CSV→/data-preparation 流程存在；欄位與對齊須升級 | 升級不翻掉（U7） | requests.py:50；case_import_service.py:36 |
| U2-2 | 技術可行（有風險） | open 決策 PIT 可行；風險＝樣本選取靠未來（P0-01） | 全樣本驗證必備 | P0-01 |
| U2-3 | 技術可行 | 12h open 對 1h/4h 邊界整齊；須 1h 無缺根 | K2 失敗清單 | P1-02 |
| U2-4 | 技術可行 | 三種反例混 0 可；按種類分報 | `negative_kind` 欄 | S3.5 |
| U2-5 | 技術可行 | 事件後報酬表＝單類、多 horizon 描述統計 | K5-(i) | — |
| U2-6 | 技術可行 | 一兩萬列表格式 ML 夠；pooled 必要 | K4 | S3.8 |
| U2-7 | — | 三題皆有處置（S3.6／3.7／3.4） | — | — |
| U2-8 | — | 本輪即是 | — | — |
| S3.1 | 同意 | case-control 合法＋全樣本驗證必備 | 列 P0 風險、強制產出 | P0-01 |
| S3.2 | 同意 | 三情境＝契約主維度 | `decision_time_rule`＋`event_known_at_decision` 兩欄 | — |
| S3.3 | 同意 | 皆為標準守衛 | — | — |
| S3.4 | 同意 | 取 t₀ 列＋窗內摘要；缺四類 operator | K7 | P2-04 |
| S3.5 | 同意 | GBDT 易學易分者；IC 受抽樣 | 按 `negative_kind` 分報；兩段式各一份 | — |
| S3.6 | 同意 | 時間出場第一版；triple-barrier 殘留 | — | — |
| S3.7 | 部分同意 | 方向對；預設見 K3（A/B 不建議「全留」為唯一預設，改「全留＋唯一性權重」且並報簇首） | K3 | — |
| S3.8 | 同意 | pooled 必要；同時刻簇 | K4 最小版 | — |
| S3.9 | 同意 | API 已收 event_timestamps；前端無入口 | 對齊層換算＋一個入口 | ic_models.py:150；icAnalysisStore.ts:78 |
| S3.10 | 同意 | IC 篩、ML 組合、全樣本驗 ML | — | — |
| S3.11 | 同意 | 同頁事件模式最省殼 | — | U10 |
| T1–T3 | 同意 | 產生器第一版可產 | K9 | — |
| T4／T6 | 同意 | 登記待資料源 | 契約 `source` 欄留位 | — |
| T5／T7 | 同意 | 匯入即可 | — | — |
| T8 | 同意 | 契約加 `ref_symbol`（選填）；分析另排 | K1 | — |
| T9 | 同意 | meta-labeling＝C 情境；契約加 `source_model_id`＋`signal_value` | K1；接 GAP-1 ledger | — |
| T10 | 同意 | `event_shape∈{instant,interval}`＋`interval_end` | K1 | — |
| P0–P10 | 同意 | 流程完整；P4 特徵步驟須標「於 ② 段內連續算、取決策列」 | — | — |
| G1–G6 | 同意 | 可由 /search 升級＋event_filter 引擎 | 欄位分 feature/outcome 兩類（P1-03） | P1-03 |
| J1 | 同意（強化） | 全樣本驗證＝硬 | P0-01 | — |
| J2 | 同意 | — | — | — |
| J3 | 同意 | — | K7 補 operator | — |
| J4 | 同意 | — | — | — |
| J5 | 同意 | — | — | — |
| J6 | 同意 | 最小版＝per-symbol 切＋pooled 統計＋時間簇 | K4 | — |
| J7 | 同意 | — | — | — |
| J8 | 同意 | — | — | — |
| J9 | 同意 | — | — | — |
| J10 | 同意 | 引擎落 momentum/ 純函式 | P1-03 | — |

## B. K1–K10 提案

**K1 匯入契約欄位**（SoT＝`momentum/Analysis/contracts/event_import_contract.json`）
必填：`event_id`、`symbol`、`event_timeframe`（t₀ 所在 TF）、`t0`（epoch ms UTC，open_time；單位閘：值 <1e11 視為秒⇒拒）、`direction∈{long,short}`、`decision_time_rule∈{t0_open,trigger_bar_close,next_bar_open}`、`event_known_at_decision∈{false,true}`（A/B=false、C=true；validator：`t0_open` ⇒ 必 false）、`label∈{0,1}`、`label_value`（float；進場價→答案窗末之報酬；U2）、`label_window`（`{start_rule∈{entry}, horizons_bars:[...], agg∈{all,any,majority,value}, threshold}`）、`label_ref_price∈{t0_open,t0_close,next_open}`、`negative_kind`（label=0 必填；自由字串＋建議枚舉 `same_trigger_no_follow|range_bound|down_move|other`）、`control_kind∈{user_labeled_same_trigger,user_labeled_mixed,platform_universe}`、`rule_snapshot`（/search `SearchConfiguration.to_dict()` 原樣）＋`rule_digest`、`source_file_digest`。選填：`event_type_tag`、`ref_symbol`（T8）、`source_model_id`／`signal_value`（T9）、`event_shape`／`interval_end_ms`（T10）、`feature_timeframes:[...]`、`meta`。
收據（對齊後產，非輸入）：`observed_through_ms`、`decision_ts_ms`、`feature_cutoff_ms{per tf}`、`entry_ts_ms`、`label_start_ms`、`label_end_ms`、`matched_feature_rows{tf: open_time}`、`drop_reason`。

**K2 對齊**：純函式 `align_events(events, features_by_tf, rules)`；`t0_open` ⇒ `decision_ts=t0`，`feature_cutoff(tf)=最後一根 open_time+tf ≤ decision_ts 之列`；`trigger_bar_close` ⇒ `decision_ts=t0+event_tf`；`next_bar_open` ⇒ `=t0+event_tf`（進場）且 feature_cutoff 同 close。失敗枚舉：`missing_feature_tf`、`gap_in_feature_tf`、`label_window_incomplete`、`nan_in_features`、`unit_mismatch`；全部進 `n_dropped_by_reason`，禁靜默。

**K3 連續觸發**：C ⇒ 預設 `first_in_cluster`，G＝答案窗 bars（可調），並報 `all_with_uniqueness`；A/B ⇒ 預設 `all_with_uniqueness`（AFML ch.4 平均唯一性＝每事件 1/重疊事件數 之窗內平均），並報 `first_in_cluster`；報告 `n_raw/n_effective/overlap_fraction`；「兩種都跑」保留為 B2 之敏感度檢定（結論翻盤 ⇒ 降級 `unstable_under_dedupe`）。

**K4 切分與 pooled**：per-symbol 時間切（沿 `_build_holdout_split_plan`：purge=max(purge_gap, horizon)＋embargo）；pooled 統計＝各 symbol 事件列合併後計算，但 (i) 同時刻（同 1h bucket）跨 symbol 事件歸同一 `time_cluster_id`，bootstrap／唯一性以 cluster 為單位；(ii) 報告 per-symbol 與 pooled 並列；(iii) registry #4 之完整 panel IC（固定效應等）不在本票。

**K5 三表**：(i) 事件後報酬表：horizons 可配（預設 event_tf×{1,2,4,8}＋使用者答案窗）；每格 n／mean／median／win_rate／IQR／block-bootstrap CI；單類、不需反例；按 `direction` 分。(ii) 辨別表：逐特徵 AUC＋Mann-Whitney p＋BH-FDR；PR-AUC 於不平衡；按 `negative_kind` 分組各一份＋合併；兩段式＝(b,c) vs 正例、(a) vs 正例。(iii) 條件 IC：stage3 timestamps 模式（事件列＝對齊後 `feature_row_ts`）＋stage4/5；label＝`label_value`（連續）；`sample_scope.kind=event`；A′ 保留。三表皆走 `capability_status`（`ok|unavailable|degraded`）＋reason 枚舉。

**K6 防運氣**：B1 必備＝(a) label 置亂 ⇒ 辨別表 AUC 之 95% CI 含 0.5、條件 IC≈0（固定 seed、≥200 次置亂）；(b) PIT 後移探針：把 `feature_cutoff` 人為 +1 bar ⇒ validator 必 raise；(c) 缺反例 ⇒ fail-closed。B3＝規則抽取候選入 GAP-1 ledger、return series→PBO/DSR。

**K7 變化類特徵**：新增 `RollingAggregator` 聚合：`argmax_pos`、`argmin_pos`（窗內極值距今幾根）、`streak`（連續同號長度）、`count_above(threshold)`；新增 operator `bars_since(event_col)`（事件列＝布林特徵，如 `ma_cross_up`）。共用函式清單：`event_filter.apply_filter`（遮罩）、`_build_holdout_split_plan`／`SplitPlan`／`validate_split_integrity`（切分）、`ic_engine.compute_ic`＋stage5 FDR（條件 IC）、`pit_stats`（PIT 原語）、`survivor_contract`（輸出）。

**K8 全樣本驗證輸出（第一版就建完整，但不碰回測層）**：驗證期每根 bar 之 open（A/B）或 close（C）打分 ⇒ 產出：(1) 精確率／召回／F1／PR 曲線＋AUC（全樣本基率下）；(2) lift（模型 top-k% 之正例率 ÷ 基率）；(3) 訊號頻率（每月幾次、每 symbol 幾次）；(4) 簡單持有報酬：entry_price→label_end close，等權、不計手續費／倉位／複利，報 mean／median／win_rate／分布＋block bootstrap CI；(5) 按 symbol、按年份／季之穩定性表；(6) 訓練樣本基率 vs 全樣本基率並列＋`sample_design=case_control` 揭露；(7) 與序列型「全部 K 線」IC 報告並排連結。**不做**：倉位、手續費、資金曲線、複利、滑價模型（回測層）。

**K9 事件產生器**：`momentum/Analysis/event_generation/`（純函式）：`generate_events(features_by_tf, klines, rule: RuleSpec) → events`；`RuleSpec`＝`{trigger_conditions（feature_cols ≤ 決策時點 ∪ outcome_cols）, label_spec, negative_specs[{kind, conditions}], direction, decision_time_rule, dedupe, sampling}`；條件語法沿 `event_filter.validate_query` 白名單 `df.eval`；欄位分類由引擎標記（outcome 欄名前綴 `fwd_`／`t0_`），feature 條件引用 outcome 欄 ⇒ 拒絕；去重在產生期；輸出合規事件檔＋`rule_snapshot`。`/search` 之 `SearchConfiguration`／`_add_calculated_columns` 升級為 RuleSpec 之 adapter（U7）。T1–T3／T10 由 RuleSpec 表達；T5／T7 匯入；T8 `ref_symbol` 條件第二版；T9 來源＝IC 主線 survivors 訊號，走同契約。

**K10 分批**：B1 契約＋對齊＋去重／簇＋切分＋失敗清單＋K6(a)(b)(c) oracle＋單特徵辨別 baseline；B2 三表＋`sample_scope.event` 擴欄升版＋IC 頁事件模式入口；B3 全樣本驗證（K8）＋變化類 operator（K7）；B4 事件產生器完整版（K9；/search 升級）；B5 規則抽取＋DSR/PBO 接點＋持久化＋前端占位殼。B1 單獨價值＝「外部標註被無洩漏地組成資料集」；B2＝回答「有無 pattern」；B3＝回答「實盤會怎樣」。

## 未查
- `two_stage_search`／`case_search` 路由欄位對照全表；Feature Factory 多 TF merge-asof 既有工具；萬級事件 bootstrap 牆鐘。
