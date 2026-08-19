# Reconcile — 20260819-gap3-x-consult-r1

**來源** 20260819-gap3-recon-codex.md, 20260819-gap3-recon-grok.md　|　**roster** codex,grok

## 群集 / 處置（Claude 填，2026-08-19）

三方共 **24 條** findings（codex 6／grok 8＝鎖定 14 條；claude 10 為非鎖來源 `handoffs/20260819-gap3-recon-claude.md`），下列六個群集**引用全部 24 條，0 掉項**。
**Composer 缺席（DEGRADE，collection-failed）**：首派與同 round 單家補跑皆於 Cursor 端 `RetriableError: [resource_exhausted]` 三次重連失敗（`handoffs/20260819-gap3-recon-composer.runlog`；scratchpad `gap3_rerun.log`），非 brief／環境問題；consult 為 SPEC **輸入**非簽核閘，依「95% 解法就收、殘留具名記錄」以 codex＋grok＋主委收斂；Composer 視角於 SPEC adversarial（三家全員）補到。
獨立性註記：codex（20:43）、grok（20:40）於主委版（20:39）前後交件，codex runlog 顯示掃過 `handoffs/` 但其 P0-01 六時間欄拆分、P1-05 DSR/PBO 不可直接套 AUC 為主委版所無；grok P1-04 秒／毫秒單位坑為三方中唯一提出；判非附和。

Verdict：可進 **decision-gated SPEC 起草**——無全域停工 BLOCKING；但 SPEC 初稿須先拿到使用者對 Q0／Q1／Q2／Q4 四題產品語意之裁決（白話閘），技術題（C1 PIT 不變式、C2 契約欄位、C3 切分、C4 升版、C5 estimand 分層、C6 分類）三方一致於下列處置；SPEC 不得直接 Frozen／派工。

### C1 — PIT 時間軸須由契約**顯式**承載（六時間欄），現雛形同根對齊＋靜默跳過不得作相容預設（三方一致；採 codex 最嚴版）
**引用**: CODEX-R1-P0-01, GROK-R1-P0-01, CLAUDE-R1-P0-01, CLAUDE-R1-P0-02

**處置＝SPEC 前置裁決 D1＋Task B1 對齊純函式**。收斂結論：
1. 碼證成立：`xgboost_batch_service.py:618` 精確相等、`:641` 同根列、`:621`／`:651` 靜默 `continue`；`CaseRecord` 無決策時點欄。使用者原例（t₀＝觸發根 open、特徵含收盤才知指標）下 `:641` **是 look-ahead 面**。
2. 採 codex 拆欄：每事件對齊 receipt 必含 `observed_through`／`decision_at`／`feature_cutoff`／`entry_at`／`label_start`／`label_end`，不變式 `observed_through ≤ feature_cutoff ≤ decision_at ≤ entry_at ≤ label_start < label_end`，由 validator 機械檢查；匯入輸入層只需 `t0`（觸發根 open_time）＋`decision_time_rule`＋`label_window`，其餘由對齊函式**推導並寫入 receipt**。
3. `decision_time_rule` 枚舉＝`trigger_bar_close`（預設）／`next_bar_open`；`trigger_bar_open` **只在** `observed_through ≤ t0` 有證據時合法（事件由前一根／排程／外部資料於開盤前已知），否則 validator 拒絕——不以文字 `t0_open` 同時表達兩種語意（codex）。
4. 特徵列＝`feature_cutoff` 當時已收盤之最後一列（per-TF，含觸發根內子 bar iff 決策≥該根 close）；對齊失敗／越界／NaN ⇒ loud 拒絕或不可靜默之失敗清單（`n_dropped_by_reason`）。
5. **[使用者裁 Q1]** 只問一句：進場＝觸發根收盤確認後（預設）或下一根開盤；PIT 機制＝委員會定。

### C2 — 匯入契約新 SoT（不沿 `CaseRecord`）：label manifest 必填、反例同觸發 fail-closed、時間戳單一 ms（三方一致；欄位取聯集）
**引用**: CODEX-R1-P0-02, GROK-R1-P0-02, GROK-R1-P1-01, GROK-R1-P1-04, CLAUDE-R1-P0-03, CLAUDE-R1-P1-05

**處置＝SPEC Task B1.0 契約檔（唯一欄位列舉處）＋前置裁決 D2／D3**。收斂結論：
1. 新 `momentum/Analysis/contracts/event_import_contract.json`＋純函式 validator；`CaseRecord`／`/case/import` 為 legacy adapter（顯式 migration 或拒絕，禁 silent coerce），不得「加選填欄充數」。
2. 必填（聯集、codex 最嚴）：`event_id`、`symbol`、`timeframe`、`t0`（**epoch ms UTC**；量級像秒卻宣告 ms 或相反 ⇒ 拒絕，grok P1-04）、`label∈{0,1}`、`label_definition{rule_id, canonical_digest, window(start/end 語意或 horizons[]＋agg), reference_price_semantic}`、`control_kind`、`source_file_digest`、`data_snapshot_digest`；選填 `label_value`（連續，建議同時給）、`event_type_tag`、`meta`。自由字串 `label_rule_id`＋hash **單獨不足**（codex P0-02）。
3. `control_kind∈{user_labeled_same_trigger, user_labeled_other, platform_same_trigger_rule, platform_random_bars}`；**v1 只實作 `user_labeled_*`**，二元任務缺任一類別 ⇒ fail-closed `missing_control_group`；`platform_*` 留枚舉位、v1 `not_implemented`（需觸發規則＝可選產生器，第二版）；現雛形 `_select_negative_timestamps`（時間分離未觸發點）屬廢答案設計，**不沿用、不作隱式 fallback**。
4. label 重算：v1 **不重算**使用者 label；可選「一致性探針」限 `price_return_threshold` 一族（claude／grok B 選項）列 SPEC §N 或 B1 可選 task，由 SPEC adversarial 定；hash 相同不證內容正確（codex）。
5. **[使用者裁 Q2／Q4]**：反例自己標（預設）vs 要平台產；標籤規則（AND／OR／連續值、3% 基準價）由使用者定並進 manifest，平台只存不解釋。

### C3 — 去重／重疊／切分：事件 manifest 帶區間、預設 `cluster`、`all` 必配 cluster-robust 推論、per-symbol 時間切＋interval-aware purge（委員會定）
**引用**: CODEX-R1-P1-03, CLAUDE-R1-P1-04

