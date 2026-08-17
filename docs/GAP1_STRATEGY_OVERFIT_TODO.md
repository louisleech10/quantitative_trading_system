# GAP-1 策略層防過擬合（MinBTL／DSR／PBO）— TODO

版本：DRAFT（Internal，未過外部 adversarial 前不得 Frozen）｜基於 SPEC：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（R8，2026-08-17）
｜實作端：Claude 主委自任｜review／adversarial：codex+composer+grok 三家（實作者不自審）

> 冷啟動原則：執行端讀完本檔即可逐 Task 寫碼，不需回讀 SPEC；SPEC 之義務以 `SPEC ref` 指回。
> 🔴 SPEC R8 之三項收回（Task 2.4／3.4／4.3 欄位）**尚未經三家 adversarial**——本 TODO 之審查範圍**含此 delta**。

## §0 全域規則與約束（執行端讀完即可遵守）

- **解耦**：R1 `momentum/` 不 import `api/`（新模組全在 `momentum/Analysis/strategy_validation/`）；
  R3 服務端經 `momentum/factories.py::create_strategy_validation_reporter()`（**唯一**新增出口，Task 3.4）；
  R6 `pytest tests/momentum/Analysis/strategy_validation/ -q` 不需 `run_api.py`；R7 三關回傳型別＝新模組內
  frozen dataclass，**不得**直接餵 `api/models/`。範例：`from momentum.Analysis.strategy_validation.min_btl import assess_eligibility`（api 層禁此寫法，走 factory）。
- **既有檔改動白名單（SPEC §C；唯此六處，其餘一律新檔）**：① `momentum/Strategy/vectorized_backtest.py`
  （`run_backtest` 加 optional `timeframe`＋`BacktestResult.annualization: dict`）② `momentum/Optimization/objectives/strategy_backtest.py`
  （`__init__` 加 optional `timeframe`＋`:113` 改構）③ 上二者之既有測試（**只加斷言**）④ `momentum/factories.py`（只加一函式）
  ⑤ `api/routes/ml_pipeline.py`（只加回應欄位）⑥ `scripts/`（只新增 `strategy_wiring_check.{py,sh}`）。
  **不改** `momentum/Strategy/performance_metrics.py`。
- **成熟度約束**：`momentum/Strategy/`、`momentum/Optimization/`、`api/services/optimization_*`、`frontend/` 之結構
  **不得作為設計依據**（SPEC §A 成熟度地圖，[A-成熟度]）；白名單外之接線一律不做（登記於 registry「GAP-1 待補完」）。
- **不可違反原則**：不弱化 NaN/inf gate（退化一律 typed 非 ok，禁回 0.0）；不擅改輸出大小；真實資料 receipt 用
  `data_cache/feature_klines/kline_cache.h5`，禁合成 fixture 冒充；統計 oracle 只用第三方/文獻/解析（SPEC §G）。
- **禁取巧**：不得提供調整 MinBTL 公式常數之參數；不得以取樣頻率折抵年數；不得以 request `n_trials` 替代 ledger；
  不得對 CSCV 組合抽樣仍稱 PBO；不得為過測改既有斷言。
- **單位鎖定（[A-單位]）**：進 DSR 檢定統計量之 SR／skew／kurtosis／T 一律 per-period；年化值只回顯。
- **Logging**：`get_logger(__name__)`；純函式內部**不 log**（hot path）；只在 reporter／wiring 閘門層 log。
- **每 Task 交付紀律**：新測試須 mutation 自證（實跑貼 rc）；`bash -n scripts/*.sh` rc=0；每批一 commit，
  訊息 `-F .claude/tmp/…` 含 VERIFY receipt；**不 push**（三家 review 後由使用者明示）。
- **SPEC §A manifest ref**（不複製）：[A-成熟度]＝成熟度地圖；[A-裁決-A]＝範圍 A；[A-裁決-降級]＝不硬擋；
  [A-文獻]＝MinBTL 為上界／N=1 特例／target_sharpe 語意；[A-單位]＝per-period 鎖定。

## §B 批次執行策略（依賴拓撲 → 四批；每批＝一次實作＋一輪三家 code review）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1** | 1.1、1.2、1.3、1.4 | 無 | 輸入語意契約；1.4 依賴 1.3 之 `annualization` 欄位，須同批（批內順序 1.1→1.2→1.3→1.4） | 中 |
| **B2** | 2.1、2.2、2.3、2.4 | B1（1.1／1.2 之函式） | N 帳本契約＋讀寫＋wiring 閘；2.4 需 2.1 之契約檔存在 | 中 |
| **B3** | 3.1、3.2、3.3、3.4 | B1 全部、B2 2.1／2.2 | MinBTL＋DSR＋報告＋API 附警語；3.4 需 3.3 | 中 |
| **B4** | 4.1、4.2、4.3 | B1 1.1／1.2／1.4、B2 2.1／2.2；**不依賴 B3** | PBO 純核心；4.3 之守衛需 2.2 之 `LedgerReadResult.candidate_ids` | 中 |

- **批次間 Gate**：B1→B2：`pytest tests/momentum/Analysis/strategy_validation/test_frequency.py tests/momentum/Analysis/strategy_validation/test_sharpe.py tests/momentum/Analysis/strategy_validation/test_returns_contract.py tests/momentum/Strategy/test_vectorized_backtest.py tests/momentum/Optimization/test_strategy_backtest_enhanced.py -q` rc=0 ＋ 三家 review CLOSED；
  B2→B3／B4：`pytest tests/momentum/Analysis/strategy_validation/test_contract.py tests/momentum/Analysis/strategy_validation/test_ledger.py tests/momentum/Analysis/strategy_validation/test_ledger_conformance.py tests/momentum/Analysis/strategy_validation/test_wiring_check.py -q` rc=0 ＋ `bash scripts/strategy_wiring_check.sh` rc=0 ＋ 三家 review CLOSED；
  B3／B4 收尾：`pytest tests/momentum/Analysis/strategy_validation/ -q` rc=0 ＋ SPEC §V 13 條 mutation 全部實跑貼 rc ＋ 三家 review CLOSED。
- **每 Batch 派工 prompt（實作者＝Claude 自己，仍寫出以供 review brief 引用）**：
  「前置狀態：<上一批 commit sha、gate 命令 rc=0>；本批 Task：<列>；驗證命令：<列>；白名單外檔一律不碰；mutation 實跑貼 rc。」

---

## Phase B1 — 輸入語意契約（目標：年化／退化／T 語意皆可機器判讀；完成後三關有唯一合法輸入口）

