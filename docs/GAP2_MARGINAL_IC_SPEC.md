# GAP-2a 邊際 IC／多因子組合（純 IC 層）＋ GAP-2b 倖存因子輸出契約 — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md`（四方偵察收斂；主委版 `handoffs/20260818-gap2-recon-claude.md`）
> ｜日期：2026-08-18｜對應 TODO：`docs/GAP2_MARGINAL_IC_TODO.md`（本 SPEC 定版後生成）
> 票：`docs/IC_QUANT_GAP_REGISTRY.md` #2a／#2b（來源 finding CODEX-R1-P1-09、GROK-R1-P1-06；健檢收斂 C9／C10／C11）
> 使用者 2026-08-18 裁定：GAP-2 拆 2a／2b；2a 純 IC 層（不碰 ML、不碰事件型）；2b **只交付契約**（含 `sample_scope`＋provenance，序列型／事件型同一座橋），橋本體 blocked-by ML 層；GAP-3 另票。

## §RISK 風險分級

- **大小**：大（新增統計核心＋新契約，並修改 IC 主流程 `analyze`／`refilter`／`analyze_full` 三入口與報告契約）。
- **命中高風險原則**：(a) 數值正確性——邊際 IC／組合 IC 直接回答「這因子有沒有帶來新資訊」，算錯即系統性誤選；
  (b) 跨模組共用路徑——`ic_filter_orchestrator.py`（三入口）、`ic_report_contract.json`（前後端三方同步）、`ic_reporter.py`（persist）；
  (d) ML/回測正確性——2b 倖存者契約是未來 ML 訓練集的入口，`sample_scope`／`oos_guarantees` 錯標＝訓練集洩漏或事件型誤在全樣本訓練。
RISK-HIT: a,b,d
- 命中 (a)(d) ⇒ §G 必填、adversarial review 必跑（三家：codex+composer+grok）。
- `momentum/factories.py` 工廠出口：**不需要新出口**——新純函式由 `ICFilterOrchestrator`（已經 `create_ic_analyzer()`）內部呼叫；無服務端直接消費者（2b 契約唯讀，消費端 blocked）。

## §A 假設與待使用者確認

**已驗證事實（FACT-RECEIPT；11 條，皆可由 repo 內命令重現）**

- FACT-RECEIPT: `grep -rn "sample_scope" --include="*.py" --include="*.ts" --include="*.json" momentum api frontend/src scripts | wc -l` → 印出 `0`（Claude 實跑 2026-08-18；三家同日複驗成立）
- FACT-RECEIPT: `sed -n 43,45p momentum/Analysis/factor_orthogonalizer.py` → 印出 `q_matrix, _ = qr(matrix, mode="economic")` / `orth = pd.DataFrame(q_matrix, index=ordered.index, columns=order)`；`sed -n 52,62p` 同檔 → residual 僅 `float(np.var(residual))` 進 `features_meta`，序列不回傳（Claude 實跑 2026-08-18）
- FACT-RECEIPT: `sed -n 1956,1968p momentum/core/contracts.py` → 印出 `FactorModuleResult` 之 `oos_guarantees: Literal[False]`、`fit_scope: Literal["full_sample"]`；`sed -n 2004,2012p` 同檔 → `deny_factor_in_ok_oos` 只拒 `oos_guarantees is False and fit_scope=="full_sample" and module in {"orthogonalization","exposure"}` 之 dict（Claude 實跑 2026-08-18）
- FACT-RECEIPT: `grep -rn "ic_report\|ICFilterOrchestrator\|filtered_features\|summary_table" api/services/xgboost_batch_service.py momentum/Analysis/pattern_extractor.py momentum/Optimization momentum/Analysis/model_validation | wc -l` → 印出 `0`（Claude 實跑 2026-08-18）
- FACT-RECEIPT: `sed -n 920,928p momentum/Analysis/ic_filter_orchestrator.py | tr -d ' ' | tr '\n' ' '` → 印出 `split_context={"train_plan":train_plan,"test_plan":test_plan,"train_mask":train_mask,"test_mask":test_mask,"effective_horizon":effective_horizon,"expected_freq":str(expected_freq),"allowed_symbols":sorted(allowed_symbols),}`（Claude 實跑 2026-08-18）
- FACT-RECEIPT: `grep -n "def pit_train_fit" momentum/Analysis/pit_stats.py` → 印出 `551:def pit_train_fit(`（簽名 `(df, fit_mask, transform_fn)`，docstring「統計參數只得來自 fit_df」；Claude 實跑 2026-08-18）
- FACT-RECEIPT: `jq -r '.report_sections | keys | join(",")' momentum/Analysis/contracts/ic_report_contract.json` → 印出 `coverage_analysis,grouped_ic,ic_decay,net_ic_analysis,quantile_returns,turnover_analysis`（六節；Claude 實跑 2026-08-18）
- FACT-RECEIPT: `sed -n 29,35p scripts/ic_wiring_check.py | tr -d ' \n'` → 印出 `REPORT_SECTIONS=("ic_decay","quantile_returns","grouped_ic","turnover_analysis","coverage_analysis",`（五節硬編碼，與契約六節**不同步**；Claude 實跑 2026-08-18）
- FACT-RECEIPT: `sed -n 687p momentum/core/contracts.py` → 印出 `source: Literal["split", "event", "feature_filter", "full"]`（`RowMaskPlan.source` 閉集；Claude 實跑 2026-08-18）
- FACT-RECEIPT: `ls tests/golden/la0/inputs/ | grep ETHUSDT_12h` → 印出 `ETHUSDT_12h_e53e22906c35363757f4cd49d27f973e_strat_p2r12_a0_tail2000.h5` 與同名 `_meta.json`（真實 kline 衍生 fixture；`tests/momentum/helpers/ichc_run.py:run_analyze()` 之輸入；Claude 實跑 2026-08-18）
- FACT-RECEIPT: `sed -n 78,80p momentum/Analysis/ic_config_schema.py` → 印出 `class ICCalculationConfig(BaseModel):` / `methods: list[str] = ["spearman"]`（產品 IC 預設 Spearman；Claude 實跑 2026-08-18）

**待確認：無**

**已確認結果**

- `2026-08-18 使用者裁定`：GAP-2 拆 2a／2b；2a＝純 IC 層、不碰 ML、不碰事件型；2b＝契約先行（`sample_scope`＋provenance、序列型／事件型同一座橋）、橋本體 blocked-by ML 層；GAP-3 另票不碰。
- `2026-08-17 使用者裁定（成熟度地圖）`：僅 Feature Factory 完整、IC 進行中；ML／回測／Optimization 屬不完整層，其內部結構不得作為設計依據。
- `2026-08-18 使用者裁定（流程）`：技術取捨交委員會（看碼證不數人頭、取較嚴版、殘留具名三值）；只有 SPEC 白話審閱與真正的產品取捨才停下來問。

**偵察收斂之前置裁決（本 SPEC 全篇據此；四方同判，收斂檔 C 群集）**

