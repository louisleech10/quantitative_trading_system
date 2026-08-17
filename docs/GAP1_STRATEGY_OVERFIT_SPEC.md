# GAP-1 策略層防過擬合（MinBTL／DSR／PBO）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md`（四方偵察收斂，31 findings，債已銷）
> ｜日期：2026-08-17（R2＝三家 adversarial R1 後修訂）｜對應 TODO：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（本 SPEC 定版後生成）
> 票：`docs/IC_QUANT_GAP_REGISTRY.md` #1｜偵察主委版：`handoffs/20260817-gap1-recon-claude.md`
> R1 adversarial：`handoffs/20260817-gap1-specadv-{codex,composer,grok}.md`（23 findings）

## §RISK 風險分級

- **大小**：大（命中高風險原則；新增契約與統計核心，並最小幅修改一個既有回測呼叫路徑）。
- **命中高風險原則**：(a) 數值正確性——三關輸出直接用於「這個策略是不是真的有效」之判斷；
  (b) 跨模組共用路徑——新增 `momentum/Analysis/strategy_validation/` 並修改 `VectorizedBacktest.run_backtest` 簽名；
  (d) ML/回測正確性——統計量之輸入語意（報酬序列、年化、T、N、V[SR]）錯誤會系統性偏樂觀。
RISK-HIT: a,b,d
- 命中 (a)(d) ⇒ §G 必填、adversarial review 必跑（三家：codex+composer+grok）。
- **不承諾** `momentum/factories.py` 工廠出口（R1 CODEX-R1-P1-09）：三關為無狀態純函式、無跨域注入需求，
  消費端直接 import；如未來接線批需要注入點，於該批新增，本票不做。

## §A 假設與待使用者確認

**已驗證事實（FACT-RECEIPT；7 條，逐條附實跑輸出，且皆可由 repo 內命令重現——R1 COMPOSER-R1-P1-01 更正：前版引用 `scratchpad/nmax.py` 不在 repo，已改為 inline 一行重算）**

- FACT-RECEIPT: `grep -rn "deflated\|DSR\|PBO\|CSCV\|MinBTL\|min_btl" --include="*.py" momentum api` → 印出 0 行（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `ls data/optuna*` → 印出 `no matches found`；`ls results/optimization_results` → 印出目錄不存在（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `venv/bin/python -c "import h5py;f=h5py.File('data_cache/feature_klines/kline_cache.h5');print([(k,f[k+'/1h/data'].shape,f[k+'/4h/data'].shape,f[k+'/12h/data'].shape) for k in list(f.keys())[:1]])"` → 印出 `[('ADAUSDT', (20352,), (5088,), (1696,))]`（同期間，`BTCUSDT` 等各 symbol 同列數）⇒ T=20352/8760=2.3232876712328765 年（Claude 實跑 2026-08-17；**R2 CODEX-R2-P1-01 更正：前版寫 `1h/data` 缺 symbol 前綴，該路徑 KeyError**）
- FACT-RECEIPT: `grep -rn "PerformanceMetrics(" --include="*.py" momentum api` → 印出 `vectorized_backtest.py:84`、`objectives/strategy_backtest.py:113` 兩處**皆未傳** `periods_per_year`（Claude 實跑 2026-08-17）
- FACT-RECEIPT: `venv/bin/python -c "import math;T=20352/8760;print([math.floor(math.exp(T*s*s/2)) for s in (1.0,1.5,2.0,2.5)])"` → 印出 `[3, 13, 104, 1422]`（Claude 實跑 2026-08-17；**R1 GROK-R1-P0-01 更正：前版誤用四捨五入寫成 14／1423**）
- FACT-RECEIPT: `venv/bin/python -c "import math;T=20352/8760;print(2*math.log(13)/1.5**2<=T, 2*math.log(14)/1.5**2<=T)"` → 印出 `True False`（Claude 實跑 2026-08-17；證 floor 才使預算與資格閘自洽）
- FACT-RECEIPT: `grep -n "F-ST-2\|F-ST-3" docs/TEST_DESIGN_CHARTER.md` → 印出 `:102` 已登記 `F-ST-2 Deflated Sharpe(Optuna trials>10)`、`F-ST-3 PBO/CSCV(發布前)`（Claude 實跑 2026-08-17）

**待確認：無**

**已確認結果**

- `2026-08-17 使用者白話閘裁決`：交付範圍＝選項 A（契約＋純統計核心全做；接線至實際 pipeline 列具名待接線項）。
- `2026-08-17 使用者白話閘裁決`：MinBTL 判不合格時＝**降級展示＋明顯警語**；**不採** API 硬擋 promote。殘留具名見 §N。
- `2026-08-17 使用者 session 中途補充（成熟度地圖）`：僅 Feature Factory 完整、IC 進行中、
  Kline/事件抓取可能變更、**其餘（含 `momentum/Strategy/`、`momentum/Optimization/`、ML 全線）皆不完整**。

**文獻定義之誠實邊界（R1 CODEX-R1-P0-01；本 SPEC 全篇據此用詞）**

- `2*ln(N)/SR²` 在 Bailey & LdP（2014, Notices of the AMS）Eq.(3.2) 為**上界不等式**
  且推導假設**大 N 與 trial 獨立**。本 SPEC 之 `min_btl_years_upper_bound` **定義為該保守上界**（產品用資格門檻），
  函式與報告欄位皆須帶 `upper_bound` 語意，**禁**在任何輸出宣稱其為精確最短長度。
- `target_sharpe` 之語意鎖定為「**使用者想宣稱的年化夏普**（即 `E[max_N]` 之目標值）」，
  **非**觀測夏普；報告須同時輸出 observed SR 與 target SR，禁混用。
- `N=1`（無多重比較）為特例：`Φ⁻¹(1-1/N)=Φ⁻¹(0)=-∞` 不可代入 ⇒ 明定 `N=1 ⇒ SR0=0`（無 deflation）
  且 `min_btl_years_upper_bound=0.0`；此為契約而非近似。

**本 SPEC 承載之偵察 BLOCKING（收斂檔 C1/C2/C3；逐條在 §P 有對應 Task）**

- C1：N 無 fail-closed SoT（四種互不相等語意＋六條繞過路徑）→ Task 2.1／2.2／2.3 ＋ §N 繞過清單
- C2：canonical 報酬序列與 T／年化語意分裂 → Task 1.1／1.2／**1.4**／3.2
- C3：PBO 之候選×時間矩陣不存在；CPCV≠CSCV；禁 top-K → Task 4.1／4.2／4.3

## §C 約束

- 解耦 7 條相關項：R1 `momentum/` 不得 import `api/`；R2 跨域走 Protocol；
  R6 `pytest tests/momentum/` 可獨立跑；R7 DTO 不跨界（三關回傳型別為新模組內 dataclass，不得直接餵 `api/models/`）。
  R3（服務經 factories）**本票不適用**：無服務端消費者（見 §RISK 之工廠出口說明）。
