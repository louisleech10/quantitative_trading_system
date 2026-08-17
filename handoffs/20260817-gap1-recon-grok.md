# GAP-1 偵察 consult / grok | task-id=20260817-GAP1-X-CONSULT-R1

brief-kind=consult；家族=grok；輪次=R1；禁改碼；只產本檔。

## Verdict：可進 SPEC 起草（附 BLOCKING 清單須寫進 SPEC）

偵察足以讓 Claude 起草 SPEC，**但不得把種子檔「設計要點」當已裁決事實**。下列必須在 SPEC 正文具名處理，否則實作會產出裝飾性 DSR/PBO：

1. **N 無統一機器帳本**（assumed 已被碼證坐實）— 必須定義 fail-closed 的 N SoT + campaign 邊界；N 不可知時拒答／`unavailable`，禁人工手填當正式值。
2. **策略層報酬序列多源語意不一致** — 三件套入口契約必須鎖定「哪一條序列是 canonical」，其餘來源標 `not_applicable` 或拒接。
3. **`ic_report_contract.json` 不應直接當策略三關產物宿主**（語意錯位）；另立策略／優化報告契約或擴 `optimization` 產物 schema，capability status 枚舉可複用精神、不可 silently 塞進 IC 報告當 IC 結果。
4. **`combinatorial_purged_cv.py` 不可直接當 PBO-CSCV**（ML AUC path + purge/embargo；與 Bailey CSCV 的 S 塊 IS/OOS 組合語意不同）— 可借骨架，必須另寫或明確 adapter 契約。

**非 BLOCKING 但應入 SPEC 風險表**：`prediction_analyzer` 的 `np.cumsum` 權益誤用；年化 `periods_per_year` 跨模組不一致。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| # | 前提（來源） | 判定 | 證據摘要 |
|---|---|---|---|
| F1 | repo 無 DSR/PBO/CSCV/MinBTL 實作（brief fact-verified） | **fact 成立** | `grep -rn "deflated\|DSR\|PBO\|CSCV\|MinBTL\|min_btl" --include="*.py" momentum api` → 0 行、rc=0（本輪 2026-08-17 重跑） |
| F2 | CPCV 在 `model_validation/` 為 ML 孤島未接 IC/策略選擇（registry） | **fact 成立** | 模組存在且 `validate()` 走 `model.fit`+`roc_auc_score`；registry 明載 holdout-only |
| F3 | `api/routes/optimization.py` 有 `n_trials` 1–10000；Optuna 為搜尋器 | **fact 成立** | `:48` `n_trials`；task service 建 `OptunaOptimizer` + `sqlite:///data/optuna_{study_name}.db` |
| F4 | `prediction_analyzer.py:154-155` 用 `np.cumsum`（單利累加） | **fact 成立** | 實讀：`cum_strategy = np.cumsum(strategy_returns)` |
| A1 | 「嘗試次數 N」無機器化統一帳本（brief assumed） | **assumed → 本輪坐實為 fact** | 見 Q1 表與 `GROK-R1-P0-01` |
| A2 | 三件套只吃「報酬序列＋N」、可獨立新模組不改回測引擎 | **部分成立、有前置契約風險** | 引擎可不改，但**必須先鎖定序列來源**；多源語意不一致見 `GROK-R1-P0-02` |
| A3 | `ic_report_contract` 可擴 `report_sections` 承載三關 | **語意錯位（MAJOR）** | 契約 `_doc`＝IC report SoT；sections 皆 IC 子分析；`ic_wiring_check` 只盯 IC 五節 |
| A4 | MinBTL→PBO→DSR 產品順序正確 | **成立（產品層）**；計算上三關可並行實作 | 資格→選法→冠軍與 Bailey 用途一致；無碼證支持必須改序 |
| S1 | 種子：N 候選＝ML 呼叫／參數掃描／strategy_registry 快取鍵 | **候選偏窄** | registry 是策略**目錄**（YAML 3 支），不是 attempt ledger；真正計數面見 Q1 |

---

## GROK-R1-P0-01

**斷言**: 平台上不存在可 fail-closed 讀取的「策略嘗試次數 N」單一帳本；現有計數面零散且可被繞過，若 SPEC 假設「N=Optuna n_trials」則 DSR/PBO 會系統性低估 multiplicity。

