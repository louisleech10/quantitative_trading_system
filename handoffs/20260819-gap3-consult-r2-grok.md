# GAP-3 事件型 consult R2 / grok | task-id=20260819-GAP3-X-CONSULT-R2

brief-kind=consult；家族=grok；輪次=R2；read-only；審查標的＝`白話說明/GAP-3事件型討論.md`#685405d0daf9（第 6 版）。

## Verdict：可進 SPEC 起草（decision-gated；無全域停工 BLOCKING）

討論文檔之 U 系列與主線架構（契約新寫、六時間收據、全部 K 線驗證、三張表分報、產生器升級 `/search`）技術上可進 SPEC。本輪把 R1 的 C 預設改寫為 **A／B／C／兩段式全要** 後，下列前提必須寫進 SPEC 正文（不可當已裁決事實滑過）：

1. **進場／label 價格語意** ≠ IC 主線預設 close-to-close；契約必填 `reference_price_semantic`（見 `GROK-R2-P1-01`）。
2. **多 TF `feature_cutoff`＝per-TF as-of**，不是「事件 TF 前一根」單一時間戳（見 `GROK-R2-P1-03`）。
3. **case-control 合法**，但學習基率 vs 全樣本基率必須強制揭露（見 `GROK-R2-P1-02`）。
4. **條件引擎共用**允許，但必須有欄位角色（feature／outcome）＋PIT 守衛（見 `GROK-R2-P1-04`）。
5. **GAP-3 pooled 最小版 ≠ registry #4**；邊界寫死（見 `GROK-R2-P2-02`）。
6. R1 仍成立（不重證）：新匯入契約、六時間欄、毫秒單位、每標的時間切、兩種統計分開、分批、同根對齊靜默跳過禁作預設——見 `handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md` C1–C6。

U1–U11 本輪**不攻產品裁決**；未發現「技術上不可行」之 P0（無 U 系列 P0）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| # | 前提（來源） | 判定 | 證據摘要 |
|---|---|---|---|
| F1 | `/search` 篩選只准 `price_change`；進階含 `future_*`；反例＝±separation_days | **fact** | `requests.py:50`；`case_search_engine.py:336,651-658`；`search_task_service.py:788-820` |
| F2 | 匯入 CSV 必填 `symbol,timestamp,Positive_case`；BatchDownload lookback/forward/warmup | **fact** | `case_import_service.py:36`；`case_models.py:114-135` |
| F3 | IC API 收 `event_timestamps`／`event_query`；前端僅 `event_filtering` 開關 | **fact** | `ic_models.py:150-154`；orch stage3／A′；`icAnalysisStore.ts:78,106,134,336` |
| F4 | 案例→特徵：精確相等＋靜默跳過＋同根列 | **fact（R1）** | `xgboost_batch_service.py:618,621,641,651` |
| F5 | Feature Factory 有 slope／diff／rolling；缺 bars-since-cross／連續 N 根 | **fact（本輪複核）** | `rolling_aggregator.py` agg 含 `slope`；`derived_operators` 有 `ts_argmax/argmin`；`bars_since|consecutive_*|run_length` → **0 hits** |
| F6 | ML 引擎 `engine∈{xgboost,lightgbm}` | **fact** | `xgboost_batch_service.py:707-713` |
| A1 | A／B case-control＋全部 K 線驗證即充分（S3.1／J1） | **部分成立** | 統計合法，但缺強制基率／lift 揭露仍可誤讀（P1-02） |
| A2 | t₀ open＝前一根 1h／4h close，可直接餵 IC 主線（S3.9-1） | **過度簡化** | 漏 label 價格語意與 per-TF as-of（P1-01／P1-03） |
| A3 | 三反例混 0 於 GBDT 可行；IC 不受種類影響（S3.5／J4） | **方向正確** | 須按種類分報＋抽樣揭露；同意 J4 |
| A4 | C 簇首、A／B 全留降權、兩種都跑（S3.7） | **部分成立** | 預設可定；「兩種都跑」屬敏感度，不宜塞進 B1；uniqueness 算得出但 train 路徑 UNWIRED（P2-01） |
| A5 | 跨標的 pooled 最小版併進 GAP-3＝#4（S3.8／J6） | **邊界不清** | 最小版≠panel IC 重建（P2-02） |
| A6 | 產生器與 `event_filter` 共用底層（J10／K9） | **可行但缺角色守衛** | `df.eval` 安全子集已在；缺 column_role PIT（P1-04） |
| A7 | T1–T3＋T10 產生器；T5／T7 匯入；T8／T9 留欄；T4／T6 等源 | **大致成立** | T8／T9／T10 欄位形狀須在 K1 釘死 |

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