- 不可違反原則：不弱化 NaN/inf gate；不擅改輸出大小；資料真實性（禁造假、禁合成 fixture 充當真實 kline）。
- **成熟度約束（出處＝§A 成熟度地圖）**：`momentum/Strategy/`、`momentum/Optimization/`、
  `api/services/optimization_*`、`api/routes/ml_pipeline.py`、`frontend/` 之**結構不得作為設計依據**；
  凡需改其內部結構者列 §N 待接線項。
- **允許改動之既有檔白名單（唯此三處，R1 CODEX-R1-P0-02／GROK-R1-P1-04）**：
  1. `momentum/Strategy/vectorized_backtest.py`：`run_backtest` **新增** optional 參數 `timeframe: str | None = None`；
     `BacktestResult` **新增** 欄位 `annualization: dict`（平行 metadata，**不動** `metrics: Dict[str, float]` 型別）。
  2. `momentum/Optimization/objectives/strategy_backtest.py`：`__init__` 新增 optional `timeframe`，於 `:113` 傳遞。
     兩呼叫點**額外允許**顯式傳 `risk_free_rate`（預設維持現行 0.02；僅 oracle fixture 用 0.0）
     ——理由見 Task 1.3 斷言③（R2 CODEX-R2-P0-01／GROK-R2-P0-01）。
  3. 上述二者對應之既有測試檔（僅新增斷言，禁放寬既有斷言）。
  **不改** `momentum/Strategy/performance_metrics.py`（其 `0.0` 退化語意與 `Dict[str, float]` 回傳保持原狀）。
- **新資料結構一律 JSON SoT**：欄位/枚舉集合只在 Task 2.1 出現一次，其餘章節僅 pointer。
  capability status **不重新定義**，以 ref 指向 `ic_report_contract.json#capability_status`（resolver 見 Task 2.1）。

## §G Golden / Baseline

- **feature/kline 條件**：本票不碰 feature/kline 之生成/計算/merge/split/洩漏（純統計層吃報酬序列）；
  §A 的資料長度 receipt 仍使用真實 `data_cache/feature_klines/kline_cache.h5`，禁以合成資料取代該 receipt。
- **凍結時機 / reference 設定**：Task 3.1 動工前建立
  `tests/momentum/Analysis/golden/gap1_reference_cases.json`（**唯一** baseline 檔，路徑寫死），
  逐案例附 `provenance` 欄（文獻條目或解析推導出處），無 provenance 之數值不得入檔；
  測試須以 `sha256` 記錄該檔內容並斷言未被就地改寫。
- **baseline 內容（三類 oracle，皆非自造）**
  1. **文獻對照**：Bailey & López de Prado, *The Deflated Sharpe Ratio*（2014, JPM）；
     Bailey et al., *The Probability of Backtest Overfitting*（2015, J. Computational Finance）Algorithm 2.3；
     *Pseudo-Mathematics and Financial Charlatanism*（2014, Notices of the AMS）Eq.(3.2)。
  2. **解析等式性質**（可證偽）：
     - `E[max SR]/√V[SR]` 於 N=10／100／1000 ＝1.5746／2.5306／3.2551（`atol=1e-4`）。
     - `N=1` ⇒ `SR0=0` 且 DSR 退化為同輸入之 PSR 解析值（`atol=1e-10`）。
     - `cscv_path_count(S)` ＝ `C(S, S/2)`（S=12→924；S=14→3432；S=16→12870），以 `math.comb` 對照。
     - 預算不變式：`min_btl_years_upper_bound(max_trials_budget(T,SR),SR) <= T` 且
       `min_btl_years_upper_bound(max_trials_budget(T,SR)+1,SR) > T`（floor 定義下之唯一正確不變式；
       **不使用** `rtol` 比較 ← R1 GROK-R1-P1-01 更正前版之錯誤）。
     - **Mertens 估計量變異數**（DSR 分母來源，**非**跨 trial 變異數）：
       `Var(SR_hat) = (1 - γ3·SR + (γ4-1)/4·SR²) / (T-1)`（γ3=skew、γ4=kurtosis 非超額，
       SR 與 moments 皆 per-period），與手算案例對照 `atol=1e-12`。
     - **兩個變異數為不同物件（R2 GROK-R2-P1-01 之修法經主委複驗後駁回，缺陷本身接受）**：
       `Var(SR_hat)`（上式，用於檢定統計量分母）≠ `V[{SR_n}]`（跨 trial 變異數，僅用於 SR0）。
       判準＝**N=1 時 DSR 必須恰等於 PSR**：主委實跑（T=50,SR=0.8,γ3=0.5,γ4=4,V_cross=0.2）
       原式 N=1 → 1.000000 ＝ PSR ✓；改用「同一 V 當分母」→ 0.963181 ≠ PSR ✗
       ⇒ 若採 grok 之修法會弄壞本節既有 oracle，故保留論文形式並改以命名區隔消除混淆。
  3. **統計性質對照（PBO 行為 oracle，參數全部寫死於 golden 檔）**：
     `seed=20260817`、候選數 `N=50`、觀測數 `T=1200`、`S=12`、noise 為 i.i.d. 常態（σ=0.01）；
     全噪音 ⇒ PBO ∈ [0.40, 0.60]；alpha 案例＝於候選 0 之每期報酬加常數
     **`mu = 0.01 * 1.0 / sqrt(8760) = 1.0683760683760685e-04`**（σ=0.01、年化 SR 目標 1.0、1h 頻率；
     本數值於 SPEC 明列，golden 檔僅複製，**不得**只寫「寫死於 golden 檔」← R2 CODEX-R1-P1-05 殘留）
     ⇒ PBO < 0.30。
- **通過條件（可證偽，容差分尺度）**：文獻/解析類依上列各自 `atol`；`rtol` 僅用於
  `E[max SR]` 之大 N 漸近對照（`rtol=1e-3`，明示為近似）；統計類為固定 seed 之區間斷言；
  超出即列出案例 id + 實際 diff = FAIL。

## §P Phase 與依賴

### Phase B1 — 輸入語意契約（依賴：無外部 Phase；**批內順序＝1.1 → 1.2 → 1.3 → 1.4**，Task 1.4 依賴 1.3 產出之欄位）

**Task 1.1 — 年化頻率解析（單一來源）**
- 目標：把「年化係數必須由資料 timeframe 推導」落成可被機器驗的函式。
- 檔案：新增 `momentum/Analysis/strategy_validation/frequency.py::resolve_periods_per_year(timeframe: str) -> int`
- 既有 caller/影響面：新建無 caller；讀 `momentum/core/constants.py::TIMEFRAME_SECONDS`（唯一來源，不複製表）。
- 改法：`periods_per_year = round(365*24*3600 / TIMEFRAME_SECONDS[timeframe])`；未知 timeframe ⇒
  `raise UnknownTimeframeError`（fail-closed，**禁**回預設值）。不新增 timeframe 常數。
- **驗證**：`resolve_periods_per_year("1h") == 8760`、`("4h") == 2190`、`("12h") == 730`、`("1d") == 365`；
  `("7m")`／`("")`／`(None)`／`("1H")` 皆 raise。測試 `pytest tests/momentum/Analysis/strategy_validation/test_frequency.py -q` rc=0