**處置＝SPEC Task B1 `dedupe_events`／overlap＋D4**。收斂結論：
1. `SplitPlan` rows purge 單獨**不**保證事件 label 窗不相交（codex）：新增 immutable event manifest（`event_id, symbol, observation_interval, decision_at, label_start, label_end, dedupe_cluster_id, overlap_set_hash`），事件層做 interval-aware purge／split audit；`SplitPlan`／`validate_split_integrity`／`canonical_split_plan_hash` 仍負責 per-symbol chronological row identity（禁 positional index）。
2. `dedupe_policy∈{first, cluster, all_with_uniqueness}`；預設 `cluster`（代表＝簇首；codex／grok 一致），`all_with_uniqueness` 須附 AFML 平均唯一性權重＋cluster bootstrap／HAC（claude），`all` 無修正 **禁止**；報告必含 `n_events_raw／n_events_effective／overlap_fraction`。
3. test 段事件數 < tier 下限 ⇒ loud `insufficient_events_in_test`（複用 `check_sample_size` 思想，門檻入契約），**不**回退全樣本。

### C4 — `sample_scope.event` 擴欄＋倖存者契約 version 升版；ICHC R5 A′ 原樣保留（三方一致）
**引用**: CODEX-R1-P1-04, GROK-R1-P1-02, GROK-R1-P2-02, CLAUDE-R1-P2-08

**處置＝SPEC Task B2 契約升版**。收斂結論：`ic_survivor_contract.json` `event` 物件現只攜身份（`mode/definition_hash/timestamps_hash/n_*`）；擴 `event_manifest_hash`／`label_definition_hash`／`decision_time_rule`／`feature_cutoff_rule`／`label_window_rule`／`control_kind`，保留 `fallback_requested_scope`＋`degraded`；`additional_properties:false` ⇒ **先升 version（1→2）再寫 payload**，同步 validator／consumer／golden；A′ fallback 透傳 `event_timestamps`＋one-shot guard 不動。grok P2-02 校正：`sample_scope` 非測試命中另含 `frontend/src/lib/pendingFeatures.ts:54`（占位文案），不影響結論。

### C5 — estimand 分層：二元辨別 ≠ 事件條件 IC；B1＝契約＋對齊＋切分＋單特徵二元 baseline 作 permutation oracle 載體；DSR/PBO 不直接套 AUC（三方一致；B1 統計面採 codex 版）
**引用**: CODEX-R1-P1-05, GROK-R1-P1-03, CLAUDE-R1-P1-06

**處置＝SPEC 分批 B1／B2／B3＋`statistic_kind` 枚舉**。收斂結論：
1. 兩個合法問題分節、禁單一數字混報：`statistic_kind=binary_discrimination`（OOS AUC／PR-AUC／Mann-Whitney rank-biserial＋BH-FDR；需 `y∈{0,1}`）與 `statistic_kind=conditional_ic`（事件樣本內特徵 vs 連續未來報酬／`label_value`；複用 stage3 timestamps＋stage4／5＋A′，`sample_scope.kind=event`）。
2. B1 最小可交付＝匯入契約＋PIT 對齊 receipt＋dedupe/overlap manifest＋per-symbol 切分＋**單特徵二元 baseline**（作 label 置亂 oracle 載體：chance-level 以 CI／固定 seed 判定，不寫死數字）＋PIT 後移 oracle（validator 必拒）。grok／claude 之「B1 無統計」與 codex 之「B1 含 baseline」差異＝oracle 需要載體 ⇒ 採 codex。
3. B2＝conditional IC＋binary FDR 接 stage；B3＝GBDT／SHAP／`pattern_extractor`（`SplitPlan` train fail-closed）＋規則→可比較 return series→candidate ledger→GAP-1 DSR/PBO；**禁**為 AUC/point-biserial 自創 MinBTL 數字（`min_btl.py` 吃 SR/trials/years），n 不足 ⇒ `capability_status=unavailable`。

### C6 — 事件分類＝正交欄位非互斥七類；v1 只收通用匯入、產生器為可選附屬；落點命名避 `event_study`；分批／雛形處置／無 BLOCKING（三方一致）
**引用**: CODEX-R1-P1-06, GROK-R1-P2-01, CLAUDE-R1-P1-07, CLAUDE-R1-P2-09, CLAUDE-R1-P2-10

**處置＝SPEC §0 範圍＋Task 分批表＋§N**。收斂結論：
1. taxonomy 拆正交欄（codex）：`event_source∈{market,manual,external}`、`observable_family∈{price_volume,technical,regime,derivative,calendar,text}`、`event_origin∈{imported,generated}`、`event_shape∈{instant,interval}`、`label_kind∈{binary,ordinal,continuous}`；`event_type_tag` 保留為自由標籤。v1 支援＝imported records 通用時間契約（涵蓋①②③⑤⑦）；④⑥外部源、金融 CAR/AAR、即時 NLP **明列不支援**；①類規則產生器＝第二版可選附屬（grok／claude B 選項；**[使用者裁 Q0]** 支援範圍與示範類）。
2. 落點＝新純函式模組 `momentum/Analysis/event_samples/`（或 `event_import/`；避 `event_study`），`event_filter.py` 只留遮罩；API 可沿 `case.py` 路徑換新 schema；**禁改** `xgboost_batch_service` 訓練殼；舊 cases.json 不遷移（面向未來不溯及既往）。
3. 分批＝B1 契約／對齊／去重／切分／oracle → B2 統計＋契約升版 → B3 規則＋DSR/PBO → B4 持久化＋API＋前端占位殼（UAT 等整票）。Kline 層變更風險以契約隔離（綁 symbol／timeframe／bar 邊界／時區／snapshot digest，不綁 HDF5 佈局）。
4. 未查（不阻塞）：外部源現有程式面、Feature Factory 多 TF as-of 工具、萬級事件 bootstrap 牆鐘、`two_stage_search` 欄位對照全表——列 SPEC 偵察待辦。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01

**斷言**: 候選的 `decision_time∈{t0_close,t0_open,next_open}` 加上「取決策時點已收盤最後一列」仍不足以證明 `t0_open`／`next_open` 的特徵沒有使用決策後資料；若不把觀測截止、決策、進場與 label 起點拆成獨立時間欄，GAP-3 會產生不可驗的 look-ahead。

**碼證**: brief:49-50 只有 `decision_time` 與 `label_horizon`，對齊候選只要求最後已收盤列；`api/services/xgboost_batch_service.py:617-641` 以 `timestamp_sec == case_ts` 找同一列並直接取該列特徵；brief:37-38 已實核現雛形沒有 as-of／邊界正規化，且同根取值在 `t0` 被定為 open 時會把同根收盤後資訊帶入。RECHECK: `nl -ba api/services/xgboost_batch_service.py | sed -n '617,641p'`。

