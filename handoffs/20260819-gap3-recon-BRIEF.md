# GAP-3 偵察：事件型分析（事件錨定之監督式 pattern 發現）開發前事件語意 consult

brief-kind: consult

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
本輪輪次=R1。**四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`，勿寫 `#sha256:` 前綴）。**

## ⚠️ 前置說明（勿誤 block）
- 本任務是**偵察＋語意討論（read-only）**，不是 code review 某個 diff。**禁改碼、禁寫測試、禁寫 SPEC**；只產你自己的 consult 報告檔。
- `handoffs/reconcile/*/synth.md`、`docs/IC_QUANT_GAP_REGISTRY.md` 是**無戳記診斷/登記檔**，非 gating 檔；勿 STAMP-BLOCK。
- 每一條結論都要附**可獨立重現的證據**（file:line、grep 指令與輸出、文獻出處）。無證據的斷言標 `UNVERIFIED`。
- 本 brief「設計候選」節是**候選**、非裁決；歡迎逐條推翻，但推翻須附碼證或文獻。
- **使用者已裁定（2026-08-18，不受理重議）**：GAP-3 語意＝使用者**於外部自行標好**正／反例（標的＋t₀＋標籤）匯入 ⇒ 平台核心＝**事件匯入契約＋PIT 對齊特徵＋去重／切分＋條件 IC／ML**，**非**金融 event study（CAR/AAR）、**非**事件產生器；事件類型多樣、契約通用不為單一事件寫死；原「case-control」降為反例／對照組設計之一。GAP-3 設計須含 ICHC R5 裁決之 A′ 語意（fallback 保留 `event_timestamps`；收斂檔 `handoffs/reconcile/20260817-ichc-x-consult-r5/synth.md`）。
- **本輪目的**：收斂後主委要把 Q0＋Q1–Q5 用白話整理成選項給使用者裁（AskUserQuestion 阻塞），裁完才寫 SPEC。因此每題**除了你的建議，還要給出「可供使用者選的選項清單＋各選項後果」**，並標註該題是 **[使用者裁：產品語意]** 還是 **[委員會定：技術正確性，不該丟給使用者]**（使用者無法做技術決策；技術題由三家＋主委在 reconcile 定案）。

## 使用者原意（逐字義，來自 registry「GAP-3 開發前討論題」）
例＝12h K 漲≥5% 定該根 open 為 t₀；t₀ 後 24／36／48h 之 close 皆比 t₀ close 高≥3% ⇒ 正例，否則反例；特徵＝t₀ 往前 x 根 1h／4h 指標；目標＝在數千～數萬個 t₀ 中找正例共通 pattern 當策略。**這只是其中一種事件**；正反例將由使用者自外部檔案標好餵入。

