# GAP-3 偵察 consult / grok | task-id=20260819-GAP3-X-CONSULT-R1

brief-kind=consult；家族=grok；輪次=R1；禁改碼；只產本檔。

## Verdict：可進 SPEC 起草（附必須寫進 SPEC 的前置裁決；無全域停工 BLOCKING）

偵察足以讓主委起草 SPEC。使用者已裁定的產品語意（外部標好正／反例匯入；非 CAR/AAR event study；非事件產生器為核心；契約通用；R5 A′ 保留 `event_timestamps`）本輪**不重議**。

必須寫進 SPEC 正文（不可當已裁決事實滑過）的前置裁決：

1. **`decision_time` 顯式枚舉**；現雛形同根 bar 特徵在使用者原例（t₀＝觸發根 open）下是 look-ahead 面（見 `GROK-R1-P0-01`）。
2. **對齊失敗／NaN＝loud 列表或拒絕**；禁复用雛形靜默 `continue`（見同條）。
3. **B1 主統計量**：先交付匯入契約＋PIT 對齊＋去重／切分原語＋可證偽 oracle；條件 IC 與二元 AUC **語意不同、不可互換**，並列為 B2 兩模式並在報告顯式標 `statistic_kind`（見 `GROK-R1-P1-03`）。
4. **`sample_scope.event` 擴欄**（或平行 `event_import_contract`）須含 `decision_time`／`label_horizon`／`label_rule_hash`／`control_kind`，並處理倖存者契約 `version` 升版（見 `GROK-R1-P1-02`）。
5. **反例策略預設**：禁把時間分離「未觸發 bar」當默認對照而不揭露（見 `GROK-R1-P1-01`）。

**非 BLOCKING**：前端占位可延後；ML 訓練殼 `xgboost_batch_service` 本票不改（禁改殼）；外部源（資金費率／OI／新聞）登記待資料源即可。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| # | 前提（來源） | 判定 | 證據摘要 |
|---|---|---|---|
| F1 | `CaseRecord` 無 label 定義／horizon／決策時點／provenance；timestamp＝Unix 秒；對齊精確相等 | **fact 成立** | `case_models.py:16-30` 僅 `case_id/symbol/timeframe/timestamp/positive_case`＋可選 `source_file/import_time`；`xgboost_batch_service.py:618` `timestamp_sec == case_ts` |
| F2 | 特徵取 t₀ 同根 bar；未區分 open／close ⇒ t₀＝open 時同根收盤才知的指標進特徵 | **fact 成立** | `:626-628`／序列路徑仍以同 `row_idx` 為錨；無 `decision_time` 參數 |
| F3 | 反例＝正例 ± `separation_days` 的時點，非「同觸發未續漲」 | **fact 成立** | `search_task_service.py:788-818` `_select_negative_timestamps`；`:645-786` `_generate_negative_cases` 取分離候選＋K 線 |
| F4 | 非測試碼 `sample_scope` 主要在 survivor 契約／組裝；`kind=event` 物件無 label／horizon／決策時點 | **fact 大致成立；brief 略窄** | 非測試命中＝`survivor_contract.py`＋`ic_survivor_contract.json`＋前端占位文案 `pendingFeatures.ts:54`；`event_definition_keys`＝`definition_hash/timestamps_hash/mode/n_events/n_timestamps_requested`（json:256-275） |
| F5 | `_stage3_event_filter`／`EventFilter` 只做子樣本遮罩＋tier，無正反例／去重 | **fact 成立** | `event_filter.py` 全檔；對 `positive|label|negative|dedup|overlap` → **0 hits** |
| F6 | `pattern_extractor` fail-closed 要 `SplitPlan` 且 `split_label=='train'`；`SplitPlan` 有 per-symbol／pair 洩漏守衛 | **fact 成立** | `pattern_extractor.py:107-118`；`contracts.py:362-399,506+` |
| F7 | ICHC R5 定案 A′：fallback 重跑保留 `event_timestamps` | **fact 成立（已落碼）** | `reconcile/.../synth.md` E1；orch `:1142-1152` 註解＋透傳 |
| A1 | 事件類型①–⑦完備／互斥；匯入可化約通用欄 | **部分成立** | 不互斥（①∩②常見）；多數可化約；④⑥需外部源＋provenance，非新必填欄（見 Q0／P2-01） |
| A2 | 平台不產事件；反例契約選項 | **成立但欠預設政策** | 使用者已裁「非產生器核心」；未標反例時須 fail-closed 或顯式 `control_kind`（見 Q2） |
| A3 | PIT 正確＝t₀ close 決策；open 為 t₀ 會把觸發根報酬算進績效 | **方向正確；「唯一正確」過強** | 合法「前一根定義、本根 open 決策」存在；契約必須顯式枚舉而非隱含 close（見 Q1／P0-01） |
| A4 | 共用／不共用切面；主統計量二選一 | **共用切面大致成立；主統計量不可二選一糊弄** | 條件 IC ≠ 二元 AUC；B1 先契約／PIT／oracle（見 Q5／Q6／P1-03） |