### Task 1.1 — 年化頻率解析（`票 GAP-1/C2`）
- SPEC ref：Task 1.1　目標：由 timeframe 推導 `periods_per_year`，唯一來源 `TIMEFRAME_SECONDS`，未知即 raise。
- 輸入 / 輸出：`timeframe: str` → `int`；raise `UnknownTimeframeError`。
- 實作要點：
  1. 新檔 `momentum/Analysis/strategy_validation/__init__.py`（空）＋`frequency.py`：
     ```python
     from momentum.core.constants import TIMEFRAME_SECONDS
     class UnknownTimeframeError(ValueError): ...
     def resolve_periods_per_year(timeframe: str) -> int:
         if not isinstance(timeframe, str) or timeframe not in TIMEFRAME_SECONDS: raise UnknownTimeframeError(timeframe)
         return round(365*24*3600 / TIMEFRAME_SECONDS[timeframe])
     ```
  2. **不做**大小寫正規化、不做別名表、無 `default` 參數。
  3. 測試 `tests/momentum/Analysis/strategy_validation/__init__.py`＋`test_frequency.py`：參數化 `("1h",8760)("4h",2190)("12h",730)("1d",365)`；raise 案例 `"7m"`／`""`／`None`／`"1H"`。
- 修改檔案：新增 `frequency.py::resolve_periods_per_year`、`UnknownTimeframeError`　既有 caller：無。
- 不可做：不得在本檔新增 timeframe→秒之第二份表；不得提供預設值參數。
- 邊界：① 未知 timeframe → raise ② `None`／空字串 → raise ③ `"1H"` → raise。
- 風險緩解：⊘
- 驗證：`pytest tests/momentum/Analysis/strategy_validation/test_frequency.py -q` rc=0；mutation §V-8（未知回 730）⇒ raise 斷言轉紅（實跑貼 rc）。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 1.2 — typed Sharpe（`票 GAP-1/C2`）
- SPEC ref：Task 1.2　目標：三關自算 SR；退化回 NaN＋status；輸出 per-period 與年化雙欄＋Mertens 估計量變異數。
- 輸入 / 輸出：`returns: np.ndarray|pd.Series, *, periods_per_year: int, risk_free_rate: float=0.0` → `SharpeResult`（frozen dataclass：
  `value_per_period`／`value_annualized`／`status`／`reason`／`n_obs`／`periods_per_year`／`skew`／`kurtosis`／`sr_estimator_variance`）。
- 實作要點：
  1. `sharpe.py`：清理為 float ndarray；`n_obs<2`／含 NaN·inf／`std(ddof=1)==0` ⇒ 全數值欄 NaN、`status="not_computed"`（六值枚舉之一，由 `ic_config_schema.contract_enum("capability_status")` 取得）、`reason="degenerate_returns"`。
  2. `sr_pp = (mean - rf/periods)/std`；`value_annualized = sr_pp*sqrt(periods)`；`skew`／`kurtosis` 用 `scipy.stats.skew(x)`／`kurtosis(x, fisher=False)`（per-period）；
     `sr_estimator_variance = (1 - skew*sr_pp + (kurtosis-1)/4*sr_pp**2)/(n_obs-1)`。
  3. status 值**直接**取 IC 契約枚舉（不依賴 Task 2.1 檔存在）。
- 修改檔案：新增 `sharpe.py::compute_sharpe`、`SharpeResult`　既有 caller：無。
- 不可做：不得提供回 0.0 之相容模式；不得在此推導 periods；不得把年化值用於任何統計量。
- 邊界：① 空 ② 全 NaN ③ 單觀測 ④ std=0 ⑤ 含 inf ⑥ 全零。
- 風險緩解：⊘
- 驗證：`test_sharpe.py`：常數序列 ⇒ 兩 value 皆 `isnan` 且 `status!="ok"`；手算案例 `atol=1e-12`；skew/kurt 與 scipy 一致 `atol=1e-10`；`sr_estimator_variance` 手算 `atol=1e-12`；rf=0 時 `value_annualized == value_per_period*sqrt(periods)` `atol=1e-12`。mutation §V-5（退化回 0.0）與 §V-10（係數改錯）轉紅。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 1.3 — 既有回測路徑帶入年化來源（`票 GAP-1/C2`）
- SPEC ref：Task 1.3　目標：消除策略路徑隱性 730；來源可機器判讀；數值真的分叉。
- 輸入 / 輸出：`run_backtest(..., timeframe: str|None=None)`；`BacktestResult.annualization: dict`＝`{"source": "resolved"|"default_730", "periods_per_year": int, "timeframe": str|None}`。
- 實作要點：
  1. `vectorized_backtest.py`：`run_backtest` 簽名加 `timeframe: str | None = None`；內部
     ```python
     try: ppy = resolve_periods_per_year(timeframe) if timeframe else None
     except UnknownTimeframeError: ppy = None
     if ppy is None: metrics = PerformanceMetrics(equity_curve, trades).calculate_all(); ann = {"source":"default_730","periods_per_year":730,"timeframe":None}
     else: metrics = PerformanceMetrics(equity_curve, trades, periods_per_year=ppy).calculate_all(); ann = {"source":"resolved","periods_per_year":ppy,"timeframe":timeframe}
     ```
     `BacktestResult` dataclass 加欄位 `annualization: dict = field(default_factory=dict)`；早退路徑（`_validate_inputs`）亦填 `default_730`。
  2. `objectives/strategy_backtest.py`：`__init__` 加 `timeframe: str|None=None` 存 `self.timeframe`；`evaluate()` 呼叫 `run_backtest(..., timeframe=self.timeframe)`；`:113` 改 `PerformanceMetrics(result.equity_curve, result.trades, periods_per_year=result.annualization["periods_per_year"])`。
  3. **rf 傳遞**：白名單允許兩呼叫點顯式傳 `risk_free_rate`（預設維持 0.02；oracle fixture 用 0.0）。
  4. 既有測試：動工前 `git diff` 三檔斷言存檔於 commit；只加斷言。