**來源摘要**: handoffs/20260819-gap3-recon-BRIEF.md#ba5ee3a0c43d；api/services/xgboost_batch_service.py#0d11f275806e

[BLOCKING] 信心度=High。合法的 open 決策確實存在，但前提是事件已由前一根、排程或外部資料在開盤前觀測完成；同樣的 `t0_open` 文字不能同時表示「觸發根開盤」和「開盤前已知事件」。建議契約最少分開 `observed_through`、`decision_at`、`feature_cutoff`、`entry_at`、`label_start`、`label_end`，並要求 `feature_cutoff <= decision_at <= entry_at`；每事件 receipt 記錄實際使用的 bar open/close 與資料版本。預設可採「觸發根 close 決策、next open 進場」，但 open 決策只能在 receipt 能證明觀測資料不晚於 open 時通過。這是進 SPEC 前必須由使用者裁產品語意、由委員會鎖 PIT 守衛的共同前置。

## CODEX-R1-P0-02

**斷言**: 只把 label 收成二值、把 `label_rule_id` 定為自由字串＋hash、再以可選 `control_kind` 表示反例來源，無法重建 label 的實際時間窗／基準／對照抽樣，因此不能安全支撐監督式 pattern 發現或其 purge。

**碼證**: `api/models/case_models.py:16-30` 的 `CaseRecord` 僅有 `timestamp`、`positive_case`、`source_file`、`import_time`；`api/services/xgboost_batch_service.py:649-656` 對特徵 NaN 警告後跳過並以 `case.positive_case` 建 y；`api/services/search_task_service.py:788-818` 的舊反例只由正例前後 `separation_days` 產生時間點，沒有「同觸發但未達標」證明。候選 contract 在 brief:49、brief:52 將 label definition 與 control selection 留在自由字串／報告標籤。RECHECK: `nl -ba api/models/case_models.py | sed -n '16,30p'; nl -ba api/services/search_task_service.py | sed -n '788,818p'`。

**來源摘要**: api/models/case_models.py#61f72fca0397；api/services/search_task_service.py#c8357d2a7c12；handoffs/20260819-gap3-recon-BRIEF.md#ba5ee3a0c43d

[BLOCKING] 信心度=High。若 label 規則是 24∧36∧48、OR、多數、min/avg 或任意外部標註，`label_rule_id` 本身不能告訴平台 label 起訖、比較價格、使用的資料快照與是否包含觸發根；同樣地，random bars 與同觸發未續漲回答的是不同 estimand。建議 B1 的匯入列必須帶 `event_id`、`label`、canonical label-definition digest、label window start/end、reference/entry price semantic、control_kind、control-selection provenance，以及原始檔／資料快照 digest；二元監督任務缺任一類別時 fail-closed，不暗中產 random controls。平台未來可提供控制組產生器，但必須另收可重現的觸發規則與匹配／抽樣契約，不能把它當成外部匯入的隱含 fallback。

### §0 被當成事實的未驗證假設

- brief:43 的七類事件是 `assumed`，不是互斥或完備的事實；本報告在 Q0 改成正交分類。
- brief:44 的「通用欄位足夠」是 `assumed`；P0-02 證明至少需要事件窗、控制組 provenance 與可重現 digest。
- brief:45 的 close 決策／same-root 特徵是候選語意，不是唯一合法語意；P0-01 保留 open/pre-open 合法場景但要求顯式 as-of。
- brief:46 的「共用 IC、bootstrap」與「主統計量」是 `assumed`；Q5 分開二元分類 estimand 與事件條件 return IC。

## CODEX-R1-P1-03

**斷言**: `dedupe_events(events, min_gap, policy)` 與既有 rows-based `SplitPlan` 不能單獨保證事件 label window 不重疊；沒有每事件的觀測窗／label 窗／cluster identity，連續觸發會造成相關樣本、跨 split 污染與顯著性膨脹。

**碼證**: brief:51 只列 `min_gap`、`first/last/all/cluster` 與 `label_horizon`；`momentum/core/contracts.py:361-387` 的 `SplitPlan` 表達 row index、purge gap、embargo，未表達每事件的 label interval 或 overlap cluster；`momentum/Analysis/ic_filter_orchestrator.py:369-400` 目前以可解析的單一 bar horizon 建 rows purge。RECHECK: `nl -ba momentum/core/contracts.py | sed -n '361,387p'; nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '369,400p'`。

**來源摘要**: handoffs/20260819-gap3-recon-BRIEF.md#ba5ee3a0c43d；momentum/core/contracts.py#8a1415d6ea01；momentum/Analysis/ic_filter_orchestrator.py#fa7b795aaea8

[MAJOR] 信心度=High。`first`／`cluster` 可把連續觸發化成事件單位；`all` 則須明確將 cluster 作為統計單位或提供 cluster weight／cluster bootstrap，不能只把 rows 數當獨立 n。事件 label horizon 若以 seconds 或不同 TF 表達，固定 rows purge 也不等於實際時間窗不相交。建議新增 immutable event manifest：`event_id, symbol, observation_interval, decision_at, label_start, label_end, dedupe_cluster_id, overlap_set_hash`；`SplitPlan` 仍負責 per-symbol chronological row identity、purge、embargo，事件層另做 interval-aware purge／split audit。`all` 的 downstream 統計必須明列 cluster-robust 方法；沒有此資訊時拒絕顯著性聲明。

## CODEX-R1-P1-04

**斷言**: 現有 `sample_scope.event` 只保存事件模式、definition/timestamps hash 與計數；它不能讓 downstream 知道 label 語意、horizon、決策時點或控制組，而且 A′ fallback 會把 scope kind 設成 `full`，需要新的事件 manifest digest 與 degraded 語意才能安全消費。

**碼證**: `momentum/Analysis/contracts/ic_survivor_contract.json:225-285` 的 `sample_scope.event` keys 僅為 `definition_hash/timestamps_hash/mode/n_events/n_timestamps_requested`；`momentum/Analysis/survivor_contract.py:407-411,433-471` 以 fallback 決定 `kind=full`、只保留 event identity；`momentum/Analysis/ic_filter_orchestrator.py:1100-1116,1142-1153` 顯示 R5 A′ fallback 透傳 `event_timestamps` 並重跑 full sample。`handoffs/reconcile/20260817-ichc-x-consult-r5/synth.md` 的 E1/E2 也把「保留 timestamps」定為既有語意。RECHECK: `nl -ba momentum/Analysis/contracts/ic_survivor_contract.json | sed -n '225,285p'; nl -ba momentum/Analysis/survivor_contract.py | sed -n '433,471p'`。

