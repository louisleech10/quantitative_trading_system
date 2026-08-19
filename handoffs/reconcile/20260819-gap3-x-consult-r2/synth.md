# Reconcile — 20260819-gap3-x-consult-r2

**來源** 20260819-gap3-consult-r2-codex.md, 20260819-gap3-consult-r2-composer.md, 20260819-gap3-consult-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-20）

四方共 **26 條** findings（codex 10／composer 5／grok 7＝鎖定 22 條；claude 4 為非鎖來源 `handoffs/20260819-gap3-consult-r2-claude.md`），下列九個群集**引用全部 26 條，0 掉項**。
審查標的＝`白話說明/GAP-3事件型討論.md` v6（#685405d0daf9；使用者意圖 U1–U11 已定版）。三家皆提交「逐項對應表」（U2-x／S3.x／T／P／G／J 全覆蓋）與 K1–K10 提案；**無一家判 U 系列技術不可行**。
獨立性註記：codex（22:15 前後）提交最晚且最長（10 條、3 P0）；composer 本輪成功交件（前兩次 Cursor resource_exhausted）；三家在 C1（label 價格語意）、C2（per-TF cutoff）、C3（欄位角色）、C4（全樣本分母／基率）四項**彼此獨立**得到同一結論（措辭與碼證來源不同：codex 引 `case_search_engine:1229-1297`、grok 引 `label_generator.py:40-47`、composer 引 `ic_filter_orchestrator:255-287`），判非附和。

Verdict：**可進 decision-gated SPEC 起草**（三家一致；codex 之三個 P0 為「SPEC 必須寫死的契約語意」，非停工 BLOCKING——主委採 codex 較嚴解讀：K1／K2／K8／K9 四項語意須先回填討論檔並經使用者白話閘，再起草 SPEC）。U1–U11 全部技術可行；J1–J10 無一條被推翻，七條被「部分同意」＝補強條件（見各群集）。

### C1 — A／B 之 label／進場價格語意 ≠ IC 主線 close-to-close；契約必填 `reference_price_semantic`（三家＋主委一致；P0 級）
**引用**: CODEX-R2-P0-02, COMPOSER-R2-P0-01, GROK-R2-P1-01, CLAUDE-R2-P1-02

**處置＝SPEC 前置裁決 D1＋K1 硬欄**。收斂結論：
1. 碼證：IC 主線 label＝`close.shift(-h)/close-1`（`label_generator.py:40-47`；`_resolve_effective_label_horizon` 解析 `return_N`，orch `:255-287`）；`/search` 預設 `CLOSE_TO_CLOSE`（`requests.py:99-103`；`case_search_engine.py:1229-1241,1293-1297`）；使用者 U4＝t₀ **open** 進場。
2. 契約必填 `entry_price_semantic∈{trigger_open,trigger_close,next_open}`＋`label_return_mode∈{open_to_close,open_to_horizon_close,close_to_close}`（A／B 預設 `open_to_horizon_close`；C 事件後報酬表可 `close_to_close`）；條件 IC 於 A／B 用使用者附的 `label_value`（U2）或重算 open-based 序列，**禁止**靜默沿用序列型 `return_N`；若沿用須標 `label_price_mismatch=true`。
3. S3.9-1「換時間戳即可共用 IC」＝過度簡化（grok／composer）；改寫為「特徵 as-of 可換算、label 語意須另欄」。

### C2 — 六時間欄收據須 **per-TF** `feature_cutoff`；`t0_open` 只在事件於 open 前已知時合法；失敗清單枚舉 loud（三家一致）
**引用**: COMPOSER-R2-P1-01, GROK-R2-P1-03, CLAUDE-R2-P1-02

**處置＝K2 定案**。收斂結論：receipt 每事件×每 TF 一列 `{feature_cutoff_ms, last_bar_open_ms, last_bar_close_ms, row_id}`，規則 `max{close_ms ≤ decision_at}`；12h t₀ 對 1h／4h 在 UTC 整點為**常見特例**，一律走 as-of；不變式 `observed_through ≤ feature_cutoff[tf] ≤ decision_at ≤ entry_at ≤ label_start < label_end`（R1 C1 延續）；A／B 之「事件在未來」⇒ `event_known_at_decision=false`、特徵 `observed_through ≤ t0`、選樣可用結果欄（分路徑，見 C3）。失敗枚舉（聯集）：`invalid_timestamp_unit／timezone_missing／missing_bar／duplicate_bar／unsorted_bar／no_boundary_match／feature_after_decision／entry_before_decision／label_window_incomplete／nonpositive_reference_price／nan_or_inf_feature／reference_symbol_unavailable／warmup_insufficient_<tf>／tf_boundary_ambiguous`；逐事件寫 reason、禁 `continue`。

### C3 — 條件引擎須分欄位角色 `feature／selection_predicate／label`（或 `column_role∈{pit_feature,trigger_outcome,future_outcome}`），typed AST＋digest，純函式落 `momentum/`，`/search` 與 `event_filter` 皆 adapter（三家＋主委一致；codex P0）
**引用**: CODEX-R2-P0-01, CODEX-R2-P1-09, COMPOSER-R2-P1-04, GROK-R2-P1-04, CLAUDE-R2-P1-03

**處置＝K9 定案＋SPEC 前置裁決 D2**。收斂結論：`EventFilter.apply_filter` 對任意欄 `df.eval`（`event_filter.py:55-105`）無角色；`/search` 已產 `future_*`（`case_search_engine.py:336,651-658,1291-1327`）且篩選只准 `price_change`（`requests.py:50`）。定案：新純函式 `momentum/Analysis/event_samples/condition_engine.py`（或 `event_generation/`）：expression 分三類，`feature` 須 `available_at ≤ feature_cutoff`，`selection_predicate` 可含未來欄但只進抽樣 provenance，`label` 只進結果欄；canonical AST／digest、欄位角色清單、最大 lookback；多組 label 用 `label_id` manifest（非布林覆寫）；去重在產生期；輸出過 K1 validator；legacy `df.eval` 路徑保留為 adapter，**未過上述 receipt 前不得宣稱「已共用完整引擎」**。`allowed_filtering_params={'price_change'}` 改契約化允許清單。