**碼證**: VERIFY `grep -rn "deflated|DSR|PBO|CSCV|MinBTL|min_btl" --include="*.py" momentum api | wc -l` → 0；N 只見請求面/Optuna/記憶體 task/結果摘要，無統一 ledger。
- Optuna 請求面：`api/routes/optimization.py:48` `n_trials: int = Field(100, ..., ge=1, le=10000)`；寫入 `OptimizationTaskInfo.config['n_trials']`（`api/services/optimization_task_service.py:238`）與 `progress.total_trials = n_trials`（`:246`）——此為**請求目標**，不是已評估 attempt 總帳。
- 持久化：`storage=f"sqlite:///data/optuna_{study_name}.db"`（`:251`）+ `load_if_exists=True`（`optuna_optimizer.py:724/737/751`）；`initial_trials = len(self.study.trials)` 後再跑「`n_trials` **new** trials」（`:2376-2379`）。同名 study 續跑會**累積** trials，但 progress 仍以本次 `n_trials` 為 total → UI/摘要可與 SQLite 真實 `len(study.trials)` 脫節。
- 結果 JSON：`_save_result` 只寫 `best_*` + 單一 `n_trials` 欄（`:655-666`），**無** per-trial 完整 ledger 於該檔；完整 trials 靠 `OptimizationOutputService` 的 `trials.csv`（若有呼叫 `generate_outputs`）。
- 任務表：`OptimizationTaskService.tasks` 為**行程內記憶體** dict（`:156`），重啟即失；跨 task_id 無聚合。
- 前端可重複送單：`ExecutionConfigForm`/`HyperparamConfigForm` 每次 submit 新任務，`n_trials` 滑桿 max=**1000**（UI）vs API max=**10000**；無 campaign 級去重。
- 直接引擎路徑：`momentum/factories.py:create_optuna_optimizer` + `VectorizedBacktest.run_backtest` 可在無 API task 下記錄下被呼叫 → **漏記**。
- IC 層 `n_tests`（`statistical_validator.apply_fdr` 回傳 finite p 個數）是**因子多重比較 m**，語意≠策略 N，不得當 N SoT。
- `config/strategies.yaml` 僅 **3** 個策略 ID（`three_line`/`short_long_cross`/`mid_long_cross`）＝目錄大小，非嘗試次數。
RECHECK: 重跑上列 grep；讀 `optimization_task_service.create_task` + `optuna_optimizer.create_study` + 一次 `len(study.trials)` vs `config.n_trials` 對照。

**來源摘要**: api/services/optimization_task_service.py#0d6d02e08bbd

[BLOCKING] 信心度=High。SPEC 必須定義：**N 的 campaign 邊界**、**計數規則**（至少含 COMPLETE+PRUNED+有評估 metric 的 FAIL；是否含 pure sampling 未評估）、**SoT 讀取 API**、以及 **N unknown → 拒答/unavailable（禁手填正式 DSR）**。建議 SoT＝「每個 selection campaign 的 append-only attempt ledger」（可由 Optuna study 匯出 seed，但 ledger 須獨立、跨 UI 重送可關聯 `campaign_id`）。

---

## GROK-R1-P0-02

**斷言**: 策略層「報酬序列」在多個產出點語意不一致（複利權益 vs 累加假權益 vs 單期報酬；有成本 vs 無成本；年化慣例不同）；若三件套入口未鎖定 canonical 源，DSR/PBO 數值不可比且可被選錯源美化。

**碼證**: 五源對照——vectorized=`cumprod`+成本；prediction=`np.cumsum`無成本；factor=`cumprod-1`；long_short/expectancy=未年化 mean/std。
| 產出點 | 序列怎麼來 | 單位/複合 | 成本 | Sharpe 慣例 |
|---|---|---|---|---|
| `vectorized_backtest._calculate_equity_curve` `:314-339` | 出場 bar 記入 `pnl_pct`，`equity = cumprod(1+returns)` | 比例、複利權益曲線從 1.0 | **有**：`(commission+slippage)*2` 扣在 `trade_pnl_pct`（`:246-248`） | 下游 `PerformanceMetrics` 對 equity `pct_change` 後年化，`periods_per_year` **預設 730**，`rf=0.02`，`std ddof=0`（`performance_metrics.py:20,77-86`） |
| `prediction_analyzer.calculate_strategy_equity_curve` `:152-163` | `strategy_returns = actual_returns * positions`；欄位 `strategy_returns` 實際寫入 **`np.cumsum(...)`** | 累加（單利），**非** cumprod；欄名誤導 | **無**成本/滑價 | 本函式不計算 Sharpe |
| `factor_return_analyzer` `:133-148,175-270` | `ls_return = position * returns`；累積 `(1+r).cumprod()-1` | 比例、複利 | 無顯式 commission | `periods_per_year` **推斷或 365**；`rf` 預設 0；`std ddof=1` |
| `long_short_analyzer._compute_side_metrics` `:218-220` | side 報酬 mean/std | 無年化 | 無 | `sharpe = mean/std`（**非**年化） |
| `expectancy_calculator.calculate_sharpe_proxy` `:110-125` | trade returns mean/std | 無年化 | 視輸入 | `mean/std` proxy |
RECHECK: 對同一 `predicted_proba`+prices 分別跑 vectorized 與 prediction_analyzer，比對最終權益與期間報酬定義。

