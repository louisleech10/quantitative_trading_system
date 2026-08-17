# GAP-1 策略層防過擬合（MinBTL／DSR／PBO）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md`（四方偵察收斂，31 findings，債已銷）
> ｜日期：2026-08-17｜對應 TODO：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（本 SPEC 定版後生成）
> 票：`docs/IC_QUANT_GAP_REGISTRY.md` #1｜主委自產偵察版：`handoffs/20260817-gap1-recon-claude.md`

## §RISK 風險分級

- **大小**：大（命中高風險原則；跨模組新增契約與統計核心）。
- **命中高風險原則**：(a) 數值正確性——三關輸出直接用於「這個策略是不是真的有效」之判斷；
  (b) 跨模組共用路徑——新增 `momentum/Analysis/strategy_validation/` 與 `momentum/factories.py` 工廠出口；
  (d) ML/回測正確性——統計量之輸入語意（報酬序列、年化、T、N）錯誤會系統性偏樂觀。
RISK-HIT: a,b,d
- 命中 (a)(d) ⇒ §G 必填、adversarial review 必跑（三家：codex+composer+grok）。

## §A 假設與待使用者確認

**已驗證事實（FACT-RECEIPT；6 條，逐條附實跑輸出）**

- FACT-RECEIPT: `grep -rn "deflated\|DSR\|PBO\|CSCV\|MinBTL\|min_btl" --include="*.py" momentum api` → 印出 0 行（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `ls data/optuna*` → 印出 `no matches found`；`ls results/optimization_results` → 印出目錄不存在（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `h5py` 直讀 `data_cache/feature_klines/kline_cache.h5` → 印出 `1h/data (20352,)`、`4h/data (5088,)`、`12h/data (1696,)` ⇒ T=2.323 年（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `grep -rn "PerformanceMetrics(" --include="*.py" momentum api` → 印出 `vectorized_backtest.py:84`、`objectives/strategy_backtest.py:113` 兩處**皆未傳** `periods_per_year`（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `venv/bin/python scratchpad/nmax.py` → 印出 T=2.323 下 `N_max`：SR=1.0→3／1.5→14／2.0→104／2.5→1,423（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `grep -n "F-ST-2\|F-ST-3" docs/TEST_DESIGN_CHARTER.md` → 印出 `:102` 已登記 `F-ST-2 Deflated Sharpe(Optuna trials>10)`、`F-ST-3 PBO/CSCV(發布前)`（Claude 實跑 2026-08-17）

**待確認：無**

**已確認結果**

- `2026-08-17 使用者白話閘裁決`：交付範圍＝選項 A（契約＋純統計核心全做；接線至實際 pipeline 列具名待接線項）。
- `2026-08-17 使用者白話閘裁決`：MinBTL 判不合格時＝**降級展示＋明顯警語**；**不採** API 硬擋 promote（四方原建議）。
  殘留具名見 §N。
- `2026-08-17 使用者 session 中途補充（成熟度地圖）`：僅 Feature Factory 完整、IC 進行中、
  Kline/事件抓取可能變更、**其餘（含 `momentum/Strategy/`、`momentum/Optimization/`、ML 全線）皆不完整**。

**本 SPEC 承載之偵察 BLOCKING（收斂檔 C1/C2/C3；逐條在 §P 有對應 Task）**

- C1：N 無 fail-closed SoT（四種互不相等語意＋六條繞過路徑）→ Task 2.1／2.2／2.3
- C2：canonical 報酬序列與年化語意分裂（五個產出點；730 寫死；退化回 0.0）→ Task 1.1／1.2／3.2
- C3：PBO 之候選×時間矩陣不存在；CPCV≠CSCV；禁 top-K → Task 4.1／4.2／4.3

## §C 約束

- 解耦 7 條相關項：R1 `momentum/` 不得 import `api/`（新模組為純統計，無 API 依賴）；
  R2 跨域走 Protocol；R3 服務端經 `momentum/factories.py` 的 `create_*`；R6 `pytest tests/momentum/` 可獨立跑；
  R7 DTO 不跨界（三關回傳型別住 `momentum/core/contracts.py` 或新模組內 dataclass，不得直接餵 `api/models/`）。