### C4 — 全部 K 線驗證須有固定分母（evaluation manifest）＋學習／全樣本基率並列＋lift；不碰回測層（三家＋主委一致；codex P0）
**引用**: CODEX-R2-P0-03, GROK-R2-P1-02, CLAUDE-R2-P0-01

**處置＝K8 定案（U11：一次建完整）**。收斂結論：all-bars evaluation manifest 以 decision_at 為索引，只納 `eligible`（答案窗完整、資料連續、價格有效、PIT 合法）；報 `n_total／n_eligible／n_labeled／n_unknown／n_tail_excluded／n_missing`＋reason；輸出 precision／recall／F1／PR 曲線＋AUC／PR-AUC／lift（top-q%／固定閾值）／confusion matrix／訊號頻率／簡單 signed 持有報酬（entry open→答案窗末 close；與 C1 語意一致）／按 symbol、direction、反例種類、時間段分層＋CI／`prevalence_learn` vs `prevalence_full`＋`sample_design=case_control` 揭露／與序列型全 bar IC 並排。**不做**：倉位、手續費／滑價、複利、資金曲線、turnover／capacity、triple-barrier 最佳化、long-short 組合。缺任一基率欄 ⇒ `unavailable:missing_prevalence_disclosure`。

### C5 — 連續觸發：primary policy 事前固定、依情境（C＝簇首；A／B＝全留＋唯一性權重於 manifest），簇間隔用 UTC duration，「兩種都跑」降為敏感度非 B1 門檻；訓練端 sample_weight 現 UNWIRED（三家一致，codex 略嚴）
**引用**: CODEX-R2-P1-05, COMPOSER-R2-P1-02, GROK-R2-P2-01

**處置＝K3 定案**。收斂結論：manifest 每事件 `observation_interval／label_start／label_end／dedupe_cluster_id／overlap_set_hash／uniqueness_weight`；`cluster_gap` 以時間（預設＝答案窗 duration）非 row count；跨 symbol 同時刻與 interval overlap 一併 union；C primary `cluster_first`，A／B primary `all_with_uniqueness`（codex 建議全情境 cluster 為 primary——主委採三家多數「依情境」，但接受 codex 要求：A／B 全留之顯著性**必**用 cluster-robust／bootstrap，無修正 raw-all 禁出）；另一 policy＝預先登記之敏感度，報告 `sensitivity_flip`；`SampleWeightCalculator.compute_uniqueness` 存在但 `UNWIRED_MODULES` 含 `sample_weight`（grok）⇒ B1 只寫權重進 manifest／統計用有效 n，GBDT 套權重列 B3＋ML 殼閘。

### C6 — pooled 最小版：per-symbol 切後合併、macro（symbol 等權）primary＋micro 敏感度、同 UTC 時刻跨標的簇權重／cluster bootstrap；明寫不關閉 registry #4（三家一致）
**引用**: CODEX-R2-P1-04, COMPOSER-R2-P1-03, GROK-R2-P2-02

**處置＝K4 定案＋SPEC §N 邊界**。收斂結論：`time_cluster_id=floor(decision_at_ms/bucket)`（bucket 預設＝觸發 TF 一根）＋`cluster_weight`（`1/n_in_cluster` 或 bootstrap over clusters）；報 `n_symbols／per-symbol n／n_time_clusters／avg_cluster_size`；未做 cluster 調整 ⇒ `degraded`；跨 symbol 泛化宣稱須 LOSO／held-out-symbol receipt；GAP-3 pooled＝事件 panel 描述／條件統計，**不**重建 cross-sectional IC、不做 random-effects／GEE，registry #4 保持獨立。

### C7 — 三張表 estimand／CI／capability 映射；T8／T9／T10 契約形狀；DSR/PBO 只在規則→return series→ledger 後（B3）（codex 三條，composer／grok K 提案一致）
**引用**: CODEX-R2-P1-06, CODEX-R2-P1-07, CODEX-R2-P1-08

**處置＝K5／K1／K6 定案**。收斂結論：(i) 事件後報酬表 signed `(exit_h−entry)/entry`、按 direction／scenario／symbol／time／cluster 分層、cluster bootstrap／HAC CI；(ii) 辨別表只用 OOS score、AUC／PR-AUC／rank-biserial／prevalence／threshold／confusion／lift，按 `counterexample_kind` a/b/c 與兩段式腿分層，one-class ⇒ `unavailable`；(iii) 條件 IC 只吃連續 `label_value`，沿 stage3/4/5＋A′；`statistic_kind∈{event_return,binary_discrimination,conditional_ic}`，禁合併總分；capability 枚舉沿 `ic_report_contract.json`。T8 `reference_symbols[]{symbol,timeframe,alignment_rule,snapshot_digest}`；T9 `source_model{model_id,version,artifact_digest,split_plan_hash,feature_manifest_hash,available_at}` 且 `available_at ≤ decision_at` 否則 `research_only`／拒絕；T10 `event_interval{start,end,endpoints_inclusive}`＋overlap 身分。DSR/PBO：`pbo.py:169-189` 吃 returns matrix＋candidate ids＋provenance、`min_btl.py:74-101` 吃 SR/trials/years ⇒ 只在 B3 規則→同 entry/exit 語意 OOS return series→candidate ledger 後接；AUC／IC 不直接餵；B1 oracle＝label 置亂（固定 seed）＋PIT 後移必 raise。

### C8 — 變化類特徵：複用既有 `ts_argmax/argmin`／slope／diff，補 `bars_since_cross／consecutive_run／bars_since_threshold／window_max_ratio／cross_count`（grok＋主委一致；三家 K7 同向）
**引用**: GROK-R2-P2-03, CLAUDE-R2-P2-04