- 修改檔案：`vectorized_backtest.py::VectorizedBacktest.run_backtest`、`BacktestResult`；`objectives/strategy_backtest.py::StrategyBacktestObjective.__init__/evaluate`　既有 caller：`tests/momentum/Strategy/test_vectorized_backtest.py`、`test_performance_metrics.py`、`tests/momentum/Optimization/test_strategy_backtest_enhanced.py`。
- 不可做：不改 `PerformanceMetrics`；不把 source 塞進 `metrics` dict；不改 `metrics: Dict[str,float]` 型別。
- 邊界：① `timeframe=None` ② 未支援值 ⇒ 落 `default_730` ③ 12h（730 與 resolved 同值 ⇒ 用 1h 案例區分）。
- 風險緩解：⊘
- 驗證：新增斷言 ① `timeframe="1h"` ⇒ `annualization=={"source":"resolved","periods_per_year":8760,"timeframe":"1h"}` ② `None` ⇒ `source=="default_730"` ③ **`risk_free_rate=0.0` fixture** 下 `sharpe(1h)/sharpe(None)` ＝ `sqrt(8760/730)` `atol=1e-9` ③b rf=0.02 下 `periods_per_year` 分叉且兩 sharpe 不等 ②b objective 端 `timeframe="1h"` 之 sharpe 與 engine 直呼同值 `atol=1e-12` 且與 `None` 不等 ④ 既有斷言未放寬（diff 附）。mutation §V-13（fixture rf=0.02）⇒ ③ 轉紅。
- **存活至**：全票完工後保留；引擎重寫則契約存活、實作可棄。
- **覆蓋風險**：實作可能被未來引擎重寫覆蓋——已知且接受（價值主體＝契約與 B3/B4 純函式）。

### Task 1.4 — canonical 報酬序列與 T 語意（`票 GAP-1/C2`；依賴 1.3）
- SPEC ref：Task 1.4　目標：三關唯一合法輸入口；T 語意三值；DSR 禁 `bar_count`。
- 輸入 / 輸出：`extract_period_returns(backtest_result, *, timeframe: str, t_semantics: str) -> PeriodReturns`（frozen：`values`／`t_semantics`／`n_obs`／`periods_per_year`／`annualization_source`／`source_artifact_hash`／`status`／`reason`）。
- 實作要點：
  1. `returns_contract.py`：讀 `backtest_result.annualization`；缺該欄 ⇒ `status="not_computed"`、`reason="annualization_unresolved"`；`source!="resolved"` ⇒ 同 reason。
  2. 三語意：`bar_count`＝`equity.pct_change().dropna()`；`nonzero_return_bars`＝前者濾掉 `==0`；`trade_level`＝`[t.pnl_pct for t in trades]`，其 `periods_per_year` ＝ `len(trades)/available_years`（`available_years = n_bars / resolve_periods_per_year(timeframe)`）。
  3. `bar_count` 一律 `status="not_applicable"`、`reason="t_semantics_inflates_significance"`（值仍回傳供診斷）。
  4. `source_artifact_hash` ＝ `sha256` over `(equity_curve.values.tobytes(), tuple((t.entry_time,t.exit_time,t.pnl_pct) for t in trades))`（寫死於本檔）。
- 修改檔案：新增 `returns_contract.py::extract_period_returns`、`PeriodReturns`　既有 caller：無。
- 不可做：不接受 `prediction_analyzer` 之 cumsum 輸出；不自行推導 timeframe。
- 邊界：① 無交易 ② 單一交易 ③ equity 全 1.0 ④ 缺 `annualization` ⑤ timeframe 未知（1.1 raise 向上拋）。
- 風險緩解：⊘
- 驗證：`test_returns_contract.py`：① 同一 `BacktestResult`（真實 kline 跑一次 `VectorizedBacktest`）下 `bar_count.n_obs > trade_level.n_obs` ② `bar_count` ⇒ `reason=="t_semantics_inflates_significance"` ③ `default_730` ⇒ `status!="ok"` ④ `trade_level.periods_per_year` 對固定 fixture `atol=1e-9` ⑤ 缺 `annualization` ⇒ `reason=="annualization_unresolved"`。mutation §V-9 轉紅。
- **存活至**：全票完工後保留（B3 唯一輸入口）。
- **覆蓋風險**：無。

### Phase B1 測試 + Gate
- 單元：`test_frequency.py`／`test_sharpe.py`／`test_returns_contract.py`；邊界：各 Task 邊界列；效能：⋅（純算術）。
- Gate：§B 之 B1→B2 命令 rc=0；mutation §V-5／8／9／10／13 實跑貼 rc；三家 code review CLOSED。

---

## Phase B2 — N 帳本契約與 fail-closed 讀取（目標：契約唯一真相源＋讀寫 API＋wiring 閘；完成後 N 有可審計來源）

### Task 2.1 — 策略驗證契約 JSON＋唯一 resolver（`票 GAP-1/C1`）
- SPEC ref：Task 2.1　目標：15 頂層鍵 SoT、ref 可解析、drift 可偵測。
- 輸入 / 輸出：`momentum/Analysis/contracts/strategy_validation_contract.json`；`contract.py::load_strategy_validation_contract() -> dict`（含解析後 `capability_status`）、`validate_against_contract(obj: dict, section: str) -> None`（違約 raise `ContractViolation`）。
- 實作要點：
  1. JSON 頂層鍵**恰為**：`version`、`capability_status_ref`、`ledger_record_keys`、`n_fields`、`report_sections`、`eligibility_keys`、`annualization_source_values`、`t_semantics_values`、`n_semantics_values`、`selection_metric_values`、`universe_source_values`、`variance_source_values`、`metric_unit_values`、`reasons`、`reason_conditions`。
     內容依 SPEC Task 2.1（`ledger_record_keys` 為物件：11 鍵各 `{"type","required"}`＋`metric_unit`；`n_fields` 五值；`reasons` 11 值；`report_sections` 五節各含 `required_keys`／`optional_keys`／`types`／`additional_properties:false`；`eligibility_keys` 九鍵含 type；`reason_conditions` key 集合＝`reasons`）。
  2. resolver：`capability_status_ref="momentum/Analysis/contracts/ic_report_contract.json#capability_status"` → 載入、取鍵、驗非空 `list[str]`，任一失敗 raise；回傳 dict 內以 `capability_status` 鍵掛解析結果。
  3. `validate_against_contract`：驗 required 齊備／type 相符／無額外鍵／枚舉值屬集合。
