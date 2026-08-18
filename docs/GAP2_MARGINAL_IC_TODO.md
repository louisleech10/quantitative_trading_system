# GAP-2a 邊際 IC／多因子組合 ＋ GAP-2b 倖存因子輸出契約 — TODO

版本：**DRAFT R5**（2026-08-18；R10 TODO adversarial 三家：composer／grok sentinel「可 Frozen」、codex 1 MINOR（Phase B4 小節同文 §B）已寫回；A1-5 basic-tab 補正三家實核成立；R9 TODO adversarial 三家 7 findings 三群集全部接受：`page.tsx` 入白名單（A1-5）、Phase 各批 Gate 小節改 pointer §B＋逐字同命令、`write_failed` reason 字面封閉（A1-6）；三家皆確認 R8 十群集寫回成立、U6 駁回碼證可重現；R8：15 findings 十群集：14 接受寫回、1 駁回（CODEX-R8-P1-06 警語子字串，碼證於 `handoffs/reconcile/20260818-gap2-x-review-r8/synth.md` U6）：B5 白名單三檔（A1-4）、刪 4.1 `pass_class` 推導殘句、golden pre `case_id`＋`report_ref` 斷言、4.2 persist 顯式 kwargs＋三 caller 來源、`persist_suppressed` 五鍵 object、bench `fit_projection` spy、xsec N/A 節＋reporter 透傳、B1 gate 探針命令明列路徑＋每檔 `test_mutation_*` 名、「四處」→兩插入點；R7：gate 分跑、`summary_by_feature`＋root 注入 OOS、兩插入點＋`_in_fallback_rerun`、persist 顯式 kwargs＋`_features_path`、B5 toggle 具名 preset＋FeatureTierPanel、文案子字串、bench 觀測降級、mutation 唯一對映；SPEC 義務側擴張走延伸檔 A1-1..A1-6；待 R11 確認）｜基於 SPEC：`docs/GAP2_MARGINAL_IC_SPEC.md`（**R7 FROZEN**，2026-08-18 使用者白話閘核准；六輪三家 adversarial 收斂檔 `handoffs/reconcile/20260818-gap2-x-review-r{1..6}/synth.md` 皆三家 RECONCILE-STAMP）
｜實作端：Claude 主委自任｜review／adversarial：codex+composer+grok 三家（實作者不自審）｜SPEC 後續修訂走延伸檔 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（衝突時以延伸檔為準）

> 冷啟動原則：執行端讀完本檔即可逐 Task 寫碼，不需回讀 SPEC；SPEC 之義務以 `SPEC ref` 指回。
> 🔴 SPEC 已定案之七條前置裁決（§A D1–D7、D3′／D3″）與使用者三項裁決（2a／2b 拆分；橋本體 blocked；B5 表格＋toggle 預設開）為本 TODO 全部 Task 之上位約束，不重述、不得違反。

## §0 全域規則與約束（執行端讀完即可遵守）

- **解耦**：R1 `momentum/` 不 import `api/`（新模組全在 `momentum/Analysis/`：`marginal_ic.py`、`factor_combiner.py`、`survivor_contract.py`、`contracts/ic_survivor_contract.json`）；R3 無新 factories 出口（由 `ICFilterOrchestrator` 內部呼叫；`create_ic_analyzer()` 已覆蓋）；R5 新設定只住 `ic_config_schema.ICConfig.marginal_ic`；R6 `pytest tests/momentum/Analysis/ -q` 不需 `run_api.py`；R7 新 dataclass 住 `momentum/Analysis/`，API 以 dict 透傳、**不進** `api/models/`。
- **既有檔改動白名單（SPEC §C＋A1-4；唯此七處，其餘一律新檔）**：① `momentum/Analysis/ic_filter_orchestrator.py`（`_stage6b_marginal_ic` 於 `analyze()`／`refilter()` **兩插入點**掛載＋`_run_full_sample_fallback` 設 `_in_fallback_rerun` 旗標＋`analyze_cross_sectional()` 之 `analysis_results` 加 N/A status object＋`_stage7_report` 新節（含 root 注入）＋`_persist_outputs` 倖存者檔＋`_ic_cache` 兩鍵＋`STAGE_OVERRIDE_PATHS` 一鍵＋`_apply_tier_config` 具名 preset 消費；**不改**既有 stage 語意／既有報告鍵）② `momentum/Analysis/ic_config_schema.py`（`MarginalICConfig`＋`ICConfig.marginal_ic`）③ `momentum/Analysis/contracts/ic_report_contract.json`（**只**加 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`；**不加 reasons**；**只在 Task 4.1 與 orchestrator 同 commit**）④ `momentum/Analysis/ic_reporter.py`（加 `save_survivor_output`；`generate_json_report` 透傳 `marginal_ic` 新節——Task 4.1 同 commit）⑤ `scripts/ic_wiring_check.py`（`REPORT_SECTIONS` 改讀契約）⑥ **四檔（A1-4＋A1-5）**：`frontend/src/lib/types.ts`（ICHC 契約段**外**加型別）＋`frontend/src/store/icAnalysisStore.ts`（`marginal_ic` toggle：`PRESET_TOGGLES`＋`getEffectiveConfig` custom／具名 preset 分支）＋`frontend/src/components/ic-analysis/FeatureTierPanel.tsx`（**只**於 `TOGGLES` 加一列＋計數分母）＋`frontend/src/app/ic-analysis/page.tsx`（**只**加 `MarginalICTable` import＋**basic** `TabsContent` 末段 `CorrelationHeatmap` 之後掛載（A1-5 補正：deep tab 受 gating）；資料源 base `report?.marginal_ic`）⑦ 上述對應既有測試（只加斷言）。**不改** `factor_orthogonalizer.py`、`redundancy_filter.py`、`ic_engine.py`、`pit_stats.py`、`momentum/core/contracts.py`。
- **成熟度約束**：`api/services/xgboost_*`、`momentum/Analysis/model_validation/`、`momentum/Optimization/` 之內部結構**不得作為設計依據**；2b 契約只定義「讀檔→驗欄位」，**不接**任何 ML 呼叫。
- **不可違反原則**：不弱化 NaN/inf gate（逐列 finite 過濾＋`n_used`，禁 fillna）；不擅改輸出大小（既有報告鍵集不變）；真實資料 golden 用 `tests/golden/la0/inputs/ETHUSDT_12h_*_a0_tail2000.h5`（經 `tests/momentum/helpers/ichc_run.run_analyze()`），禁合成 fixture 冒充；統計 oracle 只用 SPEC §G 規格表之合成**因子／label 序列**（章程 §F 允許；禁合成價格）。
- **禁取巧**：投影／標準化／組合權重與符號**只**在 `train_mask` 估計；`fit_scope` 由呼叫方 typed 傳入，函式**禁**由 masks 形狀猜；不得用 test 段任何統計量做排序／符號／權重；不得依邊際 IC 改動倖存者集合（D4）；不得為過測改既有斷言；不得放寬 §G 容差或「重新凍結 pre 檔」換綠。
- **OOS 揭露鎖定（D3′）**：`marginal_ic` 節與倖存者檔恆帶 `independent_oos_validation=false`、`selection_sample="test"`、`oos_semantics=<契約唯一字面>`；任何輸出／前端文案禁「獨立 OOS 驗證」字樣。
- **JSON SoT**：所有新欄位名／枚舉／reason 字面**只**住 `momentum/Analysis/contracts/ic_survivor_contract.json`（Task 1.0）；程式以 `load_survivor_contract()` 讀取對照；SPEC／TODO／註解不複列鍵表（本 TODO 以「契約鍵 `X`」指稱者皆為 pointer）。
- **Logging**：`get_logger(__name__)`；純函式內部**不 log**；只在 orchestrator stage／reporter 層 log。
- **每 Task 交付紀律**：新測試檔須含 `test_mutation_*` 或行首 `# MUTATION-PROBE: n/a — <理由>`（`bash scripts/mutation_probe_check.sh <該批新測試檔路徑…>`——**必帶路徑**，無參數 rc=1；每個新增 Python 測試 Task 之驗證欄已指定其 `test_mutation_*` 名，R8 CODEX-R8-P1-09）；§V mutation 由 `scripts/gap2_mutation_probe.sh --batch Bn` 實跑貼 rc；`bash -n scripts/*.sh` rc=0；每批一 commit；每批收尾固定順序：pytest → 探針 → commit → push（背景）→ 白話 5 檔同步 → commit+push（使用者 2026-08-18 定）。
- **執行端跑驗收時主控端不得動檔**（CLAUDE.md Gotchas）；mutation 探針持 `.claude/gate/gap2_mutation_probe.lock` 互斥。

## §B 批次執行策略（依賴拓撲 → 五批；每批＝一次實作＋一輪三家 code review＋戳記）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1** | 1.0、1.1、1.2、1.3 | 無 | 契約 SoT 先行＋邊際 IC 純函式＋oracle＋探針腳本；批內順序 1.0→1.1→1.2→1.3 | 中 |
| **B2** | 2.1、2.2 | B1（1.0 契約鍵、1.1 原語、1.2 bootstrap 搬移） | 組合 IC＋paired block bootstrap CI | 小 |
| **B3** | 3.1、3.2 | B1／B2 之 dataclass `to_dict()` 鍵集 | 契約 resolver／validator／`build_survivor_output`＋conformance／tamper 測試；**不改** `ic_report_contract.json` | 中 |
| **B4** | 4.0（golden 凍結）、4.1、4.2、4.3 | B1／B2／B3 | 主流程 stage 6b 兩插入點掛載＋fallback 旗標＋xsec N/A＋報告新節＋契約增鍵（同 commit）＋倖存者檔＋golden＋wiring 改讀契約＋預算 bench receipt；批內順序 4.0→4.1→4.2→4.3 | 大 |
| **B5** | 5.1 | B4 | 前端型別鏡像＋toggle（預設開）＋唯讀表格＋vitest | 小 |