## 審查標的（今天的碼，不是文件的轉述）
**現有雛形（ML 孤島；本票＝按 IC 主線標準重建此線）**：
- 匯入契約雛形：`api/models/case_models.py:16-50` `CaseRecord`（`case_id/symbol/timeframe/timestamp(sec)/positive_case∈{0,1}`＋`source_file/import_time`）；CSV/Excel 上傳路由 `api/routes/case.py:34-70`；`CaseImportRequest/Response` :62-100
- 案例→特徵對齊：`api/services/xgboost_batch_service.py:560-660`（`timestamp_sec == case_ts` **精確相等**匹配 :618；找不到 K 線／特徵含 NaN 皆 `warning` 後 **靜默跳過** :621／:651；特徵取 t₀ **同一根** bar 的列 :641；label＝`case.positive_case` :655）；訓練入口 :720-726（`time_series_split, case_timestamps, purge_gap, embargo_pct` 傳 `train_model`）
- 反例產生雛形：`api/services/search_task_service.py:645-830`（`_generate_negative_cases`／`_select_negative_timestamps` :788：正例 ± `separation_days` 的「未觸發」點）；正例搜尋 `api/routes/two_stage_search.py`、`api/routes/case_search.py`
- 規則抽取：`momentum/Analysis/pattern_extractor.py:77-110`（`split: SplitPlan` fail-closed 必填；`oot_split` 可選）
- 切分原語：`momentum/core/contracts.py:362-400`（`SplitPlan`、`CrossSymbolLeakageError`、`SplitPairLeakageError`、`validate_split_integrity` :506、`canonical_split_plan_hash` :1236）；`momentum/Analysis/model_validation/{combinatorial_purged_cv,walk_forward_validator,oot_validator,cv_validator}.py`（ML 孤島，未接 IC 主線）
**IC 主線事件樣本路徑（序列型現況，事件型要共用的部分）**：
- `momentum/Analysis/event_filter.py`（148 行；`IEventFilter` :18、`apply_filter` :55 query／timestamps 兩模式、`check_sample_size` :128 tier）；orchestrator `_stage3_event_filter` `momentum/Analysis/ic_filter_orchestrator.py:2776-2962`；`analyze(..., event_timestamps=)` keyword-only :887-895；fallback 保留 event_timestamps :1142-1152（R5 A′）
- rows purge／horizon 守衛：`ic_filter_orchestrator.py:156-380`（`purge_gap < effective_horizon` 拒絕 :365-372）；`RowMaskPlan.source∈{split,event,feature_filter,full}` `contracts.py:682`
- 倖存者契約（GAP-2b 已落地）：`momentum/Analysis/contracts/ic_survivor_contract.json`（`sample_scope.kind∈{full,event}` :59-62；event object＝`mode/definition_hash/timestamps_hash`）；`momentum/Analysis/survivor_contract.py:278-286`／`:407`（kind 判定規則）
- 未來報酬／label：`momentum/Analysis/ic_engine.py`（rolling IC :274）、`pit_stats.py`；GAP-1 策略層 DSR/PBO：`momentum/Analysis/strategy_validation/`
- 測試紀律：`docs/TEST_DESIGN_CHARTER.md`（§F F-IC-1..9；§G 章程模板）；mutation 慣例 `scripts/mutation_probe_check.sh`、`scripts/gap2_b1_mutation_probe.sh`
- 成熟度地圖（使用者 2026-08-17 定）：只 Feature Factory 完整／IC 進行中／Kline＋事件可能變更／其餘（含回測·Optuna·ML）當不完整；設計須**契約先行＋純函式核心，禁改殼**。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: 現雛形匯入 schema＝`CaseRecord`（`case_models.py:16-50`），**無** label 定義／horizon／決策時點／來源 provenance 欄；timestamp 為 Unix 秒，對齊採精確相等（`xgboost_batch_service.py:618`），無 as-of／容差／TF 邊界正規化（Claude 實讀 2026-08-19）
fact-verified: 現雛形特徵取 t₀ 同根 bar 之列（:641），且未對「t₀ 定義為該根 open 還是 close」做任何區分 ⇒ 若使用者 t₀＝觸發根 **open**，同根收盤才算得出的指標值會進特徵（look-ahead 面）
fact-verified: 現雛形反例＝正例 ± `separation_days` 的未觸發時點（`search_task_service.py:788-820`），**非**「同觸發但未續漲」對照組
fact-verified: `sample_scope` 於非測試碼只出現在 `survivor_contract.py`＋`ic_survivor_contract.json`（`grep -rn "sample_scope" momentum api frontend/src --include='*.py' --include='*.json' --include='*.ts' | grep -v test`，Claude 實跑 2026-08-19）；`kind=event` 之 event object 只攜 `definition_hash/timestamps_hash`，**無** label 語意／horizon／決策時點
fact-verified: IC 主線 `_stage3_event_filter` 只做「子樣本遮罩」（事件時點的列）＋ tier 判定，**沒有**正／反例標籤概念、沒有事件去重／重疊處理（`event_filter.py` 全檔實讀）
fact-verified: `pattern_extractor.extract_decision_rules` 已 fail-closed 要求 `SplitPlan` 且 `split_label=='train'`（:77-110）；`SplitPlan` 有 per-symbol／時間戳連續性／pair 洩漏守衛（`contracts.py:390-400, 506`）
assumed: 使用者原例屬「價格／量行為觸發」類；事件類型可分為 ①價格／量行為觸發 ②技術結構形態 ③波動／regime 切換 ④微結構／衍生品（資金費率、OI、清算；需外部源）⑤日曆／排程 ⑥外部新聞 ⑦人工標定匯入 ← 請攻：分類是否完備／互斥、各類在**匯入契約**上需要哪些不同欄位（還是全部可化約成 `symbol+t₀+label+horizon_def+meta`）
assumed: 匯入契約只需通用欄位（`symbol, t0, label, label_definition_id/hash, decision_time_rule, horizon, source, meta`），事件產生器（規則型 ①類一兩個示範）為可選附屬、非核心 ← 請攻：平台不產事件只匯入，「反例」若使用者沒標怎麼辦——契約該強制使用者同時提供反例？還是平台提供對照組產生器？
assumed: PIT 正確的決策時點＝t₀ 觸發根 **close**（信號確認時），特徵截止＝t₀ 含該根收盤值、label 起算＝t₀ close（或下一根 open，含滑價語意）；以 open 為 t₀ 會把觸發根報酬算進績效 ← 請攻：是否存在合法的「t₀ open 決策」語意（例：事件由前一根定義）；契約該如何顯式表達決策時點而非隱含
assumed: 共用面＝資料載入／特徵計算／未來報酬／PIT 守衛／IC 函式／bootstrap；不共用＝樣本組裝（事件清單＋反例）、主統計量（條件 IC？分類 AUC？lift？）、切分／去重、報告契約、前端 ← 請攻：主統計量到底是什麼——正例 vs 反例之「特徵分布差異」（AUC／KS／IC on binary label）還是「事件子樣本內特徵 vs 未來報酬 IC」；兩者語意不同，平台要不要都做