- 修改檔案：新增 `strategy_validation_contract.json`、`contract.py::load_strategy_validation_contract`、`validate_against_contract`、`ContractViolation`　既有 caller：無。
- 不可做：不複列六值枚舉；不放實作邏輯或預設 N；不改 `ic_report_contract.json`。
- 邊界：① JSON 語法錯 ② ref 目標檔缺 ③ ref 鍵缺 ④ 未知頂層鍵 ⑤ 枚舉重複。
- 風險緩解：⊘
- 驗證：`test_contract.py`：① `load()["capability_status"] == ic_config_schema.load_report_contract()["capability_status"]` ② 六值不在策略契約字面（`grep -c`==0） ③ tmp fixture 改 ref 指不存在鍵 ⇒ raise ④ 無鍵名 `n`/`N` ⑤ 15 鍵齊 ⑥ `metric_unit_values==["per_period","annualized"]` 且 `set(reason_conditions)==set(reasons)`。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 2.2 — N 帳本讀取 API（`票 GAP-1/C1`）
- SPEC ref：Task 2.2　目標：唯一取 N 入口；缺帳本 `n_unknown`；輸出 typed `LedgerReadResult`。
- 輸入 / 輸出：`read_trial_ledger(*, research_session_id: str, dataset_key: str) -> LedgerReadResult`（frozen：`n_candidates_considered`／`n_evaluated`／`n_valid_metrics`／`n_failed_or_pruned`／`n_is_lower_bound`(恆 True)／`n_for_dsr`／`snapshot_hash`／`artifact_hashes: frozenset[str]`／`candidate_ids: frozenset[str]`／`n_semantics`／`valid_sharpe_values: tuple[float,...]`／`status`／`reason`）。
- 實作要點：
  1. `ledger.py`：路徑 `MomentumConfig.from_project_root().results_path / "strategy_validation" / f"{research_session_id}__{dataset_key}.jsonl"`（不新增設定鍵）。
  2. 逐行 `json.loads`；以契約 `ledger_record_keys` 驗（type/required/additional）；非法列 ⇒ `n_failed_or_pruned+=1`、reason 累記 `ledger_row_invalid`，**不丟棄計數**。
  3. `n_candidates_considered=len(set(candidate_id))`；`n_evaluated=len(rows_valid_schema)`；`n_valid_metrics=sum(metric_valid)`；`n_for_dsr=n_candidates_considered`；`valid_sharpe_values` 只收 `metric_name=="sharpe" and metric_unit=="per_period" and metric_valid`；`snapshot_hash=sha256(",".join(sorted(artifact_hashes))+"|"+dataset_key+"|"+research_session_id)`。
  4. 檔不存在／零列 ⇒ 全計數 0、`status="unavailable"`、`reason="n_unknown"`。
- 修改檔案：新增 `ledger.py::read_trial_ledger`、`LedgerReadResult`　既有 caller：無。
- 不可做：不接 Optuna／`_record_trial_metrics`／`optimization_task_service`；不提供手填 N 正式路徑。
- 邊界：① 檔不存在 ② 空檔 ③ 非法 JSON 行 ④ 缺必填鍵 ⑤ 同 candidate 多 attempt ⑥ 不可讀（權限）⑦ annualized row 混入。
- 風險緩解：⊘
- 驗證：`test_ledger.py`（tmp_path fixture）：① 無檔 ⇒ `status!="ok"` 且 `reason=="n_unknown"` ② 3 合法＋1 非法 ⇒ `n_evaluated==3`、`n_failed_or_pruned==1`、reason 含 `ledger_row_invalid` ③ `n_is_lower_bound is True`（3 種輸入）④ 2 筆 valid per_period sharpe ⇒ `len==2` ⑤ 同 candidate 兩 attempt ⇒ `n_candidates_considered==1`、`n_evaluated==2` ⑥ `n_for_dsr==n_candidates_considered` ⑥b annualized row 不入 `valid_sharpe_values` ⑥c `len(candidate_ids)==n_candidates_considered` ⑦ 多一列 ⇒ `snapshot_hash` 變 ⑧ 非法 row reason 字面。mutation §V-7 轉紅。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 2.3 — 生產者一致性測試（`票 GAP-1/C1`）
- SPEC ref：Task 2.3　目標：`append_trial_attempt` 唯一寫入口；未來引擎的驗收合約。
- 輸入 / 輸出：`append_trial_attempt(*, research_session_id, dataset_key, record: dict) -> None`（先以契約 schema 檢核，通過才 append 一行；失敗 raise，不寫半列；見 test_ledger_conformance.py）。
- 實作要點：
  1. `ledger.py`：先 `validate_against_contract(record, "ledger_record_keys")`；重複 `evaluation_id`（同檔內）⇒ raise；以 `open(path,"a")`＋單次 `write(json.dumps(record)+"\n")`＋`flush`；目錄自動建立。
  2. `test_ledger_conformance.py`：假想生產者寫 N 筆 ⇒ `read` 之 `n_evaluated == n_valid_metrics + n_failed_or_pruned`；缺鍵 ⇒ raise 且行數不變；`ThreadPoolExecutor(2)` 各 50 筆 ⇒ `n_evaluated==100` 且每行可 `json.loads`；重複 `evaluation_id` ⇒ raise。
- 修改檔案：`ledger.py::append_trial_attempt`　既有 caller：無。
- 不可做：不放寬 schema；不接任何真實生產者。
- 邊界：① 缺鍵 ② 型別錯 ③ 並發 ④ 磁碟不可寫 ⑤ 重複 `evaluation_id`。
- 風險緩解：⊘
- 驗證：`pytest tests/momentum/Analysis/strategy_validation/test_ledger_conformance.py -q` rc=0（含上列四斷言）。
- **存活至**：全票完工後保留（未來引擎驗收用）。
- **覆蓋風險**：無。

### Task 2.4 — 策略層 wiring 閘門（`票 GAP-1/C4`；R8 收回）
- SPEC ref：Task 2.4　目標：契約與 `report.py`／`strategy_validation/*.py` 之封閉集合比對；幽靈欄位／死枚舉／自創 reason 即紅。
- 輸入 / 輸出：`scripts/strategy_wiring_check.py`（argv 旗標 `--contract`／`--pkg` 供測試覆寫，禁 env）＋`scripts/strategy_wiring_check.sh`（`exec` 包裝，仿 `ic_wiring_check.sh`）；exit 0/1/2。
- 實作要點：
  1. W1：契約 `report_sections` 每節名 ∈ `report.py` 字面（`re.search(rf'["\']{name}["\']')`）。W2：契約 `reasons` 每值 ∈ `strategy_validation/*.py` 任一檔字面。W3：`strategy_validation/*.py` 中所有 `reason="..."`／`reason == "..."` 字面 ⊆ 契約 `reasons`。W4：`eligibility_keys` 每鍵 ∈ `report.py` 字面。
  2. 缺契約／缺 `report.py` ⇒ rc=2 並印原因；任一規則違反 ⇒ 列出項目 rc=1；全綠印 `[strategy_wiring_check] ✓ W1..W4`。
  3. 常駐測試 `test_wiring_check.py`：subprocess 跑 `.sh` rc=0；mutation：tmp 契約加未用 section ⇒ rc=1；tmp pkg 檔加自創 reason ⇒ rc=1。
  4. 🔴 治理連動：本 Task commit 須同時更新四份治理白話檔（CLAUDE.md 鐵律；`plain_docs_sync_check.sh` 會擋）。