- D1 **邊際 IC 定義＝train 擬合、test 套用之 semi-partial 秩 IC**：對候選 f 與條件集 S，先於各自 mask 內做秩→常態分數轉換（van der Waerden，`Φ⁻¹(rank/(n+1))`），於 train 段以 OLS（含截距）擬合 `z_f ~ Z_S` 得 β̂，於 test 段取殘差 `r = z_f − [1, Z_S] β̂`，`marginal_ic = Spearman(r_test, y_test)`。**非** raw 線性殘差（探針：非線性冗餘 `tanh(2s)` 下 raw 殘差 Spearman≈0.14 假陽性、秩殘差≈0）；**非** label 亦殘差化之 partial（回答的是相對量）；**非** Δcomposite（那是組合層的量，另列）。文獻：Grinold & Kahn *Active Portfolio Management* 2e ch.10（residual alpha／IC 加法性）；Qian, Hua & Sorensen ch.4；López de Prado *AFML*（相關剔除≠增量預測力）。
- D2 **不改 `factor_orthogonalizer.py` 語意、不用 `FactorModuleResult`**：現有正交化保持 full-sample research-only；邊際 IC 走新模組、新 typed 結果（`fit_scope∈{train,full_sample}`、`oos_guarantees` 隨 root status），不觸發 `deny_factor_in_ok_oos`。
- D3 **OOS 紀律**＝投影係數／標準化／組合權重與符號**只**在 `train_mask` 估計、IC **只**在 `test_mask` 評估；`fit_mode=full_sample`（loud fallback）⇒ `fit_scope=full_sample`、`oos_guarantees=False`、`pass_class=full_sample_research_only`；`ic_train_test_split=False`（無 holdout）⇒ 節 `not_applicable`、reason `no_holdout_split`（**禁**靜默退化為全樣本擬合）。不新增切分機制；不用 rolling（不觸發 stage4 warm-up 守衛）。
- D3′ **主線 test 樣本已被 selection 消費 ⇒ 不得宣稱獨立 OOS 驗證（收斂檔 C1，codex 唯一提出，採較嚴版）**：stage4 IC／stage5 門檻與 FDR／stage6 冗餘皆於 `test_mask` 計算（orch `:2910-2916`、`:3074-3079`、`:3318-3324`），root `ok_oos` 只證明 preprocessing 未於 test 擬合。故邊際 IC／組合 IC 節（a）`oos_guarantees` 沿用 root 語意（preprocessing＋投影／權重皆不在 test 擬合），（b）**必附**機器可讀揭露欄 `independent_oos_validation=false`、`selection_sample="test"`（字面入契約；validator 於 `version=1` 強制 `false`），（c）F-IC-8：每 survivor 並列 `marginal_ic_train_insample`（β̂ 於 train 擬合、於 train 評估）與 `marginal_ic`（test 評估）；composite 同列 train／test 兩值，（d）任何輸出／前端文案禁用「獨立 OOS 驗證」字樣。nested／frozen final test 列 §N R5（blocked-by 主線 holdout-only）。
- D3″ **輸入形狀**：新 stage 吃**完整 post-event `features_df`＋`label_series`＋`train_mask`／`test_mask`**（`_ic_cache`／stage3 後之物件），survivors 只取**名稱**（`filtered_df.columns`）；`filtered_df` 本身為 test 切片（orch `:3318-3324`），**禁**作 fit 資料（收斂檔 CODEX-R1-P1-03／COMPOSER-R1-P2-01）。
- D4 **禁止用邊際 IC 改變倖存者集合**（post-FDR 第二次選擇＝重開多重比較）：本票邊際 IC 為**描述統計**（`loo`＋`sequential` 兩視角），forward-stepwise **選擇**不做（見 §N R1）。
- D5 **組合＝訊號合成**（單標的縱向 IC 無橫截面持倉）：`composite_t = Σ w_i·s_i·z_i(t)`，`s_i=sign(train_ic_i)`、`w∈{equal, ic_weighted(|train_ic|)}`、`z_i`＝test 段常態分數；`composite_ic=Spearman(composite_test, y_test)`；與單因子比較附 block bootstrap CI（`docs/TEST_DESIGN_CHARTER.md` F-IC-4／F-IC-8）。OLS／Ridge 權重＝ML 層，不做。
- D6 **`sample_scope` 為結構非裸枚舉**，`kind` 值集為 `RowMaskPlan.source` 之子集，並攜帶事件定義 hash；倖存者契約＝新 JSON SoT＋獨立輸出檔；`capability_status` 以 ref 複用 `ic_report_contract.json`。
- D7 **落點＝主流程 stage 6b**（stage6 之後、stage7 之前；三入口同步），非 deep-analysis 模組（cache-hit 路徑無 series owner、opt-in 會使 2b 契約缺欄）；xsec 路徑 `not_applicable:cross_sectional_mode`。

## §C 約束

- 解耦 7 條相關項：R1 `momentum/` 不得 import `api/`；R2 跨域走 Protocol；R3 服務經 factories（本票無新服務端消費者，`create_ic_analyzer()` 已覆蓋）；R5 config 單一來源（新設定入 `ic_config_schema.ICConfig`，禁散落常數）；R6 `pytest tests/momentum/` 可獨立跑；R7 DTO 不跨界（新 dataclass 住 `momentum/Analysis/`，API 以 dict 透傳，不進 `api/models/`）。
- 不可違反原則：不弱化 NaN/inf gate（每筆計算逐列 finite 過濾並回報 `n_used`，禁 fillna）；不擅改輸出大小（既有報告鍵集**不變**，只新增）；資料真實性（§G 用真實 kline 衍生 fixture；統計 oracle 用合成**因子／label 序列**——章程 §F 允許，禁合成價格）。
- **成熟度約束**：`api/services/xgboost_*`、`momentum/Analysis/model_validation/`、`momentum/Optimization/` 之內部結構**不得作為設計依據**；2b 契約只定義「讀檔→驗欄位」，**不接**任何 ML 呼叫。
- **允許改動之既有檔白名單（唯此）**：
  1. `momentum/Analysis/ic_filter_orchestrator.py`：新增 `_stage6b_marginal_ic()` 並於 `analyze`／`refilter`／`analyze_full`／`_run_full_sample_fallback` 掛載；`_stage7_report` 之 `analysis_results` 加 `marginal_ic` 節；`_persist_outputs` 加倖存者檔輸出；`_ic_cache` 加 `stage6b_results`。**不改**既有 stage 語意與既有報告鍵。
  2. `momentum/Analysis/ic_config_schema.py`：新增 `MarginalICConfig` 並掛 `ICConfig.marginal_ic`。
  3. `momentum/Analysis/contracts/ic_report_contract.json`：`report_sections` 加 `marginal_ic`；`reasons` 加 `marginal_ic`／`marginal_ic_feature` 兩組；`metadata` 加 `survivor_output_keys`。**不改**既有值。
  4. `momentum/Analysis/ic_reporter.py`：新增 `save_survivor_output()`；`generate_json_report` 透傳新節（不改既有節）。
  5. `scripts/ic_wiring_check.py`：`REPORT_SECTIONS` 改為讀契約檔 `report_sections` 鍵（消除五／六節漂移），R3 自動涵蓋新節。
  6. `frontend/src/lib/types.ts`：ICHC 契約段**外**新增 `MarginalICSection` 型別；`CapabilityStatus` 六值**不變**。
  7. 上述對應之既有測試檔：只新增斷言，禁放寬。
  **不改** `factor_orthogonalizer.py`、`redundancy_filter.py`、`ic_engine.py`、`pit_stats.py`、`momentum/core/contracts.py`（`RowMaskPlan.source` 值集不動；新契約以 sync 測試對齊）。