---

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

## 設計候選逐條攻（非裁決）

| # | 候選 | 表態 | 理由 |
|---|---|---|---|
| 1 | `event_import_contract.json`＋validator；禁靜默跳過 | **採納（強化）** | 對齊 P0-01／P0-02；單位釘 ms（P1-04） |
| 2 | `align_events_to_features(..., decision_time)`＋receipt | **採納** | PIT 核心；須含 TF 邊界正規化 |
| 3 | `dedupe_events`＋標籤窗重疊標記；切分复用 SplitPlan／purge | **採納** | purge≥label_horizon 已有 orch `:365-372`；事件窗尚須新寫重疊圖 |
| 4 | 反例 (a)(b)(c)＋`control_kind` | **採納；B1 預設 (a)** | P1-01；(b) 觸發規則＝可選附屬產生器 |
| 5 | 主統計量 (i)(ii)(iii) | **採納分批；B1≠統計交付** | P1-03 |
| 6 | 新模組 `event_study/` 名待定；禁改 xgboost 殼 | **採納方向；命名避 event study** | 建議 `momentum/Analysis/event_samples/` 或 `event_import/`；擴 `event_filter.py` 只宜遮罩、不宜塞匯入／去重 |

---

## 必答 Q0–Q8

### Q0 事件類型盤點
**標籤**: 支援範圍＝**[使用者裁：產品語意]**；契約通用化＝**[委員會定：技術正確性]**

**選項（給使用者）**:
- **A. V1 只收通用匯入**（任何已標好的正／反例；不內建產生器）→ 最快落地；使用者自負標籤；無①示範規則。
- **B. 通用匯入＋①類一兩個規則示範產生器**（可選）→ 降低冷啟動；但產生器非核心，須防「平台會自動找事件」誤解。
- **C. V1 再加②③形態／regime 內建偵測**→ 範圍膨脹、易與特徵工程重疊；本票不建議。
- **D. 含④⑥外部源接入**→ blocked-by 資料源；本票不受理。

**後果／建議**: 使用者原例∈①。契約通用到「`symbol+t0+label+decision_time+label_horizon+label_rule_id/hash+source+meta`」即可覆蓋①②③⑤⑦；④⑥只差 `source`／外部 id 進 meta。**建議 B**（與 registry 粗建議同向）。不支援明列：④⑥資料源、金融 CAR/AAR、即時新聞 NLP。

**證據**: registry Q0；`CaseRecord` 現況；使用者 8/18 裁定。

---

### Q1 決策時點 vs t₀（PIT）
**標籤**: 正確時間軸與洩漏面＝**[委員會定]**；產品預設選哪一個＝**[使用者裁：產品語意]**