**來源摘要**: momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073；momentum/Analysis/survivor_contract.py#736d8a8cf2a5；handoffs/reconcile/20260817-ichc-x-consult-r5/synth.md#d7f5acfc3eff

[MAJOR] 信心度=High。A′ 本身不應推翻：事件 timestamps 在 fallback 仍須保留，且 root 必須標 degraded/full-sample；問題是新的事件型 survivor 若只有 timestamp identity，消費者不能判斷「同一批 timestamps 的不同 label definition」是否可比較，也不能只靠 `kind=full` 分辨 requested event 與原本全樣本。建議將 `event_contract_hash`／`event_manifest_hash`、`label_definition_hash`、`decision_time_rule`、`feature_cutoff_rule`、`label_window_rule`、`control_kind` 加入 event object，保留 `fallback_requested_scope` 與 `degraded`；GAP-2b `version=1` 應升版並同步 validator／consumer。R5 的 A′ 透傳與 one-shot guard 必須原樣保留。

## CODEX-R1-P1-05

**斷言**: 候選把事件子樣本條件 IC、二元 label 的 AUC／rank-IC、GBDT/SHAP 與 DSR/PBO 放在同一條 B1→規則流程，卻沒有先選定 estimand；這會把「預測事件 label」誤報成「事件內未來報酬 IC」，也會把 return-based DSR/PBO 直接套到 classifier metric。

**碼證**: brief:53 同時列三類統計量並要求規則接 GAP-1 DSR/PBO；`momentum/Analysis/ic_engine.py:80-108` 的 `compute_ic` 目前是 feature 對單一 label 的 Spearman/Pearson 路徑；`momentum/Analysis/strategy_validation/min_btl.py:74-101` 的 MinBTL/budget 以 `n_trials`、`target_sharpe`、年數計算；`momentum/Analysis/strategy_validation/pbo.py:169-185` 的 PBO 入口吃 `returns_matrix`、candidate universe 與 CSCV 參數。RECHECK: `nl -ba momentum/Analysis/ic_engine.py | sed -n '80,108p'; nl -ba momentum/Analysis/strategy_validation/min_btl.py | sed -n '74,101p'; nl -ba momentum/Analysis/strategy_validation/pbo.py | sed -n '169,185p'`。

**來源摘要**: handoffs/20260819-gap3-recon-BRIEF.md#ba5ee3a0c43d；momentum/Analysis/ic_engine.py#da4521cf2b8；momentum/Analysis/strategy_validation/min_btl.py#a7608ff57c24；momentum/Analysis/strategy_validation/pbo.py#35032307622a

[MAJOR] 信心度=High。兩個合法但不同的問題是：(a) `y∈{0,1}` 的監督式事件辨識，主指標應是 OOS AUC/PR-AUC、校準或 lift；(b) 已選事件樣本內 feature 對連續未來報酬的條件 IC，要求 return label 與事件條件。建議 B1 只做 (a) 的單特徵 baseline＋permutation label oracle；B2 才接條件 IC/FDR；GBDT/SHAP 與規則抽取放 B3。DSR/PBO 只在規則已轉成可比較的 return series、候選宇宙已進 ledger 且明確定義 trial count 後接入；不要為 AUC/point-biserial 自行發明 MinBTL 數字。

## CODEX-R1-P1-06

**斷言**: brief:43 的七類事件不是互斥且不是同一層級分類；只用 `event_type_tag`／`meta` 的通用匯入契約會失去必要的資料可用性、產生方式與 label 時序語意，不能形成可驗證的事件 taxonomy。

**碼證**: brief:43 將價格／量、技術形態、regime、衍生品、日曆、新聞、人工匯入並列；brief:49 只把 `event_type_tag`、`source`、`meta` 作為選填。原例的 trigger 是價格／量觀測，但其正反 label 又是另一個 outcome 定義。RECHECK: `nl -ba handoffs/20260819-gap3-recon-BRIEF.md | sed -n '43,50p'`。

**來源摘要**: handoffs/20260819-gap3-recon-BRIEF.md#ba5ee3a0c43d

[MINOR] 信心度=High。這不是要求第一版接入新聞或衍生品；它是契約建模提醒。建議將 taxonomy 拆成正交欄位：`event_source`（market/manual/external）、`observable_family`（price_volume/technical/regime/derivative/calendar/text）、`event_origin`（imported/generated）、`event_shape`（instant/interval）、`label_kind`（binary/ordinal/continuous）。第一版只承諾 imported records 的通用時間契約；外部源、事件產生器與金融 CAR/AAR 明列不支援。`event_type_tag` 可保留為可擴充標籤，但不能承擔 validator 的全部語意。

### §1 必查摘要

1. 矛盾／互斥：候選的 `t0_open`、`t0_close`、`next_open` 與「最後已收盤列」未固定觀測與進場關係，見 P0-01。
2. 端到端漏項：label window、control provenance、event manifest、survivor event semantics 缺口，見 P0-02、P1-03、P1-04；API／前端不在本輪受理範圍。
3. 不可測驗收：目前候選沒有每事件 alignment receipt、overlap audit、label manifest digest、binary/conditional estimand 的獨立 golden；列為 SPEC 必補，不以「確認正確」替代。
4. Quant 假設：同一 bar 特徵的 PIT 風險、random control 改變 estimand、overlap 破壞獨立性、AUC 與 IC 語意混用，分別見 P0-01、P0-02、P1-03、P1-05。
5. 過度工程：本輪不建議把 event generator、新聞／衍生品資料源、GBDT/SHAP、前端一次納入 B1；Q7 給出分批範圍。
6. OOM／並行：本輪沒有可證據化的新並行設計；UNVERIFIED，且不把數千～數萬事件直接當成容量承諾。
7. Cache 正確性：新事件輸入若持久化，至少需 event manifest、label source、feature/data snapshot digest；候選尚未定義，UNVERIFIED，見 P0-02/P1-04。
8. API／型別／相容：現有 CaseRecord 是舊 ML 孤島；新契約不應直接改寫 `xgboost_batch_service` 殼。新 API schema、migration 尚未寫，UNVERIFIED。
9. 測試品質：可執行 oracle 至少需 PIT boundary、duplicate/overlap、one-class、missing bar、permutation-label、cross-symbol、fallback A′；本輪未新增或執行測試，因 brief 明禁改測試。
10. Agent 可執行性：候選已有函式名，但缺 event manifest schema、欄位不變式、輸出 receipt 與可量化 gates；SPEC 需補後才能派工。
11. 必要性／短命工：`event_filter` 的 timestamps mask 可重用；若另做 import contract，不要先把欄位塞進舊 `CaseRecord` 再於後續 phase 覆蓋。其餘存活期限 UNVERIFIED，待 SPEC/TODO 明列 `存活至`／`覆蓋風險`。