- **新資料結構一律 JSON SoT**：所有新欄位名／枚舉值只在 Task 3.1 之契約檔出現一次；本 SPEC 其餘章節與 TODO 只 pointer，**不複列欄位表**。既有 `capability_status` 與 `reasons` 以 `*_ref` 指向 `ic_report_contract.json`。

## §G Golden / Baseline

- **feature/kline 條件**：本票不生成／不計算特徵、不 merge、不 split（吃 orchestrator 既有 `features_df`／`label_series`／`split_context`）；但接線後之主流程回歸必用真實 kline 衍生 fixture（§A receipt：`tests/golden/la0/inputs/ETHUSDT_12h_*_a0_tail2000.h5`，經 `tests/momentum/helpers/ichc_run.run_analyze()`），禁合成 fixture 充當。
- **凍結時機 / reference 設定**：Task 4.1 動工前跑 `scripts/gap2_freeze_golden.py`（新建）→ `handoffs/run_receipts/gap2_golden_pre.json`（**唯一** baseline 檔，路徑寫死），內容＝以預設 `ICConfig` 跑 `run_analyze()`（`case_id=gap2_golden`），記錄：`report` 去除 `marginal_ic` 節與 `metadata.survivor_output`、`generated_at`、路徑欄後之 `canonical_sha`（沿用 `ichc_run.canonical_sha` 序列化）、`summary_table` 逐 feature 逐鍵值、`filter_log.stage5_thresholds`／`stage6_redundancy` 逐鍵。檔內附 `fixture_sha256`（h5）與 `config_hash`。
- **baseline 內容（四類，皆非自造數值）**
  1. **改前==改後（行為不變型）**：B4 接線後同 fixture 同 config，上述 `canonical_sha` 與 pre 檔 **exact 相等**（`sha256` 逐字元）；`summary_table` 逐 feature 逐鍵 `abs≤1e-12`；`filter_log` 兩節逐鍵 exact。任何差異 ⇒ 列出鍵與 diff＝FAIL。
  2. **新節決定性**：同 fixture 同 config 連跑兩次，`marginal_ic` 節之 `sha256(json.dumps(sort_keys=True))` 相等（bootstrap 走固定 seed）；`ic_survivors_{case_id}.json` 去 `generated_at` 後 `sha256` 相等。
  3. **解析／構造 oracle（合成因子／label 序列，seed 寫死於測試；容差分尺度）**：
     - O1 單調冗餘：`f = g(s1)`，g 嚴格單調（`x³`、`tanh(2x)`）⇒ `marginal_ic(f | S∋s1)` 之 `|·| ≤ 0.02`（n=5000）且 `status=not_computed`／`residual_degenerate` 或值 ≤ 容差二者其一皆算通過（秩空間下 `f=x³` 之殘差為 0，`tanh` 為近 0）；**同時斷言 raw 空間殘差 Spearman `> 0.10`**（防退回 raw 空間；D1 探針值 0.14）。
     - O2 正交新資訊：`f ⟂ S`（獨立常態）且 `corr(f, y)=ρ` ⇒ `|marginal_ic − gross_ic| ≤ 0.02`（n=5000）。
     - O3 空條件集：`S=∅` ⇒ `marginal_ic == gross_ic`（`atol=1e-12`）。
     - O4 加法性（Grinold-Kahn）：k=4 獨立常態因子、`y = Σ ρ_i f_i + ε` ⇒ `sequential` 之 `Σ marginal_ic²` 與 `composite_ic²`（等權）之比值 ∈ `[0.85, 1.15]`（Spearman 對常態之偏差 `ρ_s=(6/π)asin(ρ/2)` 已含於容差；n=20000）。
     - O5 標籤置亂（MR-L1）：`y` 打亂 ⇒ 全部 `|marginal_ic| < 2/√n_test` 且 `|composite_ic| < 2/√n_test`。
     - O6 秩不變（MR-L3）：`f×c`（c>0）與 `f³` ⇒ `marginal_ic`／`gross_ic`／`composite_ic` **完全相等**（`atol=1e-12`）。
     - O7 train-fit 可證偽（獨立參考實作）：train 段 `f=+s+ε`、test 段 `f=−s+ε`（關係反轉）⇒ 以測試內**獨立 numpy 參考實作**（同 D1 定義，20 行內）計算之值 `atol=1e-12` 相等；且 `marginal_ic` 與「若在 test 擬合 β」之值差 `> 0.3`（證明擬合確在 train）。
     - O8 組合：單因子 `S={f}` ⇒ `composite_ic == gross_ic(f)`（`atol=1e-12`）；`train_ic<0` 之因子符號對齊後 `composite_ic ≥ 0` 於 O2 情形；`ic_weighted` 與 `equal` 於等 IC 因子下 `atol=1e-12` 相等。
     - O9 bootstrap：CI 含點估；同 seed 兩次 `atol=0`；`block_len ≥ effective_horizon`（斷言參數）。
  4. **契約 oracle**：`ic_survivors_{case_id}.json` 過 `validate_survivor_output()`；`feature_names == list(filtered_df.columns)` exact；`sample_scope.kind` 值 ∈ 契約枚舉且 ⊆ `RowMaskPlan.source` Literal（AST 讀 `contracts.py:687`）；`oos_guarantees == (analysis_status=="ok_oos")` 一致；缺任一必填鍵／多任一未知鍵／枚舉外值 ⇒ `ContractValidationError`。
- **通過條件**：1 exact；2 exact；3 逐條容差如上；4 fail-closed 逐條。超出即列出 oracle 編號＋實際值＝FAIL。

## §P Phase 與依賴

### Phase B1 — 邊際 IC 純函式＋oracle（依賴：無；**批內順序 1.1 → 1.2 → 1.3**）