- **邊界**：① 未知 timeframe → raise（非回 730）② 空字串/None → raise ③ 大小寫變體 `"1H"` → raise（不做寬鬆解析）。
- **存活至**：全票完工後保留（Task 1.4／B3／B4 皆依賴）。
- **覆蓋風險**：無。
- 不可做：不得在本檔新增 timeframe→秒 的第二份對照表；不得提供 `default=730` 參數。

**Task 1.2 — typed Sharpe（退化情形回 NaN＋status，非 0.0）**
- 目標：三關自算觀測 Sharpe，杜絕吃既有 `PerformanceMetrics` 的 `0.0` 混淆語意。
- 檔案：新增 `momentum/Analysis/strategy_validation/sharpe.py::compute_sharpe(returns, *, periods_per_year, risk_free_rate=0.0) -> SharpeResult`
- 既有 caller/影響面：新建無 caller。status 值直接 ref `ic_report_contract.json#capability_status`
  （**不依賴** Task 2.1 之檔案存在 ← R1 GROK-R1-P2-01）。
- 改法：`periods_per_year` 為**必填關鍵字參數**（無預設）；樣本標準差 `ddof=1`；
  回傳 dataclass 含 `value_annualized`／`value_per_period`／`status`／`reason`／`n_obs`／`periods_per_year`／
  `skew`／`kurtosis`／`sr_estimator_variance`（**Mertens 估計量變異數**，per-period 單位，
  依 §G 公式計算，供 DSR 檢定統計量之分母使用）；
  🔴 **單位鎖定（R2 GROK-R2-P1-02）**：`skew`／`kurtosis`／`sr_estimator_variance` 一律以
  **per-period 報酬**計算；`value_annualized` 僅供報告展示，**禁**代入 DSR 檢定統計量；
  空序列、`n_obs<2`、`std==0`、含 NaN/inf ⇒ `value=nan` 且 status 非 `ok`。
- **驗證**：常數序列 ⇒ `math.isnan(value)` 且 `status != "ok"`（**非** 0.0）；已知手算案例 `atol=1e-12`；
  `skew`/`kurtosis` 與 `scipy.stats.skew/kurtosis(fisher=False)` 一致（`atol=1e-10`）；
  `sr_estimator_variance` 與 §G 公式手算對照 `atol=1e-12`；
  `value_annualized == value_per_period * sqrt(periods_per_year)`（rf=0 時，`atol=1e-12`）。
  測試 `pytest tests/momentum/Analysis/strategy_validation/test_sharpe.py -q` rc=0
- **邊界**：① 空 Series ② 全 NaN ③ 單一觀測 ④ std=0 ⑤ 含 inf ⑥ 全零序列（合法但 std=0）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得提供「回 0.0」的相容模式；不得在本函式內做年化推導（呼叫方傳入，Task 1.1 負責）。