## A. 逐項對應表

> 欄位：ID | 態度 | 一句理由 | 建議 | 證據
> U 系列態度＝技術可行／有風險（不填同不同意）。

| ID | 態度 | 一句理由 | 建議 | 證據 |
|---|---|---|---|---|
| U2-1 | 技術可行 | `/search`→CSV→匯入→抓 K 線流程概念對；欄位／對齊不足 | 升級契約＋對齊，不翻頁（U7） | §2-1；`case_import_service.py:36`；R1 P0 |
| U2-2 | 技術可行（有風險） | A／B open 決策＋未來事件合法，但 label 價格語意須顯式 | 見 P1-01；六時間收據 | §2-2；`label_generator.py:40-47` |
| U2-3 | 技術可行 | 12h→1h／4h 在 UTC 整點可對齊；規則是 per-TF as-of | 見 P1-03 | §2-3；`case_models.py:131-134` |
| U2-4 | 技術可行（有風險） | 三反例全標 0 可行；易偷懶學 (b)(c) | 按種類分報＋兩段式分報 | §2-4／§3.5 |
| U2-5 | 技術可行 | 事件後報酬表不需反例；C 情境 | K5-(i) 多 horizon | §2-5 |
| U2-6 | 技術可行（有風險） | 1–2 萬列夠用但須 pooled＋同時刻簇 | 最小 pooled≠#4（P2-02） | §2-6／§3.8 |
| U2-7 | 技術可行 | 出場／連續觸發／X 根屬 K3／K5／K7 | 交 K 提案 | §2-7 |
| U2-8 | 不適用（流程） | 討論閘已遵守 | — | U3／本文檔 |
| S3.1 | 部分同意 | case-control 合法；配套不可省略基率／lift | P1-02；K8 | §3.1 |
| S3.2 | 同意 | A／B／C／兩段式＝契約維度正確 | `decision_time_rule` 枚舉 | §3.2；R1 C1 |
| S3.3 | 同意 | 連續觸發／切分／同時刻／末端未完成／置亂皆平台該擋 | 落 K3–K6 | §3.3 |
| S3.4 | 同意 | 不切固定窗；變化類特徵＋IC 選窗長 | K7 補缺、复用已有 slope／argmax | §3.4；P2-03 |
| S3.5 | 同意 | 混 0 不致錯亂；須分種類；IC 受抽樣影響 | 報告分面 | §3.5 |
| S3.6 | 同意 | 第一版時間出場；triple-barrier 列殘留 | 不碰回測層 | §3.6 |
| S3.7 | 部分同意 | 分情境預設對；「兩種都跑」不必進 B1 | K3；P2-01 | §3.7 |
| S3.8 | 部分同意 | 必須 pooled；同時刻簇對；≠整票 #4 | P2-02；K4 | §3.8；registry #4 |
| S3.9 | 部分同意 | 九成圖可复用；對齊／0-1／事件後表／前端入口要補；「換時間戳」過簡 | P1-01／P1-03；K2／K5 | §3.9；`ic_models.py:150-154`；store 僅開關 |
| S3.10 | 同意 | IC 篩→ML 組合→全 bar 驗 ML；引擎選擇不影響契約 | U8 | §3.10；`:707-713` |
| S3.11 | 同意 | 產事件／search+prep；分析同頁事件模式 | 前端占位；U10 | §3.11；pendingFeatures |
| T1 | 同意 | 價量觸發＝產生器第一批核心 | G1；K9 | §5 ① |
| T2 | 同意 | 技術指標事件；形態靠匯入 | 產生器做交叉／突破；形態＝T7 | §5 ② |
| T3 | 同意 | 波動／狀態切換可自 K 線＋特徵產 | 產生器 | §5 ③ |
| T4 | 同意（第一版不做） | 需外部源；登記即可 | §N＋registry | §5 ④ |
| T5 | 同意 | 日曆／排程＝匯入時間點 | 契約 `event_source=calendar` | §5 ⑤ |
| T6 | 同意（第一版不做） | 新聞／鏈上外部源 | §N | §5 ⑥ |
| T7 | 同意 | 人工標定＝匯入主路徑 | U2 | §5 ⑦ |
| T8 | 部分同意 | 契約留「參照標的」對；分析另排 | K1 欄位形狀 | §5 ⑧ |
| T9 | 部分同意 | meta-labeling 契約留來源模型；接 DSR/PBO 在規則→return 後 | K1／K6；勿 B1 | §5 ⑨ |
| T10 | 部分同意 | 區間型需 `event_shape=interval`＋start/end | K1；產生器可產 | §5 ⑩ |
| P0 | 同意 | 產生器升級 `/search` | K9；U6／U7 | §6 ⓪ |
| P1 | 同意 | 匯入契約升級 | K1 | §6 ① |
| P2 | 同意 | 批次抓 K 線概念保留 | 既有 BatchDownload | §6 ②；`case_models.py:114-135` |
| P3 | 同意 | 對齊收據＋多 TF | K2；P1-03 | §6 ③ |
| P4 | 同意 | FF 算特徵取決策列 | 禁同根 close 洩漏 | §6 ④；R1 P0-01 |
| P5 | 同意 | 去重／簇／降權／同時刻 | K3／K4 | §6 ⑤ |
| P6 | 同意 | per-symbol 時間切＋緩衝；統計可合併 | K4 | §6 ⑥；`SplitPlan` |
| P7 | 同意 | 三張表分開 | K5；R1 C5 | §6 ⑦ |
| P8 | 同意 | GBDT／規則只在學習段 | B3；禁改訓練殼 | §6 ⑧ |
| P9 | 同意 | 全 bar 驗證＋置亂＋DSR/PBO | K6／K8 | §6 ⑨ |
| P10 | 同意 | 報告／前端第一版占位 | UAT 整票後 | §6 ⑩ |
| G1 | 部分同意 | 任意特徵＋結果欄選樣 OK；須角色 PIT | P1-04 | §6 末-1 |
| G2 | 同意 | 多組條件→多標籤 | 一次設定 a/b/c | §6 末-2 |
| G3 | 同意 | 方向／情境／答案窗／規則摘要 | K1 | §6 末-3 |
| G4 | 同意 | 產生期可選去重並回報數 | 與 K3 參數對齊 | §6 末-4 |
| G5 | 同意 | 一鍵合規事件檔 | 輸出＝K1 schema | §6 末-5 |
| G6 | 同意 | 同引擎套全 bar＝標籤重算 | 仍受 PIT（P1-04） | §6 末-6 |
| J1 | 部分同意 | 合法＋配套對；缺強制基率欄 | P1-02 | §7 J1 |
| J2 | 同意 | 跨 TF 鐵律＝決策前已收盤 | P1-03 操作化 | §7 J2 |
| J3 | 同意 | 不切固定窗；窗內摘要＋IC 選長 | K7 | §7 J3 |
| J4 | 同意 | 反例種類欄＋分報＋兩段式合體 | K5-(ii) | §7 J4 |
| J5 | 同意 | 時間出場；TB 殘留 | 不碰回測 | §7 J5 |
| J6 | 部分同意 | 最小 pooled 要做；≠#4 整票 | P2-02 | §7 J6 |
| J7 | 部分同意 | 复用成立；對齊語意須補 | P1-01 | §7 J7 |
| J8 | 同意 | IC≠ML；接力 | U8 | §7 J8 |
| J9 | 同意 | 情境＝契約維度；類型＝標籤 | K1 taxonomy | §7 J9 |
| J10 | 部分同意 | 共用引擎可行；缺 column_role | P1-04；K9 | §7 J10 |