**Task 1.1 — 秩常態分數＋train-fit 投影原語**
- 目標：把 D1 的兩個原語落成純函式，且投影參數只能來自 train。
- 檔案：新增 `momentum/Analysis/marginal_ic.py::normal_scores(x: np.ndarray) -> np.ndarray`（van der Waerden，`rankdata(method="average")/(n+1)` 經 `scipy.stats.norm.ppf`；輸入含非有限值 ⇒ raise）；`::fit_projection(z_target: np.ndarray, z_basis: np.ndarray) -> Projection`（dataclass：`beta`（含截距）、`condition_number`、`r2_train`、`n_train`）；`::apply_residual(z_target, z_basis, projection) -> np.ndarray`。
- 既有 caller/影響面：新建無 caller。
- 改法：`fit_projection` 用 `np.linalg.lstsq(rcond=None)`；`z_basis` 為空（0 欄）⇒ `beta=[mean]`、殘差＝去均值；`condition_number = np.linalg.cond([1, Z_S])`；`r2_train` 標準定義。**禁**在函式內做任何 mask 決策（mask 由 Task 1.2 傳入切好的陣列）。
- **驗證**：`pytest tests/momentum/Analysis/test_marginal_ic.py -q -k "scores or projection"` rc=0；斷言 ① `normal_scores` 對嚴格單調變換不變（`atol=1e-12`）② `normal_scores` 均值 `|·|<1e-9`、對 n=5000 標準差 ∈ [0.95,1.0] ③ `fit_projection` 於 `z_target = 2·z_b + 1` 之 `beta ≈ [1, 2]`（`atol=1e-10`）、`r2_train ≈ 1`（`atol=1e-10`）④ 空 basis ⇒ 殘差＝去均值（`atol=1e-12`）⑤ 含 NaN 輸入 ⇒ raise。
- **邊界**：① 全相同值（ties 全部）② n=1／n=2 ③ 共線 basis（`condition_number` 極大但不 raise；由呼叫方依 `residual_degenerate` 判）④ 空 basis。
- **存活至**：全票完工後保留（1.2／2.1 依賴）。
- **覆蓋風險**：無。
- 不可做：不得回退為 raw 值投影；不得提供 `fit_on_full=True` 之參數。

**Task 1.2 — `compute_marginal_ic()`（loo＋sequential 兩視角）**
- 目標：D1／D3 之完整計算，含 gate、bootstrap CI、typed 結果。
- 檔案：`momentum/Analysis/marginal_ic.py::compute_marginal_ic(features_df: pd.DataFrame, label: pd.Series, *, train_mask, test_mask, survivors: list[str], extra_candidates: list[str] = (), params: MarginalICParams) -> MarginalICResult`；`MarginalICParams`（frozen dataclass：`min_test_rows`、`min_rows_per_regressor`、`degenerate_threshold`、`n_bootstrap`、`block_len`、`seed`、`weights_method`）；`MarginalICResult`（frozen dataclass：`status`／`reason`／`fit_scope`／`oos_guarantees`／`projection_space`／`algorithm_version`／`views`／`per_feature`／`sequential`／`removed_candidates`／`n_train`／`n_test`／`to_dict()`）。**欄位名集合＝Task 3.1 契約檔 `marginal_ic_section_keys`（本處不複列）**。
- 既有 caller/影響面：新建；B4 由 orchestrator 呼叫。
- 改法：對每個 f（`survivors` 之 loo：S＝survivors∖{f}；`sequential`：依 `|train_ic|` 遞減、tie 依名稱，S＝其前序；`extra_candidates`：S＝全部 survivors）：逐 f 取 train／test 各自「f、S、y 皆有限」列 → `normal_scores` 分段轉換 → Task 1.1 fit（train）／residual（test）→ `var(r_test) ≤ degenerate_threshold` ⇒ 該 f `not_computed:residual_degenerate` → 否則 `marginal_ic=spearmanr(r_test, y_test)`、`gross_ic=spearmanr(f_test, y_test)`、`ic_retained_ratio`（`|gross|<1e-12` ⇒ null）、`ci95` 為 moving-block bootstrap（`block_len`、`n_bootstrap`、`np.random.default_rng(seed)`）、`marginal_ic_train_insample`（同 β̂ 於 train 列之殘差對 train label 之 Spearman；D3′(c)）、`n_used_train`／`n_used_test`／`condition_number`／`r2_train`。`train_ic_i` 另算供排序與 B2。結果頂層帶 `statistic="semi_partial_rank_ic"`、`projection_space="rank_normal"`、`independent_oos_validation=False`、`selection_sample="test"`（D3′；字面由契約 `statistic_values`／`projection_space_values` 定義）。全域 gate：`n_test < min_test_rows` 或 `n_test < min_rows_per_regressor·|S|` ⇒ 節 `not_computed:insufficient_test_rows`；train 同理 `insufficient_train_rows`；`len(survivors)==0` ⇒ `not_applicable:no_survivors`；`train_mask is None` ⇒ `not_applicable:no_holdout_split`（呼叫方於 fallback 傳全 True 之 train 與 test **並**傳 `fit_scope="full_sample"` ⇒ `oos_guarantees=False`）。reason 字面集合＝`ic_report_contract.json#reasons.marginal_ic`／`marginal_ic_feature`（Task 3.1 新增，本處不複列）。
- **驗證**：`pytest tests/momentum/Analysis/test_marginal_ic.py -q` rc=0；§G O1–O7、O9 逐條為獨立測試函式；另 ⑧ `sequential[0].marginal_ic == per_feature[sequential[0].feature].gross_ic`（首個無條件集）⑨ `loo` 之 `|S|=1` 情形 `marginal_ic == gross_ic`（`atol=1e-12`）⑩ gate 三種 reason 逐一觸發 ⑪ `to_dict()` 鍵集 == 契約 `marginal_ic_section_keys`（Task 3.1 落地前先以檔內常數對照，3.1 後改讀契約）。
- **邊界**：① `survivors` 空 ② 單一 survivor ③ 全部候選 residual 退化 ④ test 段 label 全 NaN ⑤ `extra_candidates` 與 survivors 重疊（去重，以 survivors 為準）⑥ 常數因子（`normal_scores` 全 0 ⇒ 該 f `residual_degenerate`）⑦ n_test 恰等於下限。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得依 `marginal_ic` 改動 `survivors` 順序以外之任何選擇（D4）；不得用 test 段任何統計量做排序／符號／權重；不得 fillna。

**Task 1.3 — B1 mutation 探針腳本**
- 目標：把 §V-1..V-6 做成可重跑腳本，證明改壞會紅。
- 檔案：新增 `scripts/gap2_mutation_probe.sh`（`--batch B1|B2|B3|B4|B5`），沿用 `scripts/gap1_b1_mutation_probe.sh` 之 `$BACKUP_DIR` 還原、rc==1（非 2）斷言、`mkdir` 互斥鎖 `.claude/gate/gap2_mutation_probe.lock`；receipt 寫 `handoffs/run_receipts/<TS>-gap2-<batch>-probe.log`。
- 既有 caller/影響面：新建；`scripts/mutation_probe_check.sh` 之檔內 `test_mutation_*` 規則另由各測試檔滿足。
- 改法：每條 mutation＝就地 `sed` 改一行 → 跑對應 `pytest -q -x` → 斷言 rc==1 且輸出含 `FAILED` → 還原 → 斷言綠。
- **驗證**：`bash scripts/gap2_mutation_probe.sh --batch B1` rc=0 且 log 逐條 `MUTATION V-n: RED ✓ / RESTORED GREEN ✓`。
- **邊界**：① 鎖被持有 ⇒ rc=3 退出 ② 未追蹤檔還原（用備份非 `git checkout`）③ mutation 目標行不存在 ⇒ rc=2 且不留髒檔。
- **存活至**：全票完工後保留（B2–B5 沿用同腳本加 case）。
- **覆蓋風險**：無。
- 不可做：不得並行跑兩份；不得在 probe 中放寬任何測試。