**Task 1.4 — canonical 報酬序列與 T 語意契約（依賴：Task 1.3 之 `BacktestResult.annualization`；R1 COMPOSER-R1-P0-01／GROK-R1-P1-02）**
- 目標：定義三關唯一合法輸入序列之提取規則與 T 計數語意，關閉收斂檔 C2 第 4 點。
- 檔案：新增 `momentum/Analysis/strategy_validation/returns_contract.py::extract_period_returns(backtest_result, *, timeframe) -> PeriodReturns`
- 既有 caller/影響面：新建無 caller；讀 `BacktestResult`（`equity_curve`／`trades`／新增之 `annualization`）。
- 改法：回傳 dataclass 含 `values`（1D float ndarray）／`t_semantics`／`n_obs`／`periods_per_year`／
  `annualization_source`／`status`／`reason`。`t_semantics` 合法值集合住 Task 2.1（本 SPEC 不複列），
  語意定義如下（唯一定義處）：
  `bar_count`＝逐 bar 報酬含結構性 0（trade-settled 零填充）；
  `nonzero_return_bars`＝僅取非零 bar；
  `trade_level`＝逐交易 `pnl_pct` 序列，年化基準改為「每年交易數」。
  **DSR 僅允許 `trade_level` 與 `nonzero_return_bars`**；`bar_count` 一律 status 非 `ok`、
  `reason=t_semantics_inflates_significance`（理由＝結構性 0 膨脹 `√(T-1)`）。
  `annualization_source != "resolved"` ⇒ status 非 `ok`（拒絕隱性 730）；
  `BacktestResult` **無** `annualization` 欄位（Task 1.3 未落地或舊物件）⇒ status 非 `ok`、
  `reason=annualization_unresolved`（fail-closed，**禁**假設 730 ← R2 CODEX-R2-P1-03）。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_returns_contract.py -q` rc=0，斷言
  ① 同一 `BacktestResult` 下 `bar_count` 之 `n_obs` 嚴格大於 `trade_level` 之 `n_obs`（結構性 0 之存在證明）
  ② `t_semantics="bar_count"` 送入 DSR ⇒ `status != "ok"` 且 `reason == "t_semantics_inflates_significance"`
  ③ `annualization_source="default_730"` ⇒ `status != "ok"`
  ④ `trade_level` 之 `periods_per_year` ＝ 交易數/年（固定 fixture 對照，`atol=1e-9`）。
- **邊界**：① 無交易（trades 空）② 單一交易 ③ equity_curve 全 1.0 ④ `annualization` 欄位缺失 ⑤ timeframe 未知（Task 1.1 raise）。
- **存活至**：全票完工後保留（B3 之唯一輸入口）。
- **覆蓋風險**：無。
- 不可做：不得接受 `prediction_analyzer` 之 cumsum 輸出；不得自行推導 timeframe（由呼叫方傳入）。

**Task 1.3 — 既有回測路徑帶入年化來源（白名單三處）**
- 目標：消除 `periods_per_year=730` 於策略路徑之隱性寫死，並讓來源可機器判讀。
- 檔案：`momentum/Strategy/vectorized_backtest.py`（`run_backtest` 簽名＋`BacktestResult`）、
  `momentum/Optimization/objectives/strategy_backtest.py`（`__init__` 與 `:113`）。
- 既有 caller/影響面：`tests/momentum/Strategy/test_vectorized_backtest.py`、
  `tests/momentum/Strategy/test_performance_metrics.py`、`tests/momentum/Optimization/test_strategy_backtest_enhanced.py`
  （動工前先 diff 其斷言，禁放寬換綠）。
- 改法：`run_backtest(..., timeframe: str | None = None)`；`timeframe` 給定 ⇒ 經 Task 1.1 解析並傳入
  `PerformanceMetrics(..., periods_per_year=<resolved>)`，`BacktestResult.annualization =
  {"source": "resolved", "periods_per_year": <int>, "timeframe": <str>}`；
  `timeframe` 為 None 或 Task 1.1 raise ⇒ 保持現行預設值且
  `annualization = {"source": "default_730", "periods_per_year": 730, "timeframe": None}`。
  **不改** `PerformanceMetrics` 之簽名語意與 `metrics: Dict[str, float]` 型別（source 走平行 metadata）。
- **驗證**：`pytest tests/momentum/Strategy/test_vectorized_backtest.py tests/momentum/Optimization/test_strategy_backtest_enhanced.py -q` rc=0；
  新增斷言 ① `timeframe="1h"` ⇒ `annualization["periods_per_year"] == 8760` 且 `annualization["source"] == "resolved"`
  ② `timeframe=None` ⇒ `annualization["source"] == "default_730"`
  ③ **在 `risk_free_rate=0.0` 之 fixture 下**，同一報酬序列在 `timeframe="1h"` 與 `timeframe=None` 下之
  `metrics["sharpe_ratio"]` 比值 ＝ `sqrt(8760/730)`（`atol=1e-9`）——「數值真的分叉」之證明（R1 GROK-R1-P1-04）。
  🔴 **rf 必須為 0**（R2 CODEX-R2-P0-01／GROK-R2-P0-01）：`sharpe = (mean - rf/periods)/std*sqrt(periods)`
  之 `rf/periods` 項隨 periods 變化，rf=0.02 時該比值**代數上不等於** `sqrt(8760/730)`
  （主委複驗：rf=0.02 ⇒ ratio 4.5309 vs 3.4641；rf=0 ⇒ 差 <1e-15）。
  ③b 另以 `risk_free_rate=0.02`（現行預設）斷言 `annualization["periods_per_year"]` 分叉（8760 vs 730）
  且兩者 `sharpe_ratio` **不相等**（不鎖比值）——覆蓋生產預設路徑
  ④ 既有斷言未放寬（diff 附於 commit）。
- **邊界**：① `timeframe=None` ② `timeframe` 未支援值（捕捉 raise 並落 `default_730`）③ 既有 12h 測試（730 與 resolved 同值 ⇒ 須另用 1h 案例才可區分，已由斷言③覆蓋）。
- **存活至**：全票完工後保留；若未來回測引擎重寫，本 Task 之契約條文存活、實作可棄。
- **覆蓋風險**：實作可能被未來引擎重寫覆蓋——已知且接受（價值主體在契約與 B3/B4 純函式）。
- 不可做：不得把 `annualization_source` 塞進 `metrics` 字典（型別汙染）；不得改 `PerformanceMetrics` 之 `0.0` 退化語意。

### Phase B2 — N 帳本契約與 fail-closed 讀取（依賴：B1 Task 1.1／1.2 之函式，不依賴其他 Phase）

**Task 2.1 — 策略驗證契約 JSON＋唯一 resolver**
- 目標：把 N 帳本記錄結構、三關報告區段、各枚舉收斂為單一機器可讀檔，且 ref 可解析、可漂移偵測。
- 檔案：新增 `momentum/Analysis/contracts/strategy_validation_contract.json`
  ＋`momentum/Analysis/strategy_validation/contract.py::load_strategy_validation_contract()`
  （唯一 resolver）與 `validate_against_contract(obj, section)`。
- 既有 caller/影響面：新建；**不改** `ic_report_contract.json`（scope 錯位，見收斂檔 C4）。
- 改法：JSON 須含且僅含下列 13 個頂層鍵（**本 SPEC 中此欄位集合只出現於本 Task**）：
  `version`、`capability_status_ref`、`ledger_record_keys`、`n_fields`、`report_sections`、
  `eligibility_keys`、`annualization_source_values`、`t_semantics_values`、`n_semantics_values`、
  `selection_metric_values`、`universe_source_values`、`variance_source_values`、`reasons`。
  各集合內容：
  `ledger_record_keys` ＝ `research_session_id`／`dataset_key`／`candidate_id`／`evaluation_id`／
  `attempt_index`／`state`／`metric_name`／`metric_value`／`metric_valid`／`input_artifact_hash`／`ts`；
  `n_fields` ＝ `n_candidates_considered`／`n_evaluated`／`n_valid_metrics`／`n_failed_or_pruned`／`n_is_lower_bound`
  （**禁**任何鍵名為 `n` 或 `N`）；
  `annualization_source_values` ＝ `resolved`／`default_730`；
  `t_semantics_values` ＝ `bar_count`／`nonzero_return_bars`／`trade_level`；
  `n_semantics_values` ＝ `exhaustive_grid`／`adaptive_search`／`unknown`（`adaptive_search` 對應 TPE，見 §N 殘留）；
  `selection_metric_values` ＝ `sharpe`／`mean_return`；
  `universe_source_values` ＝ `full_grid`／`ledger_all_candidates`／`external_declared`；
  `variance_source_values` ＝ `explicit`／`ledger_cross_trial`（**`analytic` 已移除**：解析式屬
  `Var(SR_hat)` 而非跨 trial 變異數，見 §G 之兩變異數區隔；R2 GROK-R2-P1-01）；
  `report_sections`（R2 CODEX-R2-P1-02：前版三集合無內容）＝ `eligibility`／`min_btl`／`dsr`／`pbo`／`provenance`，
  每節必備鍵 `status`／`reason`（與 IC 契約同型），`provenance` 節必備
  `n_semantics`／`t_semantics`／`annualization_source`／`n_independence`；
  `eligibility_keys` ＝ `eligible`／`required_years_upper_bound`／`available_years`／`trials_budget`／
  `trials_used`／`target_sharpe`／`n_source`／`display_downgrade`／`warning_text_key`；
  `reasons` ＝ `n_unknown`／`t_semantics_inflates_significance`／`annualization_unresolved`／
  `universe_selection_contaminated`／`insufficient_candidates`／`cross_trial_variance_unavailable`
  （**唯一** reason 字串來源；程式與測試不得自創字面值）。
  **resolver 語意**：`capability_status_ref` 格式為 `<repo 相對路徑>#<頂層鍵名>`；
  `load_strategy_validation_contract()` 須實際 dereference（載入目標檔、取該鍵、驗證為非空字串 list），
  目標檔缺失／鍵缺失／型別不符 ⇒ raise（fail-closed，**禁**回退預設枚舉；R1 COMPOSER-R1-P2-02 要求之執行期 dereference）。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_contract.py -q` rc=0，斷言
  ① `load_strategy_validation_contract()["capability_status"]` 與
  `ic_config_schema.load_report_contract()["capability_status"]` **逐值相等**（ref 真的被解析）
  ② 六值枚舉**不**在策略契約檔字面出現（`grep -c` == 0，防兩處列舉）
  ③ 把 ref 改指向不存在之鍵（tmp fixture）⇒ raise（drift 偵測，R1 CODEX-R1-P1-08）
  ④ 無鍵名為 `n` 或 `N`；⑤ 13 個頂層鍵齊備。
- **邊界**：① JSON 語法錯 ⇒ raise ② ref 目標檔缺失 ⇒ raise ③ ref 鍵缺失 ⇒ raise ④ 未知頂層鍵 ⇒ `validate_against_contract` rc!=0 ⑤ 枚舉值重複 ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無（新檔，無既有消費者）。
- 不可做：不得在此檔複列 capability_status 六值；不得放入實作邏輯或預設 N 值。

**Task 2.2 — N 帳本讀取 API（今日無生產者 ⇒ 誠實 unavailable）**
- 目標：三關取 N 與 trial Sharpe 之唯一入口，且缺帳本時 fail-closed。
- 檔案：新增 `momentum/Analysis/strategy_validation/ledger.py::read_trial_ledger(*, research_session_id, dataset_key) -> LedgerReadResult`
- 既有 caller/影響面：新建無 caller；ledger 落地路徑由 `momentum/core/config.py` 既有輸出根目錄推導（不新增設定鍵）。
- 改法：讀 append-only JSONL；逐列以 Task 2.1 之 `ledger_record_keys` 驗證，非法列 ⇒ 計入
  `n_failed_or_pruned` 並記 reason，**不得靜默丟棄**。回傳含 Task 2.1 之五個 `n_fields`
  （`n_is_lower_bound` 恆 `True`）＋`n_semantics`＋**`valid_sharpe_values`（float list，
  僅 `metric_name="sharpe"` 且 `metric_valid=True` 之列，供 DSR 之 `ledger_cross_trial` 變異來源
  ← R1 CODEX-R1-P0-03）**＋status/reason。帳本不存在／`dataset_key` 無列 ⇒ status 非 `ok`、
  `reason=n_unknown`；**禁**回 `n=1`、**禁**以 request `n_trials` 或完成數替代。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_ledger.py -q` rc=0，斷言
  ① 無檔案 ⇒ `status != "ok"` 且 `reason == "n_unknown"`
  ② 3 合法列＋1 非法列 ⇒ `n_evaluated == 3` 且 `n_failed_or_pruned == 1` 且 reason 非空
  ③ `n_is_lower_bound is True`（參數化 3 種輸入以上）
  ④ 含 2 筆 valid sharpe ⇒ `len(valid_sharpe_values) == 2`
  ⑤ 同 `candidate_id` 兩 `attempt_index` ⇒ `n_candidates_considered == 1` 且 `n_evaluated == 2`。