---

## B. K1–K10 技術定案提案

### K1 — 匯入契約欄位

**提案**（新 SoT；不沿 `CaseRecord` 加欄；R1 C2 延續＋本輪 A／B／T8–T10）：

**必填**
| 欄位 | 型別／枚舉 | 註 |
|---|---|---|
| `event_id` | str | 全域唯一 |
| `symbol` | str | |
| `timeframe` | str | 事件標註 TF（例 12h） |
| `t0_ms` | int64 | 事件根 **open** epoch **ms** UTC；量級閘（R1 grok P1-04） |
| `direction` | `long`\|`short` | 單次研究不混（U1／U4） |
| `scenario` | `A`\|`B`\|`C`\|`two_stage` | |
| `decision_time_rule` | `trigger_bar_open`\|`trigger_bar_close`\|`next_bar_open` | A／B 預設 `trigger_bar_open`；C 預設 `trigger_bar_close` |
| `label` | 0\|1 | |
| `label_value` | float | 連續報酬（正反例都附；U2） |
| `reference_price_semantic` | `close_to_close`\|`open_to_close`\|`open_to_horizon_close` | **本輪新增硬欄**（P1-01） |
| `label_window` | `{start_rule, end_rule, horizons_ms[]\|horizons_bars[], agg}` | |
| `control_kind` | 見下 | |
| `counterexample_kind` | `none`\|`a_same_trigger_no_cont`\|`b_range`\|`c_adverse`\|`other` | 正例=`none` |
| `event_shape` | `instant`\|`interval` | |
| `label_definition` | `{rule_id, canonical_digest, rule_snapshot}` | digest＝條件 JSON canonical＋sha256 |
| `source_file_digest` | sha256 | |
| `data_snapshot_digest` | sha256 | |
| `search_config_digest` | sha256 | `/search` 條件快照（U2） |