- **批次間 Gate**：B1→B2：`pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` rc=0 **且** `pytest tests/momentum/Analysis/test_marginal_ic.py -q` rc=0（兩條分開跑；R7 COMPOSER-R7-P1-01／CODEX-R7-P1-04：共用 `-k` 會把後者整檔 deselect） ＋ `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py` rc=0（R8 CODEX-R8-P1-09：必帶路徑）＋ `bash scripts/gap2_mutation_probe.sh --batch B1` rc=0 ＋ 三家 review CLOSED＋戳記；
  B2→B3：`pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` rc=0 ＋ `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` rc=0 ＋ `--batch B2` rc=0 ＋ 三家 review CLOSED＋戳記；
  B3→B4：`pytest tests/momentum/Analysis/test_survivor_contract.py -q` rc=0 ＋ `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` rc=0 ＋ `--batch B3` rc=0 ＋ **既有** `pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q` 仍綠（證 B3 未動 report 契約）＋ 三家 review CLOSED＋戳記；
  B4→B5：`pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/Analysis/test_ichc_wiring_check.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` rc=0 ＋ `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py` rc=0 ＋ `bash scripts/ic_wiring_check.sh` rc=0 ＋ `venv/bin/python scripts/gap2_freeze_golden.py --check` rc=0 ＋ `--batch B4` rc=0 ＋ 三家 review CLOSED＋戳記；
  **B5 收尾**：`cd frontend && npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx` 全綠 ＋ `npm run build` rc=0 ＋ `npx tsc --noEmit` rc=0 ＋ `bash scripts/ic_wiring_check.sh` rc=0（含新 toggle）＋ §V **24** 條 mutation 全部實跑貼 rc ＋ 三家 review CLOSED＋戳記 → 收案。
- **每 Batch 派工 prompt**（實作者＝Claude 自己，仍寫出供 review brief 引用）：「前置狀態：<上一批 commit sha、gate 命令 rc=0>；本批 Task：<列>；驗證命令：<列>；白名單外檔一律不碰；mutation 實跑貼 rc；殘留表 registry「GAP-2 待補完」附審。」

---

## Phase B1 — 契約 SoT＋邊際 IC 純函式＋oracle（目標：欄位唯一列舉處落地；semi-partial 秩 IC 可獨立驗證）

### Task 1.0 — 契約 JSON SoT 先行（`票 GAP-2/K1`）
- SPEC ref：Task 1.0　目標：所有新欄位名／枚舉／reason 字面只在一檔出現，B1／B2 dataclass 直接對照它。
- 輸入 / 輸出：新檔 `momentum/Analysis/contracts/ic_survivor_contract.json`；`survivor_contract.py::load_survivor_contract() -> dict`。
- 實作要點：
  1. 頂層鍵**恰為**：`version`（=1）、`_doc`、`capability_status_ref`（`"momentum/Analysis/contracts/ic_report_contract.json#capability_status"`）、`reasons`（兩組：節級 `marginal_ic`＝`[no_holdout_split, insufficient_test_rows, insufficient_train_rows, no_survivors, cross_sectional_mode, disabled_by_config, candidate_budget_exceeded, all_zero_train_ic]`；feature 級 `marginal_ic_feature`＝`[residual_degenerate, zero_train_ic, insufficient_rows]`；另 `survivor_output`＝`[identity_missing, write_failed]`——**此處為唯一列舉，程式與測試皆讀檔**）、`algorithm_version`（`"gap2_marginal_ic_v1"`）、`survivor_file_keys`、`sample_scope_keys`、`sample_scope_kind_values`（`["full","event"]`）、`event_definition_keys`、`event_identity_keys`、`split_keys`、`row_identity_keys`、`provenance_keys`、`survivor_record_keys`、`marginal_ic_section_keys`（子鍵 `section_keys`／`per_feature_keys`／`sequential_keys`／`composite_keys`／`removed_candidate_keys`／`budget_keys`）、`statistic_values`（`["semi_partial_rank_ic"]`）、`projection_space_values`（`["rank_normal"]`）、`weights_method_values`（`["equal","ic_weighted"]`）、`view_values`（`["loo","sequential","removed_candidates"]`）、`fit_scope_values`（`["train","full_sample"]`）、`selection_sample_values`（`["test"]`）、`oos_semantics_values`（唯一值 `"preprocessing_and_fit_excluded_test;selection_used_test;not_independent_oos"`）、`independent_oos_validation_allowed`（`[false]`）、`survivor_output_status_keys`（五鍵 `status,reason,path,sha256,case_id`；`nullable: ["reason","path","sha256"]`）。
  2. 每個 `*_keys` 之值＝`{"<key>": {"type": "<str|int|float|bool|list|object|null>", "required": true|false, "nullable": true|false}}`，物件層皆 `"additional_properties": false`。`survivor_file_keys` 頂層必含（pointer；鍵名以檔為準）：`schema_version`／`generated_at`／`case_id`／`symbol`／`timeframe`／`analysis_status`／`oos_guarantees`／`pass_class`／`independent_oos_validation`／`selection_sample`／`oos_semantics`／`statistic`／`projection_space`／`algorithm_version`／`sample_scope`／`split`／`provenance`／`feature_names`／`feature_set_hash`／`survivors`／`composite`／`removed_candidates`／`status`／`reason`。
  3. `_doc` 逐字含：(a) 「`sample_scope.kind=event` 之倖存者只得於事件樣本訓練」(b) 「消費端須同時讀 `oos_guarantees`／`independent_oos_validation`／`oos_semantics`／`analysis_status` 四欄，禁只憑 `oos_guarantees` 判 OOS」(c) event canonical 序列化：「timestamps → int64 epoch ms UTC → sorted unique → JSON 陣列無空白（`json.dumps(list, separators=(",",":"))`）→ sha256；query 模式 `definition_hash=sha256(query.strip().encode("utf-8"))`、`timestamps_hash=null`；無事件 ⇒ 兩者 null」。
  4. `load_survivor_contract()`：`json.loads`；頂層鍵集 `==` 上列集合否則 `ContractValidationError`（複用 `ic_config_schema.ContractValidationError`）；回 dict（不解析 ref；ref 於 Task 3.1）。
- 修改檔案：新增契約檔＋`survivor_contract.py`（僅 loader）　既有 caller：無。
- 不可做：不得加 `reasons_ref`；不得動 `ic_report_contract.json`；不得在他處複列鍵表；不得把 `sample_scope` 降為字串。
- 邊界：① 檔缺 ⇒ raise ② JSON 壞 ⇒ raise ③ 頂層多／少鍵 ⇒ raise ④ `independent_oos_validation_allowed != [false]` ⇒ raise。
- 風險緩解：契約鍵集由測試 ① 鎖死，B4 增鍵須改測試（可見）。
- 驗證：`tests/momentum/Analysis/test_survivor_contract.py -k load`：① 頂層鍵集 `==` ② `capability_status_ref` 手動 split `#` 讀 `ic_report_contract.json` 該鍵 == `contract_enum("capability_status")` ③ `independent_oos_validation_allowed == [False]` ④ `oos_semantics_values` 恰一值且 `reasons` 三組非空 ⑤ 每 `*_keys` 之鍵皆帶 `type`／`required` ⑥ `sample_scope_kind_values` ⊆ AST 解析 `momentum/core/contracts.py` 內 `RowMaskPlan.source` 之 `Literal[...]` 值集（`ast.parse` 找 `ClassDef RowMaskPlan` → `AnnAssign source` → `Subscript Literal` 之 `Constant` 值）⑦ tamper：tmp 複本刪一頂層鍵 ⇒ raise。mutation：`test_mutation_missing_top_key_raises`（⑦ 即為探針）。
- **存活至**：全票完工後保留；未來 ML 橋之唯一輸入契約。
- **覆蓋風險**：無（Task 3.1 只加 resolver／validator；B4 只改 report 契約）。

### Task 1.1 — 秩常態分數＋train-fit 投影原語（`票 GAP-2/C2`）
- SPEC ref：Task 1.1　目標：D1 兩個原語為純函式；投影參數只能來自呼叫方切好的 train 陣列。
- 輸入 / 輸出：`marginal_ic.py::normal_scores(x: np.ndarray) -> np.ndarray`；`::fit_projection(z_target: np.ndarray, z_basis: np.ndarray) -> Projection`（frozen dataclass：`beta: np.ndarray`（含截距，長度 `1+k`）、`condition_number: float`、`r2_train: float`、`n_train: int`）；`::apply_residual(z_target, z_basis, projection) -> np.ndarray`。
- 實作要點：
  1. `normal_scores`：`x` 一維、`np.isfinite(x).all()` 否則 `ValueError`；`n<2` ⇒ `ValueError`；`r = scipy.stats.rankdata(x, method="average")`；`return scipy.stats.norm.ppf(r/(n+1))`。
  2. `fit_projection`：`X = np.column_stack([np.ones(n), z_basis])`（`z_basis` 形狀 `(n,k)`，`k` 可為 0 ⇒ `X` 只有截距欄）；`beta, *_ = np.linalg.lstsq(X, z_target, rcond=None)`；`condition_number = float(np.linalg.cond(X))`；`r2_train = 1 - ss_res/ss_tot`（`ss_tot==0` ⇒ `r2_train = 0.0`）；長度不符 ⇒ `ValueError`。
  3. `apply_residual`：`X_test = np.column_stack([np.ones(m), z_basis])`；`return z_target - X_test @ projection.beta`；欄數與 `beta` 長度不符 ⇒ `ValueError`。
  4. 三函式**無** mask 參數、**無** `fit_on_full` 參數；不 log。