- 不可違反原則：不弱化 NaN/inf gate；不擅改輸出大小；資料真實性（禁造假、禁合成 fixture 充當真實 kline）。
- **本任務特別注意（成熟度約束，出處＝§A 成熟度地圖）**：
  `momentum/Strategy/`、`momentum/Optimization/`、`api/services/optimization_*`、`api/routes/ml_pipeline.py`、
  `frontend/` 之**結構皆不得作為設計依據**；凡需改其內部結構者一律列 §N 待接線項，不得在本票實作。
  唯一允許的既有檔改動＝Task 1.3（兩個呼叫點傳入年化參數，有既有測試覆蓋）。
- **新資料結構一律 JSON SoT**：本 SPEC 不在散文中列舉欄位/枚舉；欄位集合只在 Task 2.1 出現一次，
  其餘章節僅 pointer。狀態枚舉**不重新定義**，以 ref 指向既有 `ic_report_contract.json#capability_status`
  （現行六值；本 SPEC 不複列，避免兩處列舉漂移）。

## §G Golden / Baseline

- **feature/kline 條件**：**不適用**——本票不碰 feature/kline 之生成/計算/merge/split/洩漏（純統計層吃報酬序列）。
  但 §A 的資料長度 receipt 使用真實 `data_cache/feature_klines/kline_cache.h5`，禁以合成資料取代該 receipt。
- **凍結時機 / reference 設定**：Task 3.1 動工前建立
  `tests/momentum/Analysis/golden/gap1_reference_cases.json`（**唯一** baseline 檔，路徑寫死），
  逐案例附 `provenance` 欄（文獻條目或解析推導出處），無 provenance 之數值不得入檔。
- **baseline 內容（三類 oracle，皆非自造 golden）**：
  1. **文獻對照**：Bailey & López de Prado, *The Deflated Sharpe Ratio*（2014, JPM）與
     Bailey et al., *The Probability of Backtest Overfitting*（2015, J. Computational Finance）之已知數值/表格；
     `MinBTL ≈ 2·ln(N)/SR²` 出自 *Pseudo-Mathematics and Financial Charlatanism*（2014, Notices of the AMS）。
  2. **解析極限性質**（可證偽等式，非近似）：
     - DSR 在 `n_trials=1` 且 skew=0、kurt=3 時，須等於同輸入之 PSR（probabilistic Sharpe ratio）解析值。
     - `E[max SR]/√V[SR]` 在 N=10／100／1000 之值＝1.5746／2.5306／3.2551（由公式獨立重算，容差 1e-4）。
     - `cscv_splits` 之組合數須恰為 `C(S, S/2)`（S=12→924；S=14→3,432；S=16→12,870）。
     - `max_trials_budget` 與 `min_btl_years` 須互為反函數：`min_btl_years(max_trials_budget(T,SR),SR) ≈ T`（rel≤1e-9）。
  3. **統計性質對照**（PBO 之行為 oracle）：全噪音候選矩陣 ⇒ PBO 落在 0.5 之統計容差內；
     單一真 alpha ＋ 其餘噪音 ⇒ PBO 顯著 < 0.5。容差與樣本數在 Task 4.2 寫死並附 seed。
- **通過條件（可證偽，容差分尺度）**：文獻/解析類 `atol=1e-4`（明示為近似者另標容差並附出處）；
  解析等式類 `atol=1e-10`；反函數性質 `rtol=1e-9`；baseline 檔本身以 `sha256` 記錄於測試中防偷改；
  統計類以固定 seed 之區間斷言；超出即列出案例 id + 實際 diff = FAIL。

## §P Phase 與依賴

### Phase B1 — 頻率與退化語意契約（依賴：無）

**Task 1.1 — 年化頻率解析（單一來源）**
- 目標：把「年化係數必須由資料 timeframe 推導」落成可被機器驗的函式與契約。
- 檔案：新增 `momentum/Analysis/strategy_validation/frequency.py::resolve_periods_per_year(timeframe: str) -> int`
- 既有 caller/影響面：新建無 caller；讀 `momentum/core/constants.py::TIMEFRAME_SECONDS`（唯一來源，不複製表）。
- 改法：`periods_per_year = round(365*24*3600 / TIMEFRAME_SECONDS[timeframe])`；未知 timeframe ⇒
  `raise UnknownTimeframeError`（fail-closed，**禁**回預設值）。不新增 timeframe 常數。