### §2 範本錨點與空殼檢查

本輪沒有 SPEC/TODO/PLAN，故 §RISK/§A/§C/§G/§P/§V/§R/§N 的 SPEC 錨點不適用；不能把「候選設計」冒充已 Frozen 的驗收條款。本文以 findings、Q0–Q8 選項與可重跑證據取代空標題，正式 SPEC 仍須補 golden、receipt、mutation/oracle 與 phase gates。

### Q0 事件類型盤點 — [使用者裁：產品語意；技術欄位由委員會定]

**Verdict**: 原例是「價格／量行為觸發」的 imported event，label 是另一路 outcome 語意；七類不應視為互斥 taxonomy。第一版應支援「外部已標定事件記錄」而非任何單一事件產生器。

**事件與陷阱**:

- price/volume：突破、大陽線、量能異常；陷阱是觸發觀測窗與結果窗混淆、同一 regime 連續觸發。
- technical structure：形態／指標條件；陷阱是指標 warmup、參數版本與同根收盤可見性。
- volatility/regime：波動或狀態切換；陷阱是狀態持續區間，不是獨立 instant，需 interval/cluster。
- microstructure/derivatives：funding、OI、清算；陷阱是外部資料源時點、頻率與 availability lag；本版不接資料源。
- calendar/scheduled：排程、財報、到期；陷阱是事件已知時點可早於 bar open，不能硬套 close trigger。
- external text/news：新聞／人工語意；陷阱是發布、抓取、可見與修訂時間；本版不做金融 event study，也不接新聞源。
- manual/external annotation：使用者外部標好的正／反例；陷阱是標註規則版本、檔案 digest、標註者與 selection universe 不可追溯。

**選項與後果**:

- A（建議）：只收通用 imported event manifest。好處是遵守使用者已裁定的外部標註核心；代價是沒有標籤就不能做二元 supervised。
- B：通用 imported manifest＋一兩個 price/volume generator 示範。好處是 demo 快；代價是容易把 generator 欄位誤升格核心，且新增規則 PIT／版本負擔。
- C：每一類都內建 generator。好處是產品表面完整；代價是外部資料、calendar/text provenance 與多種事件窗使契約膨脹，偏離本票。

**建議**: 選 A；B 可作後續附屬 adapter，C 不列第一版。依據：`CaseRecord` 現況只有單一 timestamp/label（`api/models/case_models.py:16-30`），候選已明列非 event study／非核心 generator（brief:15、brief:49-54）。

### Q1 決策時點 vs t₀（PIT） — [使用者裁：產品語意] + [委員會定：技術正確性]

**建議時間軸**（以使用者原例為主）：

`trigger_observation=[bar_open, bar_close]` → `decision_at=bar_close` → `feature_cutoff=bar_close`（只含已收盤值）→ `entry_at=next_bar_open`（若要表達可交易執行）→ `label_start=entry_at` → `label_end=label_start + horizon`。

若研究問題明確是 close-to-close 而非可交易回測，可將 `entry_at/label_start=bar_close`，但該語意要在 contract 明寫，不得以 `t0` 猜。合法 `t0_open` 只適用於事件在 open 前已由上一根、排程或外部發布資料觀測完成；若 trigger 需要同根 close 才知道，`t0_open` 是 look-ahead。

**選項與後果**:

- A（建議預設）`t0_close` 決策、next-open 進場：符合 close-confirmed signal，避免同根未收盤資訊；代價是放棄同根 close 的理想化執行，需記錄滑價／gap 語意。
- B `t0_close` 決策、t0-close label：適合分析 close-to-close 關聯；代價是不可直接宣稱 next-open 可交易績效。
- C `t0_open`：若觀測證明在 open 前完成則可用；若 t0 只是觸發根 open，會把同根 close 指標放進特徵並把觸發根報酬算入，結果偏樂觀。
- D `next_open` 作為決策時點：語意最接近實際下單，但前一晚 close signal 與 next-open feature cutoff 必須分開，不能把 next-open 寫成 event t0。

**現雛形判定**: `xgboost_batch_service.py:617-641` 同一 `case_ts` 取同一列；因此在 `case.timestamp` 被解釋為 trigger-root open 且該列特徵含 close-derived values 時，確實是 look-ahead 面。PIT guard 的結構性修法見 P0-01，未修改程式。

### Q2 反例定義 — [使用者裁：產品語意] + [委員會定：統計安全]

**統計差異**:

- 同觸發但未續漲：估計的是「在 trigger 已發生且 label outcome 不同時，哪些特徵區分成功／失敗」；通常更貼近策略決策，須確保負例有相同 trigger definition、相同觀測／label 窗。
- 未觸發任意 bar：估計的是「哪些特徵預測 trigger＋結果的聯合事件」；模型可能只學到有無大陽線、時間／regime base rate，不能冒充 trigger-conditional success。
- random bars：可作明標的 baseline/control，但需 matching universe、時間／symbol 分布與抽樣 seed/provenance；不應默認替代負例。

**選項與後果**:

- A（建議）：匯入必須同時帶正／反例；缺一類對二元任務 fail-closed。好處是 estimand 清楚、無平台暗中選樣；代價是使用者需準備控制組。
- B：平台依同 trigger rule 產 matched controls。好處是可降低人工標註負擔；代價是平台不得再聲稱「只匯入」，需新增 generator、規則版本、匹配窗與 selection bias 報告。
- C：平台隨機抽未觸發 bars。好處是容易建立 baseline；代價是可能只學 trigger prevalence，結果回答另一個問題。
- D（可作描述性附加）：允許 single-class event filter，但不得產 supervised AUC／binary pattern 結論，只回報樣本描述或 conditional return IC。

**建議**: A＋D；B 作後續 opt-in adapter；C 只作明標 `random_bars` 的對照分析，絕不作缺反例的隱式 fallback。證據：舊 `_select_negative_timestamps` 是正例前後分離點（`search_task_service.py:788-818`），並非同 trigger outcome control。

