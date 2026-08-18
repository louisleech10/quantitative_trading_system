# GAP-2a／2b 偵察 consult / grok | task-id=20260818-GAP2-X-CONSULT-R1

brief-kind=consult；家族=grok；輪次=R1；禁改碼；只產本檔。

## Verdict：可進 SPEC 起草（附 BLOCKING 清單須寫進 SPEC）

偵察足以讓 Claude 起草 SPEC。**沒有**「現有 IC 語意下邊際 IC 根本無意義」或「split 不支援 train-fit」這類全域停工 BLOCKING。現有 holdout `split_context.train_mask`／`test_mask`＋`pit_train_fit` 原語足夠承載 train-fit／test-apply。

必須寫進 SPEC 正文（不可當已裁決事實滑過）的前置裁決：

1. **殘差空間與相關定義釘死**（Spearman 產品預設下，raw Gram-Schmidt／OLS residual → Spearman ≠ 偏／半偏 Spearman；見 `GROK-R1-P0-01`）。
2. **不得复用**現有 `factor_orthogonalizer`／`FactorModuleResult` 路徑宣稱 OOS 邊際 IC（residual 丟棄＋型別鎖 `oos_guarantees=False`；見 `GROK-R1-P0-02`）。
3. **`sample_scope` 用結構、非純枚舉**；倖存者契約獨立 JSON SoT＋報告節鏡像（見 `GROK-R1-P1-02`／`P1-03`）。
4. **Forward stepwise 預設 OFF**（或另立 multiplicity 政策）；組合 IC 比較須附 CI 策略（見 `GROK-R1-P1-01`／`P1-04`）。

**非 BLOCKING**：前端圖表可延後；`ic_wiring_check` R3 不會自動護新節（須另擴或靠契約測試）；bridge 本體接 ML 仍 blocked-by 成熟度地圖（使用者已裁定）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| # | 前提（來源） | 判定 | 證據摘要 |
|---|---|---|---|
| F1 | `sample_scope` 全庫 0 命中 | **fact 成立** | 本輪重跑：`momentum`/`api`/`frontend/src`/`scripts` 下 `.py/.ts/.json` 檔內容搜尋 `sample_scope` → **0 hits** |
| F2 | `gram_schmidt` 回 QR 的 Q；逐因子 residual 只算 `np.var` 進 metadata、序列丟棄；`dropna(how="any")` 全樣本；無 rolling／expanding | **fact 成立** | `factor_orthogonalizer.py:30-63`（`qr`→`orth=q_matrix`；residual 僅 `residual_variance`） |
| F3 | `FactorModuleResult` 鎖 `oos_guarantees=False`／`fit_scope="full_sample"`；`deny_factor_in_ok_oos` 擋進 `ok_oos` | **fact 成立** | `contracts.py:1956-2012`；orch `:2194-2209` 設 `consumer_deny=True` |
| F4 | IC 倖存者無下游 ML 消費者（指定路徑 grep=0） | **fact 成立** | 本輪：`xgboost_batch_service.py`／`pattern_extractor.py`／`Optimization`／`model_validation` 對 `ic_report`/`ICFilterOrchestrator`/`filtered_features`/`summary_table` → **0** |
| F5 | IC report metadata **無**獨立 `provenance`／`config_hash`／`features_path` 欄；`config_hash` 只進 `selection_scope.scope_id` | **fact 成立** | orch `:3134-3135` `scope_id=f"{config_hash}:{split_label}"`；`provenance` 僅 `strategy_validation/*`＋`ic_reporter` 錯誤字串 |
| F6 | `passed_features` 為 stage5 `list[str]`，不以該名持久化；持久化＝filtered.h5 attrs＋`ic_report_*.json`＋parquet 10 欄 | **fact 成立** | orch `:3195-3217`；`ic_artifact_writer.py:21-32` 10 欄；`save_filtered_features` attrs |
| A1 | 邊際 IC＝candidate 對 S 之 train-fit 投影 residual 與 label 的 IC（≈偏相關秩版） | **部分成立／定義欠釘** | 回答「新資訊」較近 **semi-partial**（只殘差化因子）；真 **partial** 還殘差化 label。且產品 IC 預設 Spearman 時 raw 線性殘差會誤報（見 P0-01） |
| A2 | 組合只需 equal_z／ic_weighted；OLS／Ridge 屬 ML 外 | **大致成立** | 單標的縱向 IC 下少參數組合法有意義；權重必須 train-only（見 P1-04） |
| A3 | train-fit／test-apply 即可標 `oos_guarantees=True`；沿用 split＋pit_stats，無需新切分 | **成立（對齊現況 holdout）** | 與 `split_method=holdout` 契約一致；expanding 投影為加強項非前置。須避開 `FactorModuleResult` 型別鎖 |
| A4 | 倖存者契約＝報告新節＋獨立 JSON；最小欄位足夠 | **最小集不足** | 漏 label/horizon／symbol／tf／method／universe hash／IC 快照等（見 P1-03） |
| A5 | 本票不需前端圖表；wiring 不紅即可 | **成立（產品範圍）**；**閘不會自動護新節** | `ic_wiring_check.REPORT_SECTIONS` 硬編碼五節（見 P2-01） |