- **驗證**：`resolve_periods_per_year("1h") == 8760`、`("4h") == 2190`、`("12h") == 730`、`("1d") == 365`；
  `resolve_periods_per_year("7m")` raise。測試：`pytest tests/momentum/Analysis/strategy_validation/test_frequency.py -q`
- **邊界**：① 未知 timeframe → raise（非回 730）② 空字串/None → raise ③ 大小寫變體 `"1H"` → 明確定義為 raise（不做寬鬆解析）。
- **存活至**：全票完工後保留（B3/B4 皆依賴）。
- **覆蓋風險**：無。
- 不可做：不得在本檔新增 timeframe→秒 的第二份對照表；不得提供 `default=730` 參數。

**Task 1.2 — typed Sharpe（退化情形回 NaN＋status，非 0.0）**
- 目標：三關自算觀測 Sharpe，杜絕吃既有 `PerformanceMetrics` 的 `0.0` 混淆語意。
- 檔案：新增 `momentum/Analysis/strategy_validation/sharpe.py::compute_sharpe(returns, *, periods_per_year, risk_free_rate=0.0) -> SharpeResult`
- 既有 caller/影響面：新建無 caller。**不改** `momentum/Strategy/performance_metrics.py` 之語意（見 Task 1.3 之最小改動範圍）。
- 改法：`periods_per_year` 為**必填關鍵字參數**（無預設）；樣本標準差 `ddof=1`；
  回傳 dataclass 含 `value`／`status`／`reason`／`n_obs`／`periods_per_year`／`skew`／`kurtosis`；
  空序列、`n_obs<2`、`std==0`、含 NaN/inf ⇒ `value=nan` 且 status 取自契約枚舉（Task 2.1 之 ref）。
- **驗證**：常數序列 ⇒ `value` 為 NaN 且 status≠ok（**非** 0.0）；已知手算案例 ⇒ `abs≤1e-12`；
  `skew`/`kurtosis` 與 `scipy.stats.skew/kurtosis(fisher=False)` 一致（`abs≤1e-10`）。
- **邊界**：① 空 Series ② 全 NaN ③ 單一觀測 ④ std=0 ⑤ 含 inf ⑥ 全零序列（合法但 std=0）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得提供「回 0.0」的相容模式；不得在本函式內做年化推導（呼叫方傳入，Task 1.1 負責）。

**Task 1.3 — 既有兩呼叫點傳入年化參數（唯一允許的不完整層改動）**
- 目標：消除 `periods_per_year=730` 於策略路徑之隱性寫死。
- 檔案：`momentum/Strategy/vectorized_backtest.py:84`、`momentum/Optimization/objectives/strategy_backtest.py:113`
- 既有 caller/影響面：`tests/momentum/Strategy/test_performance_metrics.py`、
  `tests/momentum/Strategy/test_vectorized_backtest.py`、`tests/momentum/Optimization/test_strategy_backtest_enhanced.py`
  （動工前先 diff 其斷言，禁放寬換綠）。
- 改法：兩處改為顯式傳入 `periods_per_year`（由呼叫端已知的 timeframe 經 Task 1.1 解析）；
  timeframe 不可得時**保留現行預設值並記錄 `annualization_source="default_730"`**（不改行為、只讓來源可見），
  三關**拒絕**消費 `annualization_source="default_730"` 之 Sharpe（回 status≠ok）。
- **驗證**：`grep -c "PerformanceMetrics(equity_curve, trades)" momentum` == 0；
  既有三個測試檔全綠且斷言未放寬（diff 附於 PR/commit）；
  `pytest tests/momentum/Strategy/test_vectorized_backtest.py tests/momentum/Optimization/test_strategy_backtest_enhanced.py -q` rc=0；
  新增斷言：兩呼叫點之 metrics 結果須帶 `annualization_source` 且值 `== "resolved"` 或 `== "default_730"`（二值皆須有測試覆蓋）
- **邊界**：① timeframe 不可得 ② timeframe 為未支援值（Task 1.1 raise，呼叫端須捕捉並落 `default_730` 標記）。
- **存活至**：全票完工後保留；若未來回測引擎重寫，本 Task 之契約條文（年化須由資料推導）存活、實作可棄。
- **覆蓋風險**：實作可能被未來引擎重寫覆蓋——**已知且接受**（價值主體在契約與 B3/B4 純函式，見 §A 成熟度地圖）。
- 不可做：不得改 `PerformanceMetrics` 的既有回傳語意（0.0 保持原狀，避免波及未成熟層之未知 caller）。