## 設計候選（非裁決；請逐條攻）
1. **匯入契約** `momentum/Analysis/contracts/event_import_contract.json`（單一真相源）＋ `momentum/Analysis/event_import.py` 純函式 validator：必填 `symbol/timeframe/t0(epoch ms UTC)/label∈{1,0}`；必填語意欄 `decision_time∈{t0_close,t0_open,next_open}`、`label_horizon`（bars 或 seconds）、`label_rule_id`（自由字串＋hash，平台不解讀）；選填 `event_type_tag`、`source`、`meta`；fail-closed：缺欄／t₀ 對不上 bar 邊界／symbol 無資料 ⇒ 拒絕或 loud 列表（**不准靜默跳過**，對照現雛形 :621/:651）。
2. **PIT 對齊純函式** `align_events_to_features(events, features_df, decision_time)`：t₀ 正規化至 TF 邊界，特徵列＝決策時點當時**已收盤**的最後一列；輸出對齊 receipt（每事件用到哪根 bar）。
3. **去重／重疊** `dedupe_events(events, min_gap, policy∈{first,last,all,cluster})`＋標籤窗重疊標記；切分＝per-symbol 時間切＋purge/embargo ≥ label_horizon（複用 `SplitPlan`／rows purge 守衛，禁 positional index）。
4. **反例策略**：契約允許 (a) 使用者提供反例 (b) 平台依「同觸發條件未達標」產對照（需使用者提供觸發規則＝事件產生器）(c) 平台隨機未觸發 bar（明標 `control=random_bars`，報告強制揭露）。三者在報告 `sample_scope.event.control_kind` 顯式標示。
5. **主統計量**：(i) 事件子樣本條件 IC（複用 stage4，`sample_scope.kind=event`）；(ii) 正反例二元 label 之特徵 AUC／rank-IC（pointbiserial/Spearman on binary）＋ BH-FDR；(iii) GBDT＋SHAP／規則抽取（既有 `pattern_extractor`，走 `SplitPlan`）；規則挑選接 GAP-1 DSR/PBO。請表態哪個是 B1 最小可交付。
6. **落點**：新純函式模組於 `momentum/Analysis/event_study/`（名稱待定，避免與金融 event study 混淆）或擴充 `event_filter.py`；API 層沿用 `case.py` 路由但 schema 換新契約（**禁改殼**：ML 訓練殼 `xgboost_batch_service` 不動，只在輸入面接契約）。