---

## GROK-R1-P0-01

**斷言**: 在產品預設 Spearman IC 語意下，對 raw 因子做線性投影／Gram-Schmidt 後再算 Spearman，**不是**「相對 S 的新資訊」的正確統計量；非線性冗餘因子會留下假邊際 IC，SPEC 若不釘 residual 空間會系統性錯答 GAP-2a 問題。

**碼證**: 產品 IC 預設 spearman（`ic_engine.py:66,:280-308,:1006-1008`）；orth 對 raw matrix QR（`factor_orthogonalizer.py:42-56`）；本輪探針非線性冗餘 `tanh(2s)` gross≈0.78、raw-resid→Spearman≈0.14（假陽）、rank-resid≈0（正確）。
- 定義三分法（須入 SPEC 詞彙表）：(1) semi-partial `IC(resid(c|S), label)`；(2) partial 兩邊殘差化；(3) Δcomposite-IC。
- 文獻：Grinold-Kahn residual alpha；Qian 正交／偏相關；LdP AFML IC／冗餘。固定 S 投影殘差順序不變；stepwise 才有順序依賴。
RECHECK: 重跑合成探針；讀 `ic_engine` 預設 method 與 `gram_schmidt` 是否仍 raw QR。

**來源摘要**: momentum/Analysis/factor_orthogonalizer.py#989b9e4b2101

[BLOCKING] 信心度=High。SPEC 必須顯式選擇並寫進契約枚舉，建議預設：`method=spearman` ⇒ **rank-space residual → Pearson（=semi-partial Spearman）**；另輸出 `gross_ic`／`ic_retained_ratio=marginal/gross`（gross=0 時 NaN+reason）。禁止沉默复用 raw GS 後稱「邊際 Spearman IC」。

---

## GROK-R1-P0-02

**斷言**: 現有 `factor_orthogonalizer`＋deep-analysis runner **不能**承載可宣稱 `oos_guarantees=True` 的邊際 IC；若 SPEC 指示「在正交化模組上加 IC」會撞型別鎖與 `deny_factor_in_ok_oos`，或產出永遠進不了 `ok_oos` 的假整合。

**碼證**: residual 只記 var 不返回（`factor_orthogonalizer.py:48-63`）；全樣本 dropna（`:30`）；runner 鎖 `FactorModuleResult(oos_guarantees=False, fit_scope=full_sample)`＋`consumer_deny=True`（orch `:2165-2211`）；`deny_factor_in_ok_oos`（`contracts.py:1977-2012`）。
- 健檢 C10／C11：誠實 deny／unavailable（`handoffs/reconcile/20260817-ichc-x-consult-r1/synth.md`）。
RECHECK: grep `consumer_deny|FactorModuleResult`；ok_oos 掛 typed orth 應 raise。

**來源摘要**: momentum/core/contracts.py#8a1415d6ea01