### Phase B2 — 多因子組合 IC（依賴：B1 Task 1.1／1.2）

**Task 2.1 — `combine_factors()` 與 `composite_ic`（含 block bootstrap CI）**
- 目標：D5 落地；與最佳單因子之比較可證偽。
- 檔案：新增 `momentum/Analysis/factor_combiner.py::combine_factors(features_df, label, *, train_mask, test_mask, survivors, params: MarginalICParams) -> CompositeResult`；`::block_bootstrap_ci(stat_fn, arrays, *, block_len, n_bootstrap, seed, alpha=0.05) -> (lo, hi)`（moving-block，成對重抽同一 block 索引）。`CompositeResult` frozen dataclass；欄位名集合＝契約 `marginal_ic_section_keys.composite_keys`（不複列）。
- 既有 caller/影響面：新建；B4 由 orchestrator 呼叫；`block_bootstrap_ci` 供 Task 1.2 之 `ci95` 共用（1.2 先以內部實作，2.1 落地時**搬移**至本檔並由 1.2 import——此為刻意合併，見覆蓋風險）。
- 改法：complete-case（test 段所有 survivors 與 y 皆有限之列；記 `n_used_test`）；`train_ic_i` 於 train 段；`sign_i=sign(train_ic_i)`（0 ⇒ 該因子排除並記 `excluded:zero_train_ic`）；`z_i`＝test 段 `normal_scores`；`w`：`equal=1/k` 或 `ic_weighted=|train_ic_i|/Σ|train_ic|`；`composite_ic=spearmanr(composite, y)`（test）與 `composite_ic_train_insample`（同權重／符號於 train 列評估；D3′(c)）；`top_train_single`＝`argmax|train_ic|` 之因子，其 test IC；`best_single_test_ic`＝test 段最大 `|IC|`（參考值，選於 test，明標 `selected_on=test`）；`delta_vs_top_train_single`＋`ci95`（成對 block bootstrap）；`n_used_test < min_test_rows` ⇒ `not_computed:insufficient_test_rows`；`k==0` ⇒ `not_applicable:no_survivors`。
- **驗證**：`pytest tests/momentum/Analysis/test_factor_combiner.py -q` rc=0；§G O8／O9／O4（與 1.2 共用 fixture）；另 ① 兩完全相同因子等權 ⇒ `composite_ic == gross_ic`（`atol=1e-12`）② 一因子 `train_ic<0`、test 同號 ⇒ 符號對齊後 `composite_ic` 大於未對齊版（構造）③ `weights` 之和 `==1`（`atol=1e-12`）④ `delta` 之 CI 含點估 ⑤ 兩次同 seed exact 相等 ⑥ `block_len` 傳 0 ⇒ raise。
- **邊界**：① k=1 ② 全部 `train_ic=0` ⇒ `not_computed:all_zero_train_ic` ③ test 段 complete-case 為空 ④ 極端 `n_bootstrap=1`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：Task 1.2 之內部 bootstrap 於本 Task 搬移（同批內先後，非跨 Phase 白工；搬移後 1.2 測試不變仍綠）。
- 不可做：不得在 test 段估權重／符號；不得提供 OLS／Ridge 權重法；不得把 `best_single_test_ic` 當 OOS 比較基準（只作參考欄）。

**Task 2.2 — B2 mutation 探針（§V-7..V-9 入 `scripts/gap2_mutation_probe.sh --batch B2`）**
- 目標：改壞權重來源／符號來源／seed 必紅。
- 檔案：`scripts/gap2_mutation_probe.sh`（加 case）。
- 既有 caller/影響面：同 Task 1.3。
- 改法：同 Task 1.3。
- **驗證**：`bash scripts/gap2_mutation_probe.sh --batch B2` rc=0。
- **邊界**：同 Task 1.3。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：同 Task 1.3。

### Phase B3 — 倖存因子輸出契約（GAP-2b 交付物；依賴：B1／B2 之結果型別欄位名）

