brief-kind: consult

# GAP-2a／2b 偵察 consult — COMPOSER R1

**task-id**: `20260818-GAP2-X-CONSULT-R1`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-recon-BRIEF.md`  
**date**: 2026-08-18

---

## Verdict

**可進 SPEC 起草**（無根本 BLOCKING）；SPEC 須先鎖定三項設計決策再寫 Task：

1. **邊際 IC 定義**＝train 段擬合投影、test 段套用的 **rank-aware partial IC**（Spearman 預設：先 rank 再 OLS 殘差，再對 label rank 算 Spearman）；禁把現有 `gram_schmidt` 正交 Q 列或 raw OLS 殘差直接當邊際 IC。
2. **倖存者契約（2b）**＝新建 `survivor_output_contract.json` + `sample_scope` 結構體（非裸枚舉），綁定 `RowMaskPlan`／`SelectionScope`；`provenance` 最小集對齊 GAP-1 五鍵模式。
3. **scope 分批**：B1 純函式＋oracle（可單獨上線）→ B2 組合 IC → B3 契約＋持久化 → B4 orchestrator 接線（預設 off）。

**NON-BLOCKING 須寫進 SPEC**：stage6 已在 test 算冗餘相關 vs 邊際 IC train-fit 的 S 語意對齊；`composite_ic` vs `best_single_ic` 須 F-IC-4 block bootstrap CI；新 report 節須擴 `ic_report_contract.json`（brief「可不碰前端」僅指無新圖表，非免契約／wiring）。

---

## §0 挑戰前提（brief 逐條）

| 前提 | 標記 | 本輪結論 |
|---|---|---|
| `sample_scope` repo 零命中 | fact-verified | **成立**（`grep -rn sample_scope … \| wc -l` → `0`，本輪複驗） |
| `gram_schmidt` 回 Q 列、residual 只算 var 後丟棄 | fact-verified | **成立**（`factor_orthogonalizer.py:43-62`） |
| `deny_factor_in_ok_oos` 擋 `FactorModuleResult` full_sample | fact-verified | **成立**（`contracts.py:1956-2012`）；**新邊際 IC 模組若 `oos_guarantees=True` 且不掛 factor module 語意則不觸發** |
| IC 倖存者無 ML 下游消費 | fact-verified | **成立**（指定路徑 grep → `0`） |
| IC metadata 無獨立 provenance／config_hash 欄 | fact-verified | **成立**；`config_hash` 嵌在 `selection_scope.scope_id`（`ic_filter_orchestrator.py:3134-3135`） |
| 邊際 IC＝train 投影 residual IC（偏秩相關版） | assumed | **部分推翻**：raw OLS residual + Spearman **不等** rank-then-project（探針 Δ≈0.12）；SPEC 須明寫 method 分支 |
| 組合 IC 只需 equal_z／ic_weighted、OLS 屬 ML | assumed | **成立但須 train-only 估權**；ic_weighted 權重必須來自 train 段 ICIR／IC mean，test 只報 composite_ic |
| train-fit／test-apply + `pit_stats` 原語足夠 OOS | assumed | **成立**（`pit_train_fit` :551-581 已覆蓋 mask-fit 模式）；投影係數為靜態 OLS **不需** rolling；rolling warm-up（`:2917-2933`）僅擋 stage4 rolling IC，不擋點態 test 殘差 IC |
| 契約落 report 新節 + JSON；可不碰前端圖表 | assumed | **部分推翻**：無圖表 OK，但 `ic_report_contract.json#report_sections` 與 `ic_wiring_check` R3 五節鍵 **必須**同步擴充，否則 Phase 3 後會紅 |
| forward stepwise 預設 off/on | assumed | **建議預設 off**（研究 opt-in）；on 時須固定 S 擴充順序（ICIR 降序）並文件化 Gram-Schmidt 式順序依賴 |

---

## 必答 1–8

### 1. 邊際 IC 定義與統計正確性

**建議定義（Spearman 預設）**：設已選集合 \(S\)，候選 \(f\)。在 **train** 上對 \((\mathrm{rank}(f), \mathrm{rank}(S))\) 做 OLS，得殘差 \(\tilde f\)；在 **test** 上用 train 係數算 \(\tilde f_{\mathrm{test}}\)；**marginal_ic** \(=\) Spearman\((\tilde f_{\mathrm{test}}, \mathrm{rank}(y_{\mathrm{test}}))\)。**gross_ic** \(=\) Spearman\((f_{\mathrm{test}}, y_{\mathrm{test}})\)。**ic_retained_ratio** \(=\) marginal_ic / gross_ic（gross≠0 時）。