**處置＝K7 定案**。收斂結論：`RollingAggregator` 有 `slope/std/mean/rank/zscore/min/max`（`rolling_aggregator.py:45-81`）、`DerivedOperators.ts_argmax/ts_argmin`（`derived_operators.py:435-441`）已在——**不重做**；grep `bars_since|consecutive_|run_length|streak` → 0 ⇒ 新 operator 模組（`operators/state_counters.py` 或擴 `derived_operators`）經 `operator_registry` 註冊；每 operator 只看 `[t−lookback+1,t]`、輸出 `max_lookback／warmup／as-of`；NaN 語意明定不填 0；須過 Feature Factory 因果／golden 紀律。

### C9 — 分批：B1 一致（契約＋對齊收據＋manifest／切分＋oracle＋單特徵二元 baseline）；後批次序三家略異，主委定 B2 三表＋survivor v2＋K8 核心、B3 產生器完整版＋K7、B4 pattern／DSR-PBO 橋、B5 持久化／API／前端占位／UAT（codex 一條，composer／grok K10 提案）
**引用**: CODEX-R2-P1-10

**處置＝K10 定案**。收斂結論：每批須有可讀輸出、golden／negative oracle、依賴與「存活至／覆蓋風險」欄；B1 失敗不得靠後批占位或全票 UAT 遮蔽。分歧：codex B3＝產生器＋all-bars＋pattern、B4＝持久化；composer B3＝K7＋K8、B4＝產生器、B5＝API／前端；grok B2 含 K8＋產生器 MVP。主委取交集原則「先能驗證資料正確（B1）→再能看統計與實盤 estimand（B2 含 K8，因 C4 為整票靈魂）→再降低手工（B3 產生器）→再找 pattern（B4）→再上 UI（B5）」；產生器 MVP（T1 價量＋G2–G5）若 B2 有餘裕可前移，由 TODO 階段定。T4／T6 外部源 blocked-by 資料源。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P0-01

**斷言**: §6 的條件引擎允許未來結果欄參與「挑樣本」，但沒有把它與模型特徵、全 K 線驗證標籤做欄位級隔離；因此 A/B 事件可以在實作時把 future-derived 欄位帶入 X，造成不可驗的 look-ahead。

**碼證**: `白話說明/GAP-3事件型討論.md:22,197-205` 同時說挑樣本可用未來、條件可用任何 Feature Factory 特徵＋t₀ 結果＋未來欄；`momentum/DataExtraction/case_search_engine.py:1291-1327,1355-1364` 直接建立 `future_*` close-shift 欄位。`VERIFY`: `nl -ba 白話說明/GAP-3事件型討論.md | sed -n '197,205p'; nl -ba momentum/DataExtraction/case_search_engine.py | sed -n '1291,1327p'` → future return/drawdown 與 future close 欄位均存在。`RECHECK`: 同一命令重跑並檢查新 generator 的 feature/selection/label 欄位清單。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/DataExtraction/case_search_engine.py#98d2ede5f5f5`

[BLOCKING] 信心度=High。允許 future predicate 本身不是錯（case-control 的選樣可看答案），錯在文件沒有要求每個 expression 帶角色與可用時間，也沒有禁止同一欄被重用為 X。修法：契約把 expression 分成 `feature`、`selection_predicate`、`label` 三類；`feature` 必須 `available_at <= feature_cutoff`，`selection_predicate` 可含未來欄但只能寫入抽樣 provenance，`label` 只能進結果欄；canonical AST/digest、欄位角色清單、PIT validator 與全 K 線 evaluator 都必驗證此分隔。否則「全 K 線驗證」可能只是在同一個未來條件上重算 label，並未證明模型只用決策前資料。

## CODEX-R2-P0-02

**斷言**: 文件的 A/B `t₀ open`、open-entry label 與既有搜尋計算的 close-to-close 語意未形成單一可執行的價格/時間契約；直接沿用現況會把 open 買入問題算成 close-to-close。

**碼證**: `白話說明/GAP-3事件型討論.md:15,30-31,61-62,117,178-180` 定義 t₀ open、open→close 與前一根 close 對齊，但未定義 entry/label 起算的唯一欄位。`api/models/requests.py:99-103` 的搜尋預設 `CLOSE_TO_CLOSE`；`momentum/DataExtraction/case_search_engine.py:1229-1241` 的預設分支用 `close.pct_change()`，`1293-1297` 的 `future_*_return` 以當前 `close` 為分母。`VERIFY`: `nl -ba api/models/requests.py | sed -n '99,103p'; nl -ba momentum/DataExtraction/case_search_engine.py | sed -n '1229,1241p;1293,1297p'` → 現況確為 close-to-close。`RECHECK`: 以 12h t₀ 在 UTC 00:00/12:00、來源 1h/4h 各取一筆，核對 receipt 的 bar_open/bar_close、entry_price、label_start。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `api/models/requests.py#938ff6900fed`; `momentum/DataExtraction/case_search_engine.py#98d2ede5f5f5`

[BLOCKING] 信心度=High。K1/K2 必須先固定 `timestamp_unit=epoch_ms_utc`、bar index 是 open 還是 close、`decision_time_rule`、`entry_rule`、`reference_price_semantic`、`label_start/end` 與答案窗是否包含 t₀。建議六時間欄為 `observed_through, decision_at, feature_cutoff, entry_at, label_start, label_end`，並附實際每 TF bar 的 open/close；A/B 只有在 receipt 證明事件在 open 前已知時才准 trigger-open entry，否則轉為 close-confirm/next-open 或拒絕。單靠一個 `t0` 或自由字串不能驗證 12h→1h/4h 的邊界。

## CODEX-R2-P0-03

**斷言**: §3.1/§6 的「全部 K 線驗證」沒有定義每一根 bar 的可用母體、答案是否已完整、未知/中間結果如何處理及多組標籤的優先順序；因此 precision、recall、PR curve 與 lift 沒有固定分母。

