# GAP-2a／2b 偵察：邊際 IC／多因子組合（純 IC 層）＋倖存因子輸出契約（IC→ML 橋契約先行）

brief-kind: consult

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
本輪輪次=R1。**四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`，勿寫 `#sha256:` 前綴）。**

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md`、`docs/IC_QUANT_GAP_REGISTRY.md` 是**無戳記診斷/登記檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 本任務是**偵察（read-only）**，不是 code review 某個 diff。**禁改碼、禁寫測試、禁寫 SPEC**；只產你自己的 consult 報告檔。
- 每一條結論都要附**可獨立重現的證據**（file:line、grep 指令與輸出、實跑 receipt）。無證據的斷言請標 `UNVERIFIED`。
- 本 brief「設計候選」節是**候選**、非裁決；歡迎逐條推翻，但推翻須附碼證或文獻。
- 使用者已裁定（2026-08-18，不受理重議）：GAP-2 拆 2a／2b；2a 純 IC 層不碰 ML、不碰事件型；2b 只交付**契約**（含 `sample_scope`＋provenance，序列型／事件型同一座橋），橋本體 blocked-by ML 層（成熟度地圖：ML／回測屬不完整層）；GAP-3 事件型另票不碰。

## 任務背景
票＝`docs/IC_QUANT_GAP_REGISTRY.md` #2a／#2b（來源 finding：CODEX-R1-P1-09、GROK-R1-P1-06；收斂檔 `handoffs/reconcile/20260817-ichc-x-consult-r1/synth.md` C9／C10／C11）。
IC 主線現況：stage4 IC → stage5 門檻＋BH-FDR → stage6 冗餘（因子間相關 greedy/hierarchical/vif）→ stage7 報告＋持久化；
**沒有**「相對已選集合帶來多少新資訊」的統計量（邊際／residual IC），**沒有**多因子組合 IC，**沒有**可被 ML 消費的倖存者輸出契約。
本偵察產出將餵給 SPEC 起草（Claude），SPEC 再交三家 adversarial。

## 審查標的（今天的碼，不是文件的轉述）
- 正交化：`momentum/Analysis/factor_orthogonalizer.py`（153 行；`gram_schmidt` :25-75、`_resolve_priority_order` :122-142）；runner `momentum/Analysis/ic_filter_orchestrator.py:2165-2211`（`fit_scope="full_sample"`、`oos_guarantees=False`、`consumer_deny=True`）
- IC 主流程：`ic_filter_orchestrator.py`（`analyze` :860-1063；stage4 :2897、stage5 :3059、stage6 :3310、stage7 :3365；`_build_report_metadata` :3690-3747；`_persist_outputs` :3789-3852）
- 冗餘：`momentum/Analysis/redundancy_filter.py`；schema `momentum/Analysis/ic_config_schema.py:132-153`（RedundancyConfig）
- PIT 原語：`momentum/Analysis/pit_stats.py`（`pit_expanding_*`、`pit_train_fit`）；rolling IC `momentum/Analysis/ic_engine.py:274`
- 契約：`momentum/Analysis/contracts/ic_report_contract.json`；`momentum/core/contracts.py`（`FactorModuleResult` :1956、`deny_factor_in_ok_oos` :1977、`RowMaskPlan` :682（`source∈{split,event,feature_filter,full}`）、`SelectionScope` :726、`FilteredFeatureSet` :340、`ICArtifactSchema` :324）；`momentum/Analysis/ic_artifact_writer.py`
- 事件樣本：`momentum/Analysis/event_filter.py`；`_stage3_event_filter` :2715-2790
- provenance 先例：`momentum/Analysis/strategy_validation/{report,reporter,pbo}.py`、`momentum/Analysis/contracts/strategy_validation_contract.json`（GAP-1）
- ML 側（只看輸入面，本票不接）：`api/services/xgboost_batch_service.py:221-243`（`selected_features: List[str]`）、`momentum/Analysis/pattern_extractor.py:77-110`（`split` fail-closed 必填）
- 前端鏡像與 wiring 閘：`frontend/src/lib/types.ts:2036-2043`、`scripts/ic_wiring_check.py`
- 測試紀律：`docs/TEST_DESIGN_CHARTER.md`（§F F-IC-1..9、F-MC-1..3；§G 章程模板）；mutation 慣例 `scripts/mutation_probe_check.sh`、`scripts/gap1_b1_mutation_probe.sh`

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: `grep -rn "sample_scope" --include="*.py" --include="*.ts" --include="*.json" momentum api frontend/src scripts | wc -l` → `0`（Claude 實跑 2026-08-18）
fact-verified: `factor_orthogonalizer.gram_schmidt` 回傳的是 QR 的 Q（正交規範化列，:43-45），逐因子 residual 只算 `np.var` 進 metadata（:52-62），**residual 序列本身丟棄**；沒有 rolling／expanding 版本；`dropna(how="any")` 全樣本 → 該檔實讀
fact-verified: `deny_factor_in_ok_oos`（contracts.py:1977-2012）於 root `analysis_status=ok_oos` 時拒絕 `module∈{orthogonalization,exposure}` 且 `oos_guarantees=False` 的節點；`FactorModuleResult` 型別鎖 `oos_guarantees: Literal[False]`、`fit_scope: Literal["full_sample"]`（:1956-1968）⇒ 現有正交化輸出**永遠進不了** ok_oos 報告
fact-verified: IC 主線倖存者無下游消費者：`grep -rn "ic_report\|ICFilterOrchestrator\|filtered_features\|summary_table" api/services/xgboost_batch_service.py momentum/Analysis/pattern_extractor.py momentum/Optimization momentum/Analysis/model_validation | wc -l` → `0`（Claude 實跑 2026-08-18）
fact-verified: `provenance` 在 `momentum/` 只出現於 `strategy_validation/{pbo,report,reporter}.py` 與 `ic_reporter.py`（一句錯誤訊息），IC 報告 metadata **無** provenance／config_hash／features_path 獨立欄；`config_hash` 只進 `selection_scope.scope_id`（orch :3134-3135）
fact-verified: `passed_features` 是 stage5 回傳的純 `list[str]`（orch :3195-3217），從未以該名持久化；持久化物＝`{symbol}_{tf}_filtered.h5`（attrs `analysis_status/oos_guarantees/source_generated_at/source_task_id`）＋ `ic_report_{case_id}.json` ＋ parquet artifact（10 欄，`schema_version=1`）
assumed: 「邊際 IC」的正確定義＝**candidate 對已選集合 S 之 residual（train 段擬合投影、test 段套用）與 label 的 IC**（等價於偏相關的秩版本），而非簡單「正交化後 IC」或「Δ 組合 IC」← 請攻：三種定義何者才回答「帶來多少新資訊」、各自統計性質與陷阱（秩相關下投影非線性、Spearman vs Pearson residual、S 的順序依賴）
assumed: 多因子組合 IC 於本票只需「無參數／少參數」組合法（等權 z-score、IC 加權、符號對齊），OLS／Ridge 權重屬 ML 層邊界之外 ← 請攻：哪個組合法在單標的縱向 IC（非橫截面）語意下才有意義；權重是否必須只在 train 段估計
assumed: 邊際 IC 與組合 IC 必須以 **train-fit／test-apply** 產出才可標 `oos_guarantees=True`；沿用現有 `split_context.test_mask` 與 `pit_stats` 原語即可，不需新增切分機制 ← 請攻：投影係數在 train 段擬合是否足夠、是否需 rolling；rolling warm-up 守衛（orch :2917-2934）會不會被新 stage 觸發 fallback
assumed: 倖存者輸出契約可落在 IC 報告新節（`report_sections` 新增一節）＋獨立 JSON 檔（單一真相源），欄位至少含：因子名清單、`sample_scope`（full／event＋事件定義 hash）、split／scope id、config_hash、features 來源 hash、`analysis_status`／`pass_class`、生成時間、schema_version ← 請攻：欄位有無漏（例如 label 語意／horizon／timeframe／symbol／`base_universe_hash`／IC 統計快照）、`sample_scope` 該用枚舉還是結構、與 `RowMaskPlan.source` 的關係
assumed: 本票不需前端圖表（可只在既有 deep-analysis 結果 JSON 揭露＋wiring 閘不紅）← 請攻：`ic_wiring_check.py` R3 五節鍵是否會因新節而要求同步、前端 types 是否必須鏡像才不算幽靈

## 設計候選（非裁決；請逐條攻）
1. 新模組 `momentum/Analysis/marginal_ic.py`（純函式）：`compute_marginal_ic(features_df, label, selected: list[str], candidates: list[str], train_mask, test_mask, method)` → 每 candidate 之 `marginal_ic`／`gross_ic`／`ic_retained_ratio`／`n_test`；投影係數 train 擬合。
2. 貪婪前向選擇（forward stepwise by marginal IC，train 段選、test 段報）作為 stage6 之後的可選 stage（預設 off？on？請表態，附理由）。
3. `momentum/Analysis/factor_combiner.py`：`combine_factors(features_df[selected], weights_method∈{equal_z, ic_weighted})` → composite series；`composite_ic`（test 段）與 `best_single_ic` 並列輸出。
4. 契約：`momentum/Analysis/contracts/survivor_output_contract.json`（欄位／枚舉單一真相源）＋ resolver；`ic_report_contract.json#capability_status` 以 ref 複用；輸出檔 `data_cache/reports/ic_survivors_{case_id}.json`。
5. 既有 `factor_orthogonalizer.py` **不改語意**（保留 full-sample research-only），新邊際 IC 走自己的 train-fit 路徑。

