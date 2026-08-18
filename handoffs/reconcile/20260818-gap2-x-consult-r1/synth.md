# Reconcile — 20260818-gap2-x-consult-r1

**來源** 20260818-gap2-recon-codex.md, 20260818-gap2-recon-composer.md, 20260818-gap2-recon-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

四方共 **30 條** findings（codex 6／composer 6／grok 9＝鎖定 21 條；claude 9 為非鎖來源 `handoffs/20260818-gap2-recon-claude.md`），下列七個群集**引用全部 30 條，0 掉項**。
獨立性註記：composer（15:10）與 grok（15:11）於 claude 版（15:09 寫入 handoffs）近乎同時交件；codex 交件最晚且 runlog 顯示掃過 `handoffs/`，其 C1 洞見（test 樣本已被 selection 消費）為 claude／composer／grok 三版**皆無**，判非附和。

Verdict：可進 SPEC 起草——無架構性 BLOCKING；C1（codex 唯一提出）之處置＝SPEC 採**較嚴版**揭露契約＋train 側並列統計＋nested split 列 blocked-by 殘留；C2／C3 之定義與 OOS 紀律四方一致並寫死於 SPEC 前置裁決。

### C1 — 主線 test 樣本已被 selection 消費：邊際／組合統計不得宣稱獨立 OOS 驗證（codex 唯一提出；採較嚴版）
**引用**: CODEX-R1-P0-01, CODEX-R1-P1-03, COMPOSER-R1-P2-01, GROK-R1-P1-05, CLAUDE-R1-P0-03

**處置＝納入 SPEC 前置裁決 D3′＋契約欄位＋§N 殘留**。收斂結論：
1. 碼證成立：stage4 IC、stage5 門檻／FDR、stage6 冗餘皆於 `test_mask` 計算（orch `:2910-2916`、`:3074-3079`、`:3318-3324`），root `ok_oos` 只證明「preprocessing 未在 test 擬合」，**不**證明 test 未被選擇消費。
2. 較嚴版採納：邊際 IC／組合 IC 節之 `oos_guarantees` 沿用 root 語意（preprocessing＋投影／權重皆不在 test 擬合），但**必附**機器可讀揭露欄 `independent_oos_validation=false`＋`selection_sample="test"`（字面入契約），禁在任何輸出／前端文案宣稱「獨立 OOS 驗證」。
3. F-IC-8 落地：每個 survivor 並列 `marginal_ic_train_insample`（β̂ 於 train 擬合、於 train 評估）與 `marginal_ic`（test 評估）；`composite` 同列 train／test 兩值。
4. 輸入形狀（CODEX-R1-P1-03／COMPOSER-R1-P2-01）：新 stage 吃**完整 post-event `features_df`＋`label_series`＋`train_mask`／`test_mask`**，survivors 只取**名稱**（`filtered_df.columns`；`filtered_df` 本身為 test 切片，禁作 fit 資料）。S 之樣本語意不一致問題因此不存在（S 是名稱集合，不是樣本）。
5. Nested／frozen final test：`為何現在不做: blocked-by: IC 主路徑切分現狀 holdout-only`（registry「IC 主路徑切分現狀」節；WF/CPCV 未接主線）；觸發＝主線切分升級。

### C2 — 邊際 IC 定義：semi-partial 秩 IC，train 擬合／test 套用（四方一致）
**引用**: CODEX-R1-P1-02, COMPOSER-R1-P1-01, GROK-R1-P0-01, CLAUDE-R1-P0-02, COMPOSER-R1-P2-03, GROK-R1-P0-02, CLAUDE-R1-P0-01

**處置＝SPEC 前置裁決 D1／D2**。收斂結論：
1. 統計量命名寫死為 `semi_partial_rank_ic`（契約 `statistic` 枚舉唯一值）：各 mask 內秩→常態分數（van der Waerden）→train OLS（含截距）擬合 `z_f~Z_S`→test 殘差→Spearman 對 label。**非** raw 線性殘差（grok 探針：`tanh(2s)` 冗餘下 raw 殘差 Spearman≈0.14 假陽性、秩殘差≈0；composer 探針 Δ≈0.12）；**非** partial（label 亦殘差化）；**非** Δcomposite。
2. 三家一致：**不改** `factor_orthogonalizer.py`、**不用** `FactorModuleResult`（型別鎖 `oos_guarantees=False`、`deny_factor_in_ok_oos` 拒 orthogonalization）；新模組、新 typed 結果。
3. 順序：固定 S 之投影殘差對基底順序不變；順序依賴只在 stepwise。SPEC 報兩視角 `loo`（order-free）＋`sequential`（依 `|train_ic|` 遞減）。

### C3 — 禁 post-FDR 第二次選擇；組合＝訊號合成＋train-only 權重／符號＋paired block bootstrap CI（四方一致）
**引用**: GROK-R1-P1-01, GROK-R1-P1-04, COMPOSER-R1-P1-03, CLAUDE-R1-P1-04