- **邊界**：① 檔不存在 ② 空檔 ③ 非法 JSON 行 ④ 缺必填鍵 ⑤ 同 candidate 多 attempt ⑥ 檔案不可讀（權限）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：**不得**接線至 Optuna／`_record_trial_metrics`／`optimization_task_service`（§N 待接線項）；
  不得提供「使用者手填 N 當正式值」之路徑（敏感度分析見 Task 3.3 watermark）。

**Task 2.3 — 生產者一致性測試（未來引擎的入口義務）**
- 目標：把「未來搜尋引擎必須寫 ledger」變成可執行合約，而非文件承諾。
- 檔案：`momentum/Analysis/strategy_validation/ledger.py::append_trial_attempt(...)`
  ＋`tests/momentum/Analysis/strategy_validation/test_ledger_conformance.py`
- 既有 caller/影響面：新建無 caller。
- 改法：`append_trial_attempt` 為唯一合法寫入口（先以 Task 2.1 schema 檢核、通過才 append；失敗 raise）；
  conformance 測試以假想生產者呼叫後，`read_trial_ledger` 計數須自洽
  （`n_evaluated == n_valid_metrics + n_failed_or_pruned`）。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_ledger_conformance.py -q` rc=0；
  缺鍵記錄 ⇒ raise 且檔案未新增半列（行數前後相等）；並發追加 2×50 列 ⇒ 讀回 `n_evaluated == 100`；
  重複 `evaluation_id` ⇒ raise。
- **邊界**：① 缺必填鍵 ② 型別錯 ③ 並發追加 ④ 磁碟不可寫 ⑤ 重複 `evaluation_id`。
- **存活至**：全票完工後保留（未來引擎開發時作為驗收）。
- **覆蓋風險**：無。
- 不可做：不得為通過測試而放寬 schema；不得在本票接上任何真實生產者。

### Phase B3 — MinBTL＋DSR 純統計核心（依賴：B1 全部、B2 Task 2.1／2.2）

**Task 3.1 — MinBTL 上界與試驗預算**
- 目標：資格閘＋可行動的「試驗預算」（使用者裁決之產品形態）。
- 檔案：新增 `momentum/Analysis/strategy_validation/min_btl.py`：
  `min_btl_years_upper_bound(*, n_trials, target_sharpe) -> float`、
  `max_trials_budget(*, t_years, target_sharpe) -> int`、
  `assess_eligibility(*, t_years, n_trials, target_sharpe) -> EligibilityResult`
- 既有 caller/影響面：新建無 caller。
- 改法：`min_btl_years_upper_bound = 2*ln(n_trials)/target_sharpe**2`，`n_trials == 1 ⇒ 0.0`（§A 特例契約）；
  `max_trials_budget = floor(exp(t_years*target_sharpe**2/2))`（**floor，非四捨五入**）；
  `assess_eligibility` 回傳 `eligible`（三態 `True`／`False`／`None`）／`required_years_upper_bound`／
  `available_years`／`trials_budget`／`trials_used`／`target_sharpe`／`status`／`reason`；
  `n_trials` 只能來自 Task 2.2，status 非 `ok` ⇒ `eligible=None`（**禁**以 `False` 冒充已判定）。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_min_btl.py -q` rc=0，斷言
  ① `min_btl_years_upper_bound(n_trials=100, target_sharpe=1.0)` ＝ 9.210340371976184（`atol=1e-12`）
  ② `max_trials_budget(t_years=2.3232876712328765, target_sharpe=1.5) == 13`（**非 14**）；
  同 T 下 SR=1.0→3、SR=2.0→104、SR=2.5→1422
  ③ 預算不變式（§G）：對 20 組 (T,SR) 參數化，`budget` 之上界 `<= T` 且 `budget+1` 之上界 `> T`
  ④ `n_trials=1` ⇒ `0.0`；`n_trials<1`／`target_sharpe<=0`／`t_years<=0` ⇒ raise
  ⑤ **C5 產品 oracle（R1 COMPOSER-R1-P1-03）**：`assess_eligibility(t_years=2.3232876712328765,
  n_trials=100, target_sharpe=1.0).eligible is False` 且 `trials_used > trials_budget`
  ⑥ N 不可知（Task 2.2 status 非 ok）⇒ `eligible is None`
  ⑦ `n_trials=10**6` 不 overflow（回有限 float）。
- **邊界**：① `n_trials=1` ② `n_trials<1` raise ③ `target_sharpe<=0` raise ④ `t_years<=0` raise
  ⑤ N 不可知 ⑥ 極大 N ⑦ `max_trials_budget` 結果為 0（極短 T）⇒ 回 0 且 `eligible=False`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：**不得**提供調整公式常數（`2`、`ln`）之參數或旗標；不得以提高取樣頻率折抵年數
  （`t_years` 語意固定為年，見 §V 反向測試）；不得把上界輸出成「精確最短長度」。