- 修改檔案：新增 `momentum/Analysis/marginal_ic.py`（本 Task 只放三函式＋`Projection`）　既有 caller：無。
- 不可做：不得回退 raw 值投影；不得在函式內決定 mask；不得吞 NaN。
- 邊界：① 全相同值（ties 全部 ⇒ `normal_scores` 全 0）② n=1／n=2 ③ 共線 basis（`condition_number` 極大但**不 raise**；由 1.2 依殘差退化判）④ 空 basis（k=0）。
- 風險緩解：⊘
- 驗證：`tests/momentum/Analysis/test_marginal_ic.py -k "scores or projection"`：① `normal_scores(x)` 與 `normal_scores(x**3)`（x 全正）／`normal_scores(2x+1)` `atol=1e-12` 相等 ② n=5000 常態樣本：`|mean|<1e-9`、`std∈[0.95,1.0]` ③ `z_target=2·z_b+1` ⇒ `beta≈[1,2]`（`atol=1e-10`）、`r2_train≈1` ④ 空 basis ⇒ 殘差 == `z_target-mean`（`atol=1e-12`）⑤ 含 NaN ⇒ raise。mutation：`test_mutation_raw_scores_break_monotone_invariance`（把 `normal_scores` 換恆等 ⇒ ① 紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 1.2 — `compute_marginal_ic()`（loo＋sequential＋removed_candidates）（`票 GAP-2/C1,C2,C5`）
- SPEC ref：Task 1.2（含 D1／D3／D3′／D3″／D4）　目標：semi-partial 秩 IC 完整計算＋gate＋bootstrap CI＋typed 結果；`fit_scope` 必填。
- 輸入 / 輸出：`compute_marginal_ic(features_df: pd.DataFrame, label: pd.Series, *, train_mask: np.ndarray|None, test_mask: np.ndarray|None, survivors: list[str], extra_candidates: list[str] = (), params: MarginalICParams, fit_scope: Literal["train","full_sample"]) -> MarginalICResult`。`MarginalICParams`（frozen：`min_test_rows`、`min_rows_per_regressor`、`degenerate_threshold`、`n_bootstrap`、`block_len`、`seed`、`weights_method`、`max_survivors_for_loo`、`max_removed_candidates`）。`MarginalICResult`（frozen；`to_dict()` 鍵集 == 契約 `marginal_ic_section_keys.section_keys`；`per_feature[name]` 鍵集 == `per_feature_keys`；`sequential[i]` == `sequential_keys`；`removed_candidates[name]` == `removed_candidate_keys`；`budget` == `budget_keys`）。
- 實作要點：
  1. **fit_scope 守衛**：`fit_scope=="train"` 且 `train_mask is None` ⇒ 節 `not_applicable:no_holdout_split`；`fit_scope=="train"` 且 `train_mask.all() and test_mask.all()` ⇒ `ValueError("fit_scope=train with all-True masks")`；`fit_scope` **只描述投影擬合窗**；`oos_guarantees`／`pass_class` **不由本函式推導**：結果欄 `oos_guarantees=None`、`pass_class=None` 佔位，由 orchestrator `_stage7_report` 於 `_resolve_root_status` 後**注入 root 值**（單一來源；R7 GROK-R7-P1-02：事件不足 fallback 下 holdout 仍在但 root=`degraded_full_sample`）；純函式測試以 `MarginalICResult.with_root(analysis_status)` helper 填入（`ok_oos`⇒True/`oos`；否則 False/`full_sample_research_only`）。
  2. **預算 gate（先於任何計算）**：`len(survivors)==0` ⇒ `not_applicable:no_survivors`；`len(survivors) > max_survivors_for_loo` ⇒ `loo`＋`sequential` 整體 `not_computed:candidate_budget_exceeded`（`per_feature={}`、`sequential=[]`）；`len(extra_candidates∖survivors) > max_removed_candidates` ⇒ `removed_candidates` 整體同 reason；`budget={max_survivors_for_loo, max_removed_candidates, n_survivors, n_removed_candidates}`；`n_regressions` 只累計實際 `fit_projection` 呼叫次數。
  3. **train_ic**（排序／符號用）：對每 survivor `f`：train 段 `f,y` 皆有限之列 → `spearmanr` → `train_ic[f]`（NaN 若 `<2` 列或 std=0）；`sequential` 順序＝`sorted(survivors, key=lambda n: (-abs(train_ic[n]) if finite else 0.0, n))`。
  4. **單候選計算** `_one(f, S)`：`cols=[f]+S+[label]`；train 列＝`train_mask & finite(all cols)`；test 列同理；`n_used_train`／`n_used_test`；gate：`n_used_test < min_test_rows` 或 `< min_rows_per_regressor*len(S)` ⇒ 該 f `not_computed:insufficient_rows`（train 同）；`z_f_tr, Z_S_tr = normal_scores(...)`（**train 列內**）；`proj = fit_projection(z_f_tr, Z_S_tr)`；`z_f_te, Z_S_te = normal_scores(...)`（**test 列內**）；`r_te = apply_residual(z_f_te, Z_S_te, proj)`；**先** `var(r_te) <= degenerate_threshold` ⇒ `not_computed:residual_degenerate`（**禁**先算 Spearman）；否則 `marginal_ic = spearmanr(r_te, y_te)`、`gross_ic = spearmanr(f_te_raw, y_te)`、`ic_retained_ratio = marginal_ic/gross_ic if abs(gross_ic)>=1e-12 else None`；`r_tr = apply_residual(z_f_tr, Z_S_tr, proj)`、`marginal_ic_train_insample = spearmanr(r_tr, y_tr)`（`var(r_tr)` 退化 ⇒ None）；`ci95 = block_bootstrap_ci(lambda a,b: spearmanr(a,b)[0], (r_te, y_te), block_len=params.block_len, n_bootstrap=params.n_bootstrap, seed=params.seed)`（B1 先內建於 `marginal_ic.py`，B2 Task 2.1 搬至 `factor_combiner.py` 並由此 import）；`condition_number`／`r2_train`＝`proj` 欄。
  5. `loo`：對每 survivor `f`：`S=[s for s in survivors if s!=f]`（**依名稱**，禁位置）；`sequential`：依步驟 3 順序，第 i 個之 `S=order[:i]`；`removed_candidates`：對每 `c ∈ extra_candidates∖survivors`：`S=survivors`。
  6. 結果頂層：`status`／`reason`／`fit_scope`／`oos_guarantees`／`pass_class`／`statistic="semi_partial_rank_ic"`／`projection_space="rank_normal"`／`independent_oos_validation=False`／`selection_sample="test"`／`oos_semantics=<契約唯一值>`／`algorithm_version`／`views`／`per_feature`／`sequential`／`removed_candidates`／`train_ic`／`n_train`／`n_test`／`n_regressions`／`budget`。字面值一律由 `load_survivor_contract()` 讀出（如 `oos_semantics_values[0]`），**不寫死於程式**。
  7. `block_bootstrap_ci`（moving-block，成對）：`n=len(a)`；`block_len<=0` ⇒ `ValueError`；`rng=np.random.default_rng(seed)`；每次抽 `ceil(n/block_len)` 個起點 `rng.integers(0, n-block_len+1)`，串接切至 n；統計量非有限者略過；`(np.quantile(stats,0.025), np.quantile(stats,0.975))`；`n_bootstrap==1` 亦可跑。
- 修改檔案：`momentum/Analysis/marginal_ic.py`（加 `MarginalICParams`／`MarginalICResult`／`compute_marginal_ic`／暫時之 `block_bootstrap_ci`）　既有 caller：無（B4 接）。
- 不可做：不得依邊際 IC 改動 `survivors` 順序以外之任何選擇；不得用 test 段統計量做排序／符號／權重；不得 fillna；不得由 masks 形狀推 `fit_scope`；不得先算 Spearman 再判退化。
- 邊界：① `survivors` 空 ② 單一 survivor（loo 之 S=∅ ⇒ marginal==gross）③ 全部候選退化 ④ test 段 label 全 NaN（⇒ insufficient_rows）⑤ `extra_candidates` 與 survivors 重疊（去重）⑥ 常數因子（`normal_scores` 全 0 ⇒ 退化）⑦ `n_test` 恰等於下限（通過）⑧ 超預算。
- 風險緩解：所有 oracle 之產生器參數寫死於 SPEC §G 規格表（測試 helper `_gen(oracle_id)` 逐字實作該表）。
- 驗證：`tests/momentum/Analysis/test_marginal_ic.py`：§G O1a（`residual_degenerate`；且 raw 空間探針：同資料不做 `normal_scores` 之線性殘差 `var>1e-3`——證 raw 下非退化）／O1b（degenerate 或 `|marginal|≤0.02`）／O2（`|marginal−gross|≤0.02`）／O3（`S=∅` exact）／O5（Bonferroni 門檻 `norm.ppf(1-0.05/(2k))/sqrt(n_test)`）／O6（`f×c`、`f³` exact）／O7（獨立 numpy 參考實作 `atol=1e-12`；test-fit 版差 `>0.3`；`train_insample` 與 `marginal_ic` 差 `>0.3`）／O9（CI 含點估；同 seed exact；`block_len=0` raise）；另 ⑧ `sequential[0].marginal_ic == per_feature[sequential[0].feature].gross_ic` ⑨ `|survivors|=1` ⇒ loo `marginal==gross` ⑩ 三種節級 reason＋`fit_scope=train` 全 True raise ⑪ `to_dict()` 各鍵集 == 契約 ⑫ `gross<0, marginal≈gross ⇒ ratio≈1`（`atol=1e-6`）⑬ 洗牌 `survivors` ⇒ loo exact 不變、sequential 順序不變 ⑭ 超 `max_survivors_for_loo` ⇒ loo/sequential 整體 not_computed 且 `per_feature=={}`；超 `max_removed_candidates` ⇒ removed 整體 not_computed、loo 不受影響、`n_regressions` 不含 ⑮ **`fit_projection` 獨立 spy（R8 CODEX-R8-P1-07）**：`monkeypatch.setattr(marginal_ic, "fit_projection", <包裹原函式之計數器，並記每次 `Z_S.shape[1]`>)`；正常 k survivors＋m removed ⇒ spy count == `res.n_regressions` == `2k+m`（loo k＋sequential k＋removed m），每次欄數 `≤ k`；超 `max_survivors_for_loo` ⇒ spy count == 0（loo／sequential 全略過）；只超 `max_removed_candidates` ⇒ spy count == `2k`（removed 視角無任何 fit call）。mutation §V-1／2／3／4／5／6／17a／18／21／22a ⇒ 由 `scripts/gap2_mutation_probe.sh --batch B1` 實跑轉紅；檔內 `test_mutation_test_fit_projection_breaks_o7`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：`block_bootstrap_ci` 於 Task 2.1 搬移至 `factor_combiner.py`（同票刻意合併；本檔改 import，測試不變）。

### Task 1.3 — B1 mutation 探針腳本（`票 GAP-2/C7`）
- SPEC ref：Task 1.3　目標：§V-1..V-6、V-17a（train_insample 半條）、V-18、V-21、V-22a（純函式預算）可重跑證紅（V-22 orch 端於 B4）。
- 輸入 / 輸出：`scripts/gap2_mutation_probe.sh --batch B1|B2|B3|B4|B5` → rc 0／1／2／3；log `handoffs/run_receipts/<TS>-gap2-<batch>-probe.log`。
- 實作要點：
  1. 沿用 `scripts/gap1_b1_mutation_probe.sh` 骨架：`mkdir .claude/gate/gap2_mutation_probe.lock` 互斥（持有 ⇒ rc=3）；`$BACKUP_DIR` 複本還原（**非** `git checkout`）；每 case：`sed -i` 一行 → `pytest <file> -q -x -k <test>` → 斷言 rc==1 且輸出含 `FAILED`（rc==2 collection error ⇒ 探針 FAIL）→ 還原 → 斷言綠。
  2. case 表寫在腳本頂部（`V_ID|file|sed_expr|pytest_target`），**B1 十條唯一對映**（R7 CODEX-R7-P1-04／GROK-R7-P1-04）：V-1（`fit_projection` 呼叫端改傳 test 陣列→`test_o7_train_fit`）、V-2（`normal_scores` 改恆等→`test_o1a_residual_degenerate`）、V-3（`spearmanr`→`pearsonr`→`test_o6_rank_invariance`）、V-4（loo 條件集含 f→`test_o2_orthogonal_new_info`）、V-5（sequential 排序改 test IC→`test_sequential_order_by_train_ic`）、V-6（bootstrap 忽略 seed→`test_o9_bootstrap_seed_determinism`）、V-17a（`train_insample` 改 test 評估→`test_o7_train_insample_differs`）、V-18（loo 條件集依欄位位置→`test_shuffle_survivors_invariance`）、V-21（degenerate gate 移後→`test_o1a_residual_degenerate`）、V-22a（`max_survivors_for_loo` 超限仍輸出部分 per_feature→`test_budget_survivors_whole_not_computed`）。後續批次只加列；**每 V_ID 全票唯一**：V-22（orch 端 removed 預算）／V-24（`survivor_output` 五鍵）只在 B4。
  3. mutation 目標行不存在 ⇒ rc=2 且不留髒檔（先 `grep -c` 再 sed）。