**處置＝SPEC 前置裁決 D4／D5＋§N R2**。收斂結論：
1. forward-stepwise **選擇**（改變倖存者集合）預設 OFF 三家一致；主委採更嚴：本票**不實作**選擇（只報描述統計），列 `needs-research`（post-FDR 多重比較政策）。
2. 組合法限 `equal`／`ic_weighted`（|train_ic|），符號＝train IC 符號；test 只 apply；OLS／Ridge 出局（ML 層）。
3. `composite_ic` 對單因子之比較必附 paired moving-block bootstrap CI（F-IC-4／F-IC-8）；`block_len ≥ effective_horizon`；`best_single_test_ic` 只作參考欄（明標選於 test），比較基準＝`top_train_single`（train IC 最大者之 test IC）。

### C4 — `sample_scope` 為結構；倖存者契約新 JSON SoT＋嚴格欄位＋身分 hash（四方一致，欄位取聯集）
**引用**: CODEX-R1-P1-04, COMPOSER-R1-P1-02, GROK-R1-P1-02, GROK-R1-P1-03, CLAUDE-R1-P1-06

**處置＝SPEC Task 3.1（契約檔為唯一欄位列舉處）**。收斂結論：
1. `sample_scope`＝結構 `{kind, event, n_samples_*, degraded}`，`kind` ⊆ `RowMaskPlan.source`（sync 測試 AST 讀 Literal），事件 fallback ⇒ `kind=full`＋`degraded=true`。
2. 欄位聯集（codex 最嚴，採其版補齊）：symbol／timeframe／label horizon＋return_type／ordered `feature_names`＋`feature_set_hash`／`base_universe_hash`／`row_identity{train_index_hash,test_index_hash}`（用既有 `canonical_idx_hash`）／event definition hash／`features_source_hash`＋`labels_content_hash`／`config_hash`／`pit_stats_version`＋`fit_mode`／`selection_scope_id`／split（method、bounds、rows、embargo、purge）／IC 快照＋CI／status／provenance／`schema_version`／`generated_at`／`case_id`。`additional_properties=false` 全層。
3. `FilteredFeatureSet` 不升級、parquet artifact 不塞 survivor；`RowMaskPlan`／`SelectionScope` 以 digest／id 關聯。
4. `capability_status`／`reasons` 以 `*_ref` 複用 `ic_report_contract.json`（GAP-1 resolver 模式）。

### C5 — 落點＝主流程 stage 6b（三入口同步）；xsec `not_applicable`；deep 模組不適合
**引用**: GROK-R1-P2-02, CLAUDE-R1-P1-05, CLAUDE-R1-P2-08

**處置＝SPEC D7＋Task 4.1**。收斂結論：stage6 之後、stage7 之前；`analyze`／`refilter`／`analyze_full`／`_run_full_sample_fallback` 四處掛載；`refilter` 未掛即留過期數字（grok）。預設啟用與否：composer／grok 建議 OFF；主委採「計算節預設 ON（描述統計、不改選擇、O(k²n)）、選擇不做」——理由＝使用者鐵律「驗過就別預設關閉」；逃生口 `enabled=False` ⇒ 顯式 `disabled` 節。交 SPEC adversarial 續攻。

### C6 — 報告節四方同步（契約／orchestrator／wiring check／types.ts），無新圖表但不得幽靈
**引用**: CODEX-R1-P1-05, COMPOSER-R1-P2-02, GROK-R1-P2-01, CLAUDE-R1-P2-09

**處置＝SPEC Task 4.3＋B5**。收斂結論：`ic_report_contract.json#report_sections` 加 `marginal_ic`；`ic_wiring_check.REPORT_SECTIONS` 改讀契約（消除五／六節既有漂移）；主報告 `metadata.survivor_output` 只放 pointer／status／sha；`types.ts` 於 ICHC 契約段外加型別；B5 唯讀表格（使用者可於白話閘否決）。

### C7 — 測試策略：oracle 須抗 Spearman／缺失／test-fit；mutation 明列
**引用**: CODEX-R1-P1-06, CLAUDE-R1-P1-07