**Task 3.2 — Deflated Sharpe Ratio（全式寫死，V[SR] 三態）**
- 目標：冠軍檢定，輸入語意鎖死且退化 fail-closed。
- 檔案：新增 `momentum/Analysis/strategy_validation/deflated_sharpe.py::deflated_sharpe(*, period_returns, n_trials, variance_source, cross_trial_sr_variance=None, cross_trial_sr_values=None, n_semantics) -> DSRResult`
  （`cross_trial_sr_values` 直接吃 Task 2.2 之 `valid_sharpe_values`，關閉 R1 CODEX-R1-P0-03 之 dataflow 殘留）
- 既有 caller/影響面：新建無 caller；`period_returns` 型別＝Task 1.4 之 `PeriodReturns`
  （其 `t_semantics`／`annualization_source` 合法性由該 Task 判定，本函式拒收 status 非 ok）。
- 改法（全式，唯一定義處）：
  `SR0 = √V[SR] · ((1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e)))`，γ=0.5772156649015329；`N==1 ⇒ SR0=0`；
  `DSR = Φ( (SR_obs - SR0)·√(T-1) / √(1 - γ3·SR_obs + (γ4-1)/4·SR_obs²) )`，
  其中 `SR_obs`／`γ3`／`γ4`／`T` 皆取自 Task 1.2 之 `SharpeResult`（同一 periods 基準）。
  🔴 **兩個變異數各有其位（R2 GROK-R2-P1-01／P1-02）**：
  分母之 `Var(SR_hat)` **恆**取自 Task 1.2 之 `sr_estimator_variance`（per-period，無來源選項）——
  這是 `N=1 ⇒ DSR == PSR` 成立之充要條件；
  `variance_source` **只**決定 SR0 所需之跨 trial `V[{SR_n}]`，二態（值集合住 Task 2.1）：
  `explicit`（呼叫方傳 `cross_trial_sr_variance`）／`ledger_cross_trial`（`cross_trial_sr_values`
  樣本變異數，長度 `>=2`）。`n_trials == 1` ⇒ SR0=0，**不需**跨 trial 變異數；
  `n_trials > 1` 且兩者皆缺 ⇒ status 非 `ok`、`reason=cross_trial_variance_unavailable`
  （誠實不可算，**禁**無依據常數）。
  所有進入檢定統計量之 `SR_obs`／`γ3`／`γ4`／`T` 一律 **per-period**；年化值僅回顯。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_deflated_sharpe.py -q` rc=0，斷言
  ① `n_trials=1`、`variance_source="analytic"`、skew=0、kurt=3 ⇒ 等於 PSR 解析值（`atol=1e-10`）
  ② `E[max SR]/√V[SR]` 三點對照（N=10/100/1000 → 1.5746/2.5306/3.2551，`atol=1e-4`）
  ③ N 遞增 ⇒ DSR 單調不增（參數化 10 點）
  ④ `period_returns.status != "ok"`（含 `bar_count`、`default_730` 兩情形）⇒ DSR `status != "ok"` 且 `math.isnan(value)`
  ⑤ `variance_source="ledger_cross_trial"` 且 `len(cross_trial_sr_values) < 2` ⇒ `status != "ok"`
  且 `reason == "cross_trial_variance_unavailable"`
  ⑥ 兩個 `variance_source` 皆有案例覆蓋；`n_trials>1` 且兩者皆缺 ⇒ 同⑤之 reason
  ⑦ **單位不變性（R2 GROK-R2-P1-02）**：同一底層報酬序列以 `periods_per_year ∈ {1, 730, 8760}`
  三值計算，DSR **值不變**（`atol=1e-12`）——若實作把年化 SR 代入矩公式則轉紅
  ⑧ `n_semantics="adaptive_search"` ⇒ 輸出 `n_independence == "unverified"`（不做任何 effective-N 換算，
  R2 CODEX-R1-P0-01 殘留之誠實處理）。
- **邊界**：① N 不可知 ② 序列含 NaN ③ std=0 ④ `n_trials=1` ⑤ 極端 kurtosis（>50）⑥ `n_semantics` 缺失 ⇒ raise ⑦ `variance_source` 未知值 ⇒ raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得吃 `PerformanceMetrics.calculate_all()` 之 `sharpe_ratio`；
  不得以 request `n_trials`（`api/routes/optimization.py:48`）替代 ledger 值；不得接受 `t_semantics="bar_count"`。

**Task 3.3 — 報告區段與降級展示契約（使用者裁決：不硬擋）**
- 目標：三關結果之機器可讀輸出與「明顯警語」之可驗收定義。
- 檔案：新增 `momentum/Analysis/strategy_validation/report.py::build_validation_section(...)`；
  區段鍵與 `eligibility_keys` 住 Task 2.1。
- 既有 caller/影響面：新建無 caller；**不改** `optimization_output_service`／`ml_pipeline`（§N 待接線項）。
- 改法：輸出含 `eligibility`（`eligible` 三態＋reason＋`trials_budget`／`trials_used`／`target_sharpe`）、
  `min_btl`／`dsr`／`pbo` 三節各帶 status/reason，以及 `n_semantics`／`t_semantics`／`annualization_source` 回顯。
  **三關中任一 status 非 `ok`，或 `eligible is not True`** ⇒ 必須輸出 `display_downgrade=true`
  與非空 `warning_text_key`，且結構中**不得**存在任何推薦類鍵（allowlist 機械比對）。文案本體不在 momentum 層。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_report_section.py -q` rc=0，
  以 **eligibility 三態 × 三關 status（ok／非 ok）笛卡兒組合**（3×2³＝24 案例，R1 CODEX-R1-P1-07）斷言
  ① 只有「`eligible is True` 且三關皆 `ok`」時 `display_downgrade is False`
  ② 其餘 23 案例 `display_downgrade is True` 且 `len(warning_text_key) > 0`
  ③ 23 案例中推薦類鍵一律不存在（對 allowlist 差集為空集合）
  ④ 全 24 案例通過 `validate_against_contract`。
- **邊界**：① 三關皆 unavailable ② 僅 MinBTL 可算 ③ 使用者提供假設 N ⇒ 須帶
  `n_source="assumed_not_ledgered"` watermark 且 `eligible` 強制 `None`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得實作 API 層硬擋（使用者裁決）；不得把文案字串寫進 momentum 層；
  **不得複用或暗示既有 `overfitting_score`／`OverfittingCheckChart` 為本三關**（R1 GROK-R1-P2-02／COMPOSER-R1-P2-01）。

### Phase B4 — PBO（CSCV）純統計核心（依賴：B1 Task 1.1／1.2／1.4、B2 Task 2.1；**不依賴 B3**）

**Task 4.1 — CSCV 分割器（lazy＋資源守衛）**
- 目標：Bailey CSCV 之 S 塊組合切分（與 CPCV 語意分離），且不得成為 OOM 來源。
- 檔案：新增 `momentum/Analysis/strategy_validation/cscv.py`：
  `cscv_path_count(s_blocks) -> int`、`iter_cscv_splits(*, n_obs, s_blocks)` 回傳 iterator