**碼證**: `白話說明/GAP-3事件型討論.md:46-51,183-189,199-204` 要求對每一根 bar 評估並重算標籤，但沒有 `eligible/label_complete/unknown` 集合、尾端截除、multi-label precedence 或 base-rate 欄位。現有 `api/services/xgboost_batch_service.py:617-655` 對案例用精確 timestamp 找列，找不到或 NaN 就 `continue`，且只以 `positive_case` 建 y；這不是 all-bars 的可審計 universe。`VERIFY`: `nl -ba api/services/xgboost_batch_service.py | sed -n '617,655p'` → 靜默跳過與二元 y 均存在。`RECHECK`: all-bars evaluator 對同一真實 kline 輸出 `n_total/n_eligible/n_labeled/n_unknown/n_tail_excluded`，並在尾端缺答案窗時逐列拒絕或明示排除。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `api/services/xgboost_batch_service.py#0d11f275806e`

[BLOCKING] 信心度=High。A/B 的 case-control 可作學習樣本，但全 K 線驗證必須另建以決策時點為索引的 evaluation manifest：每列包含 symbol、TF、decision/entry、label completeness、label kind、outcome rule digest；答案窗未完成、缺 bar、非正價格、PIT 不合法者不可當負例。若多組條件同時命中，應用 `event_id/label_id` 保留多標籤或以契約明定 mutually-exclusive precedence，不能默默覆蓋。最小輸出須含全母體基率與學習樣本基率、各反例種別的 n、confusion matrix、threshold、n_unknown/n_excluded，並把尾端/缺資料列列入 reason enum。

## CODEX-R2-P1-04

**斷言**: J6 的 pooled 最小版只有「各標的時間切、統計合併」描述，沒有固定 symbol weighting、同時刻/重疊事件的統計單位與 #4 registry 邊界；直接合併會讓案例多的標的或共同市場衝擊支配結論。

**碼證**: `白話說明/GAP-3事件型討論.md:66-69,105-110,181-186,234,244` 只說同時刻要降權/分塊，未定義 macro/micro estimand、cluster key 或 CI。`momentum/core/contracts.py:361-387` 的 `SplitPlan` 只有單一 split 的 row identity、rows/timedelta purge 與 optional symbol，沒有 event label interval/overlap cluster。`docs/IC_QUANT_GAP_REGISTRY.md:84-86` 將 pooled/panel IC 列為 registry #4 的 blocked-by；`VERIFY`: `nl -ba momentum/core/contracts.py | sed -n '361,387p'; nl -ba docs/IC_QUANT_GAP_REGISTRY.md | sed -n '84,86p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/core/contracts.py#8a1415d6ea01`; `docs/IC_QUANT_GAP_REGISTRY.md#c36c564cb9c4`

[MAJOR] 信心度=High。K4 應把 GAP-3 的 pooled 限定為事件樣本的 panel 描述統計，不宣稱關閉 registry #4，也不直接開啟尚未重建的 cross-sectional IC。建議 primary 以每 symbol 等權的 macro 統計，另列 event-weighted micro sensitivity；同一 UTC 時刻跨 symbol 與 label interval 重疊事件以 immutable cluster 聚合，CI 用 cluster/block bootstrap 或 cluster-robust covariance；報告 `n_symbols`, per-symbol n/coverage, raw/effective n, cluster count/overlap fraction。若要跨 symbol 泛化，另用 held-out-symbol/LOSO receipt，不以 pooled train/test 取代。

## CODEX-R2-P1-05

**斷言**: S3.7/J3 只給了情境化的「簇首／全留降權」方向，沒有把 G 的時間單位、interval overlap、方向、跨 TF 及 primary/sensitivity 的角色寫成可重現契約。

**碼證**: `白話說明/GAP-3事件型討論.md:98-103` 將 C 的 G 寫成答案窗長度、A/B 允許全留降權，並要求兩種設定都跑，但未定義 G 是 bar 數還是 UTC duration、跨 symbol/TF 如何簇化、降權如何進統計。`momentum/core/contracts.py:369-372` 顯示既有 purge 仍可是 rows 或 timedelta，而非事件簇契約。`VERIFY`: `nl -ba 白話說明/GAP-3事件型討論.md | sed -n '98,103p'; nl -ba momentum/core/contracts.py | sed -n '369,372p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/core/contracts.py#8a1415d6ea01`

[MAJOR] 信心度=High。建議所有情境 primary 預設 `dedupe_policy=cluster`，簇首為事件 interval 的最早代表，`cluster_gap` 用 UTC duration/label interval 而不是不穩定的 row count；A/B 的 `all_with_uniqueness` 與 C 的 cluster 結果可作預先註冊的 sensitivity，不可兩者都當獨立 confirmatory 結論。每事件保存 `observation_interval`, `label_start/end`, `dedupe_cluster_id`, `overlap_set_hash`, uniqueness weight；報告 raw/effective n、簇大小、overlap fraction、權重總和，並以 direction/scenario 分層。缺任何 interval 時 fail-closed。

## CODEX-R2-P1-06

**斷言**: 三張統計表已被分開命名，但文件仍未固定各表的 estimand、依賴的價格語意、重疊事件的 CI、one-class/insufficient reason 與 pooled 多重比較揭露；同一事件樣本可能被誤報成可比較的 IC/AUC/報酬結果。

**碼證**: `白話說明/GAP-3事件型討論.md:88-90,114-123,183-189,240-248` 只列 AUC 類、事件後報酬與條件 IC，未給公式、CI/cluster 方法或 capability enum。`momentum/Analysis/ic_engine.py:80-108` 的 `compute_ic` 是 features 對單一 label 的 Spearman/Pearson；`momentum/Analysis/event_filter.py:93-144` 的 sample tier 只回 tier/p threshold；既有 API 可接受 `event_query/event_timestamps`（`api/models/ic_models.py:150-154`），不代表已有三表契約。`VERIFY`: `nl -ba momentum/Analysis/ic_engine.py | sed -n '80,108p'; nl -ba momentum/Analysis/event_filter.py | sed -n '93,144p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/Analysis/ic_engine.py#da4521cf2b8`; `momentum/Analysis/event_filter.py#e2c89cb3ad7c`; `api/models/ic_models.py#fbc974fb7fa4`