**Task 3.1 — 契約 JSON SoT＋resolver／validator**
- 目標：把 2b「倖存者輸出契約」寫成單一真相源＋fail-closed 讀取，並把 `marginal_ic` 節之欄位名集合一併釘死。
- 檔案：新增 `momentum/Analysis/contracts/ic_survivor_contract.json`（頂層鍵：`version`、`_doc`（含「`sample_scope.kind=event` 之倖存者只得於事件樣本訓練；消費端須驗 `oos_guarantees`／`analysis_status`」）、`capability_status_ref`、`reasons_ref`、`algorithm_version`、`survivor_file_keys`（每鍵 `{type, required}`，`additional_properties:false`）、`sample_scope_keys`、`sample_scope_kind_values`、`event_definition_keys`、`split_keys`、`provenance_keys`、`survivor_record_keys`、`marginal_ic_section_keys`（含 `per_feature_keys`／`sequential_keys`／`composite_keys`／`removed_candidate_keys`）、`statistic_values`、`projection_space_values`、`weights_method_values`、`view_values`、`fit_scope_values`、`selection_sample_values`、`independent_oos_validation_allowed`（`version=1` ⇒ `[false]`）、`row_identity_keys`）；新增 `momentum/Analysis/survivor_contract.py::load_survivor_contract()`／`::resolve_ref(ref) -> list`（`<repo 相對路徑>#<鍵路徑>`，fail-closed）／`::validate_survivor_output(payload: dict) -> None`（raise `ContractValidationError`）／`::build_survivor_output(*, report_meta, filtered_features, marginal_ic_result, composite_result, event_info, split_context, config_hash, features_source_hash, case_id, generated_at) -> dict`（純函式，只組裝不寫檔）。同步：`ic_report_contract.json` 加 `report_sections.marginal_ic`（`status_object_keys`）、`reasons.marginal_ic`／`reasons.marginal_ic_feature`、`metadata.survivor_output_keys`。
- 既有 caller/影響面：`ic_config_schema.load_report_contract`（讀既有契約；不改）；`tests/momentum/Analysis/test_ichc_contract_sync.py::test_r6_wider_contract_nodes_consistent`（新 reason 字面須在 orchestrator 組裝面出現——B4 落地前該測試會對新 reason 之「消費點存在」斷言紅 ⇒ **B3 只加契約鍵不加 reason 值，reason 值於 B4 與消費點同 commit 加入**）。
- 改法：`sample_scope`＝結構（鍵集在契約檔），`kind` 值集 ⊆ `RowMaskPlan.source`；`event`＝`null` 或 `{definition_hash, mode, n_events, n_timestamps_requested}`（`definition_hash=sha256(canonical(query|sorted timestamps))`）；事件 fallback ⇒ `kind=full` 且 `degraded=true`；`provenance`＝`{config_hash, features_source_hash, features_path, labels_content_hash, pit_stats_version, fit_mode, ic_method, label_horizon, label_return_type, report_ref, producer, contract_version, algorithm_version}`；`split`＝`{split_method, train_time_bounds, test_time_bounds, train_rows, test_rows, embargo, purge_gap, base_universe_hash, selection_scope_id, row_identity{train_index_hash, test_index_hash}}`（index hash 用既有 `momentum/core/contracts.py::canonical_idx_hash`）；`feature_names`（有序）＋`feature_set_hash`（`sha256` of ordered names）；`survivors[]`＝`{feature_name, ic_mean, icir, p_value_adj, pass_class, train_ic, gross_ic, marginal_ic_loo, marginal_ic_loo_ci95, marginal_ic_train_insample, redundancy_kept:true}`；`composite`＝B2 結果去序列；`analysis_status`／`oos_guarantees`／`pass_class`／`independent_oos_validation`／`selection_sample`／`statistic` 頂層。（以上為**語意描述**；鍵名以契約檔為準。）
- **驗證**：`pytest tests/momentum/Analysis/test_survivor_contract.py -q` rc=0；斷言 ① round-trip：`build_survivor_output(...)` 之輸出過 `validate_survivor_output` ② 缺任一 required 鍵 ⇒ raise ③ 多任一未知鍵 ⇒ raise ④ `sample_scope.kind` 枚舉外 ⇒ raise ⑤ `sample_scope.kind=event` 而 `event is null` ⇒ raise ⑥ `oos_guarantees=True` 而 `analysis_status!="ok_oos"` ⇒ raise ⑦ 契約 `sample_scope_kind_values` ⊆ AST 解析 `momentum/core/contracts.py` `RowMaskPlan.source` Literal 值集 ⑧ `capability_status_ref`／`reasons_ref` 解析成功且與 `contract_enum("capability_status")` 相等 ⑨ `marginal_ic_section_keys` 各子集 == B1／B2 dataclass `to_dict()` 鍵集 ⑩ `additional_properties:false` 對所有物件層生效（tamper 測試）⑪ `independent_oos_validation=True` ⇒ raise（`version=1`）⑫ `feature_set_hash != sha256(feature_names)` ⇒ raise ⑬ `row_identity.test_index_hash` 與 `canonical_idx_hash(test_plan.row_index)` 相等（B4 整合時斷言）。
- **邊界**：① 空 survivors（合法，`survivors=[]`＋`status=not_applicable`）② degraded root ③ 事件 fallback ④ ref 指向不存在檔／鍵 ⇒ raise。
- **存活至**：全票完工後保留；未來 ML 橋（registry #2b 本體）之唯一輸入契約。
- **覆蓋風險**：無（橋本體只讀不改本檔；契約演進走 `version`）。
- 不可做：不得在 SPEC／TODO／程式註解複列欄位表；不得把 `sample_scope` 降為字串；不得接任何 ML 呼叫。

**Task 3.2 — B3 mutation 探針（§V-10..V-12 入 `--batch B3`）**
- 目標：拿掉 `sample_scope`／放寬 `additional_properties`／改 kind 枚舉 ⇒ 必紅。
- 檔案：`scripts/gap2_mutation_probe.sh`。
- 既有 caller/影響面：同 1.3。
- 改法：同 1.3。
- **驗證**：`bash scripts/gap2_mutation_probe.sh --batch B3` rc=0。
- **邊界**：同 1.3。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：同 1.3。

### Phase B4 — 主流程接線＋報告節＋持久化＋golden（依賴：B1／B2／B3；**動工前先凍結 §G pre 檔**）

**Task 4.1 — `MarginalICConfig` 與 stage 6b 掛載三入口**
- 目標：D7 落地；預設啟用；三入口一致；fallback／xsec 誠實。
- 檔案：`momentum/Analysis/ic_config_schema.py::MarginalICConfig(enabled: bool = True, min_test_rows: int = 30 (ge 10), min_rows_per_regressor: int = 5 (ge 1), degenerate_threshold: float = 1e-10, weights_method: Literal["equal","ic_weighted"] = "equal", n_bootstrap: int = 1000 (ge 1, le 20000), bootstrap_seed: int = 20260818, include_removed_candidates: bool = True)`＋`ICConfig.marginal_ic`；`momentum/Analysis/ic_filter_orchestrator.py::_stage6b_marginal_ic(features_df, label_series, stage5_results, stage6_results, split_context, config) -> dict`，於 `analyze()`（stage6 後）、`refilter()`、`analyze_full()`（經 analyze）、`_run_full_sample_fallback()`（`fit_scope=full_sample`）四處掛載；`_stage7_report` 之 `analysis_results["marginal_ic"]`；`_ic_cache["stage6b_results"]`。
- 既有 caller/影響面：三入口既有測試（`tests/momentum/test_ic_filter_orchestrator.py`、`tests/momentum/Analysis/test_ic1d_orchestrator_integration.py`、`tests/momentum/Analysis/test_ichc_*`）——動工前 diff 其斷言，禁放寬。
- 改法：`enabled=False` ⇒ 節 `{"status":"disabled","reason":"disabled_by_config"}`（**非**裸 `{}`）；`split_context is None` 且非 fallback ⇒ `not_applicable:no_holdout_split`；fallback ⇒ 全 True masks＋`fit_scope=full_sample`、`oos_guarantees=False`；xsec ⇒ `not_applicable:cross_sectional_mode`；`block_len=max(effective_horizon, ceil(n_test**(1/3)))`；`survivors=list(filtered_df.columns)`、`extra_candidates=passed_features∖survivors`（`include_removed_candidates`）；結果 `to_dict()` 進報告節，並帶 `oos_guarantees`／`fit_scope`／`pass_class`（與 root 一致）。reason 字面（Task 3.1 預留鍵）於本 Task 一併寫入 `ic_report_contract.json#reasons`。
- **驗證**：`pytest tests/momentum/Analysis/test_gap2_stage6b_wiring.py tests/momentum/Analysis/test_ichc_contract_sync.py -q` rc=0；斷言 ① 預設 config 跑 `run_analyze()` ⇒ `report["marginal_ic"]["status"]=="ok"` 且 `oos_guarantees is True` 且 `fit_scope=="train"` ② `enabled=False` ⇒ `status=="disabled"` 且鍵集恰 `{status,reason}` ③ 強制 fallback（`ic_train_test_split=False`＋`preprocessing.fit_mode=full_sample` 路徑）⇒ `oos_guarantees is False`、`fit_scope=="full_sample"`、root `degraded_full_sample` ④ `refilter()` 後節與新 survivors 一致（`per_feature` 鍵集 == 新 `filtered_df.columns`）⑤ `deny_factor_in_ok_oos(report)` 於 ok_oos 不 raise ⑥ `test_r6_wider_contract_nodes_consistent` 綠（新 reason 消費點存在）⑦ 節 `sha256` 兩次相等（§G-2）⑧ 既有斷言未放寬（diff 附 commit）⑨ `bash scripts/ic_wiring_check.sh` rc=0。
- **邊界**：① 無 survivors ② 單 survivor ③ n_test 低於下限 ④ cache-hit `refilter` ⑤ `include_removed_candidates=False`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得改動 stage4–6 任何既有輸出；不得把 stage 6b 做成 deep 模組；不得在 xsec 路徑呼叫計算。