**正確時間軸（委員會定）**:
1. **觸發觀測時點**：規則所需最後一根資訊就緒之時（例：該根 close 後才知「漲≥5%」）。
2. **決策時點** `decision_time`：允許下單／形成特徵截止的時刻。
3. **特徵截止**：≤ 決策時點已收盤的最後一列（含當根 iff 決策≥該根 close）。
4. **label 起算**：通常＝決策時點對應價（t₀ close 或 next open，滑價語意）。
5. **label 結束**：起算＋`label_horizon`。

**選項（給使用者，預設建議）**:
- **A. `t0_close`（建議預設）** → 特徵可含觸發根收盤指標；進場最早收盤／下一根；觸發根 open→close 報酬**不**算策略績效若 label 從 close 起。洩漏面最小（對「收盤確認」類）。
- **B. `t0_open`** → 僅當事件由**更早資訊**定義（前一根已確認）才合法；若觸發用當根 close 定義卻決策＝open ⇒ **look-ahead**（現雛形風險面）。
- **C. `next_open`** → 顯式隔根進場／滑價；特徵截止＝t₀ close；最保守執行語意。

**現雛形 `:641`**: 在使用者原例（t₀＝open＋當根觸發）下 **是 look-ahead 面**（P0-01）。契約必須顯式攜帶 `decision_time`，禁止隱含。

---

### Q2 反例定義
**標籤**: 統計後果／廢答案機制＝**[委員會定]**；未標反例時產品行為＝**[使用者裁]**

**選項（給使用者）**:
- **A. 強制使用者同時提供正＋反例**（建議 B1）→ 契約簡單；無觸發規則依賴；使用者負擔高。
- **B. 允許缺反例＋平台「同觸發未達標」對照** → 需觸發規則（可選產生器）；對照組因果清晰；實作較重。
- **C. 允許缺反例＋隨機／時間分離 bar** → 易做；**廢答案**（學有無觸發）＋基率扭曲；必須 loud `control_kind`＋報告警告。
- **D. A 為預設，B／C 顯式 opt-in** → 兼顧。

**委員會定後果**: 未觸發任意 bar 的 negative 讓模型先分「觸發 vs 非觸發」，對「續漲 pattern」問題無效；matched control（同觸發、label=0）才對題。時間分離雛形∈C 類（P1-01）。**建議 D／A**。

---

### Q3 去重／重疊／切分
**標籤**: **[委員會定]**（可附產品偏好選項）

**選項（產品偏好可問使用者）**:
- **A. `first`**：窗內只留最早 t₀ → 樣本少、獨立性較好。
- **B. `cluster`**：合併連續觸發為一事件（代表 t₀＝簇首或簇中心）→ 需定義簇間隙。
- **C. `all`＋權重／重疊標記**：保留全部但統計用 HAC／cluster bootstrap → 實作重、報告複雜。
- **D. `all` 無修正** → **禁止**（顯著性虛高）。

**技術定案建議**: 預設 **A 或 B**；一律輸出重疊圖（label 窗相交對）。切分＝**per-symbol 時間切**＋`purge_gap/embargo ≥ label_horizon`（复用 `SplitPlan`／`validate_split_integrity`／orch `:365-372`）；**禁 positional index**。新寫：`dedupe_events`、label-window overlap 標記、事件列→`RowMaskPlan(source="event")` 組裝。IC／AUC 在重疊未處理時標準誤偏小——報告須含 `n_events_raw`／`n_events_deduped`／`overlap_fraction`。

---

### Q4 標籤嚴格度
**標籤**: AND/OR／閾值／基準價＝**[使用者裁：產品語意]**；平台是否重算 label＝**[委員會定]**

**選項（給使用者）**:
- **A. 外部已算好 label，平台只存 `label`＋`label_rule_id/hash`**（建議）→ 契約穩；平台不解釋規則；不一致難自檢。
- **B. A＋可選 label 重算器（使用者提供規則 DSL／參數）做一致性抽檢** → 可驗；範圍／DSL 成本高。
- **C. 平台強制重算並覆蓋使用者 label** → 易與外部標註衝突；不建議。