**control_kind**∈`{user_labeled_same_trigger, user_labeled_other, platform_same_trigger_rule, platform_random_bars}`；v1 只實作 `user_labeled_*`（R1 C2）。

**六時間收據（對齊輸出，可推導）**：`observed_through`／`decision_at`／`feature_cutoff`（**每 TF 一列**）／`entry_at`／`label_start`／`label_end`；不變式 `observed_through ≤ feature_cutoff ≤ decision_at ≤ entry_at ≤ label_start < label_end`（R1 C1；A／B 下 `observed_through` 對**特徵**可 ≤t0 open，對**結果欄選樣**可到 label_end——選樣與特徵分路徑，見 P1-04）。

**選填**
- `event_type_tag`（T1–T10 自由標）
- `observable_family`／`event_source`／`event_origin`（R1 正交 taxonomy）
- **T8**：`reference_symbols: string[]`；`relation_kind∈{lead_lag,relative_strength,co_move}`；分析 B2+
- **T9**：`source_model_id`；`source_signal_id`；`source_artifact_hash`（meta-labeling）
- **T10**：`interval_start_ms`／`interval_end_ms`（`event_shape=interval` 時必填）；代表點規則 `interval_repr∈{start,end,first_touch}`
- `meta` object

**可證偽驗收**：validator 單測——缺硬欄／秒當毫秒／A 缺 `reference_price_semantic`／interval 缺 end → reject；合法列 → receipt 六時間齊。

### K2 — 對齊收據與自動換算

**提案**：
1. 輸入：`t0_ms`＋`decision_time_rule`＋特徵 TF 集合。
2. `decision_at`：`trigger_bar_open`→t0_ms；`trigger_bar_close`→t0_ms+tf_duration；`next_bar_open`→下一根 open。
3. 每 TF：`feature_cutoff = max{bar.close_time | close_time ≤ decision_at}`；取該 bar 特徵列（P1-03）。
4. `entry_at`：A／B 預設＝`decision_at`（open 進場）；C 預設＝決策 close 或 next open（產品已裁者寫死）。
5. 失敗清單枚舉（loud，禁 `continue`）：`bar_missing`／`timestamp_unit_mismatch`／`feature_cutoff_after_decision`／`label_window_past_eof`／`nan_features`／`tf_boundary_unaligned`／`duplicate_event_id`。

**可證偽**：同一事件 12h／1h／4h receipt 中 1h 與 4h 的 `feature_cutoff_ms` 不同且皆 ≤`decision_at`；缺 bar ⇒ 失敗清單計數＋1、訓練列不靜默少。

### K3 — 連續觸發預設

| 情境 | 預設 policy | G（簇間隔） | 降權 |
|---|---|---|---|
| C | `cluster_first` | G＝答案窗長度（時間） | 簇內其餘丟棄 |
| A／B | `all_with_uniqueness` | G＝答案窗（用於簇 id） | `w=1/n_overlap` 寫 manifest（AFML 平均唯一性）；見 P2-01 |
| 共通 | 報告必含 `n_raw／n_effective／overlap_fraction` | | |
| 敏感度 | B2 可跑 `cluster_first` vs `all_with_uniqueness` 對照；**B1 不強制兩種都跑** | | |

**可證偽**：合成 5 根連續觸發＋答案窗重疊 → C 只留 1；A／B 留 5 且權重和反映重疊；結論翻盤時報告 `sensitivity_flip=true`。

### K4 — 切分與 pooled