- 修改檔案：新增 `scripts/gap2_mutation_probe.sh`　既有 caller：無。
- 不可做：不得並行跑兩份；不得在 probe 中放寬測試；不得跳過還原後綠檢。
- 邊界：① 鎖被持有 ② 未追蹤檔還原 ③ 目標行缺。
- 風險緩解：`bash -n` 語法檢；動 `scripts/` 須同步白話 5 檔（`plain_docs_sync_check`）。
- 驗證：`bash scripts/gap2_mutation_probe.sh --batch B1` rc=0；log 逐條 `MUTATION V-n: RED ✓ / RESTORED GREEN ✓`；`bash -n scripts/gap2_mutation_probe.sh` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B1 測試 ＋ Gate
- **單一來源＝§B「B1→B2」列（R9 V2：Phase 小節不得另寫命令）**，逐字：`pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` rc=0 **且** `pytest tests/momentum/Analysis/test_marginal_ic.py -q` rc=0（分開跑）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py` rc=0（**必帶路徑**）；`bash scripts/gap2_mutation_probe.sh --batch B1` rc=0；三家 code review CLOSED＋戳記。

## Phase B2 — 多因子組合 IC（目標：訊號合成＋paired block bootstrap CI）

### Task 2.1 — `combine_factors()` 與 `composite_ic`（`票 GAP-2/C3`）
- SPEC ref：Task 2.1（D5）　目標：等權／`ic_weighted` 合成、train-only 符號權重、test 評估、對 `top_train_single` 之 delta 附 CI。
- 輸入 / 輸出：`factor_combiner.py::combine_factors(features_df, label, *, train_mask, test_mask, survivors, params: MarginalICParams, fit_scope: Literal["train","full_sample"]) -> CompositeResult`（frozen；`to_dict()` 鍵集 == 契約 `composite_keys`）；`::block_bootstrap_ci(...)`（自 1.2 搬入，簽名不變）。
- 實作要點：
  1. `fit_scope` 守衛同 Task 1.2 步驟 1；`k=len(survivors)==0` ⇒ `not_applicable:no_survivors`。
  2. complete-case：test 列＝`test_mask & finite(survivors+label)`；`n_used_test < min_test_rows` ⇒ `not_computed:insufficient_test_rows`。
  3. `train_ic_i`＝train 列 `spearmanr(f_i, y)`；`sign_i = np.sign(train_ic_i)`；`sign_i==0` 或 NaN ⇒ 排除並記 `excluded[name]="zero_train_ic"`；全排除 ⇒ `not_computed:all_zero_train_ic`。
  4. `z_i`＝test 列 `normal_scores(f_i)`；`w`：`equal ⇒ 1/k'`、`ic_weighted ⇒ |train_ic_i|/Σ|train_ic|`（`k'`＝未排除數）；`composite = Σ w_i·sign_i·z_i`；`composite_ic = spearmanr(composite, y_te)`；`composite_ic_train_insample`＝同權重／符號於 train 列（`normal_scores` 於 train 列）評估。
  5. `top_train_single`＝`argmax|train_ic|` 之因子名，其 test IC；`best_single_test_ic`＝test 段 `max|spearmanr(f_i,y)|`（欄 `selected_on="test"`，只作參考）；`delta_vs_top_train_single = composite_ic − top_train_single_test_ic`；`delta_ci95`＝成對 block bootstrap（同一 block 索引重抽 `(composite, f_top, y)` 三列，統計量＝兩 Spearman 之差）。
  6. 結果欄：`status`／`reason`／`method`／`weights`（dict）／`signs`／`excluded`／`composite_ic`／`composite_ic_train_insample`／`top_train_single`／`top_train_single_test_ic`／`best_single_test_ic`／`best_single_feature`／`delta_vs_top_train_single`／`delta_ci95`／`n_used_test`／`n_used_train`／`fit_scope`／`oos_guarantees`。
- 修改檔案：新增 `momentum/Analysis/factor_combiner.py`；`marginal_ic.py` 改 `from momentum.Analysis.factor_combiner import block_bootstrap_ci`　既有 caller：Task 1.2。
- 不可做：不得在 test 段估權重／符號；不得提供 OLS／Ridge；不得把 `best_single_test_ic` 當比較基準。
- 邊界：① k=1 ② 全 `train_ic=0` ③ complete-case 為空 ④ `n_bootstrap=1` ⑤ `ic_weighted` 下權重和 `==1`。
- 風險緩解：⊘
- 驗證：`tests/momentum/Analysis/test_factor_combiner.py`：§G O4（規格表 seed 20260818；`Σmarg²/composite²∈[0.90,1.10]`、`composite_ic∈[0.55,0.61]`、各 marg∈[0.26,0.31]、`ic_weighted` vs `equal` `atol=1e-3`）／O8（`S={f}` ⇒ `composite_ic == sign(train_ic)·gross_ic` `atol=1e-12` 含負 IC 案例；`f2=f1` ⇒ 同；等 train IC 下兩法 `atol=1e-12`）／O9；另 ① 兩相同因子等權 ⇒ `composite_ic == sign·gross`（`atol=1e-12`）② 一因子 train_ic<0、test 同號 ⇒ 對齊版 composite_ic > 未對齊版（構造）③ `weights` 和 `==1`（`atol=1e-12`）④ `delta_ci95` 含點估 ⑤ 同 seed exact ⑥ `block_len=0` raise ⑦ `to_dict()` 鍵集 == 契約；Task 1.2 測試搬移後仍綠。mutation §V-7／8／9（B2 探針）；檔內 `test_mutation_test_sign_breaks_o8`（monkeypatch 符號改由 test 段估 ⇒ O8 負 IC 案例紅）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 2.2 — B2 mutation 探針（`票 GAP-2/C7`）
- SPEC ref：Task 2.2　目標：§V-7（符號用 test IC）／V-8（權重用 test IC）／V-9（`block_len` 強制 1）入 `--batch B2`。
- 輸入 / 輸出：`scripts/gap2_mutation_probe.sh` case 表加三列。
- 實作要點：同 Task 1.3。
- 修改檔案：`scripts/gap2_mutation_probe.sh`　既有 caller：無。
- 不可做：同 1.3。
- 邊界：同 1.3。
- 風險緩解：⊘
- 驗證：`bash scripts/gap2_mutation_probe.sh --batch B2` rc=0。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B2 測試 ＋ Gate
- **單一來源＝§B「B2→B3」列**，逐字：`pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` rc=0；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` rc=0；`bash scripts/gap2_mutation_probe.sh --batch B2` rc=0；三家 code review CLOSED＋戳記。

## Phase B3 — 倖存因子輸出契約 resolver／validator／組裝（GAP-2b 交付物）

### Task 3.1 — resolver／validator／`build_survivor_output`（`票 GAP-2/C4`）
- SPEC ref：Task 3.1（D6；R2 L3／L4；R4 N1）　目標：fail-closed 讀取與純函式組裝；消費端義務機器可驗；**不改** `ic_report_contract.json`。
- 輸入 / 輸出：`survivor_contract.py::resolve_ref(ref: str) -> list`；`::validate_survivor_output(payload: dict, *, report_meta: dict|None=None, report_ref_path: str|None=None) -> None`；`::build_survivor_output(*, report_meta, filtered_features: list[str], marginal_ic_result: MarginalICResult|None, composite_result: CompositeResult|None, summary_by_feature: dict[str, dict], root_analysis_status: str, event_identity: dict, split_context: dict|None, config_hash: str, features_source_hash: str, features_path: str, labels_content_hash: str, symbol: str, timeframe: str, case_id: str, generated_at: str, fit_mode: str, pit_stats_version: str, ic_method: str, label_horizon: int, label_return_type: str, report_ref: str) -> dict`。
- 實作要點：
  1. `resolve_ref("<repo 相對路徑>#<a.b.c>")`：路徑相對 repo root（`Path(__file__).resolve().parents[2]`）；檔不存在／鍵路徑不存在 ⇒ `ContractValidationError`；回 list。
  2. `validate_survivor_output`：讀契約；遞迴驗每物件層：required 齊、無未知鍵（`additional_properties:false`）、型別、nullable；枚舉：`sample_scope.kind∈sample_scope_kind_values`、`statistic`／`projection_space`／`fit_scope`／`selection_sample`／`oos_semantics` ∈ 各值集；`independent_oos_validation ∈ independent_oos_validation_allowed`（即必 False）；`kind=="event"` 而 `event is None` ⇒ raise；OOS 四欄互斥：`oos_guarantees=True` ⇔ `analysis_status=="ok_oos"` ⇔ `pass_class=="oos"`；`degraded_full_sample` ⇔ `full_sample_research_only` ⇔ `oos_guarantees=False`；否則 raise；`feature_set_hash == sha256(json.dumps(feature_names, separators=(",",":")).encode()).hexdigest()` 否則 raise；`survivors[i].feature_name` 序列 == `feature_names`；身分：`report_meta` 給定 ⇒ `payload.symbol == report_meta["symbol"]` 且 `payload.timeframe == report_meta["timeframe"]`（`report_meta` 缺任一鍵 ⇒ raise，**禁** `None==None`）；`report_ref_path` 給定 ⇒ `Path(report_ref_path).name == f"ic_report_{payload['case_id']}.json"` 否則 raise。
  3. `build_survivor_output`：純組裝（不寫檔、不 log）：`sample_scope`＝`{kind: "event" if event_identity.mode in ("query","timestamps") and not fallback else "full", event: {definition_hash, timestamps_hash, mode, n_events, n_timestamps_requested} or None, n_samples_total, n_samples_test, degraded: bool(fallback)}`；`split`＝`{split_method, train_time_bounds, test_time_bounds, train_rows, test_rows, embargo, purge_gap, base_universe_hash, selection_scope_id, row_identity:{train_index_hash: canonical_idx_hash(train_plan.row_index), test_index_hash: canonical_idx_hash(test_plan.row_index)}}`（無 split ⇒ bounds/rows 以 full 表述、index hash 對全 index）；`provenance`＝`{config_hash, features_source_hash, features_path, labels_content_hash, pit_stats_version, fit_mode, ic_method, label_horizon, label_return_type, report_ref, producer:"ic_filter_orchestrator", contract_version, algorithm_version}`；`survivors[]`＝每 name：`{feature_name, ic_mean, icir, p_value_adj, pass_class, train_ic, gross_ic, marginal_ic_loo, marginal_ic_loo_ci95, marginal_ic_train_insample, redundancy_kept: True}`（IC 快照自 `report_meta`／`summary_table` 由呼叫方預先抽成 dict 傳入 `summary_by_feature`——**加此參數**）；`composite`＝`composite_result.to_dict()` 或 status 物件；`removed_candidates`＝`marginal_ic_result.removed_candidates`；頂層 OOS 四欄＋`selection_sample`／`oos_semantics`／`statistic`／`projection_space`／`algorithm_version`；`status`／`reason`（無 survivors ⇒ `not_applicable:no_survivors`）。
  4. **不**在本 Task 讀 `report_ref` 檔；validator 之身分對照由呼叫方傳 `report_meta`／`report_ref_path`（B4 傳入）。