[BLOCKING] 信心度=High。採設計候選 5：正交化**不改語意**；新模組 `marginal_ic.py`（純函式）走 `pit_train_fit`／train_mask 擬合投影、test_mask 評 IC。輸出勿用 `FactorModuleResult`；另立 payload／`oos_guarantees` 布林與 `fit_scope="train_mask"`（或等價字串）契約。

---

## GROK-R1-P1-01

**斷言**: 以 marginal IC 做貪婪前向選擇若**預設 ON**，會在 stage5 FDR 之後重開 selection multiplicity／順序依賴，使「test 段報表」變成選模後的有偏 OOS。

**碼證**: stage6 只做相關 greedy／vif（`redundancy_filter.py:67-104`），不算對 label 增量 IC；stage5 已 FDR 出 `passed_features`（orch `:3195-3217`）；charter F-MC-1..3 未涵蓋 post-FDR stepwise。
- 固定 S 的 marginal 無順序問題；stepwise 每步改 S 才有順序依賴。
RECHECK: grep Analysis 無現成 forward-selection by residual IC。

**來源摘要**: momentum/Analysis/redundancy_filter.py#5f57224be356

[MAJOR] 信心度=High。表態：**預設 OFF**。ON 時須：(a) 選模只在 train 段比 marginal；(b) test 只報預先登記候選的持出指標；(c) 記錄 `selection_path`／種子順序／n_steps；(d) 與 FDR 政策的關係寫明（建議 stepwise 候選域＝stage5 survivors，禁回灌全宇宙）。設計候選 2 可留作可選 stage，但不可默認開啟。

---

## GROK-R1-P1-02

**斷言**: `sample_scope` 目前全庫不存在；若契約只寫枚舉 `full|event` 不足以讓未來事件型倖存者 fail-closed 消費，也無法對齊既有 `RowMaskPlan.source`。

**碼證**: 本輪 `sample_scope` 全庫 hits=0；`RowMaskPlan.source∈{split,event,feature_filter,full}`（`contracts.py:682-698`）是列遮罩鑑別器而非 survivor 輸出欄；event_filter 吃 `event_timestamps`（orch `:2715+`）。
- GAP-1 先例：獨立 `strategy_validation_contract.json`＋`capability_status_ref`，可類比 2b。
RECHECK: 重跑 sample_scope 搜尋；讀 RowMaskPlan 與 event_filter 回傳鍵。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#4f1f03ff1d68

[MAJOR] 信心度=High。建議 `sample_scope`＝**結構**：
```text
{
  "kind": "full" | "split" | "event" | "feature_filter",  // 對齊 RowMaskPlan.source 超集
  "row_mask_source": "...",           // 回指 RowMaskPlan.source
  "base_universe_hash": "...",
  "event": null | {"definition_hash": "...", "timestamps_hash": "...", "n_events": N},
  "split_label": "train"|"val"|"test"|"full"|null
}
```
枚舉值單一真相源進 `survivor_output_contract.json`；禁止只在 prose 寫 full/event。

---

## GROK-R1-P1-03

**斷言**: brief 假設的倖存者最小欄位集不足以支撐可重現消費；且 `FilteredFeatureSet`／現有 parquet artifact **都不是**合格宿主。

**碼證**: `FilteredFeatureSet` 僅定義無消費者（`contracts.py:340-346`）；parquet 10 欄無 sample_scope（`ic_artifact_writer.py:21-32`）；filtered.h5 attrs 無獨立 config_hash／label horizon；ML 入口仍是 `selected_features: List[str]`（`xgboost_batch_service.py:221-226`）。
- report metadata 有 `selection_scope`（orch `:3732-3741`）但 `passed_features` 不以該名持久化。
RECHECK: 列真實 ic_report JSON 頂層／metadata 鍵，確認無 provenance 區塊。

**來源摘要**: momentum/Analysis/ic_artifact_writer.py#1204d38072f1

[MAJOR] 信心度=High。契約欄位提案（每欄附消費理由）見下方必答 5；SoT＝`momentum/Analysis/contracts/survivor_output_contract.json`＋檔 `data_cache/reports/ic_survivors_{case_id}.json`；IC 報告 `report_sections` 可加 `survivor_output` 節做 status 鏡像（`capability_status` **ref 复用**，禁複列六值）。