**處置＝SPEC §G 3／§V**。收斂結論：線性組合 oracle 只在 Pearson 空間精確 ⇒ SPEC 改用「單調冗餘（`x³`／`tanh`）⇒ 秩殘差近 0 且 raw 殘差 >0.10」與獨立參考實作 `atol=1e-12`；覆蓋 remove-projection／test-fit／reverse-mask／shuffle-S／label permutation／weight-unfreeze／hash mismatch 之 mutation；每新測試檔須 `test_mutation_*` 或具名 N/A。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01
**斷言**：目前 holdout 的 test 同時供 stage4 IC、stage5 threshold/FDR、stage6 redundancy，`_resolve_root_status` 仍可給 `ok_oos`；任何 marginal/combiner 接在此後都會把選擇結果誤標獨立 OOS。**碼證**：`ic_filter_orchestrator.py:1028-1045,3059-3228,3318-3363,1153-1176`；採用 train/validation 做選擇、凍結 final test 報告，或明確 `in_sample_research_only`/nested split。**來源摘要**：momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c
## CODEX-R1-P1-02
**斷言**：brief 的「candidate residualized against S」不可直接命名 marginal/partial IC：partial Pearson 要 residualize candidate 與 label，現有 Gram-Schmidt 還是 full-sample、順序依賴且只回傳 Q/variance；Spearman rank 後再 residualize 與 residual 後 Spearman 不是同一統計量。**碼證**：`factor_orthogonalizer.py:25-63,122-142`；契約須分 `partial_pearson`/`semi_partial`/`spearman_variant`、fit scope、intercept、排序與 S order invariance。**來源摘要**：momentum/Analysis/factor_orthogonalizer.py#989b9e4b2101；`momentum/core/contracts.py#8a1415d6ea01`。
## CODEX-R1-P1-03
**斷言**：`run_deep_analysis()` 預設以 `_filtered_features_df` 作 candidate，而 split 下 stage6 的 `filtered_df` 是 test-only；這與 train-fit/test-apply marginal projection 所需的完整 post-preprocessing/event frame 不相容，且 rolling/PIT marginal 會另需 warmup/fallback 標記。**碼證**：`ic_filter_orchestrator.py:973-990,1038-1045,1840-1847,3318-3363`；輸入應拆成 full frame、train mask、test mask、frozen survivor set，禁止把 test selection 當 fit data。**來源摘要**：momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c
## CODEX-R1-P1-04
**斷言**：目前無 `sample_scope` 欄位；event timestamps 在 report 被移除只留計數，HDF5 只存 status/OOS/time/task，ICArtifact/FilteredFeatureSet 也沒有可驗證 artifact identity，故 consumer 無法重建 exact rows 或防 stale/cross-symbol cache。**碼證**：`event_filter.py:66-105`、`ic_filter_orchestrator.py:2770-2776`、`ic_reporter.py:774-802`、`contracts.py:323-347,681-746`；新增 strict additionalProperties=false survivor envelope，至少含 row identity/event-definition/input-label/config/split/PIT hashes、scope_id、symbol/tf/horizon、ordered features、stats/CI/status。**來源摘要**：momentum/Analysis/event_filter.py#e2c89cb3ad7c；momentum/Analysis/ic_reporter.py#e7eb62b1699e；momentum/core/contracts.py#8a1415d6ea01。
## CODEX-R1-P1-05
**斷言**：新增 survivor report section 不能只加 JSON：現有 contract validator/reporter/TS `ICReport`/`ic_wiring_check.py` 都固定五節；若契約獨立，主 IC report 應只放 pointer/status，否則必須同步四方與測試，避免 frontend/consumer ghost field。**碼證**：`ic_report_contract.json:27-47`、`ic_reporter.py:315-360`、`frontend/src/lib/types.ts:2036-2165`、`scripts/ic_wiring_check.py:30-36,115-126`；目前 wiring check 已實跑只覆蓋五節。**來源摘要**：momentum/Analysis/contracts/ic_report_contract.json#6937da262f；scripts/ic_wiring_check.py#bdf0f75f4271；frontend/src/lib/types.ts#e92be7b6da87。
## CODEX-R1-P1-06
**斷言**：單一「候選是 S 的線性組合 ⇒ marginal≈0」oracle 只對明確 Pearson 線性投影/同 sample/同 schema 成立，對 Spearman、缺失、權重重估與 test-fit 不成立；缺 mutation/paired CI 會讓錯誤實作假綠。**碼證**：`docs/TEST_DESIGN_CHARTER.md:7-61,82-105` 已要求 mutation、F-IC-3/4/8、F-MC-1/2；新增測試須覆蓋 remove-projection、test-fit、reverse-mask、shuffle-S、label permutation、weight-unfreeze、hash/symbol mismatch。**來源摘要**：docs/TEST_DESIGN_CHARTER.md#e9be08bb5d5f。
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


## 戳記

（待三家 append RECONCILE-STAMP）

RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:3a79228f71db3539b23920528dafdfdd45c49b4b3ecd66e73ddc30f9669ce282 task:20260818-GAP2-X-STAMP-R1
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:3a79228f71db3539b23920528dafdfdd45c49b4b3ecd66e73ddc30f9669ce282 task:20260818-GAP2-X-STAMP-R1
RECONCILE-STAMP: codex APPROVED 2026-08-18 sha256:3a79228f71db3539b23920528dafdfdd45c49b4b3ecd66e73ddc30f9669ce282 task:20260818-GAP2-X-STAMP-R1