- 修改檔案：`momentum/Analysis/survivor_contract.py`（加三函式）　既有 caller：無（B4 接）。
- 不可做：不得改 `ic_report_contract.json`；不得在他處複列鍵表；不得把 `sample_scope` 降為字串；不得接 ML。
- 邊界：① 空 survivors ② degraded root ③ 事件 fallback ④ ref 指向不存在檔／鍵 ⑤ `event_timestamps=None`（query 模式）⑥ `report_meta` 缺 symbol。
- 風險緩解：C4 checklist 常數在測試內，⑭ 機檢 ⊆ 契約鍵集。
- 驗證：`tests/momentum/Analysis/test_survivor_contract.py`：① round-trip（用 B1／B2 合成結果組裝 ⇒ 過 validator）② 缺 required ⇒ raise ③ 未知鍵 ⇒ raise ④ kind 枚舉外 ⇒ raise ⑤ kind=event 而 event None ⇒ raise ⑥ `oos_guarantees=True` 而 `analysis_status!=ok_oos` ⇒ raise ⑦ kind_values ⊆ RowMaskPlan.source（AST）⑧ `capability_status_ref` 解析 == `contract_enum`；不存在檔／鍵 ⇒ raise ⑨ `marginal_ic_section_keys` 各子集 == B1／B2 `to_dict()` 鍵集 ⑩ 各物件層 tamper 加鍵 ⇒ raise ⑪ `independent_oos_validation=True` ⇒ raise ⑫ `feature_set_hash` 不符 ⇒ raise ⑬ （B4）`row_identity.test_index_hash == canonical_idx_hash(test_plan.row_index)` ⑭ checklist ⊆ 契約鍵 ⑮ 身分三欄：symbol／timeframe 與 `report_meta` 不符或缺 ⇒ raise；`case_id` 與 `report_ref_path` 檔名段不符 ⇒ raise；三欄各自篡改／缺失／正常 ⑯ `oos_semantics` 非唯一字面 ⇒ raise ⑰ `ok_oos`＋`oos_guarantees=False`、`pass_class` 不一致 ⇒ raise ⑱ 同 timestamps 亂序／重複 ⇒ 相同 `timestamps_hash`；query 模式 `timestamps_hash is None`。mutation §V-10／11／12／17b（validator 半）／19（三欄）／20 ⇒ `--batch B3`（V-24 屬 B4 Task 4.2）；檔內 `test_mutation_validator_skips_feature_set_hash`。
- **存活至**：全票完工後保留；未來 ML 橋之唯一輸入契約讀取器。
- **覆蓋風險**：無。