---

## GROK-R1-P1-04

**斷言**: 單標的縱向（time-series）IC 語意下，等權 z-score／train 段 IC 加權（含符號對齊）有意義；但 `composite_ic` vs `best_single_ic` 若無 CI／自相關處理，易在小 test 段上假陽性宣稱組合優於單因子。

**碼證**: 主線為縱向 time-series IC（`ic_engine.compute_ic`／rolling）；charter F-IC-4／F-IC-8 要求 NW／bootstrap CI 與 train-vs-test CI；權重應對齊 `pit_train_fit`（`pit_stats.py:551-581`）只在 train 估。
- OLS／Ridge 屬監督擬合，踏出 2a 純 IC 邊界。
RECHECK: 讀 charter F-IC-4／F-IC-8 原文是否仍要求 CI。

**來源摘要**: docs/TEST_DESIGN_CHARTER.md#e9be08bb5d5f

[MAJOR] 信心度=High。SPEC：`weights_method∈{equal_z, ic_weighted}`；`ic_weighted` 權重＝train 段 IC（符號對齊後 |IC| 或 ICIR）；test 段只 apply。比較輸出必含 `n_test`、點估、以及 bootstrap／NW CI（或 `capability_status=unavailable`＋reason 當 n_test 不足）。禁止無 CI 的「組合勝出」產品文案。

---

## GROK-R1-P1-05

**斷言**: train-fit／test-apply 足以在**現有 holdout 契約**下宣稱與主線一致的 `oos_guarantees=True`；不需要新切分機制，但必須自備 n_test 守衛，且不可誤走 rolling warm-up 或 `FactorModuleResult` 路徑。

**碼證**: holdout split 已建 train/test mask 且可標 oos_guarantees（orch `:890-944`）；split_method 契約 holdout｜full_sample_fallback（`ic_report_contract.json:18`）；stage4 rolling warm-up（`:2917-2933`）不自動護「單次 residual Spearman」路徑。
- refilter 驗 `pit_stats_version`＋`fit_mode`（`:1701-1724`）；expanding 投影為加強項非前置。
RECHECK: 讀 stage4 warm-up 與 `pit_train_fit` 簽名。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c

[MAJOR] 信心度=High。OOS 規則寫進 SPEC：投影／標準化／IC 權重 **只** fit 於 `train_mask`；評測 IC **只**於 `test_mask`；full_sample_fallback 時強制 `oos_guarantees=False`／`analysis_status=degraded_full_sample`。cache／版本鍵含 `pit_stats_version`＋邊際 IC 演算法版本字串。

---

## GROK-R1-P2-01

**斷言**: `ic_wiring_check` R3 只對硬編碼五節掃描「裸空 `{}` 字面」；新增 `report_sections` 鍵**不會**自動被該閘保護，前端 `CapabilityStatus` 鏡像也不因契約新節而強制更新。

**碼證**: `ic_wiring_check.py:30-36` R3 只盯五節裸空 `{}`；契約已有 `net_ic_analysis` 卻不在 R3 集合（`ic_report_contract.json:28-42`）＝「契約有節≠wiring 有護」先例；前端只鏡像 CapabilityStatus（`types.ts:2036-2043`）。
RECHECK: 跑 `python scripts/ic_wiring_check.py`；確認 REPORT_SECTIONS 無新節名。

**來源摘要**: scripts/ic_wiring_check.py#bdf0f75f427b

[MINOR] 信心度=High。本票可無圖表；但 SPEC 若加報告節，須**同步**：(a) 契約＋後端組裝非裸空；(b) 擴 R3 集合或加 survivor 專用契約測試；(c) 前端鏡像列為可選後續（使用者裁定不需圖時可 §N user-ruling）。

---

## GROK-R1-P2-02

**斷言**: 邊際／組合 IC 的正確落點是 stage6 之後的主線**可選 stage**（吃 redundancy 後的 survivor 集合），不是 deep-analysis 的 `factor_orthogonalization` 模組；且 `refilter` 目前只重跑 stage5→7，新 stage 若不掛上會在門檻重篩後留下過期邊際數字。