[MAJOR] 信心度=High。K5 最低應明定：(i) 報酬表用 signed `(exit_price_h-entry_price)/entry_price`，依 entry/label 語意和 direction 分層；重疊 horizon 以事件/時間 cluster bootstrap 或 HAC 給 CI。(ii) 二元辨別只用 OOS score，報 AUC/PR-AUC/Mann–Whitney rank-biserial、n_pos/n_neg、prevalence、threshold、反例 kind/兩段式與 calibration/lift；one-class 只能 `capability_status=unavailable`。(iii) conditional IC 只吃連續 `label_value`，沿 stage3/4/5 的 event manifest 做遮罩與 FDR，絕不能把 y=0/1 當 return IC。所有缺資料、樣本不足、fallback、one-class 必須映射到既有 reason enum，禁止空表或靜默跳過。

## CODEX-R2-P1-07

**斷言**: T8/T9/T10 僅列「留欄位」不足以重建事件或防 T9 模型訊號的洩漏；沒有 reference alignment、model provenance/availability 與 interval event identity 的契約形狀。

**碼證**: `白話說明/GAP-3事件型討論.md:164-169,199-203,240-249` 只說 T8 先留參照標的、T9 可接 meta-labeling、T10 可寫區間，未列必填子物件或可用時間。現有 Feature Factory 的 cross-symbol reference 以 `config.cross_sectional.reference_symbol` 作 cache key（`momentum/FeatureEngineering/feature_factory.py:1806-1828`），而 IC survivor 的 event object 現只有 definition/timestamps/mode/count（`momentum/Analysis/contracts/ic_survivor_contract.json:256-285`）。`VERIFY`: `nl -ba 白話說明/GAP-3事件型討論.md | sed -n '164,169p'; nl -ba momentum/Analysis/contracts/ic_survivor_contract.json | sed -n '256,285p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/FeatureEngineering/feature_factory.py#770f90883573`; `momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073`

[MAJOR] 信心度=High。K1 應規定：T8 `reference_symbols[]`、reference timeframe、alignment rule、reference snapshot/config digest 與 reference availability；T9 `model_id/version`, artifact digest, training/split/feature manifest digest, score threshold, signal generated_at/available_at，且 `available_at <= decision_at`，沒有 OOS/availability receipt 則 `research_only` 或拒絕；T10 `event_shape=interval`、`event_start/end`、端點是否包含、source rule digest、overlap/dedupe identity。這些欄位不能只塞自由 `meta`，否則下游無法驗證同一事件語意。

## CODEX-R2-P1-08

**斷言**: 文件把打亂答案、DSR/PBO 與全 K 線驗證排在同一條線，但沒有定義 candidate universe、return series 與 trial ledger，因此 DSR/PBO 不能從 AUC/IC 或未記錄的模型試驗直接推出。

**碼證**: `白話說明/GAP-3事件型討論.md:69,127-131,187-189,246` 只說打亂答案與 DSR/PBO 接上；`momentum/Analysis/strategy_validation/min_btl.py:74-101` 依 `n_trials`/Sharpe/年數，`momentum/Analysis/strategy_validation/pbo.py:169-189` 依 returns matrix、candidate ids/count、selection metric 與 provenance。`VERIFY`: `nl -ba momentum/Analysis/strategy_validation/pbo.py | sed -n '169,189p'; nl -ba momentum/Analysis/strategy_validation/min_btl.py | sed -n '74,101p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/Analysis/strategy_validation/min_btl.py#a7608ff57c24`; `momentum/Analysis/strategy_validation/pbo.py#35032307622a`

[MAJOR] 信心度=High。K6/K10 應分批：B1 做固定 seed 的 label-permutation oracle、PIT 後移必 raise、契約/切分/manifest；B2 做三表與 conditional IC；只有 B3 將每個規則/模型訊號轉為相同 entry/exit 語意的 OOS return series、寫 candidate ledger，再接 DSR/PBO/MinBTL。AUC、PR-AUC、rank-biserial 不直接餵 return-based DSR/PBO；`n_trials` 必從 ledger/provenance 讀，不能由 request 任意填。每個 oracle 需記實際命令、seed、輸入 digest、預期 fail/pass。

## CODEX-R2-P1-09

**斷言**: J10 直接把現有 `event_filter` 的 `df.eval(engine="python")` 當完整事件產生器底層，會把查詢安全性、PIT、multi-label、future-role 與 rule digest 混在同一個布林遮罩內，不能作為新契約的唯一 SoT。

**碼證**: `白話說明/GAP-3事件型討論.md:196-205,238,249` 要求 `/search` 完整化並與 event_filter query 共用；`momentum/Analysis/event_filter.py:55-105` 只驗 identifier/blocklist 後以 `df.eval(query, engine="python")`，結果僅回 `mode/query/n_events/tier`，沒有欄位 availability/role、AST digest 或 label provenance。`api/models/requests.py:38-55` 仍把初始篩選參數硬限為 `price_change`。`VERIFY`: `nl -ba momentum/Analysis/event_filter.py | sed -n '55,105p'; nl -ba api/models/requests.py | sed -n '38,55p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/Analysis/event_filter.py#e2c89cb3ad7c`; `api/models/requests.py#938ff6900fed`

[MAJOR] 信心度=High。K9 建議在 `momentum/` 建純函式、typed safe-subset AST/DSL：只允許已註冊欄位、比較/布林/區間/缺值運算，編譯成 mask 並輸出 canonical expression digest、欄位角色、最大 lookback/availability；API `/search` 與 IC `event_filter` 都做 adapter。future outcome 可進 `selection_predicate/label`，不得進 `feature`；多組 label 用 `label_id`/manifest 保留重疊，不靠一個布林 mask 覆寫。legacy `df.eval` 可維持既有 query 路徑，但在新 generator 未通過上述 receipt 前不得宣稱已共用完整引擎。

## CODEX-R2-P1-10

**斷言**: U6 的「完整版事件產生器」與 P10 的「第一版只占位、UAT 等整票」沒有按可交付價值切批；若把十類事件、跨標的、三表、ML、前端和外部欄位視為同一批，沒有可獨立驗收的 B1。