### Phase B2 — N 帳本契約與 fail-closed 讀取（依賴：B1 Task 1.2 之 status 枚舉 ref）

**Task 2.1 — 策略驗證契約 JSON（唯一真相源）**
- 目標：把 N 帳本記錄結構、三關報告區段、狀態語意收斂為單一機器可讀檔。
- 檔案：新增 `momentum/Analysis/contracts/strategy_validation_contract.json`
- 既有 caller/影響面：新建；**不改** `ic_report_contract.json`（scope 錯位，見收斂檔 C4）。
- 改法：本檔須含且僅含下列頂層鍵（**本 SPEC 中此欄位集合只出現於本 Task，其餘章節僅 pointer**）：
  `version`、`capability_status_ref`（值＝`momentum/Analysis/contracts/ic_report_contract.json#capability_status`，
  以 ref 複用六值枚舉、禁複列）、`ledger_record_keys`、`n_fields`、`report_sections`、
  `eligibility_keys`、`annualization_source_values`、`reasons`。
  `ledger_record_keys` 須涵蓋：`research_session_id`／`dataset_key`／`candidate_id`／`evaluation_id`／
  `attempt_index`／`state`／`metric_name`／`metric_value`／`metric_valid`／`input_artifact_hash`／`ts`。
  `n_fields` 須為四個**分列**欄位：`n_candidates_considered`／`n_evaluated`／`n_valid_metrics`／`n_failed_or_pruned`
  （**禁**任何單一欄位命名為 `n` 或 `N`）＋ `n_is_lower_bound`（bool）。
- **驗證**：`jq -e '.capability_status_ref' <file>` rc=0；
  `pytest tests/momentum/Analysis/strategy_validation/test_contract.py -q` 斷言
  ① 六值枚舉**不**在本檔字面出現（防兩處列舉）② 四個 n_fields 皆在 ③ 無鍵名為 `n`/`N`。
- **邊界**：① JSON 語法錯 ⇒ 載入 raise ② ref 指向的檔缺失 ⇒ raise（fail-closed）③ 未知鍵 ⇒ `validate_against_contract` rc!=0。
- **存活至**：全票完工後保留（B3/B4 與未來接線批皆消費）。
- **覆蓋風險**：無（新檔，無既有消費者）。
- 不可做：不得在此檔複列 capability_status 六值；不得放入實作邏輯或預設 N 值。

**Task 2.2 — N 帳本讀取 API（今日無生產者 ⇒ 誠實 unavailable）**
- 目標：三關取 N 的唯一入口，且缺帳本時 fail-closed。
- 檔案：新增 `momentum/Analysis/strategy_validation/ledger.py::read_trial_ledger(*, research_session_id, dataset_key) -> LedgerReadResult`
- 既有 caller/影響面：新建無 caller；ledger 落地路徑由 `momentum/core/config.py` 之既有輸出根目錄推導（不新增設定鍵）。
- 改法：讀 append-only JSONL；逐列以 Task 2.1 之 `ledger_record_keys` 驗證，非法列 ⇒ 計入
  `n_failed_or_pruned` 並記 reason，**不得靜默丟棄**；回傳四個 n 欄位＋`n_is_lower_bound=true`（恆真，人手迭代不可觀測）
  ＋status。帳本不存在／`dataset_key` 無列 ⇒ `status≠ok`、`reason=n_unknown`，**禁**回 `n=1`、
  **禁**以 request `n_trials` 或完成數替代。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_ledger.py -q` rc=0；無檔案 ⇒ `status != "ok"` 且 `reason == "n_unknown"`（字面斷言）；
  含 3 合法列＋1 非法列 ⇒ `n_evaluated==3` 且非法列進 `n_failed_or_pruned` 且 reason 非空；
  `n_is_lower_bound is True` 恆成立（參數化測試至少 3 種輸入）。
- **邊界**：① 檔不存在 ② 空檔 ③ 非法 JSON 行 ④ 缺必填鍵 ⑤ 同 `candidate_id` 多 `attempt_index`（去重為 1 candidate、attempts 各計）⑥ 檔案權限不可讀。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：**不得**接線至 Optuna／`_record_trial_metrics`／`optimization_task_service`（成熟度約束，§N 待接線項）；
  不得提供「使用者手填 N」之正式路徑（敏感度分析路徑見 Task 3.3 之 watermark 要求）。

**Task 2.3 — 生產者一致性測試（未來引擎的入口義務）**
- 目標：把「未來搜尋引擎必須寫 ledger」變成可執行的合約測試，而非文件承諾。
- 檔案：新增 `momentum/Analysis/strategy_validation/ledger.py::append_trial_attempt(...)`
  ＋`tests/momentum/Analysis/strategy_validation/test_ledger_conformance.py`
- 既有 caller/影響面：新建無 caller。
- 改法：`append_trial_attempt` 為唯一合法寫入口（先以 Task 2.1 之 schema 檢核、通過才 append；寫入失敗 raise）；
  conformance 測試以「假想生產者」呼叫該函式後，`read_trial_ledger` 之四個 n 欄位須自洽
  （`n_evaluated == n_valid_metrics + n_failed_or_pruned`）。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_ledger_conformance.py -q` 全綠；
  以缺鍵記錄呼叫 ⇒ raise（不得寫入半列）；並發追加 2×50 列 ⇒ 讀回 100 列且無交錯損壞。