- 修改檔案：新增 `scripts/strategy_wiring_check.py::main`、`scripts/strategy_wiring_check.sh`　既有 caller：無。
- 不可做：不改 `ic_wiring_check.py`；不用散文/關鍵字判斷。
- 邊界：① 契約缺 ⇒ 2 ② `report.py` 缺 ⇒ 2 ③ `reasons` 空 ⇒ 1。
- 風險緩解：⊘
- 驗證：`bash scripts/strategy_wiring_check.sh` rc=0；`bash -n scripts/strategy_wiring_check.sh` rc=0；`pytest tests/momentum/Analysis/strategy_validation/test_wiring_check.py -q` rc=0；兩 mutation 實跑 rc=1。
- **存活至**：全票完工後保留；前端接線批加 W5。
- **覆蓋風險**：無。

### Phase B2 測試 + Gate
- 單元：`test_contract.py`／`test_ledger.py`／`test_ledger_conformance.py`／`test_wiring_check.py`；邊界：各 Task；效能：⋅。
- Gate：§B 之 B2→B3／B4 命令 rc=0；四份治理白話檔同步；三家 code review CLOSED。

---

## Phase B3 — MinBTL＋DSR 純統計核心（目標：資格閘＋冠軍檢定＋報告契約＋API 警語；完成後不合格＝降級展示）

### Task 3.1 — MinBTL 上界與試驗預算（`票 GAP-1/C5`）
- SPEC ref：Task 3.1　目標：`min_btl_years_upper_bound`／`max_trials_budget`／`assess_eligibility` 三函式；floor；三態 eligible。
- 輸入 / 輸出：`min_btl_years_upper_bound(*, n_trials:int, target_sharpe:float)->float`；`max_trials_budget(*, t_years:float, target_sharpe:float)->int`；`assess_eligibility(*, t_years:float, ledger_result: LedgerReadResult, target_sharpe:float)->EligibilityResult`（frozen：`eligible: bool|None`／`required_years_upper_bound`／`available_years`／`trials_budget`／`budget_capped: bool`／`trials_used`／`target_sharpe`／`status`／`reason`）。
- 實作要點：
  1. `min_btl.py`：參數驗證（`n_trials<1`／`target_sharpe<=0`／`t_years<=0` ⇒ `ValueError`）；`n_trials==1 ⇒ 0.0`；否則 `2*math.log(n_trials)/target_sharpe**2`。
  2. `max_trials_budget`：`x=t_years*target_sharpe**2/2`；`x>700` ⇒ 回 `10**18` 並由 `assess_eligibility` 標 `budget_capped=True`；否則 `math.floor(math.exp(x))`（**floor**）。
  3. `assess_eligibility`：`ledger_result.status!="ok"` ⇒ `eligible=None`、status/reason 傳遞、`trials_used=None`；否則 `trials_used=ledger_result.n_for_dsr`、`eligible = required<=t_years`。
- 修改檔案：新增 `min_btl.py` 三函式＋`EligibilityResult`　既有 caller：無。
- 不可做：不提供調常數之參數；不以頻率折抵年數；不輸出「精確最短長度」語意。
- 邊界：① N=1 ② N<1 raise ③ SR≤0 raise ④ T≤0 raise ⑤ N 不可知 ⇒ None ⑥ N=1e6 ⑦ budget=0（極短 T）⇒ `eligible=False`。
- 風險緩解：⊘
- 驗證：`test_min_btl.py`：① `(100,1.0)`＝9.210340371976184 `atol=1e-12` ② `max_trials_budget(2.3232876712328765,1.5)==13`；SR=1.0→3、2.0→104、2.5→1422 ③ 20 組參數化 `ub(budget)<=T<ub(budget+1)` ④ N=1 ⇒ 0.0；三種 raise ⑤ C5 oracle：`assess_eligibility(t_years=2.3232876712328765, ledger_result=<n_for_dsr=100 fixture>, target_sharpe=1.0).eligible is False` 且 `trials_used>trials_budget` ⑥ ledger status≠ok ⇒ `eligible is None` ⑦ N=10**6 有限 ⑧ **反向測試**：同一期間 1h/4h/12h 三 fixture 之 `available_years` 差 `atol=1e-6`。mutation §V-2／3 轉紅。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.2 — Deflated Sharpe Ratio（`票 GAP-1/C2`）
- SPEC ref：Task 3.2　目標：全式寫死；分母恆 Mertens；SR0 之跨 trial 變異二態；snapshot 綁定。
- 輸入 / 輸出：`deflated_sharpe(*, period_returns: PeriodReturns, ledger_result: LedgerReadResult|None=None, n_trials: int|None=None, variance_source: str, cross_trial_sr_variance: float|None=None, n_semantics: str) -> DSRResult`（frozen：`value`／`sr0`／`sr_obs_per_period`／`n_trials_used`／`variance_source`／`n_independence`／`status`／`reason`）。
- 實作要點：
  1. `deflated_sharpe.py`：`period_returns.status!="ok"` ⇒ 傳遞 status/reason、`value=nan`。`ledger_result` 與 `n_trials` 互斥（皆給 ⇒ `ValueError`；皆缺 ⇒ `ValueError`）。`n_semantics`／`variance_source` 不在契約枚舉 ⇒ `ValueError`。
  2. `sr = compute_sharpe(period_returns.values, periods_per_year=period_returns.periods_per_year)`；`SR_obs=sr.value_per_period`、`g3=sr.skew`、`g4=sr.kurtosis`、`T=sr.n_obs`；`den=sqrt(1-g3*SR_obs+(g4-1)/4*SR_obs**2)`。
  3. `N = ledger_result.n_for_dsr if ledger_result else n_trials`；`N==1 ⇒ SR0=0`；否則需 `V_cross`：`explicit` ⇒ `cross_trial_sr_variance`（須有限且 >0，否則 `degenerate_returns`）；`ledger_cross_trial` ⇒ `statistics.variance(ledger_result.valid_sharpe_values)`（`len<2` ⇒ `cross_trial_variance_unavailable`）；
     `SR0 = sqrt(V_cross)*((1-γ)*norm.ppf(1-1/N)+γ*norm.ppf(1-1/(N*e)))`，γ=0.5772156649015329。
  4. snapshot：`ledger_result` 在場 ⇒ 驗 `period_returns.source_artifact_hash in ledger_result.artifact_hashes` 且 `len(valid_sharpe_values)<=n_valid_metrics`，否則 `ledger_snapshot_mismatch`。
  5. `value = norm.cdf((SR_obs-SR0)*sqrt(T-1)/den)`；`n_independence = "unverified" if n_semantics=="adaptive_search" else "assumed_independent"`。