### Q3 去重／重疊／切分 — [委員會定：技術正確性]

**選項與後果**:

- `first`：每個連續觸發 cluster 留最早事件；樣本單位簡單但可能捨棄後續新資訊。
- `last`：留最後事件；結果偏向事件確認較晚的狀態，需文件化。
- `cluster`（建議預設）：先以 observation/label window overlap 形成 cluster，再以明確 representative 或 cluster-level label；可保留 cluster size。
- `all`：保留每個事件；必須使用 cluster weight／cluster bootstrap／HAC 或 equivalent，不能以 event count 宣稱獨立 n。

切分仍可複用 `SplitPlan`、`validate_split_integrity`、`canonical_split_plan_hash` 的 per-symbol/time identity 與既有 `purge_gap >= effective_horizon` guard（`momentum/Analysis/ic_filter_orchestrator.py:369-400`）。新寫部分是 event interval overlap、dedupe cluster、label-window aware purge、事件 manifest receipt；rows purge 僅在固定 TF 且 horizon 語意已鎖定時可作下層實作。對應 P1-03。

### Q4 標籤嚴格度 — [使用者裁：產品語意] + [委員會定：驗證邊界]

**選項與後果**:

- AND（24∧36∧48）：正例稀少，語意是整段路徑持續達標；不平衡會影響 PR-AUC、threshold 與 split 可用性。
- OR：正例較多，語意較寬，可能把短暫達標誤當持續 pattern。
- majority：中間折衷，但需明定 ties、各 horizon 權重與缺 bar 行為。
- continuous min/avg return：保留資訊，適合條件 return IC；不再是原生二元分類，不能只套 AUC。
- reference price：`t0_close` 適合 close-confirmed analytic return；`next_open` 適合可交易 entry，但 gap/slippage 需另欄。

**契約建議**: B1 接受使用者已算好的 label，但不得只留下自由 `label_rule_id`；要求 canonical definition digest、horizon list／start-end semantics、reference price semantics、source/data snapshot digest、每列 label。平台可在後續針對少數已支援的規則提供 label verifier；不能為通用外部 label 自行重算，也不能宣稱 hash 相同就證明內容正確。這使「外部標註核心」與「可重現 provenance」同時成立。

證據：現有 label horizon 解析只從 `return_N` 欄名取得 bar 數（`ic_filter_orchestrator.py:255-310`），而候選 Q4 要支援 AND/OR/majority/continuous，兩者不是同一契約層。

### Q5 共通 pattern 防運氣 — [委員會定：技術正確性]

**Estimand 分層**:

- binary event success：`y∈{0,1}`，單特徵 baseline 用 OOS AUC/PR-AUC、point-biserial 或明確命名的 binary rank association；多特徵 model 才談 OOS AUC/lift/calibration。
- conditional return IC：在已選 event sample 內，feature 與連續未來報酬的 IC；需要 return label、event scope 與 label horizon，不能把 binary `y` 直接當成同義的 future-return IC。
- rules/SHAP：只作 train-scope explanation，須有 OOS rule lift／stability；不得只看 in-sample importance。

**選項與後果**:

- A（建議 B1）：import＋PIT＋時間切分＋binary single-feature baseline＋置亂 label oracle。可證偽、能先驗證資料路徑；不交付 GBDT 規則。
- B：B1 同時做 conditional IC。好處是與 IC 主線一致；代價是必須先鎖 continuous return label／horizon，scope 變大。
- C：B1 直接做 GBDT/SHAP。好處是 demo 有 pattern；代價是模型選擇與解釋先於資料契約，容易只驗 in-sample。

置亂 label 的 oracle 預期是 chance-level binary discrimination 與 null IC；驗收應用分布／置信區間與固定 seed，不寫死未有來源的單一數字。把 label window 前移後，PIT validator 必須拒絕「label_end/feature_cutoff 先於可觀測邊界」的資料；這是資料契約 gate，不是統計結果 gate。

DSR/PBO 不直接等於 AUC/IC 的 MinBTL：現有 `min_btl_years_upper_bound` 是 Sharpe/trial/years 函式，PBO 是 returns matrix＋candidate universe 的 CSCV。只有後續將候選規則轉為可比較的 return series、登錄 candidate universe、定義 trial count 後才可接 GAP-1。數千～數萬只代表可能的 row count，不足以單獨推出 OOS 或 MinBTL。

### Q6 共用／不共用與落點 — [委員會定：技術正確性]

**可共用（保留邊界）**:

- `momentum/Analysis/event_filter.py:18-105` 的 query/timestamp mask 與 sample tier 可作低層 primitive；它不是 label-aware event assembler，不能直接承擔 dedupe/control。
- `momentum/Analysis/ic_filter_orchestrator.py:2784-2857` 的 timestamp normalization、index intersection 與 R5 A′ fallback wiring 可作參考／共用，但新事件 import 應在純函式 boundary 完成後再進 stage。
- `momentum/Analysis/ic_engine.py:80-108` 可供 continuous conditional IC；binary metrics 應有獨立函式／契約，不把 Spearman on binary label 叫成所有情境的 IC。
- `momentum/Analysis/pit_stats.py` 的 current-inclusive PIT primitives 可作已收盤特徵計算基礎；event temporal alignment receipt 仍需新寫。
- `momentum/core/contracts.py:361-411,506-530,681-710,1236-1243` 的 `SplitPlan`、split integrity、`RowMaskPlan` 與 hash 可重用；event interval/cluster 不在其現有欄位內。
- `momentum/Analysis/pattern_extractor.py:77-110` 的 train `SplitPlan` fail-closed 與 optional OOT plan 可在 B3 使用；本輪不把 ML 殼接入 B1。

**必須新寫**: `event_import_contract.json`／純 validator、canonical event/label manifest、bar boundary/as-of alignment receipt、dedupe/overlap cluster、control provenance、binary metrics＋permutation oracle、event-aware split/purge adapter、event report extension。`sample_scope.event` 至少要加 event/label manifest digest、decision/feature cutoff rule、label horizon/window、control_kind；建議 GAP-2b contract version 由 1 升 2。top-level 已有 `label_horizon` 不等於 event object 已保存完整 label semantics。

### Q7 scope／分批 — [使用者裁：產品 scope；技術 gates 由委員會定]

**選項與後果**:

- 一次完成：最早得到端到端 demo，但契約、統計、ML、持久化、前端同時變動，難以隔離 PIT／label 錯誤；不建議。
- B1（建議）：匯入契約＋PIT 對齊 receipt＋dedupe/overlap manifest＋per-symbol time split/purge＋binary permutation oracle。單獨上線價值是能回答「這批外部標註是否被正確、無洩漏地組成資料集」，即使尚無 classifier。
- B2：conditional return IC 或 binary AUC/PR-AUC＋FDR。只有在 B1 manifest／estimand 已鎖定後才接 stage；兩種 metric 應可各自 unavailable，而非互換。
- B3：GBDT/SHAP、train/OOS rule extraction、cross-symbol/OOS stability；接 `SplitPlan`，再做 candidate ledger 與 DSR/PBO bridge。
- B4：survivor/report persistence、API schema、前端占位殼。只能在 report contract version 與 fallback/degraded semantics 鎖定後做。

**與現雛形的關係**: `case.py`／`CaseRecord` 應視為 legacy adapter 或 deprecated import path，不宜把新事件語意塞回 `positive_case`；`xgboost_batch_service` 維持既有 ML 殼，B1 只輸出純函式產生的 strict dataset/manifest。若直接「沿用 route、換 schema」而沒有 adapter receipt，舊路徑的 exact timestamp、NaN warning skip、legacy negative sampling 會把新契約降回舊語意。證據：brief:23-27、brief:49-54；xgb:617-655。

### Q8 能否進 SPEC — [委員會定：技術 gate；產品選項仍需使用者裁]

**Verdict**: 足以進「decision-gated SPEC 起草」，不足以進 Frozen SPEC／開工。偵察已把共用原語、現況差距與分批切開，但下列是 BLOCKING：

1. Q1 要選 close-to-close 或 next-open／pre-open 語意，並由契約承載 observation/decision/feature/label times。
2. Q2 要決定缺反例時 fail、opt-in generator 或只做 descriptive；不能同時宣稱平台只匯入又默默生成 controls。
3. Q4 要鎖 label definition／reference price／horizon provenance；只有自由 `label_rule_id` 不足。
4. Q5 要先選 B1 estimand（建議 binary supervised baseline）並把 conditional IC、GBDT、DSR/PBO 延後至各自 gate。
5. Kline 可能變更時，alignment contract 必須綁 symbol、timeframe、bar boundary/timezone/calendar、source snapshot digest 與實際 matched bar receipt，不能只 hash t0 timestamps。
6. OOS／最小樣本／MinBTL 不可由「數千～數萬」直接推導；需在 SPEC 寫可證偽的 data sufficiency 與 unavailable/degraded 狀態，數值門檻若無來源先列待裁／待研究。

非阻塞事項：外部新聞／衍生品資料源、前端樣式、ML 超參與金融 CAR/AAR 均依 brief 排除或 blocked-by 既有層，不影響本輪進入 decision-gated SPEC。

### 未查清單（不作阻塞理由）

- 未讀取或修改任何尚不存在的 GAP-3 SPEC/TODO/PLAN；因此正式 §G golden、mutation receipt 與 phase task 存活期限待後續 SPEC。
- 未跑全套 pytest、npm build、governance gate；本票 read-only consult 且 brief 禁改碼／測試，這些命令不適合作為本輪語意證據。
- 未接觸外部資料源、前端樣式、容量／效能與 pooled/panel IC；均在 brief 不受理範圍。

## GROK-R1-P0-01

**斷言**: 現雛形以 `timestamp_sec == case_ts` 取**同一根**特徵列、且缺 bar／NaN 時 `warning` 後 `continue`；在使用者原例（t₀＝觸發根 **open**、特徵含收盤才知的指標）下，這條路徑把觸發根 close 資訊餵進特徵，屬 look-ahead 面，且樣本流失靜默。

**碼證**: 精確相等匹配 `xgboost_batch_service.py:617-622`；同根取值 `:626-628`（`row_idx`→`shared_feature_names`）；NaN 跳過 `:649-652`；`CaseRecord` 無 `decision_time`（`case_models.py:16-30`）。使用者原例見 registry「GAP-3 開發前討論題」與 brief L18–19（12h 漲≥5% 定該根 **open** 為 t₀）。
RECHECK: 讀 `:599-652`；確認無 as-of／容差／`decision_time` 分支。

**來源摘要**: api/services/xgboost_batch_service.py#0d11f275806e

[BLOCKING] 信心度=High。SPEC 必須：(a) 契約必填 `decision_time∈{t0_close,t0_open,next_open}`（建議產品預設 `t0_close`）；(b) 特徵列＝決策時點**已收盤**的最後一列；(c) 對齊失敗／越界／NaN → loud 拒絕或回傳不可靜默丟棄的失敗清單（對照設計候選 1／2）。禁止把現 `:618/:641/:651` 行為寫成「相容預設」。

---

## GROK-R1-P0-02

**斷言**: 以現有 `CaseRecord`／`/case/import` schema 直接當 GAP-3 匯入契約會系統性遺失 PIT／label 語意；本票必須新建契約（SoT JSON＋純函式 validator），不得「在 CaseRecord 上加選填欄」假裝完備。

**碼證**: `CaseRecord` 必填僅五欄＋可選來源（`case_models.py:16-30`）；路由 `api/routes/case.py:34-70` 接 CSV／Excel 導入；無 `label_horizon`／`label_rule_id`／`decision_time`／`control_kind`。倖存者端 event 物件同樣無這些鍵（`ic_survivor_contract.json` `event_definition_keys`）。
RECHECK: grep CaseRecord 欄位；對照設計候選 1 必填清單。

**來源摘要**: api/models/case_models.py#61f72fca0397

[BLOCKING] 信心度=High。建議 SoT＝`momentum/Analysis/contracts/event_import_contract.json`＋`event_import.py` 純函式；API 可沿用 `case.py` 路徑但 **schema 換新契約**（禁改 `xgboost_batch_service` 訓練殼）。舊 CSV 欄位映射＝明確 migration／拒絕，非 silent coerce。

---

## GROK-R1-P1-01

**斷言**: 現雛形反例＝正例時間 ± `separation_days` 的候選時點（必要時再貼近 K 線），**不是**「同觸發條件未達續漲標籤」的 matched control；若 SPEC 默認复用此路徑且不強制揭露 `control_kind`，分類器可學「有無觸發」廢答案。

**碼證**: `_select_negative_timestamps` `:788-818` 只做時間分離；`_generate_negative_cases` `:682-774` 在 before/after 取 K 線列並標 `market_phase="反例"`，未重跑使用者觸發規則。`EventFilter` 亦無正反例概念（F5）。
RECHECK: 讀 `:645-818`；確認無 trigger-rule 重放。