### Task 3.2 — B3 mutation 探針（`票 GAP-2/C7`）
- SPEC ref：Task 3.2　目標：§V-10..V-12、V-17b（validator 半條）、V-19（三欄）、V-20 入 `--batch B3`（V-24 於 B4）。
- 輸入 / 輸出：`scripts/gap2_mutation_probe.sh` case 表加列。
- 實作要點：同 Task 1.3；V-19 以三個 case（symbol／timeframe／case_id）各自 sed。
- 修改檔案：`scripts/gap2_mutation_probe.sh`　既有 caller：無。
- 不可做：同 1.3。
- 邊界：同 1.3。
- 風險緩解：⊘
- 驗證：`bash scripts/gap2_mutation_probe.sh --batch B3` rc=0（V-19 三 case 各 rc=1／還原 rc=0）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B3 測試 ＋ Gate
- **單一來源＝§B「B3→B4」列**，逐字：`pytest tests/momentum/Analysis/test_survivor_contract.py -q` rc=0；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py` rc=0；`bash scripts/gap2_mutation_probe.sh --batch B3` rc=0；**既有** `pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q` 仍綠；三家 code review CLOSED＋戳記。

## Phase B4 — 主流程接線＋報告節＋持久化＋golden（目標：三入口一致、契約增鍵同 commit、改前==改後可證偽）

### Task 4.0 — §G pre 檔凍結（`票 GAP-2/§G`；**動工順序第一**）
- SPEC ref：§G 凍結時機　目標：在改 orchestrator 前記錄基準。
- 輸入 / 輸出：`scripts/gap2_freeze_golden.py`（`--write`／`--check`）→ `handoffs/run_receipts/gap2_golden_pre.json`；`::gap2_canonical_sha(report: dict) -> str`（**唯一**序列化實作，測試 import）。
- 實作要點：
  1. `gap2_canonical_sha`：`r = copy.deepcopy(report)`；有序 scrub：① `r.pop("marginal_ic", None)` ② `r["metadata"].pop("survivor_output", None)` ③ `metadata` 刪 `filtered_features_path`／`filtered_generated_at`／`generated_at`／`filtered_features_written`；頂層刪 `generated_at` ④ 其餘沿用 `tests/momentum/helpers/ichc_run.canonical_sha` 之序列化（import 之，不重寫）。
  2. `--write`：`run_analyze()`（預設 config；`case_id` 由 helper 決定＝`_resolve_case_id(metadata)` 實值 `ic_gatekeeper`，**不改 helper**——A1-2）→ 寫 `{fixture_sha256, config_hash, case_id, canonical_sha, summary_table (list), filter_log:{stage5_thresholds, stage6_redundancy}, generated_by, ts}`（**`case_id` 欄必寫**，R8 CODEX-R8-P1-03／GROK-R8-P1-01）；`--check`：重跑比對 `case_id` exact、`canonical_sha` exact、`summary_table` 逐鍵 `abs≤1e-12`、`filter_log` 兩節 exact；差異 ⇒ 印鍵＋diff、rc=1。
  3. 路徑無關性：`--check` 於兩個不同 sidefx 目錄各跑一次，兩 sha 相等否則 rc=1。
- 修改檔案：新增 `scripts/gap2_freeze_golden.py`（先 commit pre 檔，再動 4.1）　既有 caller：無。
- 不可做：不得重新凍結換綠；不得在 scrub 清單外多刪鍵。
- 邊界：① pre 檔缺 ⇒ `--check` rc=2 ② fixture sha 不符 ⇒ rc=1 ③ sidefx 目錄不可寫。
- 風險緩解：pre 檔 commit 於本 Task 獨立 commit（可審計）。
- 驗證：`venv/bin/python scripts/gap2_freeze_golden.py --write` rc=0 且檔存在；`--check` rc=0（改動前自對照）；`bash -n` N/A（python）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 4.1 — `MarginalICConfig`＋stage 6b 兩插入點掛載＋fallback 旗標＋xsec N/A＋契約增鍵（同 commit）（`票 GAP-2/C5,C6,K1,L2,L4,L5`）
- SPEC ref：Task 4.1（D7；K1；K3；L2；L4；L5；N2）　目標：三入口＋fallback 一致；`fit_scope` typed；`event_identity` 入 cache；預算 gate；契約節鍵與組裝字面同 commit。
- 輸入 / 輸出：`ic_config_schema.py::MarginalICConfig(enabled=True, min_test_rows=30(ge10), min_rows_per_regressor=5(ge1), degenerate_threshold=1e-10, weights_method: Literal["equal","ic_weighted"]="equal", n_bootstrap=1000(ge1,le20000), bootstrap_seed=20260818, include_removed_candidates=True, max_survivors_for_loo=200(ge1), max_removed_candidates=200(ge0))`＋`ICConfig.marginal_ic`；`ic_filter_orchestrator.py::_stage6b_marginal_ic(features_df, label_series, stage5_results, stage6_results, split_context, config, *, fit_scope) -> dict`。
- 實作要點：
  1. `_stage6b_marginal_ic`：`enabled=False` ⇒ `{"status":"disabled","reason":"disabled_by_config"}`（**非**裸 `{}`）；`survivors=list(stage6_results["filtered_df"].columns)`；`extra=[f for f in stage5_results["passed_features"] if f not in survivors] if include_removed_candidates else []`；masks：holdout ⇒ `split_context["train_mask"/"test_mask"]`、`fit_scope="train"`；fallback ⇒ `np.ones(n,bool)` 兩者、`fit_scope="full_sample"`；無 split 且非 fallback ⇒ `not_applicable:no_holdout_split`；`block_len=max(effective_horizon, ceil(n_test**(1/3)))`；`params=MarginalICParams(...)` 自 config；`res=compute_marginal_ic(...)`；`comp=combine_factors(...)`；回 `{**res.to_dict(), "composite": comp.to_dict()}`——**`oos_guarantees`／`pass_class` 維持 `None` 佔位，本函式不推導**（A1-3；R8 CODEX-R8-P1-02／GROK-R8-P1-02：刪除 R2 之「`oos` iff `fit_scope=="train"`」句），只由步驟 2 之 `_stage7_report` 注入 root 值。**xsec 路徑（R8 CODEX-R8-P1-08）**：`analyze_cross_sectional()` 之 `analysis_results` 於現五節 `_xsec_na` 旁（`:1518-1536`）加 `"marginal_ic": dict(_xsec_na)`（＝`{status:"not_applicable", reason:"cross_sectional_mode"}`）；**禁**於 xsec 呼叫 `_stage6b_marginal_ic`／計算函式；`ic_reporter.generate_json_report` 透傳（白名單④）：`if "marginal_ic" in analysis_results: report["marginal_ic"] = analysis_results["marginal_ic"]`——**缺鍵時省略該鍵、不得寫裸 `{}` 預設**（既有 10 處直接呼叫 reporter 之測試傳最小 `analysis_results`，不得為此改既有斷言）；orchestrator 三路徑（analyze／refilter／xsec）保證恆給 status object，故 `run_analyze()` 產出之報告恆含 `marginal_ic`（wiring R3／contract sync 以此為 oracle）。
  2. 掛載**兩個插入點**（R7 COMPOSER-R7-P2-02／CODEX-R7-P1-01）：`analyze()` stage6 後、stage7 前（現 `:1039-1047` 之後）；`refilter()` stage6 後、`_stage7_report` 前（現 `:1746-1754`）。`analyze_full()` 經 `analyze` 自動覆蓋。**fallback 判定唯一機制（R7 GROK-R7-P0-03）**：`_run_full_sample_fallback()` 於遞迴呼叫 `analyze()` 前設 `self._in_fallback_rerun = True`（`try/finally` 還原 False；`__init__` 初始 False）；`_stage6b` 邏輯：`if self._in_fallback_rerun: fit_scope="full_sample", masks=all-True` `elif split_context is None: not_applicable:no_holdout_split` `else: fit_scope="train"`。`_stage7_report`：於 `_resolve_root_status(report_meta)` 後呼叫 `self._inject_root_oos(section, analysis_status, oos_guarantees)`（獨立可 patch 之 helper：`section["oos_guarantees"]=oos_guarantees`、`section["pass_class"]="oos" if analysis_status=="ok_oos" else "full_sample_research_only"`；只對 `status=="ok"` 之節注入；root 單一來源），再組報告；**persist 順序**：`_persist_outputs` 於 `_ic_cache` 建立前被呼叫（現 `:3437`），故新增 kwargs `stage6b_results`／`event_identity`／`features_path`／`label_series` **顯式傳入**（不讀 `_ic_cache`）；`_ic_cache` **只在 persist 完成後**承接 immutable snapshot：`_ic_cache["stage6b_results"]=<注入後之節 deepcopy>`、`_ic_cache["event_identity"]=self._event_identity`；`analyze()` 入口存 `self._features_path=features_path`、`self._labels_path=labels_path`（供 refilter 路徑）。
  3. `event_identity`：於 `_stage3_event_filter` **pop timestamps 之前**計算 `{mode: "timestamps"|"query"|"none", definition_hash, timestamps_hash, n_events, n_timestamps_requested}`（序列化規格＝契約 `_doc`；helper `survivor_contract.compute_event_identity(query, timestamps)`）→ `_ic_cache["event_identity"]`（不可變 dict）；deep／refilter cache key 含 `event_identity` 之 hash（既有 cache key 組裝處加一段）。
  4. `STAGE_OVERRIDE_PATHS["marginal_ic"]=("marginal_ic","enabled")`（供 B5 toggle 與 wiring R1b）。
  5. **同 commit** 修 `ic_report_contract.json`：`report_sections.marginal_ic={"status_object_keys":["status","reason"]}`；`metadata.survivor_output_keys=["status","reason","path","sha256","case_id"]`。**不加 reasons**。
  6. reason 字面：orchestrator **一律** `load_survivor_contract()["reasons"]` 取值（不寫死；R7 COMPOSER-R7-P2-01／GROK-R7-P1-05）；測試⑫＝執行路徑產出之 reason ∈ 契約集合（load 路徑），另可選 AST 掃描 `_stage6b_marginal_ic` 內字串常數 ⊆ 契約（若無常數則 vacuous 通過亦可）。
- 修改檔案：`ic_config_schema.py`、`ic_filter_orchestrator.py`（`_stage6b_marginal_ic`／兩插入點／`_run_full_sample_fallback` 旗標／`analyze_cross_sectional` N/A 節／`_stage7_report`／`_apply_tier_config`／`STAGE_OVERRIDE_PATHS`）、`ic_reporter.py`（`generate_json_report` 透傳）、`contracts/ic_report_contract.json`　既有 caller：三入口既有測試（`tests/momentum/test_ic_filter_orchestrator.py`、`tests/momentum/Analysis/test_ic1d_orchestrator_integration.py`、`tests/momentum/Analysis/test_ichc_*`）——動工前 diff 斷言，禁放寬。
- 不可做：不得改 stage4–6 既有輸出；不得做成 deep 模組；不得於 xsec 路徑呼叫計算；不得加 reasons 進 report 契約；不得由 masks 推 `fit_scope`；不得於 `_stage6b_marginal_ic` 內以 `fit_scope` 推 `oos_guarantees`／`pass_class`（唯 `_stage7_report` root 注入）；reporter 不得對缺鍵補裸 `{}`。
- 邊界：① 無 survivors ② 單 survivor ③ n_test 低於下限 ④ cache-hit `refilter` ⑤ `include_removed_candidates=False` ⑥ 超預算 ⑦ 缺 symbol。
- 風險緩解：§G-1 golden 於 4.0 已凍結；本 Task 每步跑 `gap2_freeze_golden.py --check`。
- 驗證：`tests/momentum/Analysis/test_gap2_stage6b_wiring.py`＋`test_ichc_contract_sync.py`：① 預設 config `run_analyze()` ⇒ `report["marginal_ic"]["status"]=="ok"`、`fit_scope=="train"`，且 **`oos_guarantees`／`pass_class` 與 root 一致為 oracle**：`report["analysis_status"]=="ok_oos"` ⇒ `(True,"oos")`（R8 U2：不以 `fit_scope` 為 oracle）② `enabled=False` ⇒ `status=="disabled"` 且鍵集恰 `{status,reason}` ③ 強制 fallback ⇒ `oos_guarantees is False`、`fit_scope=="full_sample"`、root `degraded_full_sample`；③′ **holdout 存在但事件不足 fallback**（`_stage3_event_filter` 設 `metadata.event_filter.fallback=True`（現 `:2781`）、`_run_full_sample_fallback` **未**觸發、split 仍 applied ⇒ root `degraded_full_sample`）⇒ 節 `fit_scope=="train"` **但** `oos_guarantees is False`、`pass_class=="full_sample_research_only"`（root 單一來源；A1-3——此 case 即證 `fit_scope` 不可推 OOS 欄） ④ `refilter()` 後 `per_feature` 鍵集 == 新 `filtered_df.columns` ⑤ `deny_factor_in_ok_oos(report)` 不 raise ⑥ `test_r6_wider_contract_nodes_consistent` 綠 ⑦ 節 sha256 兩次相等 ⑧ 既有斷言未放寬（diff 附 commit）⑨ `bash scripts/ic_wiring_check.sh` rc=0 ⑩ cache 命中後 `refilter()` ⇒ 鍵集 == 新 columns 且 `_ic_cache["stage6b_results"]` sha 與命中前不同 ⑪ 同上⑥ ⑫ orchestrator marginal reason 字面 ⊆ 契約 reasons ⑬ 同 request analyze→refilter 兩次 `event_identity` 相等；換 request 不沿用舊 cache ⑭ 缺 symbol ⇒ `metadata.survivor_output.status=="computation_failed"`、reason `identity_missing`、`marginal_ic` 節仍 ok ⑮ 超 `max_survivors_for_loo` ⇒ loo＋sequential 整體 not_computed 無部分值；超 `max_removed_candidates` ⇒ removed 整體 not_computed、loo 不受影響、`n_regressions` 不含 ⑯ **xsec（R8 CODEX-R8-P1-08）**：以 xsec 輸入跑 `analyze_cross_sectional()` ⇒ `report["marginal_ic"] == {"status":"not_applicable","reason":"cross_sectional_mode"}`（exact），且 `_stage6b_marginal_ic` 未被呼叫（spy count 0）；`bash scripts/ic_wiring_check.sh` R3 對 xsec 報告不報裸空。mutation §V-13／14／22 ⇒ `--batch B4`；檔內 `test_mutation_fit_scope_derived_oos_breaks_root_oracle`（重現 R2 bug：monkeypatch `_inject_root_oos` 為恆等＋`_stage6b_marginal_ic` 依 `fit_scope=="train"` 填 `oos_guarantees=True/pass_class="oos"` ⇒ ③′ 紅；還原綠）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 4.2 — 倖存者檔持久化＋報告 metadata 鏡像（`票 GAP-2/C4,L3,N1`）
- SPEC ref：Task 4.2（L3；N1；P1）　目標：2b 契約檔落地並與報告互指；三形狀五鍵。
- 輸入 / 輸出：`ic_reporter.py::save_survivor_output(payload: dict, output_dir: str, case_id: str) -> str`；`_persist_outputs` 寫 `report_meta["survivor_output"]`（五鍵）。
- 實作要點：
  1. `save_survivor_output`：`validate_survivor_output(payload)` → tmp 檔寫入 → `os.replace` 至 `output_dir/ic_survivors_{case_id}.json` → 回路徑；例外向上拋。
  2. `_persist_outputs`：`case_id=self._resolve_case_id(metadata)`；`symbol=metadata.get("symbol")`、`timeframe=metadata.get("timeframe")`；缺任一 ⇒ **不組裝不寫檔**、`survivor_output={status:"computation_failed", reason:"identity_missing", path:None, sha256:None, case_id}`；否則 `payload=build_survivor_output(..., report_ref=f"ic_report_{case_id}.json", summary_by_feature=..., event_identity=event_identity, stage6b_results=stage6b_results, features_path=features_path, label_series=label_series, ...)`——**四者皆為 `_persist_outputs` 之顯式 kwargs（R8 U4：CODEX-R8-P1-04／GROK-R8-P0-02／COMPOSER-R8-P1-01），禁讀 `self._ic_cache`（persist 時尚未建立）**；三 caller 之參數來源：(a) `_stage7_report`（`analyze()`／`analyze_full()`／fallback 遞迴皆經此）：`stage6b_results=analysis_results["marginal_ic"]`（注入後）、`event_identity=self._event_identity`（本 request 於 stage3 計算）、`features_path=self._features_path`、`label_series=<本輪 label Series>`；(b) `refilter()` → `_stage7_report`：同 (a)，`self._event_identity`／`self._features_path` 沿用同 request 之值（測試⑬）；(c) **fallback wrapper** `_run_full_sample_fallback`（現 `:1142`；內層 analyze 以 `_suppress_persist` 跳過，wrapper 於 root 重註 degraded 後為唯一寫出點）：先 `self._inject_root_oos(report["marginal_ic"], "degraded_full_sample", False)` 重注入（與 `_annotate_root_status_and_pass_class` 同點，保 validator ⑰ 一致），再 `stage6b_results=report["marginal_ic"]`、`event_identity=self._event_identity`、`features_path=self._features_path`、`label_series=self._ic_cache["label_series"]`（此處 `_ic_cache` 已由內層 analyze 建立，與現行讀 `features_df` 同源，合法）；`_persist_outputs` 只此二呼叫點（`:1142`／`:3432`），若實作發現其他 caller ⇒ 停工回報，不得自行改順序；`validate_survivor_output(payload, report_meta=report_meta, report_ref_path=report_json_path)`；寫檔 ⇒ `{status:"ok", reason:None, path, sha256, case_id}`；寫檔失敗 ⇒ `{status:"computation_failed", reason:"write_failed", path:None, sha256:None, case_id}`（**A1-6**；R9 CODEX-R9-P1-03：`reason` 恆為契約字面 `write_failed` exact、由 `load_survivor_contract()["reasons"]["survivor_output"]` 取值，**禁**拼接例外類別；例外類別／訊息只進 `get_logger(__name__).error(..., exc_info=True)`；不上拋，報告照存）；空 survivors 亦寫檔；`_suppress_persist` ⇒ 不寫、`survivor_output` 為**完整五鍵 object** `{status:"not_computed", reason:"persist_suppressed", path:None, sha256:None, case_id}`（A1-1 逐字；R8 CODEX-R8-P1-05：`status` 與 `reason` 兩欄**分立**，禁串成 `"not_computed:persist_suppressed"` 單一字串；`reason` 由 `load_survivor_contract()["reasons"]["survivor_output"]` 取值；此 reason 加入契約 `reasons.survivor_output`——**Task 1.0 契約於 B4 增此值，屬 B4 commit 內對契約檔之允許修改；測試 1.0-① 鍵集不變，僅值增**）。
  3. `features_source_hash`＝`hashlib.file_digest(open(self._features_path,"rb"),"sha256")`（`_features_path` 由 `analyze()` 入口存；refilter 沿用）；`labels_content_hash`＝`sha256(label_series.to_numpy().tobytes())`（`label_series` 顯式傳入 `_persist_outputs`）；`config_hash=self._config_hash`；`summary_by_feature`＝由 `report["summary_table"]` 轉 `{feature_name: row}`（在 `_persist_outputs` 內做，report 已組好）；`root_analysis_status=report["analysis_status"]`。
- 修改檔案：`ic_reporter.py`、`ic_filter_orchestrator.py::_persist_outputs`、`ic_survivor_contract.json`（reasons.survivor_output 加 `persist_suppressed`）　既有 caller：`tests/momentum/Analysis/test_ic_persist_redirect_*.py`（新寫檔必經同一 `output_dir` 解析）。
- 不可做：不得寫 `data_cache/features/*.h5` attrs；不得於 `_suppress_persist` 下寫檔；不得寫身分不明之檔。
- 邊界：① 空 survivors ② degraded root ③ 事件 fallback ④ 目錄不可寫 ⑤ 缺 symbol ⑥ 並發同 case_id。
- 風險緩解：原子 replace；validator 前置。
- 驗證：`tests/momentum/Analysis/test_gap2_survivor_persist.py`＋`test_ic_persist_redirect_unit.py`：⓪ **四形狀**（ok／identity_missing／write_failed（`reason=="write_failed"` exact，A1-6：mock `os.replace` raise ⇒ reason 不含例外類別）／`_suppress_persist` ⇒ `{status:"not_computed", reason:"persist_suppressed", path:None, sha256:None, case_id}`）皆恰五鍵、`status`／`reason` 分欄 exact 且 `reason ∈ load_survivor_contract()["reasons"]["survivor_output"]`、nullable 規則成立 ① 檔存在且過 validator ② `feature_names == list(filtered_df.columns)` ③ `sha256(file) == survivor_output.sha256` ④ hermetic redirect 下 `data_cache/reports/` 無新檔 ⑤ 事件模式 ⇒ `sample_scope.kind=="event"` 且 `event.definition_hash` 64 hex ⑥ 事件 fallback ⇒ `kind=="full"`、`degraded is True` ⑦ 並發：兩執行緒同 case_id ⇒ 最終檔完整 JSON 且過 validator ⑧ **persist 不讀 `_ic_cache`**：於 `_ic_cache is None` 之 orchestrator 實例直接呼叫 `_persist_outputs(..., stage6b_results=..., event_identity=..., features_path=..., label_series=...)` ⇒ 不 raise、倖存者檔 `event.definition_hash` == 傳入 `event_identity` 之值；fallback wrapper 路徑（③′／⑥）倖存者檔 `oos_guarantees is False` 且與報告節一致。mutation §V-15／24 ⇒ `--batch B4`；檔內 `test_mutation_persist_reads_ic_cache_breaks_cold_call`（monkeypatch `ICFilterOrchestrator._persist_outputs` 為「忽略 `event_identity` kwarg、改讀 `self._ic_cache["event_identity"]`」之變體 ⇒ ⑧ 於 `_ic_cache is None` 下 `TypeError` 紅；還原綠）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 4.3 — golden 對照＋wiring check 讀契約＋預算 bench receipt＋B4 探針（`票 GAP-2/§G,C6,N2`）
- SPEC ref：Task 4.3（N2）　目標：改前==改後可證偽；R3 自動涵蓋新節；`n_regressions==600` 與資源 receipt；§V-13..V-16、V-22..V-24。
- 輸入 / 輸出：`tests/momentum/Analysis/test_gap2_golden.py`；`scripts/ic_wiring_check.py`（`REPORT_SECTIONS = tuple(load_report_contract()["report_sections"].keys())`）；`handoffs/run_receipts/<TS>-gap2-budget-bench.log`；`scripts/gap2_mutation_probe.sh --batch B4`。
- 實作要點：
  1. `test_gap2_golden.py`：讀 pre 檔（缺 ⇒ fail，非 skip）；live `run_analyze()` ⇒ `gap2_canonical_sha` exact、`summary_table` 逐鍵 `abs≤1e-12`、`filter_log` 兩節 exact；**A1-2 identity（R8 U3）**：`report["metadata"]["survivor_output"]["case_id"] == pre["case_id"]`（exact，期望 `ic_gatekeeper`）且倖存者檔 `report_ref == f"ic_report_{pre['case_id']}.json"`（`report_ref` 檔名段 == pre `case_id`）；§G-2：兩次 `marginal_ic` 節 sha 相等、倖存者檔去 `generated_at` sha 相等；兩 sidefx 目錄 sha 相等。
  2. wiring：`REPORT_SECTIONS` 改讀契約（`ic_config_schema.load_report_contract`）；R3 對六＋一節掃裸空。
  3. bench：合成 k=200 survivors＋200 removed、n=20000（seed 20260818）跑 `compute_marginal_ic`＋`combine_factors`；記 wall time、`resource.getrusage(RUSAGE_SELF).ru_maxrss` 至 receipt；斷言 `n_regressions==600` **且以獨立 spy 對證（R8 CODEX-R8-P1-07）**：`monkeypatch.setattr(marginal_ic, "fit_projection", <計數包裹＋記每次 `Z_S.shape[1]`>)` ⇒ spy count == `res.n_regressions` == 600（loo 200＋sequential 200＋removed 200）、每次欄數 `max ≤ 200`（設計矩陣 `n×≤201` 含 intercept／基底上界）；兩個超預算 case（`max_survivors_for_loo=199` ⇒ spy count == 0；`max_removed_candidates=199` ⇒ spy count == 400）皆寫入 receipt；`n_regressions` 不得由獨立 counter 湊數。**明示（R7 CODEX-R7-P1-03）**：receipt 為**觀測資料**、無 wall time／RSS 通過閾值；本票對 OOM 的保護宣稱**僅**＝迴歸次數計數上界（`≤600`、每次 lstsq `n×≤201`），**不**宣稱資源絕對上限（上限須有核准來源，列為觀測供日後定閾）。
  4. 探針 case 加 V-13／14／15／16／22／23／24。
- 修改檔案：新增 `test_gap2_golden.py`；`scripts/ic_wiring_check.py`；`scripts/gap2_mutation_probe.sh`　既有 caller：`tests/momentum/Analysis/test_ichc_wiring_check.py`；白話 5 檔（動 `scripts/`）。
- 不可做：不得重新凍結 pre 檔；不得跳過 §G-1 任一鍵；不得對 bench 設時間斷言。
- 邊界：① pre 檔缺 ② fixture sha 不符 ③ 契約新節鍵在 orchestrator 以裸 `{}` 組裝 ⇒ wiring 紅。
- 風險緩解：⊘
- 驗證：`pytest tests/momentum/Analysis/test_gap2_golden.py tests/momentum/Analysis/test_ichc_wiring_check.py -q` rc=0；`venv/bin/python scripts/gap2_freeze_golden.py --check` rc=0；`bash scripts/ic_wiring_check.sh` rc=0；`bash scripts/gap2_mutation_probe.sh --batch B4` rc=0；receipt 檔存在且含 `n_regressions=600`＋`fit_projection_spy=600`＋兩超預算 case spy 值；`test_gap2_golden.py` 檔內 `test_mutation_scrub_extra_key_breaks_canonical_sha`（`gap2_canonical_sha` 多刪一鍵 ⇒ 與 pre `canonical_sha` 不等 ⇒ 紅）；bench 測試（住 `test_gap2_golden.py` 或 `test_marginal_ic.py`）之 spy 斷言由 `test_mutation_counter_without_fit_call_breaks_spy`（`n_regressions` 改為預算公式湊數而不呼叫 `fit_projection` ⇒ spy≠counter 紅）覆蓋。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B4 測試 ＋ Gate
- **單一來源＝§B「B4→B5」列（R10 CODEX-R10-P2-01：同文逐字）**：`pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/Analysis/test_ichc_wiring_check.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` rc=0 ＋ `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_gap2_golden.py` rc=0 ＋ `bash scripts/ic_wiring_check.sh` rc=0 ＋ `venv/bin/python scripts/gap2_freeze_golden.py --check` rc=0 ＋ `--batch B4` rc=0 ＋ 三家 review CLOSED＋戳記；另 `bash scripts/plain_docs_sync_check.sh` ✓（動 `scripts/`）。

## Phase B5 — 前端最小鏡像（使用者 2026-08-18 白話閘裁定：表格＋toggle 預設開）

### Task 5.1 — `types.ts` 型別＋toggle＋唯讀表格（`票 GAP-2/C6,R4`）
- SPEC ref：Task 5.1　目標：報告新節在 IC 頁面可見；面板可勾選（預設勾）；無新 API。
- 輸入 / 輸出：`frontend/src/lib/types.ts`（ICHC 契約段**外**加 `MarginalICSection`／`MarginalICPerFeature`／`MarginalICComposite`／`SurvivorOutputMeta`；`ICReport.marginal_ic?: MarginalICSection | SectionStatusObject`；`metadata.survivor_output?: SurvivorOutputMeta`）；`frontend/src/store/icAnalysisStore.ts`（`PRESET_TOGGLES` 三 preset 加 `marginal_ic: true`；`getEffectiveConfig` **custom** 分支 stageOverrides 加 `marginal_ic: Boolean(state.featureToggles.marginal_ic)`，**且具名 preset 分支**（foundation／intermediate／advanced）比照 `fdr_correction` 送出 `marginal_ic`——R7 COMPOSER-R7-P1-04／GROK-R7-P0-02）；`frontend/src/components/ic-analysis/FeatureTierPanel.tsx`（硬編碼 `TOGGLES` 加一列 `{key:"marginal_ic", label:"邊際 IC／多因子組合"}` 並改計數——R7 GROK-R7-P0-01：面板 checkbox 來源是此檔非 store 自動列舉）；後端 `ic_filter_orchestrator._apply_tier_config` 具名 preset 分支消費 `STAGE_OVERRIDE_PATHS["marginal_ic"]`（Task 4.1 一併加；純 mapping，不改其他鍵）；新增 `frontend/src/components/ic-analysis/MarginalICTable.tsx`＋`MarginalICTable.test.tsx`；面板 toggle 標籤「邊際 IC／多因子組合」。
- 實作要點：
  1. 表格欄：feature／gross_ic／marginal_ic_loo／ci95／ic_retained_ratio／marginal_ic_train_insample；下方一列 composite：method／composite_ic／top_train_single(test IC)／delta＋ci95；數值 `toFixed(4)`；`ci95` null ⇒ `—`。
  2. 節 `status!=="ok"` ⇒ 顯示 `status`／`reason` 文字，不畫表；`oos_guarantees===false` ⇒ 既有 degraded 樣式警語；恆顯示一行小字「倖存者選於同一測試段；本節數字為描述統計，非獨立驗證」（對應 `independent_oos_validation=false`；字串**不含**「獨立 OOS 驗證」子字串——R7 CODEX-R7-P1-05）；**禁**「獨立 OOS 驗證」字樣。
  3. 接入 IC 結果頁：既有容器 `frontend/src/app/ic-analysis/page.tsx`（**A1-5**；R9 CODEX-R9-P1-02／COMPOSER-R9-P1-01／GROK-R9-P0-01）**只**做兩件事——① `import MarginalICTable from '@/components/ic-analysis/MarginalICTable'` ② 於 **basic** `TabsContent`（現 `:753`）末段、`CorrelationHeatmap`（現 `:810`）之後、同一 `<div>` 內加 `<ChartErrorBoundary title="邊際 IC／多因子組合"><MarginalICTable section={report?.marginal_ic} /></ChartErrorBoundary>`（**A1-5 補正**：deep tab 受 `deepTabVisible`（`:214`）gating，base 節掛 deep 會在 deep 關閉時不可見；資料源＝base `report`，**非** `deepAnalysisReport`；不改其他區塊／tab／樣式）；`MarginalICTable` props：`section?: MarginalICSection | SectionStatusObject | null`（缺席 ⇒ 不渲染）；toggle 關 ⇒ 送出 config `marginal_ic.enabled=false`。
- 修改檔案：既有四檔＝**A1-4＋A1-5 白名單 §C#6**（`types.ts`／`icAnalysisStore.ts`／`FeatureTierPanel.tsx`／`app/ic-analysis/page.tsx`；R8 CODEX-R8-P1-01／GROK-R8-P0-01＋R9 V1：SPEC 原只列 `types.ts`，已走延伸檔擴為四檔）＋新增 `MarginalICTable.tsx`／`MarginalICTable.test.tsx`；後端 `_apply_tier_config` 於 Task 4.1（白名單①）　既有 caller：`scripts/ic_wiring_check.py` R1a／R1b（新 toggle 須映射至後端 `STAGE_OVERRIDE_PATHS`，Task 4.1 已加）；`npm run build`。
- 不可做：除 `marginal_ic` 外不得新增 store toggle；不得改 `CapabilityStatus` 六值；不得畫圖表；不得寫「獨立 OOS 驗證」字樣（元件測試以 `expect(text).not.toContain` 斷言）。
- 邊界：① 節缺席（舊報告）⇒ 不渲染 ② `ci95` null ③ 100+ survivors（可捲動）④ toggle 關。
- 風險緩解：vitest 四條＋build＋tsc。
- 驗證：`cd frontend && npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx` 全綠（≥4：ok 表格／disabled 文字／degraded 警語／空 survivors）；`npm run build` rc=0；`npx tsc --noEmit` rc=0；`bash scripts/ic_wiring_check.sh` rc=0（含新 toggle R1a／R1b）；⑤ toggle 關 ⇒ 送出 config `marginal_ic.enabled=false`——**須覆蓋 intermediate 與 advanced 具名 preset 及 custom 三條路徑**（store 單元測試斷言 `getEffectiveConfig()` 輸出）；後端收到 ⇒ 節 `status=="disabled"`；表格顯示 disabled 文字；元件測試 `expect(text).not.toContain("獨立 OOS 驗證")`；⑥ **頁面實際掛載（A1-5）**：`grep -c "MarginalICTable" frontend/src/app/ic-analysis/page.tsx` ≥ 2（import＋JSX）且 JSX 位於 `TabsContent value="basic"` 區塊內（A1-5 補正）（vitest 掛載 page 或腳本化 grep 斷言皆可，寫進 `MarginalICTable.test.tsx` 或 B5 收尾 receipt）；禁以「元件單測綠」代替接入。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B5 測試 ＋ Gate（收案）
- 見 §B「B5 收尾」；§V 24 條 mutation 全部貼 rc；三家 code review CLOSED＋戳記；registry「GAP-2 待補完」複核觸發；HANDOFF／ROADMAP／白話 5 檔同步；收案。

---

## 追溯表（SPEC → TODO；100% 覆蓋）

| SPEC 項 | 原文節錄（≤30 字） | TODO 位置 |
|---|---|---|
| Task 1.0 | 契約 JSON SoT 先行 | Task 1.0 |
| Task 1.1 | 秩常態分數＋train-fit 投影原語 | Task 1.1 |
| Task 1.2 | `compute_marginal_ic()`（loo＋sequential） | Task 1.2 |
| Task 1.3 | B1 mutation 探針腳本 | Task 1.3 |
| Task 2.1 | `combine_factors()` 與 `composite_ic` | Task 2.1 |
| Task 2.2 | B2 mutation 探針 | Task 2.2 |
| Task 3.1 | 契約 resolver／validator／組裝 | Task 3.1 |
| Task 3.2 | B3 mutation 探針 | Task 3.2 |
| §G 凍結時機 | Task 4.1 動工前跑 freeze | **Task 4.0（新增，B4 首件）** |
| Task 4.1 | `MarginalICConfig` 與 stage 6b 掛載（兩插入點＋fallback 旗標＋xsec N/A；OOS 欄 root 注入 A1-3） | Task 4.1 |
| Task 4.2 | 倖存者檔持久化＋metadata 鏡像 | Task 4.2 |
| Task 4.3 | golden／wiring 讀契約／B4 探針／bench | Task 4.3 |
| Task 5.1 | types.ts＋唯讀表格＋toggle | Task 5.1 |
| §A D1–D7、D3′／D3″ | 前置裁決 | §0 全域規則；Task 1.2／2.1／4.1 |
| §A 使用者裁決 | 拆分／橋 blocked／B5 表格＋toggle | §0；Task 5.1 |
| §G 1–4 | 改前==改後／決定性／oracle／契約 | Task 4.0／4.3；1.2／2.1；3.1 |
| §V mutation 1–24 | 改壞必紅 | 各 Task 驗證欄「mutation §V-n」；`--batch Bn` |
| §V 章程 | Oracle 矩陣／§F／已知不測無 | Task 1.2／2.1（統計）、4.2（並發）、4.3（OOM 計數＋receipt） |
| §C 白名單 7 處（#6 依 A1-4＋A1-5 擴四檔） | 唯此 | §0；Task 5.1 |
| §N R1／R2／R3／R5 | 三值殘留 | 不生 Task；registry「GAP-2 待補完」G2-R1／R2／R3／R5；每批 review brief 附審 |
| §N R4 | 前端表格 | 使用者裁定納入 ⇒ Task 5.1 |
| §R 回退 | 每批獨立 commit；`enabled=False` 逃生口 | §B；Task 4.1 ② |
| Phase 依賴 | B1→B2→B3→B4→B5 | §B 表 |
| 合計 | SPEC Task 12／§G 4 類／§V 24／§N 4（＋R4 收回） | TODO Task 13（含 4.0）／全對應 |

## 階段 3 自檢
1. 追溯：SPEC 12 Task → TODO 13 Task（4.0 為 §G 凍結時機之獨立化，非新義務）；§G／§V／§N 全對應。
2. 深度：每 Task 實作要點 ≥3、檔案到函式名、邊界 ≥2、驗證含 atol／rc／字面斷言。
3. 語義：跨 Task 同檔——`marginal_ic.py`（1.1／1.2）同批；`survivor_contract.py`（1.0 loader／3.1 其餘）跨批但 1.0 只 loader、3.1 不動 loader；`ic_filter_orchestrator.py`（4.1／4.2）同批；`ic_survivor_contract.json`（1.0 建；4.2 增一 reason 值）——4.2 之增值不改鍵集，Task 1.0 測試①仍綠；`ic_report_contract.json` 只在 4.1；`scripts/gap2_mutation_probe.sh`（1.3 建、2.2／3.2／4.3 加 case）。引用之既有函式（`contract_enum`、`load_report_contract`、`ContractValidationError`、`canonical_idx_hash`、`_resolve_case_id`、`STAGE_OVERRIDE_PATHS`、`ichc_run.canonical_sha`／`run_analyze`）皆已 grep 確認存在。
4. 全棧：後端（4.1／4.2）→ 報告 JSON（API 透傳，`api/models` 不改）→ 前端（5.1 型別＋toggle＋表格）三欄齊；wiring R1a／R1b／R3 覆蓋。
5. 錨點：`## §0`、`## §B`、每 Task 含「驗證」「邊界」「不可做」「**存活至**」「**覆蓋風險**」。

## 階段 4 handoff
`SPEC=docs/GAP2_MARGINAL_IC_SPEC.md AMEND=docs/GAP2_MARGINAL_IC_AMENDMENTS.md TODO=docs/GAP2_MARGINAL_IC_TODO.md FOCUS=TODO R11 確認（R10 W1 一行同文寫回；三家 sentinel ⇒ FROZEN）`