- 修改檔案：新增 `deflated_sharpe.py::deflated_sharpe`、`DSRResult`　既有 caller：無。
- 不可做：不吃 `PerformanceMetrics.calculate_all()`；不接受 `bar_count`；不接受 request `n_trials` 冒充；不用年化值進統計量。
- 邊界：① N 不可知 ② 序列含 NaN ③ std=0 ④ N=1 ⑤ kurt>50 ⑥ `n_semantics` 缺 ⇒ raise ⑦ `variance_source` 未知 ⇒ raise。
- 風險緩解：⊘
- 驗證：`test_deflated_sharpe.py`：① N=1、skew=0、kurt=3 ⇒ 等於 PSR 解析值 `atol=1e-10` ② `E[maxSR]/√V` 三點 1.5746/2.5306/3.2551 `atol=1e-4` ③ N 遞增 ⇒ 單調不增（10 點）④ `bar_count`／`default_730` ⇒ `status!="ok"` 且 `isnan(value)` ⑤ `ledger_cross_trial` 且 `len<2` ⇒ `reason=="cross_trial_variance_unavailable"` ⑤b `ledger_result`＋`n_trials` 同傳 ⇒ raise；snapshot 不涵蓋 ⇒ `ledger_snapshot_mismatch` ⑥ 兩 `variance_source` 皆有案例 ⑦ `periods_per_year∈{1,730,8760}` 三值 DSR 不變 `atol=1e-12` ⑧ `adaptive_search` ⇒ `n_independence=="unverified"`。mutation §V-1／11／12 轉紅。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.3 — 報告區段與降級展示契約（`票 GAP-1/C4`）
- SPEC ref：Task 3.3　目標：三關結果之機器可讀輸出；任一非 ok 或 `eligible is not True` ⇒ 降級＋警語＋無推薦鍵。
- 輸入 / 輸出：`build_validation_section(*, eligibility: EligibilityResult, dsr: DSRResult|None, pbo: PBOResult|None, provenance: dict) -> dict`（通過 `validate_against_contract(_, "report_sections")`）。
- 實作要點：
  1. `report.py`：組五節 `eligibility`／`min_btl`／`dsr`／`pbo`／`provenance`，各帶 `status`／`reason`；`provenance` 帶 `n_semantics`／`t_semantics`／`annualization_source`／`n_independence`。
  2. `all_ok = eligibility.eligible is True and all(s.status=="ok" for s in (min_btl,dsr,pbo))`；`display_downgrade = not all_ok`；`warning_text_key = "" if all_ok else "strategy_validation.downgraded"`（key 非文案）。
  3. 結構中**不放**任何推薦類鍵（allowlist：契約 `report_sections`＋`eligibility_keys` 之鍵集合；輸出鍵集合須 ⊆ allowlist）。
  4. 假設 N（敏感度）：`provenance.n_source="assumed_not_ledgered"` ⇒ 強制 `eligible=None`。
- 修改檔案：新增 `report.py::build_validation_section`　既有 caller：無。
- 不可做：不做 API 硬擋；不寫文案字串；不複用 `overfitting_score` 命名。
- 邊界：① 三關皆 unavailable ② 僅 MinBTL 可算 ③ 假設 N。
- 風險緩解：⊘
- 驗證：`test_report_section.py`：eligibility 三態 × 三關 ok/非 ok ＝ 24 案例參數化：① 僅「True 且三 ok」`display_downgrade is False` ② 其餘 23 例 `True` 且 `len(warning_text_key)>0` ③ 23 例輸出鍵 ⊆ allowlist ④ 24 例 `validate_against_contract` 不 raise。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 3.4 — `ml_pipeline` 回應附資格狀態＋警語（`票 GAP-1/C4`；R8 收回；非硬擋）
- SPEC ref：Task 3.4　目標：唯一消費冠軍 trial 之 API 路徑上落實「降級展示＋警語」，**不拒絕**。
- 輸入 / 輸出：`momentum/factories.py::create_strategy_validation_reporter() -> StrategyValidationReporter`（新類於 `strategy_validation/reporter.py`，方法 `for_study_trial(study_name:str, trial_number:int) -> dict`）；`api/routes/ml_pipeline.py::create_ml_pipeline` 回應 model 加 optional 欄位 `strategy_validation: dict|None`。
- 實作要點：
  1. `reporter.py`：`for_study_trial` 內部以 `research_session_id=study_name`、`dataset_key=f"trial:{trial_number}"` 呼叫 `read_trial_ledger`（今日必為 `n_unknown`）→ `assess_eligibility`（`t_years` 由呼叫方傳入或無 ⇒ `eligible=None`）→ `build_validation_section(dsr=None,pbo=None,...)`；任何例外 ⇒ 回 `{"status":"computation_failed","reason":str(exc)[:200],"display_downgrade":True,"warning_text_key":"strategy_validation.downgraded"}`。
  2. `factories.py`：`def create_strategy_validation_reporter(): from momentum.Analysis.strategy_validation.reporter import StrategyValidationReporter; return StrategyValidationReporter()`（懶 import，仿既有）。
  3. `ml_pipeline.py`：在成功回應組裝處 `response.strategy_validation = create_strategy_validation_reporter().for_study_trial(request.study_name, request.trial_number)`；置於 try 內、失敗不影響原流程；`CreatePipelineResponse` 加 `strategy_validation: Optional[Dict[str, Any]] = None`。
  4. 新測試 `tests/api/test_ml_pipeline_strategy_validation.py`（`TestClient`＋monkeypatch pipeline service 成功路徑）。
- 修改檔案：新增 `reporter.py::StrategyValidationReporter.for_study_trial`；`factories.py::create_strategy_validation_reporter`；`api/routes/ml_pipeline.py::create_ml_pipeline`＋`CreatePipelineResponse`　既有 caller：`tests/test_phase6_end_to_end.py`、`tests/test_frontend_integration.py`（動工前 grep 其對 `CreatePipelineResponse` 之斷言，禁放寬）。
- 不可做：不拒絕請求；不在 route 內做統計計算；不改回應其他欄位。
- 邊界：① 無 ledger ② reporter 例外 ③ study/trial 不存在（既有 404 路徑不變）。
- 風險緩解：⊘
- 驗證：新測試：① 成功回應含 `strategy_validation` 且 `display_downgrade is True` ② `warning_text_key` 非空 ③ HTTP 狀態碼同既有 ④ monkeypatch reporter raise ⇒ 仍 2xx 且 `strategy_validation["status"]=="computation_failed"` ⑤ 既有兩測試檔全綠且斷言未放寬。`grep -r "from api\." momentum/` == 0。
- **存活至**：全票完工後保留；`ml_pipeline.py` 重寫則欄位契約存活。
- **覆蓋風險**：實作可能被 API 層重寫覆蓋——已知且接受（價值主體＝欄位契約與 Task 3.3）。