- **邊界**：① 缺必填鍵 ② 型別錯 ③ 並發追加 ④ 磁碟不可寫 ⑤ 重複 `evaluation_id`（拒絕，raise）。
- **存活至**：全票完工後保留（未來引擎開發時作為驗收）。
- **覆蓋風險**：無。
- 不可做：不得為了通過測試而放寬 schema；不得在本票把任何真實生產者接上。

### Phase B3 — MinBTL＋DSR 純統計核心（依賴：B1 全部、B2 Task 2.1／2.2）

**Task 3.1 — MinBTL 與試驗預算（互為反函數）**
- 目標：資格閘＋可行動的「試驗預算」輸出（使用者裁決之產品形態）。
- 檔案：新增 `momentum/Analysis/strategy_validation/min_btl.py`：
  `min_btl_years(*, n_trials, target_sharpe) -> float`、
  `max_trials_budget(*, t_years, target_sharpe) -> int`、
  `assess_eligibility(*, t_years, n_trials, target_sharpe) -> EligibilityResult`
- 既有 caller/影響面：新建無 caller。
- 改法：`min_btl_years = 2*ln(n_trials)/target_sharpe**2`；`max_trials_budget = floor(exp(t_years*target_sharpe**2/2))`；
  `assess_eligibility` 回傳 `eligible`（bool）／`required_years`／`available_years`／`trials_budget`／
  `trials_used`／`status`／`reason`；`n_trials` 來源限 Task 2.2 之讀取結果，`status≠ok` ⇒
  `eligible=None`（三態，**禁**以 False 冒充「已判定不合格」）。
- **驗證**：`min_btl_years(n_trials=100, target_sharpe=1.0)` ≈ 9.2103（abs≤1e-4）；
  `max_trials_budget(t_years=2.323, target_sharpe=1.5) == 14`；
  反函數性質 `min_btl_years(max_trials_budget(T,SR),SR) <= T`（對 20 組 (T,SR) 參數化）；
  `n_trials=1` ⇒ `min_btl_years==0.0`；`target_sharpe<=0` ⇒ raise。
- **邊界**：① `n_trials=1` ② `n_trials<1` ⇒ raise ③ `target_sharpe<=0` ⇒ raise ④ `t_years<=0` ⇒ raise
  ⑤ N 不可知（status≠ok）⇒ `eligible=None` ⑥ 極大 N（1e6）不得 overflow。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：**不得**提供任何調整公式常數（`2`、`ln`）之參數或旗標（使用者裁決＋「禁取巧」鐵律）；
  不得以提高取樣頻率折抵年數（`t_years` 語意固定為年，見 §V 之反向測試）。