| 替代定義 | 與邊際 IC 關係 | 陷阱 |
|---|---|---|
| Gram-Schmidt Q 列 IC | 非邊際；Q 是全域正交基，非「相對 S 的增量」 | 順序依賴（`factor_orthogonalizer.py:122-142` ICIR 排序）；full-sample `dropna` |
| raw OLS 殘差 + Spearman | Pearson 偏相關的秩近似，**非** Spearman 偏相關 | 探針：同數據 raw vs rank-then-OLS 差 ≈0.12 |
| Δ(composite_IC) | 組合層增量，非單因子邊際 | 權重估計洩漏若未 train-only |

**S 順序**：forward stepwise 天然順序依賴 ⇒ SPEC 固定 **ICIR 降序** 擴充 S（與現有 redundancy `tiebreaker=icir` 一致）；報告須輸出 `selection_order: list[str]`。文獻：Grinold & Kahn (*Active Portfolio Management*) 邊際 contribution／orthogonal factor 思想；Qian et al. 多因子正交與 incremental signal；LdP 強調 OOS 估計與過擬合控制——邊際 IC 是 **exploratory 秩信號**，不能替代 FDR 閘。

### 2. OOS 紀律

**train-fit／test-apply 足以標 `oos_guarantees=True`**（對邊際 IC／組合 IC 模組），條件：投影／z-score 參數／ic 權重 **僅** train 估計；test 只 transform。實作應走 `pit_train_fit`（`pit_stats.py:551-581`）或等價顯式 mask，禁 full-sample `dropna(how="any")`。

- **PIT expanding／rolling**：投影係數為有限維 OLS，**不需要** expanding 版；rolling 僅當要做 **rolling marginal IC 時間序列** 時才用 `pit_stats` rolling 原語（本票 2a 可不做）。
- **`deny_factor_in_ok_oos`**：只 deny `module∈{orthogonalization,exposure}` 且 `oos_guarantees=False`（`contracts.py:2005-2012`）；新 `marginal_ic` 結果應為 **IC 統計節**／plain dict，**不要**包進 `FactorModuleResult`。
- **rolling warm-up**：stage4 `:2917-2933` 在 test 列不足時 skip；新 stage 若不算 rolling IC 則不觸發；若算 rolling marginal 須共用 `_adjust_rolling_windows` 與 min_test_rows 邏輯。
- **cache 鍵**：新模組須含 `pit_stats_version`+`fit_mode`+`selection_scope.scope_id`+method，防 cross-run 污染。

### 3. 多因子組合

單標的縱向語意下 **有意義** 的組合：**equal_z**（train 估 μ/σ → test z-score → 等權平均）、**ic_weighted**（train ICIR 或 IC mean 為權 → test 線性合）。**無意義／越界**：cross-sectional rank 組合、test 段重估權重、OLS/Ridge 組合（ML 層）。

**composite_ic vs best_single_ic**：必須並列，且依 `docs/TEST_DESIGN_CHARTER.md` **F-IC-4**（自相關>0.1 → block bootstrap）與 **F-IC-8**（train vs test diff+CI）對 **差值** 給 CI；否則不可宣稱 composite 優於 best single。

### 4. 落點

**建議**：stage6 **之後** 新增可選 stage6b（marginal IC + 可選 forward stepwise）與 stage6c（composite IC），輸入 `stage6_results["filtered_df"].columns` + `split_context` + `stage5 passed_features` 語意上的 S。

- **deep-analysis 模組**：不適合作為邊際 IC 主落點（與 stage4–6 割裂、難共用 `selection_scope`）。
- **`refilter`／`analyze_full`**：須在 `fit_mode=full_sample` 時標 `analysis_status=degraded_full_sample`、邊際 IC 節 `capability_status=unavailable`（與現有 orthogonalization `export_scope=in_sample_research_only` 對稱）。
- **cross-sectional**：本票 out of scope；xsec 分支維持 `unavailable`。
- **report 節**：`marginal_ic_analysis`、`composite_ic_analysis` 用 `capability_status` ref（`ic_report_contract.json:4-11`），禁裸 `{}`。

### 5. 倖存者輸出契約（2b）

**提案欄位**（消費端理由）：

| 欄位 | 消費端需要 |
|---|---|
| `schema_version` | fail-closed 解析 |
| `survivor_features: list[str]` | ML `selected_features` 將來直接讀 |
| `sample_scope: {kind, row_mask_plan_ref?, event_def_hash?}` | 序列 full vs 事件子樣本；**禁**裸 `full\|event` 枚舉 |
| `selection_scope_id` | 對齊 FDR universe／BH m |
| `config_hash` | 重現門檻／FDR 設定 |
| `features_path` + `features_content_hash` | 防 stale HDF5 |
| `label_horizon` + `label_spec_hash` | ML 對齊 y 語意 |
| `symbol` + `timeframe` + `base_universe_hash` | 單標的身份 |
| `split_method` + `analysis_status` + `oos_guarantees` | 能否進 ok_oos 管線 |
| `pass_class` / `eval_status` 快照 | 倖存原因可追溯 |
| `generated_at` + `source_task_id` | 與 `save_filtered_features` attrs 對齊 |
| `ic_snapshot: {per_feature: {ic_test, marginal_ic?, q_value}}` | 審計／UI 不必重算 |
| `provenance: {status, reason, n_semantics, …}` | 對齊 GAP-1 五鍵（`strategy_validation_contract.json:131-139`） |