- 既有 caller/影響面：新建無 caller；**不 import** `momentum/Analysis/model_validation/combinatorial_purged_cv.py`
  （語意不同，見收斂檔 C3）。
- 改法：等分 `n_obs` 為 S 塊，**餘數規則＝前 `n_obs % S` 塊各多 1 個觀測**（寫死，唯一定義處）；
  S 必為偶數否則 raise；回傳 **lazy iterator**（不實體化全部 paths，R1 CODEX-R1-P1-06）；
  **雙重預算守衛（fail-closed，禁隨機抽樣冒充完整 CSCV）**：`cscv_path_count(s_blocks) > 20000`
  **或** `cscv_path_count(s_blocks) * n_obs > 20_000_000`（索引元素上限，隨 `n_obs` 變動
  ← R2 CODEX-R1-P1-06 殘留）⇒ `raise CscvBudgetExceeded`。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_cscv.py -q` rc=0，斷言
  ① `cscv_path_count(12) == 924`、`(14) == 3432`、`(16) == 12870`，且與 `math.comb(S, S//2)` 相等
  ② 每組 IS 與 OOS 聯集覆蓋全索引、交集為空（對 S=12 全 924 組驗證）
  ③ `n_obs=1205, s_blocks=12` ⇒ 前 5 塊長度 101、其餘 100（餘數規則）
  ④ S=13（奇數）raise；`s_blocks > n_obs` raise
  ⑤ `cscv_path_count(20) == 184756` 且 `iter_cscv_splits(n_obs=1200, s_blocks=20)` raise `CscvBudgetExceeded`；
  另 `s_blocks=16`（12870 paths，未超 path cap）搭 `n_obs=2000`（元素 25,740,000 > 2e7）亦 raise（元素預算生效）
  （**不實體化**，避免 1.77 GiB index payload）
  ⑥ iterator 為 lazy：`inspect.isgenerator` 為真，且取 `next()` 之計數探針 == 1。
- **邊界**：① S 奇數 ② `s_blocks > n_obs` ③ 餘數不整除 ④ S=2 ⑤ S=20（超預算 raise）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得對組合做隨機子取樣（`max_paths` 式）而仍稱 PBO；不得回傳 list。

**Task 4.2 — PBO 值（矩陣語意與 oracle 全寫死）**
- 目標：由候選×時間報酬矩陣算 PBO。
- 檔案：新增 `momentum/Analysis/strategy_validation/pbo.py::probability_of_backtest_overfitting(*, returns_matrix, s_blocks, selection_metric, universe_provenance) -> PBOResult`
- 既有 caller/影響面：新建無 caller。
- 改法（唯一定義處，R1 CODEX-R1-P1-05）：`returns_matrix` shape 固定 **(T, N)**＝列為時間、欄為候選，
  同一時間索引須跨候選同步（長度不一致 ⇒ raise）；`selection_metric` 值集合住 Task 2.1；
  含 NaN 之候選標 invalid 並**自分母剔除**（記 `n_candidates_invalid`，不得靜默丟棄）；
  有效候選數 <2 ⇒ status 非 `ok`；相對排名採 `r = rank/(N_valid+1)`，**平手用平均排名**；
  `ω = ln(r/(1-r))`；`PBO = P(ω<0)` ＝ OOS 排名落於中位以下之 path 比例；回傳 PBO 值＋logit 摘要＋status。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_pbo.py -q` rc=0，斷言
  ① §G 全噪音 fixture（`seed=20260817`、N=50、T=1200、S=12）⇒ `0.40 <= pbo <= 0.60`
  ② §G 單一 alpha fixture ⇒ `pbo < 0.30`
  ③ **轉置矩陣**（(N, T)）輸入 ⇒ raise（防錯軸仍跑綠）
  ④ 全平手矩陣 ⇒ `r == 0.5` 且 `omega == 0.0`（平均排名規則）
  ⑤ 5 候選含 1 NaN 候選 ⇒ `n_candidates_invalid == 1` 且分母為 4
  ⑥ 有效候選數 1 ⇒ `status != "ok"` 且 `math.isnan(pbo)`（**禁**回 0）。
- **邊界**：① 候選數<2 ② NaN 候選 ③ 全候選相同 ④ T 不足以切 S 塊 ⑤ 平手 ⑥ 轉置輸入。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得在此層自行重跑回測取得矩陣（矩陣由呼叫方提供；重算式接線屬 §N 待接線項）。

**Task 4.3 — 候選宇宙污染防護（禁 top-K）**
- 目標：把「禁用全樣本 top-K 子集」做成機械拒絕。
- 檔案：`momentum/Analysis/strategy_validation/pbo.py` 之 `universe_provenance` 驗證。
- 既有 caller/影響面：Task 4.2。
- 改法：`universe_provenance` 為必填 dataclass，含 `selection_free`（bool）與 `source`
  （值集合＝Task 2.1 之 `universe_source_values`）；`selection_free is not True` ⇒ 直接回
  status 非 `ok`、`reason=universe_selection_contaminated`，**不計算 PBO**。
- **驗證**：`pytest tests/momentum/Analysis/strategy_validation/test_pbo_universe_guard.py -q` rc=0，斷言
  ① `selection_free=False` ⇒ `status != "ok"` 且 `math.isnan(value)` 且 `reason == "universe_selection_contaminated"`
  ② `selection_free=True` 但 `source` 不在枚舉 ⇒ raise（`pytest.raises`）
  ③ `universe_provenance=None` ⇒ raise。
- **邊界**：① `selection_free=False` ② `universe_provenance=None` ③ `source` 未知值。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。
- 不可做：不得提供 `force=True` 之繞過參數。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 含 a,d ⇒ 必附 mutation 設計。13 條清單（每條實跑貼 rc；改壞後**必須**有測試轉紅）：
  1. 刪除 DSR 之 γ 項 ⇒ Task 3.2 斷言② 轉紅。
  2. `min_btl_years_upper_bound` 之 `ln(n_trials)` 改為 `n_trials` ⇒ Task 3.1 斷言①③ 轉紅。
  3. `max_trials_budget` 之 `floor` 改為 `round` ⇒ Task 3.1 斷言②③ 轉紅（R1 實錯之回歸鎖）。
  4. CSCV 之 IS/OOS 對調 ⇒ Task 4.2 斷言①② 至少一條轉紅。
  5. `compute_sharpe` 退化情形回 0.0 ⇒ Task 1.2 status 斷言轉紅。
  6. 移除 `universe_provenance` 檢查 ⇒ Task 4.3 斷言① 轉紅。
  7. `read_trial_ledger` 缺檔時回 `n=1` ⇒ Task 2.2 斷言① 轉紅。
  8. `resolve_periods_per_year` 未知 timeframe 回 730 ⇒ Task 1.1 raise 斷言轉紅。
  9. DSR／`assess_eligibility` 接受 `annualization_source="default_730"` 或 `t_semantics="bar_count"`
     ⇒ Task 1.4 斷言②③ 與 Task 3.2 斷言④ 轉紅（R1 COMPOSER-R1-P1-04）。
  10. 解析 V[SR] 係數改錯（如 `(γ4-1)/4` 改 `γ4/4`）⇒ Task 1.2 `variance_analytic` 對照與
      Task 3.2 斷言①（N=1 退化為 PSR）轉紅（R1 GROK-R1-P1-03）。
  11. DSR 分母改用跨 trial `V[{SR_n}]`（grok R2 建議之錯誤形式）⇒ Task 3.2 斷言①（N=1 退化為 PSR）轉紅。
  12. `compute_sharpe` 之 `skew`／`kurtosis` 改以年化 SR 計算 ⇒ Task 3.2 斷言⑦（單位不變性）轉紅。
  13. Task 1.3 斷言③ 之 fixture 若用 `risk_free_rate=0.02` ⇒ 該比值斷言轉紅（rf 必須為 0 之回歸鎖）。
- **反向測試（防「用頻率折抵年數」取巧）**：同一期間之 1h／4h／12h 序列，`assess_eligibility` 之
  `available_years` 三者差異 `atol=1e-6`；若實作把 bar 數當年數則轉紅。
- 測試層級：單元（各純函式）／整合（`build_validation_section` 串三關 24 案例）／Golden 對照
  （`tests/momentum/Analysis/golden/gap1_reference_cases.json`，含 `sha256` 防改）／邊界（下列目錄）。
  全部可獨立 `pytest tests/momentum/Analysis/strategy_validation/ -q` 跑，不需 `run_api.py`（R6）。
- **防假綠**：Task 1.3 動工前 diff 三個既有測試檔斷言並附 diff；不得放寬或刪除既有斷言換綠。
- **邊界目錄（適用項）**：空 DF ✓／全 NaN 列 ✓／Inf ✓／std=0 ✓／重複·亂序 timestamp ✓（ledger `evaluation_id` 重複）／
  API 重啟 ✗（本票無 API 層）／並發寫 ✓（Task 2.3）／**OOM 降載 ✓（Task 4.1 之 `CscvBudgetExceeded` 守衛，
  斷言⑤；R1 CODEX-R1-P1-06 後由 N/A 改為適用）**／大尺度浮點 reduction ✓（極大 N 之 `exp`／`ln`）。

## §R 回退

- 四批各自獨立 commit，可單獨 revert；B1 Task 1.3 為唯一觸及既有檔者，單獨成 commit 以便單點回退。
- 依賴方向：B1 無依賴；B2 依賴 B1 函式；B3 依賴 B1+B2；**B4 依賴 B1+B2，不依賴 B3**
  （R1 COMPOSER-R1-P1-02 更正前版假依賴）⇒ B3 與 B4 可獨立 revert。
- 新模組（除 Task 1.3）**無既有 caller** ⇒ revert 即完全移除，無下游破壞。
- 三關為純函式，`pytest tests/momentum/Analysis/strategy_validation/ -q` rc=0 即可用，
  **不加預設關閉旗標**（對齊「驗過就別預設關閉」）；逃生口＝呼叫方不呼叫。
- Golden（`gap1_reference_cases.json`）FAIL ⇒ 不 merge。

## §N N/A 登記

- **接線類 Task（具名待接線項，理由＝§A 成熟度地圖：上游皆不完整，改其結構將於重寫時作廢）**：
  1. Optuna／`_record_trial_metrics` 寫入 ledger（生產者接線）— 待引擎成熟；義務由 Task 2.3 conformance 鎖住。
  2. `api/services/optimization_output_service.py` 產出候選×時間矩陣（PBO 重算式接線）— 待引擎成熟。
  3. `api/routes/ml_pipeline.py` 掛載 eligibility 檢查 — 待 pipeline 路徑成形。
  4. `frontend/` 之降級展示面板與警語文案 — 待後端接線完成；本票僅定義 `display_downgrade`／`warning_text_key`。
  5. 策略層 wiring 閘門（等價 `ic_wiring_check.py` 但吃策略契約）— 待接線批；本票不擴 IC 版（其 sections 為 IC 封閉集合）。
- **C1 之 N 繞過路徑逐條具名（R1 CODEX-R1-P0-04；本票以契約覆蓋、接線待未來批）**：
  ① 換 `study_name` 重開 study ② UI/API 重複送單無 idempotency ③ 記憶體 task registry
  `_cleanup_old_tasks(keep_latest=100)` 淘汰 ④ 行程重啟遺失 registry ⑤ `factories.create_optuna_optimizer`
  與 `VectorizedBacktest.run_backtest` 直呼 ⑥ UI 上限 1000 vs API 上限 10000。
  **本票覆蓋方式**：`dataset_key`＋`research_session_id` 為 ledger 查詢主鍵（跨 study 自動彙總）、
  `n_is_lower_bound` 恆真、缺帳本 `n_unknown` fail-closed。**未覆蓋**：上列六條在生產者未接線前
  無法被機器阻止 ⇒ 屬待接線項 1 之驗收範圍，不得宣稱本票已關閉 C1 之繞過面。
- **層級隔離**：IC 之 FDR `n_tests` 與 XGBoost `total_cases` **禁**映射為策略 N（因子層已由 FDR/HAC 罰過）；
  本票以 ledger 之 `dataset_key` 語意隔離，且契約不提供任何從 IC/XGBoost 計數取 N 之欄位。
- **API 層硬擋 promote**：本票不實作 — **使用者 2026-08-17 裁決採「降級展示＋明顯警語」**。
  🔴 **具名殘留**：`api/routes/ml_pipeline.py:124-245` 之 promote/建 pipeline 路徑仍可消費不合格冠軍
  （CODEX 偵察 R1-P1-06 之洞不關閉）。緩解＝Task 3.3 之機器可讀 `eligibility` 欄位。
  觸發改判條件：使用者要求，或該路徑實際上線並產生誤用。
- **TPE 自適應搜尋使「N 個獨立候選」前提失真**：本票不修（屬搜尋器設計）；
  緩解＝契約 `n_semantics_values` 含 `adaptive_search`，報告須回顯；
  DSR 之 `variance_source="ledger_cross_trial"` 在 adaptive 下為有偏估計 ⇒ 報告須同時輸出 `n_semantics`
  供讀者判斷，且 `analytic` 為預設建議來源。
- **effective independent N（R2 CODEX-R1-P0-01 殘留）**：`adaptive_search` 下之「有效獨立試驗數」
  本票**不做任何換算**（無公認可驗方法）；誠實處理＝DSR 輸出 `n_independence="unverified"`（Task 3.2 斷言⑧）
  ＋報告 `provenance.n_semantics` 回顯。**禁**以任何係數把 adaptive N 折算成獨立 N。
- **MinBTL 上界之近似誤差量化**：本票不做（需獨立 Monte Carlo 研究）；
  誠實處理＝函式名與報告欄位皆帶 `upper_bound` 語意（§A），禁宣稱精確值。
- **`prediction_analyzer.py:154` `np.cumsum` 單利權益**：本票不修（不在策略路徑，收斂檔 C2 第 6 點）；
  另立小票；Task 1.4 明定三關不得消費該路徑輸出。