**Task 4.2 — 倖存者檔持久化＋報告 metadata 鏡像**
- 目標：2b 契約檔實際落地並與報告互指。
- 檔案：`momentum/Analysis/ic_reporter.py::save_survivor_output(payload: dict, output_dir: str, case_id: str) -> str`（`validate_survivor_output` 後原子寫 `ic_survivors_{case_id}.json`）；`ic_filter_orchestrator.py::_persist_outputs` 呼叫並寫 `report_meta["survivor_output"]={status, reason, path, sha256}`（鍵集＝契約 `metadata.survivor_output_keys`）。
- 既有 caller/影響面：`tests/momentum/Analysis/test_ic_persist_redirect_*.py`（persist 導向 fixture）——新寫檔必經同一 `output_dir` 解析，hermetic 測試不得落到真 `data_cache/`。
- 改法：空 survivors 亦寫檔（`survivors=[]`＋status）；`_suppress_persist` 時不寫；寫檔失敗 ⇒ `report_meta["survivor_output"]={status:"computation_failed", reason:...}`（不吞例外於 log 之外）。
- **驗證**：`pytest tests/momentum/Analysis/test_gap2_survivor_persist.py tests/momentum/Analysis/test_ic_persist_redirect_unit.py -q` rc=0；斷言 ① 檔存在且過 validator ② `feature_names == list(filtered_df.columns)` ③ `sha256(file) == report_meta.survivor_output.sha256` ④ hermetic redirect 下 `data_cache/reports/` 無新檔 ⑤ 事件模式（`event_timestamps` 給定且 tier 充足）⇒ `sample_scope.kind=="event"` 且 `event.definition_hash` 為 64 hex ⑥ 事件 fallback ⇒ `kind=="full"` 且 `degraded is True`。
- **邊界**：① 空 survivors ② degraded root ③ 事件 fallback ④ 目錄不可寫。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得寫入 `data_cache/features/*.h5` attrs（不改既有 h5 契約）；不得在 `_suppress_persist` 下寫檔。

**Task 4.3 — §G golden 凍結／對照＋wiring check 讀契約＋B4 探針**
- 目標：改前==改後可證偽；wiring R3 自動涵蓋新節；§V-13..V-16。
- 檔案：新增 `scripts/gap2_freeze_golden.py`（產 `handoffs/run_receipts/gap2_golden_pre.json`；`--check` 模式比對）、`tests/momentum/Analysis/test_gap2_golden.py`；修改 `scripts/ic_wiring_check.py`（`REPORT_SECTIONS` 改讀 `ic_report_contract.json#report_sections` 鍵）；`scripts/gap2_mutation_probe.sh --batch B4`。
- 既有 caller/影響面：`tests/momentum/Analysis/test_ichc_wiring_check.py`（subprocess 常駐）；白話 5 檔（動 `scripts/` 須同步）。
- 改法：pre 檔於 Task 4.1 動工前產生並 commit；`test_gap2_golden.py` 讀 pre 檔與 live 跑對照（§G-1）；§G-2 決定性；wiring check R3 對契約全部節鍵掃裸空。
- **驗證**：`pytest tests/momentum/Analysis/test_gap2_golden.py tests/momentum/Analysis/test_ichc_wiring_check.py -q` rc=0；`bash scripts/gap2_freeze_golden.py --check` rc=0；`bash scripts/gap2_mutation_probe.sh --batch B4` rc=0；`bash scripts/ic_wiring_check.sh` rc=0。
- **邊界**：① pre 檔缺 ⇒ 測試 fail-closed（非 skip）② fixture sha 不符 ⇒ fail ③ 契約新節鍵在 orchestrator 以裸 `{}` 組裝 ⇒ wiring 紅。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得以「重新凍結 pre 檔」讓對照變綠；不得跳過 §G-1 任何鍵。

### Phase B5 — 前端最小鏡像（依賴：B4；使用者可於白話閘否決 ⇒ 改列 §N user-ruling）

**Task 5.1 — `types.ts` 型別＋唯讀表格**
- 目標：報告新節在 IC 頁面可見（表格：每 survivor 之 gross／marginal_loo／ci95／retained；composite vs top-train-single＋CI），無新 toggle、無新 API。
- 檔案：`frontend/src/lib/types.ts`（ICHC 契約段**外**加 `MarginalICSection`）；新增 `frontend/src/components/ic-analysis/MarginalICTable.tsx`＋`MarginalICTable.test.tsx`；接入現有 IC 結果頁 deep 區塊之後（唯讀）。
- 既有 caller/影響面：`scripts/ic_wiring_check.py` R1a/R1b（無新 toggle ⇒ 不受影響）；`npm run build`。
- 改法：節 `status!="ok"` ⇒ 顯示 status/reason 文字（不畫表）；`oos_guarantees=false` ⇒ 顯示既有 degraded 樣式警語；數值四位小數。
- **驗證**：`cd frontend && npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx` 全綠（≥4 條：ok 表格／disabled 文字／degraded 警語／空 survivors）；`npm run build` rc=0；`npx tsc --noEmit` rc=0；`bash scripts/ic_wiring_check.sh` rc=0。
- **邊界**：① 節缺席（舊報告）⇒ 不渲染 ② `ci95` null ③ 100+ survivors（表格可捲動）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得新增 store toggle；不得改 `CapabilityStatus` 六值；不得畫圖表（表格即可）。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a,d ⇒ 必附。17 條（每條實跑貼 rc；改壞後**必須**有測試轉紅；統一由 `scripts/gap2_mutation_probe.sh --batch Bn` 執行）：
  1. Task 1.1 `fit_projection` 改為在 test 陣列擬合（呼叫端傳錯 mask）⇒ §G O7 轉紅。
  2. `normal_scores` 改為恆等（raw 空間）⇒ §G O1 之 `tanh` 案例轉紅（raw 殘差 Spearman>0.10 之反向斷言亦紅）。
  3. `spearmanr` 改 `pearsonr` ⇒ §G O6 秩不變轉紅。
  4. loo 之條件集誤含 f 自身 ⇒ §G O2（marginal≈gross）轉紅。
  5. `sequential` 排序改用 test IC ⇒ 排序 oracle（Task 1.2 驗證⑧＋構造 train/test IC 順序不同之案例）轉紅。
  6. bootstrap 忽略 seed ⇒ Task 1.2／2.1 決定性斷言轉紅。
  7. `combine_factors` 符號改用 test IC ⇒ Task 2.1 驗證②轉紅。
  8. `ic_weighted` 權重改用 test IC ⇒ 構造 train≠test IC 之案例對參考實作轉紅。
  9. `block_len` 強制 1（iid）⇒ Task 2.1 `block_len ≥ effective_horizon` 斷言轉紅。
  10. `build_survivor_output` 移除 `sample_scope` ⇒ Task 3.1 驗證①轉紅。
  11. validator 放寬 `additional_properties` ⇒ Task 3.1 驗證③轉紅。
  12. 契約 `sample_scope_kind_values` 加入 `"panel"` ⇒ Task 3.1 驗證⑦（⊆ RowMaskPlan.source）轉紅。
  13. stage 6b 於 fallback 仍標 `oos_guarantees=True` ⇒ Task 4.1 驗證③與 Task 3.1 驗證⑥轉紅。
  14. `enabled=False` 改輸出裸 `{}` ⇒ Task 4.1 驗證②與 wiring R3 轉紅。
  15. `save_survivor_output` 之 `feature_names` 改為 `passed_features` ⇒ Task 4.2 驗證②轉紅。
  16. 既有 stage6 任一鍵值被改動（探針故意改 `redundancy_log.method` 字串）⇒ §G-1 golden 轉紅。
  17. `independent_oos_validation` 改輸出 `True` ⇒ Task 3.1 驗證⑪轉紅；`marginal_ic_train_insample` 改為在 test 評估 ⇒ 構造 train／test 關係反轉案例（§G O7 fixture）之 train／test 兩值「必不相等」斷言轉紅。