### Phase B3 測試 + Gate
- 單元：`test_min_btl.py`／`test_deflated_sharpe.py`／`test_report_section.py`／`tests/api/test_ml_pipeline_strategy_validation.py`；邊界：各 Task；效能：⋅。
- Gate：`pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` rc=0；`bash scripts/strategy_wiring_check.sh` rc=0；mutation §V-1／2／3／11／12 貼 rc；三家 code review CLOSED。

---

## Phase B4 — PBO（CSCV）純統計核心（目標：選法穩定性檢定；完成後 top-K 污染機械拒絕）

### Task 4.1 — CSCV 分割器（`票 GAP-1/C3`）
- SPEC ref：Task 4.1　目標：S 塊組合 lazy iterator；雙重預算 fail-closed。
- 輸入 / 輸出：`cscv_path_count(s_blocks:int)->int`；`iter_cscv_splits(*, n_obs:int, s_blocks:int)` → generator of `(is_idx: np.ndarray, oos_idx: np.ndarray)`；`CscvBudgetExceeded(RuntimeError)`。
- 實作要點：
  1. `cscv.py`：`s_blocks%2!=0`／`s_blocks>n_obs` ⇒ `ValueError`；`cscv_path_count=math.comb(S,S//2)`。
  2. 預算：`path_count>20000 or path_count*n_obs>20_000_000` ⇒ raise `CscvBudgetExceeded`（在建立 generator 前）。
  3. 塊邊界：`base=n_obs//S; rem=n_obs%S`；前 `rem` 塊長 `base+1`，其餘 `base`；`itertools.combinations(range(S), S//2)` 逐組 `yield (concat(blocks[i] for i in combo), concat(其餘))`。
- 修改檔案：新增 `cscv.py`　既有 caller：無。
- 不可做：不隨機抽樣；不回傳 list；不 import `combinatorial_purged_cv.py`。
- 邊界：① S 奇 ② S>n_obs ③ 餘數 ④ S=2 ⑤ S=20 超預算。
- 風險緩解：⊘
- 驗證：`test_cscv.py`：① `cscv_path_count(12)==924`、14→3432、16→12870 且 `==math.comb` ② S=12 全 924 組 IS∪OOS＝全索引且交集空 ③ `n_obs=1205,S=12` ⇒ 前 5 塊 101、餘 100 ④ S=13 raise；S>n_obs raise ⑤ `cscv_path_count(20)==184756` 且 `iter_cscv_splits(1200,20)` raise；`S=16,n_obs=2000` raise（元素預算）⑥ `inspect.isgenerator` 為真且 `next()` 計數探針==1。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 4.2 — PBO 值（`票 GAP-1/C3`）
- SPEC ref：Task 4.2　目標：逐 path 四步演算法＋path 級退化處理；PBO 分母＝`n_paths_used`。
- 輸入 / 輸出：`probability_of_backtest_overfitting(*, returns_matrix: np.ndarray, n_obs:int, n_candidates:int, candidate_ids: Sequence[str], s_blocks:int, selection_metric:str, universe_provenance: UniverseProvenance, ledger_result: LedgerReadResult|None=None) -> PBOResult`（frozen：`value`／`logits_min`／`logits_median`／`logits_max`／`n_paths`／`n_paths_used`／`n_paths_skipped`／`n_path_exclusions`／`n_candidates_invalid`／`status`／`reason`）。
- 實作要點：
  1. `pbo.py`：先跑 Task 4.3 守衛（非 ok 即回）；`returns_matrix.shape!=(n_obs,n_candidates)` 或 `len(candidate_ids)!=n_candidates` ⇒ `ValueError`；含 NaN/inf 之欄 ⇒ invalid（`n_candidates_invalid`）；有效 <2 ⇒ `insufficient_candidates`。
  2. 每 path：`metric(col, idx)`＝`sharpe`→`compute_sharpe(col[idx], periods_per_year=1).value_per_period`（per-period；非有限 ⇒ 該候選該 path 剔除）／`mean_return`→`np.mean`；path 有效候選 `<2` ⇒ 跳過（`n_paths_skipped`）；champion＝IS metric 最大、平手取最小索引；OOS 對 path 有效候選算 metric，`rank = scipy.stats.rankdata(oos_metrics, method="average")[champion]`（升冪名次；名次越大＝OOS 越好），`r=rank/(N_valid_on_path+1)`，`ω=ln(r/(1-r))`，`ω<0`＝champion 落於中位以下。
  3. 全 path 跳過 ⇒ `all_paths_degenerate`；`value = mean(ω<0)` over used paths。
- 修改檔案：新增 `pbo.py::probability_of_backtest_overfitting`、`PBOResult`　既有 caller：無。
- 不可做：不自行重跑回測；不改 rank 分母為全域。
- 邊界：① 候選<2 ② NaN 候選 ③ 全候選相同 ④ T 不足 ⑤ 平手 ⑥ 轉置 ⑦ 某 path 全退化。
- 風險緩解：⊘
- 驗證：`test_pbo.py`＋golden `tests/momentum/Analysis/golden/gap1_reference_cases.json`（含 `sha256` 自檢與 `provenance`）：① 全噪音（seed=20260817,N=50,T=1200,S=12,σ=0.01）⇒ `0.40<=pbo<=0.60` ② 候選 0 加 `mu=0.01*1.0/sqrt(8760)`（測試內重算並斷言等於 golden 值 `atol=1e-18`）⇒ `pbo<0.30` ③ 轉置 raise、合法 T<N（`n_obs=50,n_candidates=1200` shape 相符）不 raise ④ 全平手 ⇒ `r==0.5`、`ω==0` ④b 雙冠 ⇒ 最小索引 ④c 5 vs 3 有效候選雙 path ⇒ 分母 6 與 4（同名次 ω 不同）⑤ 5 候選含 1 NaN ⇒ `n_candidates_invalid==1`、分母 4 ⑥ 有效 1 ⇒ `status!="ok"` 且 `isnan` ⑦ 常數切片 fixture ⇒ `n_path_exclusions>0`／`n_paths_skipped` ⑧ 全退化 ⇒ `all_paths_degenerate`。mutation §V-4 轉紅。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Task 4.3 — 候選宇宙污染防護（`票 GAP-1/C3`；R8 欄位逐字）
- SPEC ref：Task 4.3　目標：`UniverseProvenance` frozen dataclass；唯一成功路徑 `ledger_all_candidates`。
- 輸入 / 輸出：`UniverseProvenance(selection_free: bool, source: str, candidate_set_hash: str, candidate_count: int, declared_by: str)`（`__post_init__` 驗型別）；守衛函式 `check_universe_provenance(prov, candidate_ids, n_candidates, ledger_result) -> tuple[str,str]`（status, reason）。
- 實作要點：
  1. `pbo.py`（同檔）：`prov is None` ⇒ `ValueError`；`source` 不在契約 `universe_source_values` ⇒ `ValueError`；`selection_free is not True` ⇒ `universe_selection_contaminated`。
  2. `source in ("full_grid","external_declared")` ⇒ `universe_provenance_unverifiable`（無例外）。
  3. `source=="ledger_all_candidates"`：`ledger_result is None` ⇒ unverifiable；驗 `frozenset(candidate_ids)==ledger_result.candidate_ids` 且 `candidate_count==ledger_result.n_candidates_considered==n_candidates==len(candidate_ids)` 且 `candidate_set_hash==hashlib.sha256(",".join(sorted(candidate_ids)).encode()).hexdigest()`；三者皆符 ⇒ `("ok","")`。