**`sample_scope` 形狀**：結構體 `kind: "full" \| "event" \| "feature_filter"` + 可選 `RowMaskPlan` 序列化（`source∈{split,event,feature_filter,full}`，`contracts.py:682-697`）+ `event_def_hash`（事件定義 canonical hash，非 GAP-3 實作）。

**與現有 DTO**：`SelectionScope` **複用**（嵌入 `selection_scope_id`）；`FilteredFeatureSet` **不擴**（內部 DTO）；`ICArtifactSchema` **平行**（per-feature 長表 vs 倖存者清單短 JSON）；新建 `SurvivorOutputContract` validator。

**ML 消費（只描述）**：`xgboost_batch_service.start_batch_analysis(selected_features=…)`（`:221-226`）將來讀 `ic_survivors_{case_id}.json` 的 `survivor_features`；`pattern_extractor` 仍要獨立 `SplitPlan`（`:100-110` fail-closed），契約只保證特徵名＋樣本範圍一致。

### 6. 測試策略

| Oracle | 預期 |
|---|---|
| candidate = S 中線性組合 | marginal_ic ≈ 0 |
| candidate ⊥ S（構造）且與 y 相關 | marginal_ic ≈ gross_ic |
| label 置亂（test） | marginal_ic ≈ 0（F-IC-6） |
| 特徵×c 單調變換 | Spearman marginal 不變 |
| composite equal_z，兩完全相關因子 | composite_ic ≈ 單因子 |
| 契約 round-trip | JSON → validator → 缺 `sample_scope` fail-closed |

**Mutation**（改壞須 FAIL）：train 係數洩漏到 test 擬合；`oos_guarantees=True` 卻 full-sample fit；survivor JSON 缺 `features_content_hash` 仍 export；`deny_factor_in_ok_oos` 路徑塞入 research-only orthogonalization。

### 7. scope 分批

| 批 | 內容 | 單獨價值 |
|---|---|---|
| **B1** | `marginal_ic.py` 純函式 + oracle tests | **有** — 可單元驗證統計定義 |
| **B2** | `factor_combiner.py` + bootstrap CI | **有** — 組合 IC 可獨立 benchmark |
| **B3** | `survivor_output_contract.json` + writer + round-trip | **有** — 2b 契約可先落地，ML 仍 blocked |
| **B4** | orchestrator stage + report 節 + persist | 需 B1–B3；預設 config off |

### 8. 是否足以進 SPEC／BLOCKING

**足以進 SPEC**。無「邊際 IC 在單標縱向 IC 語意下無意義」或「split 不支援 train-fit」類根本阻塞；阻塞項是 **定義與契約未寫死**（見 findings P1-01～03），非架構不可行。

---

## Findings

## COMPOSER-R1-P1-01

**斷言**: brief 假設「train 段 OLS 投影 residual 再算 Spearman」即邊際 IC；在 Spearman 預設下，raw OLS 殘差與 rank-then-OLS 殘差可差 >0.1，兩者統計語意不同，SPEC 若不分支定義會實作錯誤。

**碼證**: 探針 `/tmp/composer-gap2-r1/spearman_marginal_probe.txt`：`ic_gross=0.5666`，`marginal_ic_raw_OLS_residual=0.5242`，`marginal_ic_rank_then_OLS=0.3997`，`delta=0.1245`；`ic_engine.compute_rolling_ic` 註解 spearman 用 PIT rank（`ic_engine.py:284-307`）。

**來源摘要**: momentum/Analysis/ic_engine.py#da4521cf2b82

[MAJOR] 信心度=High；會把 Pearson 偏相關殘差誤標為 Spearman 邊際 IC，forward stepwise 排序錯誤。修法：SPEC 鎖 `method=spearman|pearson` 兩套；spearman 路徑 rank→OLS→Spearman。

---

## COMPOSER-R1-P1-02

**斷言**: `sample_scope` 在 repo 完全不存在，2b 契約是綠地設計；不能只加枚舉字串，必須結構化並綁定 `RowMaskPlan.source` 四值閉集。

**碼證**: `grep -rn "sample_scope" momentum api frontend/src scripts | wc -l` → `0`（2026-08-18 本輪）；`RowMaskPlan.source` 閉集 `split|event|feature_filter|full`（`contracts.py:687-697`）。