**碼證**: deep 含 `factor_orthogonalization`（orch `:1862-1872`）屬 research-only；`refilter` 只重跑 stage5→6→7（`:1736-1765`）；`analyze_full`＝analyze＋deep inject（`:1770-1804`）；xsec 另路徑，registry #4 排除。
RECHECK: 讀 refilter 全程無其他 stage 呼叫。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c

[MINOR] 信心度=High。建議 stage 名 `stage6_5_marginal_composite`（可選，default off）；輸入＝stage6 `filtered_df` 欄位作 S，候選域可＝S（自檢）∪ stage5 未進 S 者（若產品要「落選者增量」）；輸出進 report section＋survivor 檔。`refilter`／cache invalidate 必須列入 TODO 強制項。

---

## 必答 1–8（逐條 verdict）

### 1. 邊際 IC 定義與統計正確性
**Verdict**: 採用 **train 段擬合、test 段評測的 semi-partial IC** 作為 GAP-2a 主定義：  
`marginal_ic = Corr( resid(c | S)_{test}, label_{test} )`，其中投影係數只來自 train。  
Spearman 產品預設下 residual 在 **rank 空間**完成（見 P0-01）。  
與偏相關：semi-partial ≠ partial；與 GS：固定 S 的投影殘差≈GS／QR 殘差（順序不變）；與 Δcomposite-IC：不同問題，可並列不可替換。  
S 順序：單次 vs 固定 S 無順序問題；stepwise 才有（P1-01）。

### 2. OOS 紀律
**Verdict**: holdout train-fit／test-apply **足以**對齊現況 `oos_guarantees=True`（P1-05）。不需新切分。須避 `deny_factor_in_ok_oos`／`FactorModuleResult`；自備 min_n_test；rolling warm-up 守衛不自動適用。expanding 投影＝加強項。cache 鍵含 `pit_stats_version`＋演算法版本。

### 3. 多因子組合
**Verdict**: `equal_z`／`ic_weighted`（train 估權＋符號對齊）在縱向 IC 有意義；OLS／Ridge 出局。`composite_ic` vs `best_single_ic` 必須附 CI（F-IC-4／F-IC-8）或標 unavailable。

### 4. 落點
**Verdict**: 主線可選 stage（stage6 後），default off；深析正交化不改。影響面：`analyze`／`refilter`／report／persist；`analyze_full` 不自動等於開啟。xsec／cross-sectional 首批 `not_applicable`。`capability_status` 用 ref 复用。

### 5. 倖存者輸出契約（2b）
**Verdict**: 新建 `survivor_output_contract.json`（設計候選 4 成立）。建議欄位：

| 欄位 | 消費端為何需要 |
|---|---|
| `schema_version` | 演進／fail-closed |
| `case_id`／`generated_at` | 對帳／新鮮度 |
| `symbol`／`timeframe` | ML／特徵路徑定位 |
| `feature_names: list[str]` | 今日 `selected_features` 直接對接 |
| `sample_scope`（結構，見 P1-02） | 事件型倖存者禁在 full 上訓練 |
| `selection_scope_id`／嵌套 `SelectionScope` 關鍵欄 | 與 FDR 宇宙對帳 |
| `base_universe_hash` | 與 `RowMaskPlan`／scope 對帳 |
| `config_hash` | 重現實驗 |
| `features_content_hash`／`features_path` | 防錯接舊 h5 |
| `labels_content_hash`／`label_spec{horizon,name,method}` | 防 label 偷換 |
| `ic_method` | spearman／pearson |
| `analysis_status`／`oos_guarantees`／`pass_class` | 禁把 degraded 當 ok_oos 喂 ML |
| `split_method` | holdout vs fallback 誠實 |
| `ic_snapshot[{feature,ic_mean,icir,p_value,marginal_ic?}]` | 不開完整 report 也能審 |
| `redundancy_method`／`n_input`／`n_output` | 選擇路徑審計 |
| `provenance{status,reason,producer,contract_version}` | 對齊 GAP-1 五節精神的最小集 |
| `capability_status`／`reason` | 空／失敗誠實 |