**來源摘要**: momentum/Strategy/vectorized_backtest.py#ddfa9b52ade8

[BLOCKING] 信心度=High。SPEC 入口契約建議：**canonical = strategy_backtest 路徑的 period returns（由 equity.pct_change 或 trade 記帳還原的 bar returns，已扣成本）**；`prediction_analyzer` 累加曲線**不得**進 DSR/PBO 直到修復。`periods_per_year` 必須由 timeframe 推導並寫入 artifact metadata，禁 silent 730。

---

## GROK-R1-P1-01

**斷言**: `PerformanceMetrics.sharpe_ratio()` 預設 `periods_per_year=730` 與 `FactorReturnAnalyzer` 的推斷／365 預設不相容；直接把該函式輸出當 Bailey DSR 的觀測年化夏普，會在錯誤年化假設下扭曲 deflation。

**碼證**: `performance_metrics.py:20` 預設 periods_per_year=730；`factor_return_analyzer.py:195` 預設/推斷 365；strategy_backtest evaluate 未覆寫 → 冠軍 Sharpe 默認 730。
- `performance_metrics.py:20` 預設 `730`；`:85-86` `excess/std * sqrt(periods_per_year)`。
- `factor_return_analyzer.py:195` `periods = int(periods_per_year or 365)`；`:386-394` 由 DatetimeIndex median delta 推導 `(24*365)/hours`。
- Bailey DSR 需要一致的 SR、V[SR]（偏度/峰度/樣本長 T）與 trials N；**年化倍數進 SR 後必須與 T 的時間單位一致**。
- `StrategyBacktestObjective.evaluate`（`objectives/strategy_backtest.py:112-117`）用 `PerformanceMetrics(...).calculate_all()` **未傳** `periods_per_year` → 策略優化冠軍 Sharpe **默認 730**。
RECHECK: 對 1h bar 序列手算 `sqrt(8760)` vs `sqrt(730)` 倍率差（約 3.46×）。

**來源摘要**: momentum/Strategy/performance_metrics.py#60154cf6f758

[MAJOR] 信心度=High。SPEC 應規定：DSR 輸入優先用**非年化** period Sharpe + 明確 `n_obs`/`freq`，或年化時 **強制** 與 bar 頻率綁定的 `periods_per_year`（寫入 report metadata）；禁止依賴 730 預設。

---

## GROK-R1-P1-02

**斷言**: 既有 `CombinatorialPurgedCV` 不能直接充當 PBO 的 CSCV 分割器； purging/embargo 與 model-path AUC 目標與 Bailey/CSCV（S 塊組合 → IS 冠軍 logit rank vs OOS）語意不同。

**碼證**: `combinatorial_purged_cv.py` 的 `validate()` 走 model.fit+roc_auc（:84-116），非策略報酬矩陣上的 Bailey CSCV IS/OOS 排名。
- `combinatorial_purged_cv.py:18-25`：`n_groups`/`n_test_groups`/`purge_gap`/`embargo_pct`/`max_paths`；`split()` 產 train/test **索引**並 `_apply_purge_embargo`（`:73`）。
- `validate()`（`:84-116`）對每 path **fit model** 並算 **roc_auc_score**，不是對一組策略回測報酬做 IS 選冠→OOS 相對排序。
- Bailey PBO/CSCV：把 T 觀測切 S 塊，取 C(S,S/2) 種組合，每種把一半當 IS 選最佳策略、另一半 OOS，統計 OOS 排名掉出中位的比例；**輸入是策略×時間的報酬矩陣**，不是特徵矩陣 X 上的 classifier。
- 可複用的只有「組邊界 + combinations 枚舉」骨架；purge/embargo 對標的 label 重疊有意義，對**已實現策略報酬序列**的 CSCV 通常**不直接套同一 purge 語意**（除非標的是 overlapping forward returns 且要防洩漏——那是另一層）。
RECHECK: 對照 López de Prado《Advances in Financial Machine Learning》CSCV 章與本檔 `validate()` 回傳鍵。