**碼證**: `白話說明/GAP-3事件型討論.md:174-194,196-207,221,249-250` 同時要求完整 `/search`、新契約、三張表、全部 K 線、pattern、前端占位及四批，但未列各批輸入/輸出/依賴/存活期。`api/services/case_import_service.py:35-37` 的既有必要欄位只有三欄，`api/services/batch_download_service.py:218-245` 的 warmup/全域時間窗仍是舊批次下載參數。`VERIFY`: `nl -ba api/services/case_import_service.py | sed -n '35,37p'; nl -ba api/services/batch_download_service.py | sed -n '218,245p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `api/services/case_import_service.py#7ed5b2f8190c`; `api/services/batch_download_service.py#bdb1876667e7`

[MAJOR] 信心度=High。這不是反對 U6，而是要求可收斂的批次邊界。K10 建議 B1=新事件契約＋對齊 receipt＋interval manifest/purge＋單特徵二元 baseline/oracles；B2=三表、capability/reason、survivor contract version；B3=typed generator 的 T1–T3/T10＋all-bars evaluator＋pattern；B4=持久化/API/前端占位/UAT 與 T8/T9 adapter；T4/T6 外部資料源另列 blocked-by。每批要有可讀輸出、golden/negative oracle、依賴與「存活至」欄，不能以全票完成才首次驗收。

## COMPOSER-R2-P0-01

**斷言**: 討論檔 S3.9-1／J2 假設 A／B「t₀ open 決策」可直接以 IC 主線「前一根時間戳＋`return_N` horizon」表達，但現 IC label 語意為 **close-to-close forward return**，與使用者 U4「open 買入」的 label／持有報酬不一致；若不新增 `entry_price_semantic`（及可選獨立 label 欄），條件 IC 與 K8 全 K 線驗證會系統性偏離 A／B estimand。

**碼證**: IC 主線 `_resolve_effective_label_horizon` 從 `labels_df` 欄名 `return_(\d+)` 解析（`ic_filter_orchestrator.py:255-287`）；stage3 後統計仍對連續 `return_N`（`ic_engine.py` 路徑，經 orch `:2776+`）。使用者 A／B：決策＝t₀ **open**、進場價＝open（討論檔 §2-2、U4）。舊 ML 殼同根取值風險 R1 已證（`xgboost_batch_service.py:617-628`）。RECHECK: `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '255,287p'`；對照討論檔 §3.9-1 與 §2-2。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[BLOCKING for SPEC estimand 章] 信心度=High。修法：契約必填 `entry_price_semantic∈{trigger_open,trigger_close,next_open}`＋`label_return_mode∈{open_to_close,open_to_horizon_close,c2c}`；對齊 receipt 寫入實際 `entry_at`／`label_start` 價格來源；條件 IC 在 A／B 預設用 `label_value`（使用者已附實際漲幅，U2）或重算 open-based return，**禁止**靜默沿用序列型 c2c `return_N` 當 A／B 主 label。

---

## COMPOSER-R2-P1-01

**斷言**: J2「12h t₀ 的 open 與 1h／4h 邊界對得整齊」在 **特徵 as-of** 層大致成立，但單一「把 t₀ 換成一根 1h 戳」不足以表達多 TF 特徵截止；對齊失敗清單若只有一個 `feature_row_ts` 會在 12h 觸發＋1h＋4h 並用時漏報半數 TF 越界。

**碼證**: 討論檔 §2-3、J2 宣稱 UTC 00:00／12:00 邊界對齊；Feature Factory 多 TF 獨立計算（`batch_download_service` 支援多 TF `case_models.py:131-134`）。現對齊無 per-TF receipt（R1 C1）。RECHECK: 讀 `api/models/case_models.py:114-135`；grep `feature_cutoff` momentum/ → 0 命中（本輪）。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[MAJOR] 信心度=High。K2 定案：receipt 內 `feature_cutoffs: {tf: {last_bar_open_ms, last_bar_close_ms, row_id}}`；失敗枚舉增 `missing_tf_bar`／`tf_boundary_ambiguous`／`warmup_insufficient_<tf>`。12h t₀ open 時 1h／4h 各自取 `max(close_ms) < decision_at_ms` 的最後一根。

---

## COMPOSER-R2-P1-02

**斷言**: S3.7 要求簇首與全留降權「**兩種都跑一次**」在 1–2 萬事件規模會使下游 ML／統計計算量近似翻倍，且 A／B（預測型）與 C（確認型）的最優預設不同；寫成硬性雙跑會拖慢 B2/B3 驗收節奏。

**碼證**: 討論檔 §3.7 L103「兩種設定都跑一次」；規模 §3.8 L104–110（150–200 標的、1–2 萬案例）。R1 C3 已要求 `dedupe_policy` 枚舉與 overlap 報告。RECHECK: 討論檔 §3.7–3.8。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[MAJOR] 信心度=Medium。K3 定案（見 B）：**主報告**用情境預設（C=`cluster` 簇首；A／B=`all_with_uniqueness` AFML 權重）；**敏感度附錄**才跑另一政策；報告必寫 `dedupe_policy_primary`／`sensitivity_policy`／`conclusion_flips_under_alt_policy: bool`。非禁用雙跑，但降為驗收選項而非 B1 硬門檻。

---

## COMPOSER-R2-P1-03

**斷言**: J6／S3.8 將 GAP-4「多標的合併估 IC」併入 GAP-3 最小版正確，但若 pooled 統計不強制 **同 UTC 時刻跨標的簇**（market-wide shock）降權，會把「BTC+ETH+SOL 同刻大漲」算成 3 個獨立樣本，顯著性與 IC 標準誤膨脹。