1. **切分**：per-symbol 時間切；`purge_gap`／`embargo` ≥ 答案窗（時間語意；`SplitPlan.purge_semantic` 可 `timedelta`）；禁 positional（既有守衛）。
2. **事件層**：manifest 帶 `label_start/end`；interval-aware purge（R1 C3）。
3. **pooled 最小版**：切後 concat；統計標 `pool_method=concat_after_per_symbol_split`。
4. **同時刻簇**：跨 symbol 若 `|t_i-t_j|≤δ`（δ 預設＝事件 TF 一根）→ 同一 `cross_symbol_cluster_id`，權重或 cluster-robust SE。
5. **與 #4 邊界**：見 P2-02；不關閉 registry #4。

**可證偽**：兩 symbol 同時刻事件 → effective n＜raw n；train/test 無 label 窗相交。

### K5 — 三張表

| 表 | 計算 | 揭露 | capability |
|---|---|---|---|
| (i) 事件後報酬 | 事件後多 horizon 簡單報酬；mean／median／winrate／n／bootstrap CI；**不需反例**；按 direction／tag 分面 | `statistic_kind=event_post_return` | n＜門檻→`unavailable` |
| (ii) 正反例辨別 | OOS AUC／PR-AUC／Mann-Whitney；**按 counterexample_kind**；兩段式各一 | `statistic_kind=binary_discrimination` | 單類別→`unavailable:missing_control_group` |
| (iii) 條件 IC | 复用 stage3 timestamps／query＋stage4／5；label＝連續 `label_value`（注意 P1-01 價格語意） | `statistic_kind=conditional_ic`；A′ fallback 保留 timestamps | 既有 `insufficient_events` 等 |

枚舉复用 `ic_report_contract.json` 之 `capability_status`：`ok|not_applicable|not_computed|computation_failed|disabled|unavailable`（#808c611283ed）。

**可證偽**：同批事件三表可獨立 `not_computed`；禁單一數字混報（R1 C5）。

### K6 — 防運氣

| 檢定 | B1？ | 做法 |
|---|---|---|
| label 置亂 oracle | **是** | 固定 seed 置亂 y；二元 baseline AUC CI 含 0.5；IC≈0 |
| PIT 後移 | **是** | feature_cutoff 故意 > decision_at ⇒ validator **raise** |
| 基率揭露 | **是** | 見 P1-02 |
| DSR/PBO | **否（B3）** | 僅當規則→可比較 return series→ledger；禁對 AUC 自創 MinBTL（R1 C5） |

### K7 — 變化類特徵

**要補（具名）**
1. `bars_since_cross(series_a, series_b, window)` — 距上次 a 上穿／下穿 b 的 bar 數  
2. `consecutive_sign_run(series, window)` — 連續同號根數（量能放大／同向 K）  
3. `bars_since_threshold(series, op, value)` — 距上次破閾  
4. `window_max_ratio(series, window)` — 窗內 max／當前（或 max／min）  
5. `window_extremum_lag(series, window, mode=argmax|argmin)` — **若**既有 `ts_argmax/argmin` 輸出已是窗內位置，則包一層「距今 bars」即可，不重算（P2-03）

**已有可共用（不重寫）**：`RollingAggregator._compute_slope`（`rolling_aggregator.py:49+`）；`DerivedOperators.ts_argmax/ts_argmin`（`derived_operators.py:435-439`）；`feature_factory` worldquant 路徑（`:1361`）。

**落點**：`momentum/FeatureEngineering/operators/` 新函式＋`operator_registry`；IC／事件路徑只讀欄。

**可證偽**：單元測已知序列 bars_since＝7；grep 新名進 registry；舊 slope／argmax 輸出 byte 不變。

### K8 — 全部 K 線驗證輸出

**要出（一次建完整；GAP-3 範圍內）**
- 分類：precision／recall／PR 曲線／AUC；固定閾值與 top-q% 的 lift  
- 頻率：訊號率（每日／每根）、依 symbol、依時間分段（半年／年）穩定性  
- 報酬：簡單持有＝**open 進、答案窗末 close 出**（與 `reference_price_semantic` 一致）；mean／median／winrate／n／CI  
- 基率：`prevalence_learn` vs `prevalence_full`（P1-02）  
- 與序列型全 bar IC **並排**：同一特徵集、同切分、兩欄 `sample_scope=event|full`

**不該在 GAP-3 做（碰回測層）**：倉位 sizing、手續費／滑價、複利權益曲線、資金曲線、槓桿、組合 long-short 建構（U1 殘留）、最佳化出場（J5）。