- 修改檔案：`pbo.py::UniverseProvenance`、`check_universe_provenance`　既有 caller：Task 4.2。
- 不可做：不提供 `force`；不接受自備 hash 為證明。
- 邊界：① `selection_free=False` ② None ③ 未知 source ④ 同數量不同集合。
- 風險緩解：⊘
- 驗證：`test_pbo_universe_guard.py`：① `selection_free=False` ⇒ `status!="ok"`、`isnan(value)`、`reason=="universe_selection_contaminated"` ② 未知 source ⇒ raise ③ None ⇒ raise ④ `external_declared` ⇒ `universe_provenance_unverifiable` ④b `full_grid` 自洽仍 unverifiable ⑤ `ledger_all_candidates` 缺 `ledger_result`/`candidate_ids` ⇒ 同 ⑤b 50 選 top-10 自算 hash 正確 ⇒ 仍拒 ⑤b2 50 vs 50 但 1 id 不同 ⇒ 仍拒 ⑤c 三項全符 ⇒ `ok`。mutation §V-6 轉紅。
- **存活至**：全票完工後保留。
- **覆蓋風險**：無。

### Phase B4 測試 + Gate
- 單元：`test_cscv.py`／`test_pbo.py`／`test_pbo_universe_guard.py`；Golden：`gap1_reference_cases.json`；邊界：各 Task；效能：S=16 案例 wall-time 記錄於 receipt（不設硬門檻）。
- Gate：`pytest tests/momentum/Analysis/strategy_validation/ -q` rc=0；§V 13 條 mutation 全部貼 rc；`bash scripts/strategy_wiring_check.sh` rc=0；三家 code review CLOSED；registry「GAP-1 待補完」表逐項複核觸發條件未成立。

---

## 追溯表（SPEC → TODO；100% 覆蓋）

| SPEC 項 | 原文節錄（≤30 字） | TODO 位置 |
|---|---|---|
| Task 1.1 | 年化頻率解析（單一來源） | Task 1.1 |
| Task 1.2 | typed Sharpe（退化情形回 NaN＋status） | Task 1.2 |
| Task 1.3 | 既有回測路徑帶入年化來源（白名單三處） | Task 1.3 |
| Task 1.4 | canonical 報酬序列與 T 語意契約 | Task 1.4 |
| Task 2.1 | 策略驗證契約 JSON＋唯一 resolver | Task 2.1 |
| Task 2.2 | N 帳本讀取 API（今日無生產者） | Task 2.2 |
| Task 2.3 | 生產者一致性測試 | Task 2.3 |
| Task 2.4 | 策略層 wiring 閘門（R8 收回） | Task 2.4 |
| Task 3.1 | MinBTL 上界與試驗預算 | Task 3.1 |
| Task 3.2 | Deflated Sharpe Ratio（全式寫死） | Task 3.2 |
| Task 3.3 | 報告區段與降級展示契約 | Task 3.3 |
| Task 3.4 | ml_pipeline 回應附資格狀態＋警語 | Task 3.4 |
| Task 4.1 | CSCV 分割器（lazy＋資源守衛） | Task 4.1 |
| Task 4.2 | PBO 值（矩陣語意與 oracle 全寫死） | Task 4.2 |
| Task 4.3 | 候選宇宙污染防護（禁 top-K） | Task 4.3 |
| §G golden 三類 | 文獻／解析等式／統計性質 | Task 3.1 ①②③⑤、3.2 ①②、4.1 ①、4.2 ①②＋golden 檔 |
| §V mutation 1–13 | 13 條清單 | 各 Task 驗證欄「mutation §V-n」；B4 Gate 全部貼 rc |
| §V 反向測試 | 1h/4h/12h `available_years` 相等 | Task 3.1 驗證 ⑧ |
| §RISK a,b,d | 數值／跨模組／ML 回測 | §0 約束＋三家 review 必跑 |
| §N 殘留 8 項 | 為何現在不做三值 | 不生 Task；registry「GAP-1 待補完」表；B4 Gate 複核觸發 |
| Phase 依賴 | B1→B2→{B3,B4} | §B 表 |
| 合計 | SPEC Task 15／§G 3 類／§V 13＋1／§N 8 | TODO Task 15／全對應 |

## 階段 3 自檢（一輪）
1. 追溯：15/15 Task；§G／§V／§N 全對應；無真遺漏。
2. 深度：每 Task 實作要點 ≥3 含偽碼、檔案到函式名、邊界 ≥2、驗證有 atol／rc／字面斷言。
3. 語義：跨 Task 同檔＝`ledger.py`（2.2／2.3）與 `pbo.py`（4.2／4.3）皆同批無衝突；引用之既有函式（`TIMEFRAME_SECONDS`、`contract_enum`、`load_report_contract`、`MomentumConfig.results_path`、`create_ml_pipeline`）皆已 grep 確認存在；Task 1.3 改既有 caller 有測試同步；golden 由 Task 4.2 產出。
4. 全棧：Task 3.4 為唯一 API 層；前端不在本票（registry G1-R3）。
5. 錨點：`## §0`、`## §B`、每 Task 含「驗證」「邊界」「**存活至**」「**覆蓋風險**」「不可做」。

## 階段 4 handoff
`SPEC=docs/GAP1_STRATEGY_OVERFIT_SPEC.md TODO=docs/GAP1_STRATEGY_OVERFIT_TODO.md FOCUS=完整審查（含 SPEC R8 三項收回之 delta；§N 殘留逐條攻「為何現在不做」）`