嚴格度（AND 24∧36∧48 vs OR vs 連續型）屬**使用者規則**，進 `label_rule_id` 字串／hash，**不進**平台枚舉（否則每種事件改契約）。不平衡 ⇒ 報告強制 base rate、建議用 PR-AUC／balanced metrics；不在匯入期靜默 resample。

**委員會建議**: **A 為 B1**；B 列 §N 可選。3% 相對 t₀ close 或進場價＝使用者規則之一，契約只要求 `label_rule_id` 可重現。

---

### Q5 共通 pattern 防運氣
**標籤**: **[委員會定]**

**最小可證偽組合**:
1. 條件子樣本 IC（`event_filter` timestamps 模式＋A′；`sample_scope.kind=event`）。
2. 二元辨別統計＋BH-FDR（B2）。
3. GBDT／SHAP／`pattern_extractor`（已要 `SplitPlan` train）＋OOS／跨標的。
4. 規則挑選接 GAP-1 `strategy_validation/`（`pbo.py`／`deflated_sharpe.py`／`min_btl.py`）。
5. Oracle：置亂 label ⇒ AUC≈0.5／IC≈0；把 label 窗前移製造洩漏 ⇒ purge／PIT 守衛必攔。

**MinBTL 量級**: 數千～數萬事件下，具體門檻依報酬分佈／SR 假設而定——SPEC 應**调用**既有 `min_btl` 原語並要求報告印出計算假設，**禁止**本 consult 發明單一魔術數字（anti-hallucination）。n 不足 ⇒ `capability_status=unavailable`＋tier（复用 `check_sample_size` 思想，門檻另訂於契約）。

---

### Q6 共用／不共用面與落點
**標籤**: **[委員會定]**

**可共用（file:line 級）**:
- 事件遮罩：`event_filter.py:55-105`；orch `_stage3_event_filter` `:2776-2962`；`analyze(..., event_timestamps=)` `:887-895`；A′ fallback `:1142-1152`。
- purge／horizon：orch `:365-372`；`SplitPlan`／`validate_split_integrity`／`RowMaskPlan`（`contracts.py:362-400,506,682-698`）。
- 倖存者身份：`survivor_contract.py:278-286,407,471`；`ic_survivor_contract.json`。
- IC／PIT／bootstrap：`ic_engine.py`、`pit_stats.py`（序列型主線）。
- 規則／過擬合：`pattern_extractor.py:77-110`；`strategy_validation/*`。

**必須新寫**:
- 匯入契約 validator、PIT `align_events_to_features`、`dedupe_events`／overlap、反例／control 組裝、二元辨別統計＋FDR 報告節、`statistic_kind`、匯入失敗 loud 清單、（可選）①類示範產生器。

**`sample_scope.event` 擴欄**: 要（P1-02）；影響 GAP-2b 契約 **version 升版**＋既有 golden／conformance。建議匯入契約獨立 version，倖存者鏡像子集欄位。

**落點命名**: 避免 `event_study/`（金融術語碰撞）；建議 `event_samples/` 或 `event_import/`。

---

### Q7 scope／分批
**標籤**: 分批邊界＝**[委員會定]**；要做幾批才開做＝可附 **[使用者裁]** 節奏

**建議分批**:
| 批 | 內容 | 單獨上線價值 |
|---|---|---|
| **B1** | 匯入契約＋PIT 對齊＋去重／重疊標記＋SplitPlan 相容切分原語＋oracle＋loud 失敗清單 | **高**（正確樣本是一切前提） |
| **B2** | 條件 IC（接 stage3/4＋A′）＋二元 AUC／rank-IC＋FDR；`statistic_kind`；`sample_scope` 擴欄 | 高（回答「有無 pattern」） |
| **B3** | 切分強化＋`pattern_extractor`＋DSR/PBO | 中（策略候選） |
| **B4** | 報告契約持久化＋前端占位殼 | 中（可觀測） |