**來源摘要**: momentum/Analysis/model_validation/combinatorial_purged_cv.py#08ac8896b686

[MAJOR] 信心度=High。落點建議：新模組 `momentum/Analysis/strategy_selection_validation/`（或 `momentum/Strategy/selection_gates/`）實作 `min_btl` / `pbo_cscv` / `deflated_sharpe`；CPCV 保持 ML 孤島，本票**不要**把 registry #2（IC↔ML 橋）塞進來。

---

## GROK-R1-P1-03

**斷言**: 把三關結果塞進 `ic_report_contract.json` 的 `report_sections` 會造成「IC 報告 vs 策略選擇報告」產物語意錯位；且 `ic_wiring_check` **不會**自動盯到策略三關。

**碼證**: `ic_report_contract.json` `_doc` 自承 IC report SoT；`ic_wiring_check.py` `REPORT_SECTIONS` 僅五個 IC 節，無策略閘。
- 契約 `_doc`（`ic_report_contract.json:1`）：「IC report 契約單一真相源」；`report_sections` 鍵＝`quantile_returns`/`ic_decay`/`grouped_ic`/`turnover_analysis`/`coverage_analysis`/`net_ic_analysis`——皆 IC 子分析。
- `capability_status` 枚舉（`:4-10`）可複用精神（`ok`/`unavailable`/…），但宿主不應是 IC report。
- `scripts/ic_wiring_check.py` 檔頭：`REPORT_SECTIONS = (ic_decay, quantile_returns, grouped_ic, turnover_analysis, coverage_analysis)`——封閉集合；策略三關不在掃描範圍。
- 優化產物既有宿主：`optimization_results/<task_type>/<task_id>/summary.json` + `trials.csv` + html（`optimization_output_service.py:26-71`）更貼近策略選擇敘事。
RECHECK: 讀契約 `_doc` 與 wiring `REPORT_SECTIONS` 常數是否仍無 strategy gate 鍵。

**來源摘要**: momentum/Analysis/contracts/ic_report_contract.json#6937da262f34

[MAJOR] 信心度=High。建議：新契約檔（例 `strategy_selection_report_contract.json`）或擴 optimization summary schema；status 模型沿用 capability 枚舉；前端若做開關再**另**擴 wiring／或新建 strategy wiring 閘——不可假設 `ic_wiring_check` 會自動保護。

---

## GROK-R1-P1-04

**斷言**: 即使單次 Optuna study 的 `len(study.trials)` 可讀，仍不足以當「研究結論級 N」：同 window 多次重送、手動掃參、signal_density 與 strategy_backtest 混用、PRUNED trial 是否計入等未定義，會讓 MinBTL/DSR 結論可被協議性低估 N 而通過。

**碼證**: 前端每次新 task_id、無 campaign_id；pruning 預設 ON；三 task_type 共用 Optuna 殼卻無跨 type N 定義。
- 前端每次提交新 `task_id`（見 optimization pages）；無強制 `campaign_id`。
- `StrategyBacktestObjective` 搜尋空間約 9 維連續/離散（`create_search_space` `:86-101`）——每次 trial 是一次策略參數假設。
- Pruner：`enable_pruning` 預設 True（route `:52`）；`TrialPruned` 在 optimizer 多處 raise——Optuna 仍保留 PRUNED trial 物件，但若實作只數 `COMPLETE` 會低估 N。
- signal_density / model_hyperparam / strategy_backtest 三 `task_type` 共用 Optuna 殼（task service `:264-272`），**N 語意是否跨 type 加總**無定義。
RECHECK: 對含 PRUNED 的 study 比較 `len(trials)` vs `len([t for t in trials if t.state==COMPLETE])`。

**來源摘要**: api/routes/optimization.py#93008df279ae

[MAJOR] 信心度=High。SPEC 計數規則表必須顯式；預設保守（**多算 N**）優於樂觀。