- **測試層級**：單元（B1–B3 純函式）／整合（B4 三入口、persist redirect）／Golden（§G-1／G-2 真實 kline 衍生 fixture）／邊界（各 Task 邊界欄）／前端元件（B5）。可獨立 `pytest tests/momentum/Analysis/` 跑，不需 `run_api.py`。
- **防假綠**：diff 既有測試斷言（三入口測試、contract sync、wiring check、persist redirect），不得放寬／刪除；`scripts/mutation_probe_check.sh` 對新測試檔全綠；oracle 不得從待測自身衍生（O7 用獨立參考實作、O1–O6 用解析性質）。
- **邊界目錄**：空DF ✓（無 survivors）／全NaN列 ✓（label 全 NaN、常數因子）／Inf ✓（finite 過濾）／std=0 ✓（residual_degenerate、zero_train_ic）／重複·亂序 timestamp ✗（上游 stage0 已守，不重做）／API 重啟 ✗（無狀態）／並發寫 ✓（原子寫檔）／OOM 降載 ✗（k≤數十、n≤數萬，O(k²n) 可忽略；具名不測）／大尺度浮點 reduction ✗（不適用）。
- **測試章程（`docs/TEST_DESIGN_CHARTER.md` §G 模板）**：
  - 風險原則：a,b,d。必做類別：A2 洩漏 MR（MR-L1 O5、MR-L2 O7 變體、MR-L3 O6）、A4 契約、A6 golden、A9 邊界。
  - Oracle 矩陣：O3／O6／O7／O8 EXACT（atol 1e-12）；O1／O2／O4 TOLERANCE（容差寫死＋seed）；O5 STATISTICAL（H0：無資訊，α=0.05，n_min=1000，多重比較＝Bonferroni 於同測試內多因子）；O9 EXACT（seed）；§G-1 EXACT sha。
  - 統計（§F）：F-IC-4 block bootstrap（Task 1.2／2.1）；F-IC-6 標籤置亂（O5）；F-IC-8 train vs test（`train_ic` 與 test `gross_ic` 並列輸出）；F-MC-1（不改 FDR；D4 禁第二次選擇）。
  - 真實路徑：G-OLD＝§G-1 pre 檔；G-NEW＝§G-2；hermetic＝persist redirect。資料 manifest：`tests/golden/la0/inputs/ETHUSDT_12h_*_a0_tail2000.h5@<sha256 寫入 pre 檔>`。信心：full。已知不測：OOM／並發（具名如上）。

## §R 回退

- 每 Phase 獨立 commit 可單獨 revert；B4 之 `marginal_ic.enabled=False` 為一鍵逃生口（回到既有報告鍵集；節顯式 `disabled` 非裸空）；§G-1 FAIL ⇒ 不 merge；B5 為純前端可獨立 revert。

## §N N/A 登記

> 殘留規則（使用者 2026-08-17 定死）：每條必帶 `為何現在不做:`，值只允許 `blocked-by:`／`user-ruling:`／`needs-research:`；附觸發條件；同步登記於 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-2 待補完」節；白話閘逐條說明。

- 本 SPEC 無被省略之必填段（Golden 已於上節填寫，mutation 已於 §V 填寫）。
- R1 IC→ML 橋本體（讀 `ic_survivors_*.json` 餵 `xgboost_batch_service.selected_features` 並強制 `sample_scope`）— `為何現在不做: user-ruling:2026-08-18 使用者裁定橋本體 blocked-by ML 層（成熟度地圖：ML／回測屬不完整層、可能重寫；接上即隨殼作廢，同 G1-R1）`；觸發：ML 層重寫或宣告穩定時，以本契約 `version` 為輸入起新票；登記處：registry #2b（既有列）。
- R2 以邊際 IC 做 forward-stepwise **選擇**（改變倖存者集合）— `為何現在不做: needs-research: post-FDR 第二次選擇之多重比較政策（候選域、α 分配、train 選／test 報的誠實揭露）尚無委員會認可之方法；四方偵察同判預設不得開啟`；觸發：委員會定出政策（可引 registry #4 Pooled IC 之樣本量增益後再議）；登記處：registry「GAP-2 待補完」。
- R3 cross-sectional（`analyze_cross_sectional`）路徑之邊際 IC — `為何現在不做: blocked-by: registry #4 Pooled/Panel IC（xsec 主路徑之 IC 估計量／切分尚未按主線標準重建，先接即隨其重建作廢）`；觸發：#4 完工；登記處：同上。
- R4 前端表格（B5）— **預設納入**；若使用者於白話閘否決 ⇒ 轉 `user-ruling:<日期＋否決>` 並登記。
- R5 nested／frozen final test（讓邊際／組合統計可宣稱獨立 OOS 驗證）— `為何現在不做: blocked-by: IC 主路徑切分現狀 holdout-only（registry「IC 主路徑切分現狀」節；WF／CPCV 未接主線，主線 test 同時供 stage4-6 選擇；本票以 D3′ 揭露欄誠實標示）`；觸發：主線切分升級（WF／CPCV 接入或 nested holdout 契約成立）；登記處：registry「GAP-2 待補完」。
- mutation：**非 N/A**（§V 17 條，逐條由 `scripts/gap2_mutation_probe.sh` 實跑）。