**來源摘要**: momentum/core/contracts.py#8a1415d6ea01

[MAJOR] 信心度=High；裸 `sample_scope: "event"` 無法讓 ML 驗證列對齊，事件型倖存者將來必錯。修法：`sample_scope: {kind, mask_plan?, event_def_hash?}` + JSON schema。

---

## COMPOSER-R1-P1-03

**斷言**: 設計候選 3「composite_ic vs best_single_ic」未納入 F-IC-4 block bootstrap／F-IC-8 CI，在章程下不可作為唯一驗收。

**碼證**: `docs/TEST_DESIGN_CHARTER.md` L100：`F-IC-4 Newey-West/block bootstrap(自相關>0.1 必做)`；`F-IC-8 train vs test IC diff+CI(1a OOS 必報)`。

**來源摘要**: docs/TEST_DESIGN_CHARTER.md#e9be08bb5d5f

[MAJOR] 信心度=High；會產出「composite 略高於 best single」的不可證偽結論。修法：B2 測試含 block bootstrap 差值 CI；報告並列 `delta_ic` + `ci_95`。

---

## COMPOSER-R1-P2-01

**斷言**: stage6 冗餘在 `split_context` 存在時只取 `test_mask` 列算相關（`ic_filter_orchestrator.py:3318-3324`），而邊際 IC 擬在 train 擬合投影；若 S 取 stage6 輸出，兩 stage 對「已選集合」的樣本範圍不一致。

**碼證**: `_stage6_redundancy` `features_for_redundancy = features_df.loc[test_mask]`（`:3318-3324`）；邊際 IC 設計候選 1 明確 `train_mask`/`test_mask` 分離。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c

[MINOR] 信心度=Medium；不阻 SPEC，但須決策：marginal IC 的 S 來自 stage5 `passed_features`（train 語意）還是 stage6 倖存者（test 語意）。建議 **S_base=stage5 passed，forward stepwise 在 train 擴充，test 只報**；stage6 僅去冗，不當 S 的 fit 樣本。

---

## COMPOSER-R1-P2-02

**斷言**: brief「不需前端圖表」被誤讀為免改契約；新增 report 節必須擴 `ic_report_contract.json#report_sections` 並更新 `ic_wiring_check` R3 掃描集合，否則裸空或幽靈鍵。

**碼證**: 現 `report_sections` 僅六節、無 marginal/composite（`ic_report_contract.json:27-42`）；`REPORT_SECTIONS` 五鍵閉集（`ic_wiring_check.py:30-36`）；R3 掃裸空 `{}`（`:116-118`）。

**來源摘要**: momentum/Analysis/contracts/ic_report_contract.json#6937da262f34

[MINOR] 信心度=High；Phase 3 接線後 wiring 紅或契約漂移。修法：SPEC Task 明列 contract + `ic_wiring_check.py` + `types.ts` 三方同步（無新 UI 元件）。

---

## COMPOSER-R1-P2-03

**斷言**: 現有 `factor_orthogonalizer.gram_schmidt` 為 full-sample research-only（residual 變異進 metadata、序列丟棄），不可作為邊際 IC 實作捷徑；候選 5「不改語意」正確，但 SPEC 須禁止 orchestrator 用其輸出冒充 marginal_ic。

**碼證**: `dropna(how="any")` 全樣本（`factor_orthogonalizer.py:30`）；residual 僅 `np.var`（`:52-56`），輸出為 Q 矩陣（`:43-44`）；runner `oos_guarantees=False`+`consumer_deny=True`（`ic_filter_orchestrator.py:2194-2209`）。

**來源摘要**: momentum/Analysis/factor_orthogonalizer.py#989b9e4b2101

[MINOR] 信心度=High；捷徑會繼承 full-sample 洩漏與順序依賴。修法：新模組獨立路徑；orthogonalizer 僅 diagnostic。

---

## 被當成事實的未驗證假設（§0）

見上表「assumed」列三項已標 **部分推翻／須 SPEC 鎖定**；其餘 fact-verified 本輪複驗成立。

---

ASSUMPTIONS_VERIFIED: sample_scope grep=0；downstream grep=0；orthogonalizer/residual 碼讀；deny_factor_in_ok_oos；stage4 warm-up :2917-2933；pit_train_fit；Spearman 探針；ic_wiring_check 全綠  
TESTS_RUN: `grep -rn sample_scope … \| wc -l` → 0；`python3 scripts/ic_wiring_check.py` → R1a/R1b/R2/R3 全綠 rc=0；Spearman 探針見 `/tmp/composer-gap2-r1/spearman_marginal_probe.txt`；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-recon-composer.md --family composer`（收尾跑）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 consult）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼；契約欄位為提案）  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-recon-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap2-r1`；保留 `/tmp/claude-501`  
STATUS: DONE