## 必答（逐條 verdict，附證據；每題標 [使用者裁] 或 [委員會定]，並給選項＋後果）
**Q0 事件類型盤點**：有哪些事件類型、各自如何定義／標定／陷阱、平台契約要通用到什麼程度、使用者原例屬哪一類；第一版契約應支援到哪一類（附「不支援的明列」）。
**Q1 決策時點 vs t₀（PIT）**：給出正確的 PIT 時間軸（觸發觀測時點／決策時點／特徵截止／label 起算／label 結束），選項（t₀ open／t₀ close／next open）各自的洩漏面與績效偏誤；契約如何顯式攜帶；現雛形 :641 是否為 look-ahead。
**Q2 反例定義**：同觸發未續漲（對照組）vs 未觸發任意 bar 的統計後果（模型學「有無觸發」廢答案／類別不平衡／base rate）；使用者沒標反例時平台該拒絕、產生、還是兩者；對照組產生是否需要觸發規則（⇒ 事件產生器不可避免？）。
**Q3 去重／重疊／切分**：連續觸發算幾個事件（first／cluster／all＋權重）；標籤窗重疊 ⇒ 樣本不獨立，對 IC／AUC／顯著性的影響與修正（HAC／cluster bootstrap／去重）；切分＝per-symbol 時間切＋purge/embargo 事件窗；哪些複用 `SplitPlan`／rows purge 守衛、哪些要新寫。
**Q4 標籤嚴格度**：24∧36∧48 皆≥3%（AND）vs 任一（OR）vs 多數 vs 連續型（min/avg 報酬）；3% 相對 t₀ close 或進場價；不平衡比例的下游影響；契約是否應只收「使用者已算好的 label」而把規則留在 `label_rule_id` 之外（平台不重算）——還是提供「label 重算器」驗使用者標籤一致性。
**Q5 共通 pattern 防運氣**：條件子樣本 IC（`event_filter` 共用）＋GBDT/SHAP／規則抽取＋OOS／跨標的／FDR；規則挑選須接 GAP-1 DSR/PBO（`strategy_validation/`）；數千～數萬事件下的 MinBTL 量級；最小可證偽 oracle（置亂 label ⇒ AUC≈0.5／IC≈0；把 label 窗前移製造洩漏 ⇒ 必須被守衛攔下）。
**Q6 共用／不共用面與落點**：逐項列出與序列型 IC 主線共用的函式（file:line）與必須新寫的；`sample_scope.event` 契約是否要擴欄（label 語意／horizon／決策時點／control_kind）及對 GAP-2b 契約 `version` 的影響。
**Q7 scope／分批**：一次做完 vs 分批（例：B1 匯入契約＋PIT 對齊＋去重純函式＋oracle；B2 條件 IC／二元 AUC＋FDR 接 stage；B3 切分＋規則抽取接 `SplitPlan`＋DSR/PBO；B4 報告契約＋持久化＋前端占位殼）；哪批單獨上線就有價值；與現雛形（case 路由／xgboost_batch）的關係＝**重建／包裝／棄用**各自後果。
**Q8 能否進 SPEC**：偵察是否足以進 SPEC 起草？有無 **BLOCKING**（例：Kline 層可能變更 ⇒ 對齊契約該綁什麼；事件樣本量不足以支撐 OOS）？

## Time-box 與範圍紀律
- 優先序＝Q1（PIT）＞ Q2（反例）＞ Q3（去重／切分）＞ Q0（盤點）＞ Q4 ＞ Q5 ＞ Q6 ＞ Q7 ＞ Q8。查不完的具名列「未查」清單，**不當阻塞**。
- **不受理範圍**：治理機制與流程；前端樣式；ML 模型選型／超參（橋本體 blocked-by ML 層，G2-R1）；金融 event study（CAR/AAR）方法論；外部資料源接入（資金費率／OI／新聞；登記為待資料源即可）；Pooled/Panel IC（registry #4）；容量／效能（#5／#6）；「應該先做別的票」排序意見。
- 提醒：本票**不是**接 ML 訓練、不是改 `xgboost_batch_service` 殼；是把「事件匯入→PIT 對齊→樣本組裝→條件 IC／二元統計→倖存者契約」按 IC 主線標準重建成純函式核心＋契約。

## 產出
canonical 四欄 findings + 必答 Q0–Q8 逐條 verdict（每題：[使用者裁]/[委員會定]＋選項清單＋各選項後果＋你的建議＋證據）+ **Verdict**（可進 SPEC／BLOCKING 清單／scope 建議）。**禁改碼**（只產 consult 檔）。收尾清 /tmp workdir（保留 claude-501）。