**Task 3.2 — Deflated Sharpe Ratio**
- 目標：冠軍檢定，輸入語意鎖死且退化 fail-closed。
- 檔案：新增 `momentum/Analysis/strategy_validation/deflated_sharpe.py::deflated_sharpe(*, returns, n_trials, periods_per_year, sharpe_variance=None, t_semantics) -> DSRResult`
- 既有 caller/影響面：新建無 caller；內部使用 Task 1.2 `compute_sharpe`、Task 1.1 頻率解析結果。
- 改法：`E[max SR] = sqrt(V[SR]) * ((1-γ)*Φ⁻¹(1-1/N) + γ*Φ⁻¹(1-1/(N*e)))`，γ=0.5772156649015329；
  檢定統計量含 `√(T-1)` 與 skew/kurtosis 修正；`t_semantics` 為**必填**枚舉（值集合住 Task 2.1 契約），
  三關拒絕 `annualization_source="default_730"` 之輸入；`sharpe_variance=None` 且無法自 ledger 取得
  trial 間 SR 變異數 ⇒ `status≠ok`、`reason` 具名（**禁**以任意預設變異數計算）。
- **驗證**：`n_trials=1`、skew=0、kurt=3 ⇒ 等於同輸入 PSR 解析值（abs≤1e-10）；
  `E[max SR]/√V[SR]` 三點對照（N=10/100/1000 → 1.5746/2.5306/3.2551，abs≤1e-4）；
  N 增大 ⇒ DSR 單調不增（參數化 10 點）；退化序列 ⇒ `status≠ok` 且 `value` 為 NaN。
- **邊界**：① N 不可知 ② 序列含 NaN ③ std=0 ④ `n_trials=1` ⑤ 極端 kurtosis（>50）⑥ `t_semantics` 缺失 ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得吃 `PerformanceMetrics.calculate_all()` 之 `sharpe_ratio`（0.0 語意，見收斂檔 C2）；
  不得以 `n_trials` 之請求值（`api/routes/optimization.py:48`）替代 ledger 值。

**Task 3.3 — 報告區段與降級展示契約（使用者裁決：不硬擋）**
- 目標：三關結果之機器可讀輸出與「明顯警語」之可驗收定義。
- 檔案：新增 `momentum/Analysis/strategy_validation/report.py::build_validation_section(...)`；
  區段鍵與 `eligibility_keys` 住 Task 2.1 契約。