---

## GROK-R1-P2-01

**斷言**: `prediction_analyzer.py` 的 `np.cumsum` 權益是真實缺陷（單利累加、欄名假裝 period returns 的累積），但是否構成本票**前置阻塞**取決於 canonical 輸入是否走該路徑；對 `strategy_backtest`→`vectorized_backtest` 主路徑為可並行修復，非全域 BLOCKING。

**碼證**: `:155-163` `cum_strategy = np.cumsum(strategy_returns)` 後寫入 `EquityCurveData.strategy_returns`；對照 vectorized `:338` `np.cumprod(1.0+returns)`。種子檔與 ROADMAP 記為「cumsum 問題」——本輪確認仍在。
RECHECK: `grep -n "np.cumsum" momentum/Analysis/prediction_analyzer.py`。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#472c48fe06b6

[MINOR] 信心度=High。建議：獨立小票修 cumsum→cumprod（或改欄名為 cumulative_simple_sum 並停用策略敘事）；GAP-1 SPEC 標「若接 prediction 路徑則升級為 BLOCKING 前置」。

---

## GROK-R1-P2-02

**斷言**: 既有 UI「overfitting_score / OverfittingCheckChart」不是 DSR/PBO/MinBTL，SPEC 與產品文案不得暗示平台已有策略層 Bailey 三關。

**碼證**: frontend `OverfittingCheckChart` + `overfitting_alert` WS 事件；pattern `overfitting_score`；IC heatmap `overfitting_risk`——皆非 DSR/PBO 字樣。Python 側 DSR/PBO 字串 0 命中。
RECHECK: `grep -rn "DSR\|PBO\|MinBTL\|deflated" frontend/src` 與 py grep。

**來源摘要**: handoffs/20260817-gap1-recon-BRIEF.md#926aefb422e8

[MINOR] 信心度=High。產品命名需區隔，避免使用者把既有 overfitting_score 誤讀為 PBO。

---

## 必答 1–7（逐條 verdict）

### 1. N 帳本盤點（優先）

| 計數面 | 位置 | 已持久化？ | 機器可讀？ | 可繞過／漏記 |
|---|---|---|---|---|
| Optuna `n_trials`（請求） | `api/routes/optimization.py:48`；task `config.n_trials` | 部分（config 在記憶體；結果 JSON 有摘要） | 是 | 重啟丟 task；≠實際評估數 |
| Optuna study.trials | `data/optuna_{study_name}.db` via `load_if_exists` | 是（SQLite） | 是 | 換 study_name 切割帳本；factories 直呼 |
| Progress completed/total | task service progress | 記憶體 | 是 | total=請求值；與累積 trials 脫節 |
| trials.csv / summary | `optimization_output_service` → `optimization_results/...` | 是（若 generate） | 是 | 未呼叫則無 |
| Checkpoint trial 編號 | `checkpoint_manager.py` | 是（間隔） | 部分 | 非完整 ledger |
| 前端重複送單 | Execution/Hyperparam forms | 每 task 一份 | 每 task 是 | **跨 task 無聚合** |
| UI max 1000 vs API 10000 | forms max=1000；API le=10000 | — | — | API/腳本可超過 UI |
| XGBoost batch/task | `xgboost_*_service` | 任務狀態 | 是 | 多為訓練任務；策略 N 語意弱；xgb 頁可另開 optuna `n_trials` |
| IC `n_tests` / selected features | FDR / `ic_selected_features_*.json` | 是 | 是 | **因子 m，非策略 N** |
| strategy_registry 目錄 | YAML 3 strategies | 配置 | 是 | **不是 attempt** |
| 直接 `run_backtest` / notebook | `VectorizedBacktest` | 否 | 否 | **完全盲區** |

**N SoT 設計建議（fail-closed）**:
1. 引入 `selection_campaign_id`（人為研究結論的邊界：同 symbol/TF/window/objective 族／標的 metric）。
2. Append-only `attempt_ledger`：每 attempt 記 `{campaign_id, params_hash, metric_name, metric_value, state, ts, source_task_id, study_name, trial_number}`。
3. **N_official = count(ledger rows in campaign that entered ranking universe)**；預設含 PRUNED（看過資料/半評估者保守計入——SPEC 需鎖死定義）。
4. DSR/PBO/MinBTL API：只接受 `campaign_id` → 機器讀 N；若 ledger 缺失或 `N < 1` → `status=unavailable`，**拒出正式通過標籤**。
5. 允許 `N_source=declared_unknown` 的研究草稿模式，但 UI **禁止**「通過／可上線」文案。
6. 禁止使用者覆寫 N 而不留 audit（若允許敏感性分析，結果必須 watermark `N_assumed_not_ledgered`）。