**碼證**: 討論檔 §3.3 L67–68、§3.8 L108–109 已文字要求「同一時刻一起大漲是一件事」；registry #4 邊界＝事件型先做「per-symbol 切＋pooled 描述統計」，完整 panel IC 可 degraded。無現成 `cross_symbol_time_cluster` 實作（grep → 0）。RECHECK: 討論檔 §3.8；`docs/IC_QUANT_GAP_REGISTRY.md` #4。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[MAJOR] 信心度=High。K4 最小版：`time_cluster_id = floor(decision_at_ms / cluster_bucket_ms)`（預設 bucket＝觸發 TF 一根）＋`cluster_weight=1/sqrt(n_symbols_in_cluster)` 或用 bootstrap over clusters；報告欄 `n_events_raw`／`n_time_clusters`／`avg_cluster_size`；未做 cluster 調整時 `capability_status=degraded`、禁宣稱 formal pooled inference。

---

## COMPOSER-R2-P1-04

**斷言**: J10「產生器與 IC `event_filter` 共用底層條件引擎」可行，但 `/search` 進階條件含 `future_max_drawdown` 等 **結果欄**（`case_search_engine.py:333-340`），而 ML 特徵欄不得越過 `feature_cutoff`；若共用引擎不區分 `column_phase`，實作會把 future 欄誤用進 PIT 特徵或阻擋合法觸發條件。

**碼證**: `EventFilter.apply_filter` 對任意欄 `df.eval`（`event_filter.py:76-77`）；`_add_calculated_columns` 計算 `future_*`（`case_search_engine.py:1193+`）；篩選只允許 `price_change`（`requests.py:50`）。RECHECK: `nl -ba momentum/Analysis/event_filter.py | sed -n '55,85p'`；`nl -ba momentum/DataExtraction/case_search_engine.py | sed -n '333,341p'`。

**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c

[MAJOR] 信心度=High。K9：引擎落點 `momentum/Analysis/event_condition_engine.py`（純函式）；欄位登記 `phase∈{pit_feature, trigger_outcome, future_outcome}`；query 編譯時對 `pit_feature` 自動注入 `index<=feature_cutoff`；觸發可用 `future_outcome`；匯出 ML 特徵表時 assert 無 `future_*` 列。

---

## GROK-R2-P1-01

**斷言**: 討論檔 S3.9-1 把 A／B「t₀ open 決策」化約成「餵 IC 主線前一根時間戳＋1h horizon」會靜默沿用 close-to-close label，與 open 進場／答案窗末 close 出場的持有報酬不一致，導致條件 IC 與全部 K 線驗證回答不同價格語意。

**碼證**: `LabelGenerator.generate_return`＝`close.shift(-horizon)/close - 1`（`momentum/FeatureEngineering/labels/label_generator.py:40-47`）；IC decay 路徑 `_compute_returns(close, …)`（`ic_engine.py:357,1010-1025`）。討論檔 §2-2／§3.2：決策＝t₀ **open**、A 續漲從 open 進場價起算。現雛形案例對齊同根列（`xgboost_batch_service.py:618-641`）亦無 `reference_price_semantic`。
RECHECK: `nl -ba momentum/FeatureEngineering/labels/label_generator.py | sed -n '40,47p'`；確認無 open-entry overload。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9；momentum/FeatureEngineering/labels/label_generator.py#84c38e0c11d4

[MAJOR] 信心度=High。修法：契約必填 `reference_price_semantic∈{close_to_close, open_to_close, open_to_horizon_close}`（A／B 預設 `open_to_horizon_close`；C 事件後報酬表可用 `close_to_close`）；條件 IC 若复用主線 close label 必須在報告標 `label_price_mismatch=true` 或另算 open-entry label 序列；K8 持有報酬公式鎖 open→答案窗末 close。不得宣稱「換時間戳即可共用」。

---

## GROK-R2-P1-02

**斷言**: J1／S3.1 的 case-control＋全部 K 線驗證在統計上成立，但若報告不強制輸出學習樣本基率、全樣本基率、以及依決策閾值的 precision／recall／lift，使用者仍會把 case-control 內勝率誤讀為實盤勝率。

**碼證**: 討論檔 §3.1 已寫「學習樣本勝率不是實盤勝率」，但 §6 ⑦／§7 J1 未把「基率對照＋lift」列為硬欄。現雛形無此輸出（`CaseRecord` 僅 `positive_case`；`case_models.py:16-30` 路徑；匯入 `REQUIRED_COLUMNS` 三欄 `case_import_service.py:36`）。
RECHECK: 對照 K8 提案是否含 `prevalence_train`／`prevalence_full`／`lift_at_k`。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9；api/services/case_import_service.py#7ed5b2f8190c

[MAJOR] 信心度=High。修法：K8／報告契約必含 `(n_pos,n_neg,prevalence)_learn` 與 `_full_bar`、PR 曲線、固定決策閾值（或 top-q%）下的 precision／recall／lift；缺任一 ⇒ `capability_status=unavailable` reason=`missing_prevalence_disclosure`。同意 J1 核心，不同意「有全部 K 線驗證就夠」的隱含完備性。

---

## GROK-R2-P1-03

**斷言**: 「12h t₀ open＝前一根 1h／4h close」不能用單一事件 TF 前移表達；多 TF 特徵截止必須是 **per-TF** `feature_cutoff[tf] = last closed bar with close_time ≤ decision_at`，否則 1h 特徵會錯位或誤用未收盤 bar。

**碼證**: 討論檔 §2-3／§3.9-1 寫「平台自動換算前一根」。`BatchDownloadRequest.timeframe` 已允許多 TF 列表（`case_models.py:131-134`），但現對齊是單一 `timestamp_sec == case_ts`（`xgboost_batch_service.py:618`）。R1 C1 六時間欄要求 `feature_cutoff`（synth C1）——本輪強調其必須 **按 TF 展開**，不是一個標量。
RECHECK: 對 12h open=00:00 UTC，1h last-closed close_time=23:00、4h=20:00（前一根），兩者 ≠ 同一 timestamp。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9；api/services/xgboost_batch_service.py#0d11f275806e；handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md#7d68d25d1f31

[MAJOR] 信心度=High。修法：對齊收據每 TF 一列 `feature_cutoff_ms`／`feature_bar_open_ms`／`feature_bar_close_ms`；validator 檢查 `feature_cutoff_ms[tf] ≤ decision_at`；跨 TF 合併特徵時以 decision_at 為 join key、各 TF 各自 as-of。12h↔1h／4h 在 UTC 整點對齊是**常見特例**不是唯一規則；非整點邊界（若未來支援）一律走 as-of。