- 既有 caller/影響面：新建無 caller；**不改** `optimization_output_service`／`ml_pipeline`（§N 待接線項）。
- 改法：輸出含 `eligibility`（機器可讀，含 `eligible` 三態＋`reason`＋`trials_budget`／`trials_used`）、
  `min_btl`／`dsr`／`pbo` 三節各帶 status/reason；不合格或 status≠ok 時
  **必須**同時輸出 `display_downgrade=true` 與 `warning_text_key`（文案 key，不在此層寫死文案）。
  `eligible is not True` 時**禁**在同一結構內提供任何「建議上線／採用此參數」語意欄位。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_report_section.py -q` 斷言
  ① `eligible=None`／`False` 時 `display_downgrade is True` 且 `warning_text_key` 非空
  ② 該兩情形下結構中不存在推薦類鍵（以契約 allowlist 機械比對）
  ③ 結構通過 `validate_against_contract`（Task 2.1）。
- **邊界**：① 三關皆 unavailable ② 僅 MinBTL 可算 ③ 使用者提供假設 N（敏感度分析）⇒ 須帶
  `n_source="assumed_not_ledgered"` watermark 且 `eligible` 強制 `None`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得實作 API 層硬擋（使用者裁決）；不得把文案字串寫進 momentum 層。

### Phase B4 — PBO（CSCV）純統計核心（依賴：B1、B2 Task 2.1、B3 Task 3.1）

**Task 4.1 — CSCV 分割器**
- 目標：Bailey CSCV 之 S 塊組合切分（與 CPCV 語意分離）。
- 檔案：新增 `momentum/Analysis/strategy_validation/cscv.py::cscv_splits(*, n_obs, s_blocks) -> list[tuple[np.ndarray, np.ndarray]]`
- 既有 caller/影響面：新建無 caller；**不 import** `momentum/Analysis/model_validation/combinatorial_purged_cv.py`
  （語意不同，見收斂檔 C3；如需 purge/embargo 為未來擴充，本票不做）。
- 改法：等分 `n_obs` 為 S 塊（餘數分配規則寫死並測試）；枚舉 `C(S, S/2)` 個組合，IS＝選中塊之時間序拼接、
  OOS＝補集；S 必為偶數，否則 raise。
- **驗證**：`len(cscv_splits(n_obs=1200, s_blocks=12)) == 924`；S=14→3432；S=16→12870；
  每組 IS∪OOS 覆蓋全索引且交集為空（全組合斷言）；S 為奇數 ⇒ raise。
- **邊界**：① S 奇數 ② `s_blocks > n_obs` ⇒ raise ③ `n_obs` 不被 S 整除（餘數規則）④ S=2（最小）⑤ S=20（組合數 184,756，須在測試中標明成本並以較小 S 為預設）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得對組合做隨機子取樣（`max_paths` 式）而仍稱 PBO；若未來需子取樣須另立欄位標示。

**Task 4.2 — PBO 值**
- 目標：由候選×時間報酬矩陣算 PBO。
- 檔案：新增 `momentum/Analysis/strategy_validation/pbo.py::probability_of_backtest_overfitting(*, returns_matrix, s_blocks, selection_metric, universe_provenance) -> PBOResult`
- 既有 caller/影響面：新建無 caller。
- 改法：對每組 CSCV 分割，以 `selection_metric`（枚舉住 Task 2.1）在 IS 選冠軍，取其 OOS 相對排名 `r`，
  `ω = ln(r/(1-r))`，`PBO = P(ω<0)`＝OOS 排名落於中位數以下之組合比例；回傳 PBO 值＋logit 分布摘要＋status。
- **驗證**：全噪音矩陣（固定 seed，候選 50、T 1200、S 12）⇒ PBO ∈ [0.4, 0.6]；
  單一真 alpha＋49 噪音 ⇒ PBO < 0.3；IS/OOS 對調（mutation）⇒ 上述兩斷言至少一條轉紅；
  候選數<2 ⇒ `status≠ok`（**禁**回 0）。
- **邊界**：① 候選數<2 ② 矩陣含 NaN 列（該候選標 invalid，不得靜默丟棄）③ 全候選相同 ④ T 不足以切 S 塊 ⑤ 平手排名（tie 規則寫死並測試）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得在此層自行重跑回測取得矩陣（矩陣由呼叫方提供；重算式接線屬 §N 待接線項）。

**Task 4.3 — 候選宇宙污染防護（禁 top-K）**
- 目標：把「禁用全樣本 top-K 子集」做成機械拒絕，而非註解。
- 檔案：`momentum/Analysis/strategy_validation/pbo.py` 之 `universe_provenance` 參數驗證
  ＋契約 `reasons` 之具名 reason。
- 既有 caller/影響面：Task 4.2。
- 改法：`universe_provenance` 為必填 dataclass，含 `selection_free`（bool，宣稱候選集未經全樣本績效篩選）
  與 `source`（枚舉，住 Task 2.1）；`selection_free is not True` ⇒ 直接回
  `status≠ok`、`reason=universe_selection_contaminated`，**不計算 PBO**。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_pbo_universe_guard.py -q` rc=0，斷言
  ① `selection_free=False` ⇒ `status != "ok"` 且 `math.isnan(value)` 且 `reason == "universe_selection_contaminated"`
  ② `selection_free=True` 且 `source` 不在枚舉 ⇒ raise（`pytest.raises`）
  ③ mutation：移除該檢查 ⇒ 上列 ① 轉紅（實跑貼 rc）。
- **邊界**：① `selection_free=False` ② `universe_provenance=None` ⇒ raise ③ `source` 未知值 ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得提供 `force=True` 之繞過參數。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a,d ⇒ 必附 mutation 設計。本票之 mutation 清單（每條須實跑並貼 rc，
  改壞後**必須**有測試轉紅，否則該測試判為裝飾品並重寫）：
  1. 刪除 DSR 之 γ 項（`E[max SR]` 只留第一項）⇒ Task 3.2 三點對照轉紅。
  2. `min_btl_years` 之 `ln(n_trials)` 改為 `n_trials` ⇒ Task 3.1 數值與反函數斷言轉紅。
  3. CSCV 之 IS/OOS 對調 ⇒ Task 4.2 之 PBO 行為斷言轉紅。
  4. `compute_sharpe` 退化情形回 0.0（還原舊語意）⇒ Task 1.2 status 斷言轉紅。
  5. 移除 `universe_provenance` 檢查 ⇒ Task 4.3 斷言轉紅。
  6. `read_trial_ledger` 缺檔時回 `n=1` ⇒ Task 2.2 之 `reason=n_unknown` 斷言轉紅。
  7. `resolve_periods_per_year` 未知 timeframe 回 730 ⇒ Task 1.1 raise 斷言轉紅。