### 2. 報酬序列輸入契約

- **誰產（策略主路徑）**：`VectorizedBacktest.run_backtest` → equity + trades → `PerformanceMetrics`；Optuna `StrategyBacktestObjective.evaluate` 再算一次 metrics。
- **頻率**：與 prices bar 頻率相同（index 對齊）；非固定日頻。
- **單位**：`pnl_pct`／returns 為**比例**（0.01=1%），非百分點、非對數。
- **成本**：vectorized 路徑**已扣**雙邊 commission+slippage；prediction/factor 路徑通常**無**交易成本。
- **NaN/空態**：PerformanceMetrics 對 equity dropna；空 returns → Sharpe 0.0（**注意：0.0 與 NaN 語意不同，可能美化缺資料**）；factor_return 偏好 NaN。
- **cumsum 問題**：對 prediction 路徑是缺陷；對 canonical strategy_backtest **非**本票前置 BLOCKING，但 SPEC 必須禁止該路徑進三關，或列並行修復。

### 3. 落點與複用

| 項 | 建議 |
|---|---|
| 模組路徑 | `momentum/Analysis/strategy_selection_validation/`（`min_btl.py` / `pbo_cscv.py` / `deflated_sharpe.py` + `n_ledger.py` 協議）+ `factories.create_*` |
| 呼叫點 | `StrategyBacktestObjective` 結束後／`OptimizationOutputService.generate_outputs` 組裝；可選 API 查詢 campaign 閘門 |
| CPCV 複用 | **不可直接**；可抽 shared `block_boundaries()`；PBO 另寫 CSCV over strategy return matrix |
| `sharpe_ratio()` | 可作觀測 SR **僅當** periods_per_year/rf/ddof 與 DSR 假設一致；否則在新模組內自算 period SR |

### 4. 產出契約與可見性

- 宿主：optimization `summary.json` 新 section `selection_gates: {min_btl, pbo, dsr}`，每關 `{status, reason, value, inputs:{N,T,...}}`。
- status：複用 capability 精神：`ok` / `unavailable`（N 或序列不足）/ `failed` / `not_computed`；**不合格 ≠ degraded 可上線**。
- `ic_wiring_check`：**不會**自動盯；要前端閘門需新 check 或擴允許清單——本票若做 UI，須在 TODO 單列。
- **MinBTL 未達**：API 層拒絕 `publishable=true`／冠軍「可部署」旗標；前端禁用匯出「通過」報告與一鍵套用 best_params；僅顯示阻塞原因與所需最短 T。不可只做黃標。

### 5. 測試策略（禁自造 golden 當唯一 oracle）

**第三方／文獻對照（公式正確性）**:
| 公式 | 可驗來源 | 期望形態 |
|---|---|---|
| DSR | Bailey & López de Prado 2014 論文數值例；mlfinlab `deflated_sharpe_ratio`（若 pin 版本）對同一 (SR, SR0, skew, kurt, T, N) | 機率 p 在文獻容差內（TOLERANCE） |
| PSR（DSR 特例 N=1） | 同上解析 | EXACT/TOL |
| PBO/CSCV | 2015 PBO 論文示意；公開 reference 實作對固定 synthetic strategy matrix | PBO∈[0,1]；全策略 OOS 同序時 PBO→0；純噪音冠軍 PBO 偏高（STATISTICAL 形狀） |
| MinBTL | Bailey et al. MinBTL 公式對已知 N、目標 SR | 整數長度 EXACT 或 round 規則釘死 |

**對照 TEST_DESIGN_CHARTER**:
- 必做：A3 數值、A4/§F **F-ST-2 DSR**、**F-ST-3 PBO/CSCV**、A6 邊界（N=1、T 過短、全零 returns、NaN）、A11 解耦、B1 mutation probe。
- **改壞必紅（mutation）**：
  1. 實作把 N 固定成 1 → 高 N 案例 DSR 門檻應變嚴卻變鬆 → FAIL。
  2. 打亂 OOS 標籤／對調 IS/OOS → PBO 失去單調關係 → FAIL。
  3. MinBTL 比較改成 `>` 變 `>=` 或 T 用錯年化 → 邊界案例 FAIL。
  4. 餵 prediction cumsum 曲線卻標 period returns → 與 vectorized oracle 分歧 → FAIL（契約測試）。