關係：`RowMaskPlan`／`SelectionScope` **复用欄位語意**；`FilteredFeatureSet` **不**升級為 SoT；`ICArtifactSchema` 保持 IC 長表，不塞 survivor。ML 將來：讀 JSON → `feature_names` → 今日 `selected_features`；並校驗 `sample_scope`／`oos_guarantees`（本票只定義不接）。

### 6. 測試策略
**Verdict**:
- Oracle：c∈span(S)（線性）⇒ marginal≈0；c⊥S 且與 label 相關 ⇒ marginal≈gross；label 置亂 ⇒ ≈0；特徵×正常數 ⇒ 秩不變（Spearman）。
- 非線性冗餘（tanh(S)）⇒ rank-residual≈0 且 raw-residual-Spearman **不得**當通過條件（防回歸 P0-01）。
- 組合：等權符號對齊後 composite 與單因子關係的可證偽不等式／CI 覆蓋率。
- 契約 round-trip＋缺欄／錯枚舉 fail-closed；`deny`：ok_oos 報告不得夾 full_sample orth 模組。
- Mutation：改成 full-sample fit、改 residual 空間、漏 test_mask、權重用 test IC → 必 FAIL。

### 7. scope 分批
**Verdict**: 建議四批，**B1 與 B3 單獨上線即有價值**：
- **B1** 邊際 IC 純函式＋oracle（無 orch 接線）→ 研究可腳本使用。
- **B2** 組合 IC 純函式＋CI 策略。
- **B3** survivor 契約＋寫檔＋契约測試（2b；不接 ML）→ 下游可開始對契約。
- **B4** orch 可選 stage＋report 節＋refilter／wiring／metadata。

### 8. 是否足以進 SPEC？BLOCKING？
**Verdict**: **足以進 SPEC**。BLOCKING 僅 P0-01（定義／殘差空間）與 P0-02（禁复用 orth 路徑）。無「邊際 IC 無意義」或「split 不支援」停工項。

---

## §1 十一類（consult 適配；無則標無）

1. 矛盾／互斥：無（使用者 2a／2b 拆分與 registry 一致）。  
2. 漏項：有 — survivor 欄位與 refilter 掛接（P1-03／P2-02）。  
3. 不可測：有風險 — 若不定 golden／oracle 會空殼（必答 6）。  
4. 可疑 quant 假設：有 — A1 Spearman／偏相關（P0-01）。  
5. 過度工程：風險＝預設 ON 的 stepwise／Ridge 組合；建議裁掉。  
6. OOM／並行：未查（time-box；非本票優先）。  
7. Cache：須納 `pit_stats_version`＋演算法版本（P1-05）。  
8. API／型別：契約新建；前端可延後。  
9. 測試品質：見必答 6。  
10. Agent 可執行性：SPEC 須釘檔案／函式／預設 off。  
11. 必要性／短命工：若先改 `factor_orthogonalizer` 再作廢＝短命工；應直接新模組。

---

## 設計候選逐條攻（摘要）

1. `marginal_ic.py` 純函式 — **接受**（必經 B1）。  
2. Forward stepwise 可選 stage — **接受但 default OFF**（P1-01）。  
3. `factor_combiner.py` equal_z／ic_weighted — **接受**；須 train 估權＋CI（P1-04）。  
4. `survivor_output_contract.json`＋獨立檔 — **接受**；欄位擴充（P1-03）。  
5. 不改 orth 語意 — **接受且升級為 BLOCKING 約束**（P0-02）。

---

## 未查清單（不當阻塞）

- 前端 deep-analysis 圖是否仍顯示「Neutralized IC」文案（C10 UI 誤導殘留）。  
- 全量 pytest 計數／跨 tier RAM 下邊際 IC 成本。  
- xsec 路徑與边际 IC 的具體接線差異（已建議首批 N/A）。  
- `scripts/gap1_b1_mutation_probe.sh` 是否可直接改裝為 gap2 probe（只確認慣例存在）。

---

STATUS: DONE