- **反向測試（防「用頻率折抵年數」之取巧）**：同一期間之 1h／4h／12h 報酬序列，
  `assess_eligibility` 之 `available_years` 三者差異須 ≤1e-6；若實作把 bar 數當年數則此測試轉紅。
- 測試層級：單元（各純函式）／整合（`build_validation_section` 串三關）／Golden 對照
  （`tests/momentum/Analysis/golden/gap1_reference_cases.json`）／邊界（下列目錄）。
  全部可獨立 `pytest tests/momentum/Analysis/strategy_validation/ -q`，不需 `run_api.py`（R6）。
- **防假綠**：Task 1.3 動工前 diff 三個既有測試檔之斷言並附 diff；不得放寬或刪除既有斷言換綠。
- **邊界目錄（適用項）**：空 DF ✓／全 NaN 列 ✓／Inf ✓／std=0 ✓／重複·亂序 timestamp ✓（ledger `evaluation_id` 重複）／
  API 重啟 ✗（本票無 API 層）／並發寫 ✓（Task 2.3）／OOM 降載 ✗（純函式，PBO 成本由 S/N 控制且已在 Task 4.1 邊界標明）／
  大尺度浮點 reduction ✓（極大 N 之 `exp`／`ln` overflow）。

## §R 回退

- 四批各自獨立 commit，可單獨 revert；B1 Task 1.3 為唯一觸及既有檔者，單獨成 commit 以便單點回退。
- 新模組（B1 1.1/1.2、B2、B3、B4）**無既有 caller** ⇒ revert 即完全移除，無下游破壞。
- 三關為純函式，`pytest tests/momentum/Analysis/strategy_validation/ -q` rc=0 即可用，**不加預設關閉旗標**（對齊「驗過就別預設關閉」）；
  逃生口＝呼叫方不呼叫，非旗標。
- Golden（`gap1_reference_cases.json`）FAIL ⇒ 不 merge。

## §N N/A 登記

- **接線類 Task（全部具名待接線項，理由＝§A 成熟度地圖：上游皆不完整，改其結構將於重寫時作廢）**：
  1. Optuna／`_record_trial_metrics` 寫入 ledger（生產者接線）— 待引擎成熟；本票以 Task 2.3 conformance 測試鎖住義務。
  2. `api/services/optimization_output_service.py` 產出候選×時間矩陣（PBO 重算式接線）— 待引擎成熟。
  3. `api/routes/ml_pipeline.py` 掛載 eligibility 檢查 — 待 pipeline 路徑成形。
  4. `frontend/` 之降級展示面板與警語文案 — 待後端接線完成；本票僅定義 `display_downgrade`／`warning_text_key`。
  5. 策略層 wiring 閘門（等價於 `scripts/ic_wiring_check.py` 但吃策略契約）— 待接線批；
     本票不擴 `ic_wiring_check.py`（其 `REPORT_SECTIONS` 為 IC 封閉集合）。
- **API 層硬擋 promote**：N/A — **使用者 2026-08-17 裁決採「降級展示＋明顯警語」**。
  🔴 **具名殘留（不得靜默）**：`api/routes/ml_pipeline.py:124-245` 之 promote/建 pipeline 路徑
  在此裁決下仍可消費不合格冠軍（CODEX-R1-P1-06 之洞不關閉）。緩解＝Task 3.3 之 `eligibility`
  機器可讀欄位使未來改判硬擋時無需重做契約。觸發改判條件：使用者要求，或該路徑實際上線並產生誤用。
- **TPE 自適應搜尋使「N 個獨立候選」前提失真**：N/A 於本票修復（屬搜尋器設計）；
  具名殘留＋緩解＝報告標 `n_semantics`（值住 Task 2.1 契約），DSR 之 `sharpe_variance` 缺失時 fail-closed。
- **`prediction_analyzer.py:154` `np.cumsum` 單利權益**：N/A — 不在策略路徑（收斂檔 C2 第 6 點），
  另立小票；本 SPEC 明定三關不得消費該路徑輸出。