**與現雛形關係**:
- **重建**核心（契約／PIT／樣本組裝）→ 建議。
- **包裝**舊 `CaseRecord` 當相容層 → 僅短期 adapter，不得當 SoT。
- **棄用**路徑：靜默跳過、時間分離反例當默認、同根無 `decision_time` 對齊——文件化 deprecated，勿刪殼（禁改 `xgboost_batch_service` 訓練本體）。

**建議**: 先 B1 即可開 SPEC；B2 同 epic 連續；B3／B4 可下一批。

---

### Q8 能否進 SPEC
**Verdict**: **可以進 SPEC 起草**。

**BLOCKING 清單（寫進 SPEC，非停工）**:
1. `decision_time` 必填＋對齊語意（P0-01）。
2. 新匯入契約 SoT；禁 CaseRecord 充數（P0-02）。
3. 禁靜默跳過（P0-01）。
4. B1／B2 統計分界與 `statistic_kind`（P1-03）。
5. `control_kind` 預設政策（P1-01）。
6. 時間戳 ms 單一真相＋單位閘（P1-04）。
7. `sample_scope.event` 擴欄／version 計劃（P1-02）。
8. 保留 ICHC R5 A′（fallback 保留 `event_timestamps`）。

**非本輪阻塞（具名未查／不受理）**:
- Kline 層未來變更的完整遷移矩陣（對齊契約綁「bar 邊界＋timestamp 單位＋tf」即可；細節待 Kline 票）。
- 精確 MinBTL 數字（交 `min_btl` 原語＋假設揭露）。
- 前端樣式、ML 超參、CAR/AAR、外部源、Pooled IC、容量／效能。

---

## §1 必查 11 類（consult 適配；無則標無）

1. 矛盾／互斥：設計候選 5 與「B1 最小可交付」易互斥 → **P1-03**。
2. 漏項／E2E：匯入→PIT→去重→統計→倖存者鏡像 → 分批 Q7 補齊。
3. 不可測驗收：要求 oracle／mutation（Q5）；SPEC 須寫命令級 §V。
4. 可疑 quant：look-ahead（P0-01）、廢答案反例（P1-01）、重疊獨立性（Q3）。
5. 過度工程：一次做完 B1–B4／大改 xgboost 殼 → 反對；分批＋禁改殼。
6. OOM／並行：本輪未查（事件數萬級通常不是首要；列未查）。
7. Cache：未查事件 cache key（列未查；SPEC 應含 symbol/tf/decision_time/label_rule_hash）。
8. API／型別：CaseRecord→新契約 migration（P0-02／P1-04）。
9. 測試品質：現雛形缺 PIT／control_kind 測試面 → SPEC §G 必補。
10. Agent 可執行性：純函式邊界＋契約 SoT 已夠起草。
11. 必要性／短命工：舊 CaseRecord adapter 若永久化＝短命債；限 B1 migration。

## 未查清單（不當阻塞）
- 具體①類示範規則 DSL 語法。
- `two_stage_search`／`case_search` 路由與新契約的欄位對照全表。
- 前端 `/pending-features` 事件型條目文案。
- 萬級事件下 bootstrap 牆鐘 benchmark。

---

ASSUMPTIONS_VERIFIED: CaseRecord 五欄無 decision_time／horizon；xgboost_batch :618 精確相等、:641 同根、:621/:651 靜默跳過；反例時間分離 :788-818；EventFilter 無 label／dedup；sample_scope.event 五鍵無 label 語意；SplitPlan／pattern_extractor fail-closed；A′ fallback 保留 event_timestamps（:1142-1152）；非測試 sample_scope 另含 pendingFeatures.ts。
TESTS_RUN: 唯讀 consult；`shasum -a 256` 產 digest；`grep -rn sample_scope … | grep -v test`；`grep positive|label|… event_filter.py` → 0；未跑 pytest（brief 禁改碼／禁寫測試）。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（本檔只產 consult；建議之契約擴欄待 SPEC）

STATUS: DONE