---

## GROK-R2-P1-04

**斷言**: J10／G1 把產生器與 `EventFilter` 的 `df.eval` 條件引擎共用是合理的，但若不对欄位標 `column_role∈{feature,outcome,trigger_bar}` 並在「特徵條件」路徑禁止 outcome／未來欄，共用引擎會在決策時點把未來結果欄寫進觸發特徵語意。

**碼證**: `EventFilter.apply_filter` 對任意 query 做 `df.eval(query, engine="python")`（`event_filter.py:73-79`），僅有關鍵字 blocklist（`:39-49`），**無欄位角色**。`/search` 已計算 `future_*_max_drawdown`／`future_*bar_return`（`case_search_engine.py:645-662`）且篩選進階條件使用未來欄（`:336`）。討論檔 G1 明示觸發可用「t₀ 結果＋未來結果欄」——對**選樣**合法，對**特徵**不合法。
RECHECK: `nl -ba momentum/Analysis/event_filter.py | sed -n '39,79p'`；確認無 column allowlist by role。

**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c；momentum/DataExtraction/case_search_engine.py#98d2ede5f5f5；白話說明/GAP-3事件型討論.md#685405d0daf9

[MAJOR] 信心度=High。修法：條件引擎落 `momentum/Analysis/event_samples/condition_engine.py`（純函式）；API／`/search` 包殼。Query AST 解析後依 mode：`sample_select` 允許 outcome 欄；`feature_gate`／特徵可用性檢查只允許 `column_role=feature` 且 as-of≤decision_at。G6「同一引擎套全部 K 線」重算標籤時 outcome 欄可用、但輸出的特徵列仍受 PIT 約束。

---

## GROK-R2-P2-01

**斷言**: S3.7／K3「A／B 全留＋唯一性降權」不可假設現成訓練路徑已接上；`SampleWeightCalculator.compute_uniqueness` 存在，但 `model_config.UNWIRED_MODULES` 含 `sample_weight`，GAP-3 B1 只能把 uniqueness 當報告／有效樣本數，不能當已接線的 GBDT sample_weight。

**碼證**: `compute_uniqueness`（`sample_weight_calculator.py:121-147`）；`UNWIRED_MODULES={"probability_calibration","sample_weight"}`（`model_config.py:67-68`）。討論檔 §3.7 要求報告 `原始／去重後／重疊比例`——此層可做；「降權後訓練」屬 ML 殼配線，成熟度地圖 ML 不完整層。
RECHECK: grep UNWIRED_MODULES；確認 xgboost_batch 未傳 sample_weight。

**來源摘要**: momentum/Analysis/sample_weight_calculator.py#221bbb558b47；momentum/Analysis/model_config.py#0ad4c42627aa

[MINOR] 信心度=High。K3 預設：C→`cluster_first`；A／B→`all_with_uniqueness` **權重寫入 event manifest**（`w_i=1/overlap_count` 於 label 窗），統計用有效 n／HAC 或 cluster bootstrap；GBDT 套用權重列 B3＋「ML 殼允許接線」閘。B1 敏感度「簇首 vs 全留」可選跑，**不必**兩種都進最小交付。

---

## GROK-R2-P2-02

**斷言**: J6「跨標的合併（缺口票 #4）併進 GAP-3 做最小版」若不劃界，會把 registry #4「Pooled/Panel IC 估計量重建」整票拖進 GAP-3，或相反讓 GAP-3 假裝已完成 #4。

**碼證**: registry 表列 #4＝「多標的資料合併估 IC」（`docs/IC_QUANT_GAP_REGISTRY.md` 行 14）；G2-R3 blocked-by #4（同檔行 86）。討論檔 §3.8／J6 說的是事件樣本 pooled＋同時刻簇。`SplitPlan` 已支援 `symbol` 欄做 per-symbol 切（`contracts.py:361-374`），但不是 panel IC 估計量。
RECHECK: 讀 registry #4 一行定義 vs §3.8 文字。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#c36c564cb9c4；momentum/core/contracts.py#8a1415d6ea01；白話說明/GAP-3事件型討論.md#685405d0daf9

[MINOR] 信心度=High。GAP-3 最小 pooled＝(a) 每標的時間切＋purge/embargo≥答案窗 (b) 切後列垂直合併做事件樣本統計 (c) 同時刻跨標的簇降權／cluster-robust SE (d) 報告標 `pool_method=concat_after_per_symbol_split`。**不做**：截面 IC 主路徑重建、多標的 random-effects／GEE 正式 panel 模型、改寫 `analyze_cross_sectional`——那些仍屬 #4。SPEC §N 寫「#4 仍獨立；本票不關閉 #4」。

---

## GROK-R2-P2-03

**斷言**: 討論檔 §3.4／K7 所稱「bars since cross／連續 N 根」類特徵在 Feature Factory **確實不存在**（須補）；但窗內 argmax／argmin／slope 已有，SPEC 不得把已存在算子再當新架構重做。

**碼證**: `RollingAggregator` 註冊 `slope` 等（`rolling_aggregator.py:49`）；WorldQuant `ts_argmax`／`ts_argmin`（`derived_operators.py:435-439`；`feature_factory.py:1361`）。本輪 `grep -RInE 'bars_since|consecutive_|run_length|streak_count' momentum/FeatureEngineering` → **0 hits**。
RECHECK: 同上 grep；確認 operator_registry 無 bars_since。

**來源摘要**: momentum/FeatureEngineering/operators/rolling_aggregator.py#249714e91213；momentum/FeatureEngineering/operators/derived_operators.py#a2dfc9fcfb88

[MINOR] 信心度=High。K7 清單見下方 B 節；落點建議新 operator 模組函式（或擴 `derived_operators`），經 `operator_registry` 註冊；IC 主線只消費特徵表、不重實作。已有 `ts_argmax/argmin/slope`＝共用、不重寫。

---