## 必答（逐條 verdict，附證據）
1. **邊際 IC 定義與統計正確性**：給出你認為正確的定義（公式）、與偏相關／Gram-Schmidt residual／Δcomposite-IC 的關係、在 Spearman 秩相關語意下的陷阱、S 順序依賴如何處理（固定 by ICIR？逐步？）；引用文獻（Grinold-Kahn／Qian／LdP 等）。
2. **OOS 紀律**：train-fit／test-apply 是否足以宣稱 `oos_guarantees=True`？投影是否需 PIT expanding／rolling？會不會踩 `deny_factor_in_ok_oos`／rolling warm-up 守衛／cache 鍵（`pit_stats_version`+`fit_mode`）？
3. **多因子組合**：單標的縱向 IC 語意下哪些組合法有意義；權重估計範圍；`composite_ic` 與 `best_single_ic` 的比較是否要 bootstrap CI（`docs/TEST_DESIGN_CHARTER.md` F-IC-4／F-IC-8）。
4. **落點**：新 stage 放 stage6 之後（吃 `filtered_df`）還是 deep-analysis 模組？對 `refilter`／`analyze_full`／cross-sectional 路徑的影響；報告節與 `capability_status` 枚舉如何複用不複列。
5. **倖存者輸出契約（2b）**：完整欄位清單提案（附每欄「消費端為何需要」）；`sample_scope` 的形狀（枚舉 vs 結構、如何攜帶事件定義／時間戳集合 hash）；provenance 最小集合；與 `RowMaskPlan`／`SelectionScope`／`FilteredFeatureSet`／`ICArtifactSchema` 的關係（複用／擴充／新建）；ML 側 `selected_features: List[str]` 消費者將來怎麼讀（只描述，不接）。
6. **測試策略**：邊際 IC 的可證偽 oracle（例：candidate＝已選因子的線性組合 ⇒ marginal_ic≈0；candidate 與 S 正交且與 label 相關 ⇒ marginal_ic≈gross_ic；label 置亂 ⇒ ≈0；特徵×c 秩不變）；組合 IC oracle；契約 round-trip／fail-closed 測試；哪些「改壞會 FAIL」（mutation）。
7. **scope**：一次做完 vs 分批（例：B1 邊際 IC 純函式＋oracle、B2 組合 IC、B3 契約＋持久化、B4 接線 orchestrator＋報告節）；哪批單獨上線就有價值。
8. 偵察結果是否足以進 SPEC 起草？有無 **BLOCKING**（例：現有 IC 語意下邊際 IC 根本無意義、split 機制不支援 train-fit）？

## Time-box 與範圍紀律
- 優先序＝必答 1（定義）＞ 2（OOS）＞ 5（契約）＞ 4（落點）＞ 其餘。查不完的具名列「未查」清單，**不當阻塞**。
- **不受理範圍**：治理機制與流程；前端樣式；ML 模型選型／訓練（橋本體 blocked）；事件型樣本組裝／標籤（GAP-3）；Pooled/Panel IC（registry #4）；容量／效能（#5／#6）；「應該先做別的票」排序意見。
- 提醒：本票**不是**接 ML；`sample_scope` 只是為了讓事件型倖存者將來能被正確消費而**先定義**，不是實作事件型。

## 產出
canonical 四欄 findings + 必答 1–8 的逐條 verdict + **Verdict**（可進 SPEC／BLOCKING 清單／scope 建議）。**禁改碼**（只產 consult 檔）。收尾清 /tmp workdir（保留 claude-501）。