**可證偽**：契約／報告 schema 含上列鍵；出現 `equity_curve`／`fee` 欄 ⇒ schema 測試失敗。

### K9 — 完整版事件產生器

1. **落點**：`momentum/Analysis/event_samples/condition_engine.py` 純函式；`/search` API 包殼升級（U7 不翻掉）；与 `EventFilter` 共用解析／安全 eval 子集，擴 column_role（P1-04）。  
2. **語法**：沿 `df.eval` 安全子集（現 blocklist）；擴「具名條件 DSL→eval」可選，B2。  
3. **多組條件→多標籤**：一次產出 pos＋a/b/c。  
4. **PIT**：`sample_select` 允 outcome；寫入特徵／gate 禁 outcome。  
5. **去重**：產生期可選；參數對齊 K3。  
6. **合規檔**：直接 K1 schema。  
7. **與既有**：保留 `_add_calculated_columns`／`SearchConfiguration` 作為價量結果欄來源並擴 FF 特徵 join；`allowed_filtering_params={'price_change'}`（`requests.py:50`）→ 改為契約化允許清單（特徵名＋outcome 名），非寫死單一。  

**T1–T10 落點**：T1–T3＋T10→產生器；T5／T7→匯入；T8／T9→契約欄（K1）；T4／T6→§N 等源。

**可證偽**：產生器輸出通過 K1 validator；feature_gate query 含 `future_` → reject；sample_select 含 `future_` → allow。

### K10 — 分批

| 批 | 內容 | 單獨上線價值 | 依賴 |
|---|---|---|---|
| **B1** | K1 契約＋validator；K2 對齊收據；K3 去重 manifest（權重欄）；K4 切分；K6 置亂＋PIT oracle；K5-(ii) 單特徵二元 baseline；基率揭露 | 可匯入正確事件並證明無 look-ahead | 無 |
| **B2** | K5-(i)(iii)；條件 IC 接 stage；survivor event 擴欄升版；K8 全 bar 驗證主輸出；產生器 MVP（T1 價量＋G2–G5）；K3 敏感度雙跑 | 事件研究＋條件 IC 可看 | B1 |
| **B3** | K7 變化特徵；GBDT／規則 pattern；DSR/PBO 接點；T2／T3／T10 產生器擴 | pattern 發現 | B2；ML 殼政策 |
| **B4** | API／前端事件模式入口＋占位殼收斂；T8／T9 欄位消費；持久化 | UAT 可點 | B2 |

**第一批最小可交付＝B1**（與 R1 C5／C6 一致，並納入本輪 P1-01／P1-02／P1-03 硬欄）。

---

### §1 必查摘要

1. 矛盾／互斥：S3.9-1「換時間戳共用 IC」vs open-entry label（P1-01）；J6 vs registry #4（P2-02）。  
2. 漏項：per-TF feature_cutoff、reference_price_semantic、column_role、基率欄——本輪補進 K。  
3. 不可測驗收：K1–K10 各附可證偽；正式 SPEC 仍須 §G golden。  
4. Quant：case-control 基率、重疊 n、close≠open label、未來欄進特徵——已攻。  
5. 過度工程：不把 #4 panel IC、回測層、TB 最佳化、外部源接入 B1。  
6. OOM：200 標的全史 FF＝重；沿用 per-case lookback 抓取；牆鐘 UNVERIFIED。  
7. Cache：digest 欄已列；實作細節待 SPEC。  
8. API／相容：新契約；舊 CaseRecord adapter 顯式；禁改 xgboost 訓練殼。  
9. 測試：本輪禁寫測；列出 oracle 清單供 SPEC。  
10. Agent 可執行性：K 提案已到欄位／枚舉／落點檔。  
11. 短命工：勿先改 CaseRecord 再拆；條件引擎一步到位純函式。

### §2 獵空殼

本輪標的為討論文檔非 SPEC——§RISK／§G 等 SPEC 錨點 **N/A**。討論檔 §7 編號完整、U／J／K 可對應；未發現「僅表頭無內容」空殼。正式 SPEC 仍須補 golden／receipt／mutation。

---

## 未查（不阻塞）

- 萬級事件 bootstrap 牆鐘與記憶體  
- Feature Factory 多 TF 既有 as-of 工具是否已有可复用函式（除對齊層新建外）  
- `two_stage_search` 前端欄位全表對照  
- T8 lead-lag 分析估計量（契約留欄即可）

STATUS: DONE