**來源摘要**: api/services/search_task_service.py#c8357d2a7c12

[MAJOR] 信心度=High。表態：契約允許 (a) 使用者提供反例 (b) 同觸發未達標對照（需觸發規則＝**可選**產生器附屬）(c) 隨機／時間分離 bar（強制 `control_kind=random_bars|time_separated`＋報告揭露）。**B1 預設＝(a) fail-closed**：匯入若全為正例且未選 (b)/(c) ⇒ 拒絕。禁止默認走現雛形而不標 control_kind。

---

## GROK-R1-P1-02

**斷言**: GAP-2b 落地的 `sample_scope.event` 只攜事件**身份**雜湊（definition／timestamps／mode／計數），不足以承載 GAP-3 的 label 語意、決策時點、horizon、對照組種類；擴欄必然觸及倖存者契約版本與 `additional_properties:false`。

**碼證**: `event_definition_keys` 僅五鍵（json:256-275）；`sample_scope_keys`＝kind/event/n_samples_*/degraded（:225-254）；組裝規則 `survivor_contract.py:407`／`:471`；消費義務文案要求 event 倖存者只在事件樣本訓練（json `_doc` L3）。A′ fallback 保留 timestamps（orch `:1142-1152`）解決的是**遮罩身份**，不是 label 語意。
RECHECK: 列 `event_definition_keys`；確認無 decision_time／label_horizon／control_kind。

**來源摘要**: momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073

[MAJOR] 信心度=High。建議兩層：(1) **匯入／樣本組裝**契約獨立 SoT（設計候選 1）；(2) 寫入倖存者時 `sample_scope.event` **擴** `decision_time`／`label_horizon`／`label_rule_hash`／`control_kind`（或 `event_analysis` 平行物件），`schema_version`／契約 `version` 升版＋migration 測試。禁止在 `additional_properties:false` 下「先寫進 payload 再補契約」。

---

## GROK-R1-P1-03

**斷言**: 「事件子樣本內特徵 vs 未來報酬的條件 IC」與「正／反例二元 label 上的特徵 AUC／rank-IC」回答不同科學問題；設計候選 5 若未釘 B1 最小可交付，實作代理會把兩者糊成單一 `event_ic` 輸出並誤接 stage4。

**碼證**: 序列型 stage3 只遮罩列（`event_filter.py:55-105`；orch `_stage3_event_filter` `:2776+`），統計仍是對未來報酬的 IC（主線 `ic_engine`）；雛形 ML 路徑 label＝`case.positive_case`（`xgboost_batch_service.py:655`）走分類 AUC。兩者輸入標籤不同（連續 forward return vs binary）。
RECHECK: 對照 stage4 輸入是否吃 binary label（否）。

**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c

[MAJOR] 信心度=High。B1 MVP＝匯入契約＋PIT 對齊＋去重／重疊標記＋`SplitPlan` 相容切分原語＋oracle（置亂 label⇒AUC≈0.5／IC≈0；label 窗前移⇒守衛拒絕）。B2 再接：(i) `statistic_kind=conditional_ic` 复用 stage4＋`sample_scope.kind=event`（A′）；(ii) `statistic_kind=binary_discrimination`（AUC／point-biserial＋BH-FDR）。B3＝GBDT／`pattern_extractor`＋GAP-1 DSR/PBO。平台**兩者都做**，但報告必須分節、禁單一數字混報。

---

## GROK-R1-P1-04

**斷言**: 時間戳單位在雛形（Unix **秒**）與倖存者事件序列化契約（epoch **ms** UTC）不一致；匯入契約若寫死 ms 卻接舊 CSV 秒值，會造成精確相等對齊全面失敗或錯位一個 1000× 因子。

**碼證**: `CaseRecord.timestamp` 描述「Unix timestamp」、xgboost 路徑與 `timestamp_sec` 比（`:584-618`）；倖存者 `_doc`：「timestamps → int64 epoch **ms** UTC → sorted unique → sha256」（`ic_survivor_contract.json:3`）。設計候選 1 寫 `t0(epoch ms UTC)`。
RECHECK: 對同一事件用 sec 與 ms 各算 `timestamps_hash` 應不同；validator 須單位閘。

**來源摘要**: momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073

[MAJOR] 信心度=High。SPEC：匯入契約欄位固定 **epoch ms UTC**；讀舊秒資料須顯式 `timestamp_unit` 或前置轉換器；對齊函式輸入／receipt 一律 ms；與 bar 邊界正規化同一純函式出口。Fail-closed：值落在「像秒」的量級卻宣告 ms（或相反）⇒ 拒絕並給理由。

---

## GROK-R1-P2-01

**斷言**: brief／registry 的事件類型①–⑦**不是**互斥分類，且除需外部源的④⑥外，標定所需契約欄位可化約為同一組通用欄；第一版「通用匯入＋①類可選示範產生器」成立，但不可把⑦「人工標定」寫成與①並列的互斥類（⑦是來源通道，①–⑥是語意類）。

**碼證**: registry Q0 粗盤點（`docs/IC_QUANT_GAP_REGISTRY.md:22-25`）；使用者原例屬①；成熟度地圖／不受理範圍排除外部源接入本票。雛形已有人工 CSV 匯入通道（`case.py:34-70`）＝⑦通道已存在但 schema 不足（P0-02）。
RECHECK: 列「不支援」＝④⑥本票不接資料源；②③⑤以匯入契約支援、不內建辨識器。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#333ed10fd833

[MINOR] 信心度=High。建議契約：`event_type_tag` 選填自由字串＋可選枚舉提示；必填仍是 `symbol/timeframe/t0/label/decision_time/label_horizon/label_rule_id`。產生器＝附屬、非核心（對齊使用者裁定）。

---

## GROK-R1-P2-02

**斷言**: brief 前提 F 條寫「非測試碼 sample_scope 只出現在 survivor_contract＋json」略窄；前端占位 `pendingFeatures.ts` 亦提及，不影響後端契約結論，但 reconcile 勿把該 grep 當「全產品面 0 消費者文案」。

**碼證**: 本輪 `grep -rn sample_scope momentum api frontend/src --include='*.py' --include='*.json' --include='*.ts' | grep -v test` → survivor 契約／組裝＋`frontend/src/lib/pendingFeatures.ts:54`。
RECHECK: 重跑同指令。

**來源摘要**: frontend/src/lib/pendingFeatures.ts#f2a52d8c6c57

[MINOR] 信心度=High。無修碼需求；僅校正前提表述。

---