- 禁：只用隨機種子自造「看起來合理」的 PBO 當唯一 golden；禁合成 kline 充策略正確性（可用**合成報酬矩陣**測公式，標 FAITHFUL|SYNTHETIC）。

### 6. scope 建議

| 期 | 內容 | 防護價值 |
|---|---|---|
| **P0（本票最小可上線）** | N ledger 契約 + 從 Optuna study 匯入 + **MinBTL + DSR** 掛 strategy_backtest 完成路徑；fail-closed unavailable | MinBTL 擋「N 太大／歷史太短」；DSR 擋「冠軍夏普被 multiplicity 吹起」——**單關 DSR 在無誠實 N 時無意義，故 N 與 DSR 同批** |
| **P1** | **PBO/CSCV**（需策略×時間報酬矩陣；trial 級 returns 持久化） | 評估**選法**穩定；算力與存儲顯著較大 |
| **可切** | prediction_analyzer cumsum 修復；IC 契約擴；CPCV 接 IC | **不要**併入本票主線 |
| **一次做完？** | 公式可同模組骨架一次設計；**交付可分兩批**：P0=N+MinBTL+DSR，P1=PBO | 無 N 的任何關都是裝飾 |

### 7. 是否足以進 SPEC？BLOCKING 清單

**足以進 SPEC 起草**。BLOCKING 須寫進 SPEC §RISK/§A（非「之後再說」）：

1. N SoT + campaign + unknown 拒答（`GROK-R1-P0-01`/`P1-04`）
2. 報酬序列 canonical 契約 + 禁混源（`GROK-R1-P0-02`）
3. 策略報告宿主 ≠ 默認 IC report（`GROK-R1-P1-03`）
4. PBO 不直接複用 CPCV validate()（`GROK-R1-P1-02`）
5. 年化／`periods_per_year` 顯式化（`GROK-R1-P1-01`）

**非 BLOCKING**：cumsum 修復（限非 canonical 路徑時）；既有 overfitting_score 文案區隔。

---

## §1 必查 11 類（偵察語境）

1. 矛盾/互斥：種子「可擴 IC 契約」vs 契約實為 IC-only → 見 P1-03。
2. 漏項：N ledger、trial-level returns 持久化（PBO 要）、UI hard-block、年化 metadata。
3. 不可測：若 SPEC 不鎖第三方 oracle 版本/文獻表，DSR 會變不可驗。
4. 可疑 quant：730 年化、cumsum 權益、PRUNED 不計 N、0.0 Sharpe 填空。
5. 過度工程：勿為此建分散式 queue；ledger + 三純函式即可。
6. OOM：PBO 組合數 C(S,S/2)×策略數 — 需 cap S 與策略子集（對齊 CPCV max_paths 思維）。
7. Cache：campaign_id / params_hash 必須入 key；禁跨 symbol。
8. API：optimization 回應加 `selection_gates`；向後相容預設 `not_computed`。
9. 測試：見 Q5；mutation 必做。
10. Agent 可執行：SPEC Task 須寫到檔案+函式+驗收命令。
11. 短命工：若先 hack 讀 `n_trials` 請求值再換 ledger，前期 adapter 須標存活至 P0 ledger 完工。

---

## 未查清單（time-box，不當阻塞）

- Optuna SQLite 在本機 `data/` 是否有真實歷史 study 可抽樣（目錄狀態未深挖）。
- `signal_density` objective 的 metric 是否應納入同一 campaign 的 N（產品決策）。
- mlfinlab 是否已在 venv 依賴中（第三方 oracle 需 pin 或 vendor 公式單測）。
- 前端 optimization 結果頁 hard-block 的具體元件樹（只確認現有 overfitting UI 非三關）。
- White Reality Check / SPA（charter F-ST 提及）— 明確**不在**本票三件套。

---

## 產出與清理

- 本檔：`handoffs/20260817-gap1-recon-grok.md`
- 禁改碼、禁寫測試：遵守
- `/tmp` workdir：本輪未建立獨立 cx workdir；保留 `/tmp/claude-501`；未刪除他人檔

STATUS: DONE
