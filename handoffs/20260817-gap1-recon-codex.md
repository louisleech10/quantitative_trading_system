# GAP-1 偵察 — DSR/PBO/MinBTL 策略層防過擬合 — codex R1

**task-id**: `20260817-GAP1-X-CONSULT-R1` | **family**: CODEX | **brief**: `handoffs/20260817-gap1-recon-BRIEF.md`  
**scope**: read-only consult；本輪未改程式、測試、`data_cache/` 或根 `HANDOFF.md`。

## Verdict

可進 SPEC 起草，但不能直接進三件套實作。SPEC 必須先收斂三個 BLOCKING：
(1) 研究邊界內的 N ledger 與 unknown/fail-closed 語意；(2) 唯一 canonical reward-series contract；
(3) PBO 所需的 candidate-by-time return matrix。否則 DSR/PBO 只能產生看似精確、但不可稽核的數字。

## §0 前提核對

| brief 前提 | 本輪判定 | 證據 |
|---|---|---|
| repo 已有 DSR/PBO/CSCV/MinBTL 實作 | **未確認；目前沒有命中** | `rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' --glob '*.json' 'DSR|PBO|CSCV|MinBTL|Minimum Backtest' momentum api frontend scripts` → 無輸出，`rg_rc=1`。這是檢索結果，不是功能測試。 |
| N 有統一 machine-readable SoT | **推翻** | Optuna、checkpoint、記憶體 task、IC factor count、XGBoost case count 各自存在；沒有跨域、run-scoped、append-only ledger。 |
| 三件套只需一條 reward series + N | **推翻一半** | DSR 可吃單條 canonical series；PBO 還需要同一資料窗中多個候選的績效矩陣。現有輸出只保留標量 trial metadata 與 champion equity curve。 |
| `ic_report_contract.json` 可直接加 strategy sections | **不成立** | 該契約 sections 是 IC 子分析；`scripts/ic_wiring_check.sh` 本輪 `rc=0` 只代表既有 IC wiring 綠，不代表策略三關已接線。 |
| MinBTL→PBO→DSR 是必然數學順序 | **只能作產品相依順序** | MinBTL 是資格 gate；PBO 與 DSR 可共享凍結 ledger 後並行計算。SPEC 需定義 UI/eligibility 的順序，不能把 seed 候選當定理。 |

## 必答 1：N ledger 盤點與 fail-closed 建議

| 計數面 | 位置／目前語意 | 持久化與機器可讀 | 漏記、重複或可繞過 |
|---|---|---|---|
| Optuna request N | `api/routes/optimization.py:37-53,121-135`；`n_trials` 是請求目標 | task config 與 progress 可讀 | 不是實際 candidate/evaluation 數；`n_trials` 另在 `optimization_analysis.py:583-604` 被用作 case 數，名稱已語意衝突。 |
| Optuna trials | `momentum/Optimization/optuna_optimizer.py:681-759,2374-2381,2460-2512`；SQLite study 可讀 | `sqlite:///data/optuna_{study_name}.db`；`load_if_exists=True` | 同名 study 包含歷史 rows；換 study name 就換邊界。retry 在同一 trial 內重試 `:780-817`；duplicate prune、backfill `:2530-2582` 使 configured N、complete N、all rows、unique params 不相等。 |
| Checkpoint | `momentum/Optimization/checkpoint_manager.py:83-167` | pickle snapshot，可讀 | 不是 append-only event ledger；同時保存 configured `n_trials` 與 `len(study.trials)`，無穩定 candidate identity、research session 或事件 provenance，且舊 snapshot 會被保留數限制清理。 |
| Task/result store | `api/services/optimization_task_service.py:155-165,644-666,790-838` | task registry 在記憶體；成功 result JSON 有 `n_trials` | registry 只保留最近 100 個完成 task；result 的欄位無 state-by-candidate、attempt、dataset hash 或 N policy。失敗／取消流程也不等於有可查 ledger。 |
| XGBoost batch/single | `api/services/xgboost_batch_service.py:221-328`；`api/services/xgboost_task_service.py:129-224` | task manager 主要在記憶體 | batch 的 `total_cases` 是 cases，不是策略 candidate N；single task 是一次 model run，沒有策略 trial ledger。不可誤映射成 DSR N。 |
| IC factor selection | `momentum/Analysis/long_short_analyzer.py:168-189`；`momentum/Analysis/factor_return_analyzer.py:272-315` | results/config 可讀但非策略 attempt ledger | `top_n`／selected features 是因子篩選層級；不得和策略參數搜尋 N 混算，也不得用 IC FDR 的 n-tests 代替。 |
| frontend duplicate sends | `frontend/src/app/strategy-test/page.tsx:461-499,1085-1102`；`frontend/src/hooks/useOptimization.ts:78-110` | 無 server idempotency ledger | UI disabled 是本地狀態；無 idempotency key／server dedup。重試、另一 tab、直接 API 仍可能建立另一 task；此處是可繞過風險，非本輪實際發送。 |

**N SoT 建議**：先定義 `research_session_id`／`dataset_key`／`candidate_id`（canonical params hash）／`evaluation_id`／`attempt_index`／state／metric-validity／input-artifact hash／timestamp。ledger 要把 candidate identity 與 execution attempts 分開，並分列 `n_candidates_considered`、`n_evaluated`、`n_valid_metrics`、`n_failed_or_pruned`；不可把其中一個未定義的數直接命名為 N。DSR/PBO 缺 ledger、session boundary、dataset identity 或 candidate matrix 時回 `unavailable`／`n_unknown`，不以 1、request `n_trials` 或完成數猜測。人工研究迭代若未記錄，只能把 observed N 明示為 lower bound，不能宣稱是真實總 N。

## 必答 2：reward-series contract

| producer | 實際語意 | 頻率／成本／缺值問題 |
|---|---|---|
| `momentum/Strategy/vectorized_backtest.py:314-339` | trade exit bar 的 `pnl_pct` 加到 bar return，`np.cumprod(1.0 + returns)` 形成 equity | 與 prices 同頻但其餘 bar 是結構性 0；交易成本／滑價在 engine trade PnL 內處理（`vectorized_backtest.py:41-47,246-249`）；input 沒有完整 NaN/inf gate。 |
| `momentum/Analysis/prediction_analyzer.py:136-170` | `actual_returns * position` 後 `np.cumsum`；欄位名叫 `strategy_returns` 卻裝 cumulative path | 無成本／滑價／frequency contract；API `api/routes/pattern_analysis.py:1047-1051` 先把 NaN actual return 填 0。不能直接作 DSR 的 period returns。 |
| `momentum/Analysis/factor_return_analyzer.py:48-63,78-147,175-270` | PIT position × future return；`(1+r).cumprod()-1`，另有自己的 periods 推斷 | identity raw returns、turnover semantics 與 vectorized trade settlement 不同；risk metrics 是另一路徑（sample std、periods 預設／推斷亦不同）。 |
| `momentum/Strategy/performance_metrics.py:19-36,77-86` | 對 equity 做 `pct_change()`；空／無波動回傳 `0.0` | 預設 `periods_per_year=730`、`ddof=0`；0.0 混淆「真 SR=0」與「不可計算」。`strategy_backtest.py:112-121` 未傳 frequency。 |

結論：三套序列不能互換。P0 路徑應明定唯一 canonical source（建議由同一 strategy backtest engine 輸出 period-return vector，並同時保留 unit、frequency、cost/slippage、NaN policy、warmup、empty semantics）；`prediction_analyzer` 的 cumsum 路徑要明確隔離或另票修復。所有 invalid/empty/zero-variance 情形在三關內應是 typed unavailable/invalid，而不是正常數字 0。

## 必答 3：落點、CPCV/CSCV、Sharpe 相容性

建議新增 `momentum/Analysis/strategy_validation/`（或等價 strategy-validation domain），由 factory 暴露純統計元件；不要把策略選擇統計塞到 IC 或 ML-only `model_validation`。`momentum/Analysis/model_validation/combinatorial_purged_cv.py:41-82` 只產 X/y 的 train/test indices；`validate():84-165` 每 path fit model 並輸出 AUC／feature stability。它沒有 strategy-by-block return matrix、IS winner、OOS rank/logit，因此**不可直接當 PBO CSCV**；最多複用經審查後的 group/purge/embargo primitive。

現有 `PerformanceMetrics.sharpe_ratio()` 只有在 SPEC 鎖定 period frequency、risk-free、ddof、T semantics 且處理 empty/constant series 後才可當 observed SR；不能把 730 與 factor analyzer 的另一套 periods 視為共用真相。PBO 的核心輸入不是 champion 一條曲線，而是同一 dataset/session 的完整 candidate×time（或 candidate×block）returns，含 frozen candidate universe 與 selection rule。

## 必答 4：output/status、wiring 與 UI hard block

目前 `momentum/Analysis/contracts/ic_report_contract.json` 只有 IC sections/status；`frontend/src/lib/types.ts:2036-2048,2123-2165` 也只有 IC report。`api/services/optimization_output_service.py:150-174,177-213` 沒有三關 section，`_decide_recommended_action():502-522` 只看 expectancy、Sharpe 與 constraints。`api/routes/ml_pipeline.py:124-245` 可依 study/trial 建 pipeline，未要求 DSR/PBO/MinBTL eligibility；這是 server-side hard block 缺口。前端頁面 disabled submit 不能取代 API gate。

建議另立 strategy validation contract，或在 optimization result 建平行且有版本的 section；不要把策略 verdict 偽裝成 IC section。契約須明確區分 `available`（若新增此 vocabulary）、`unavailable`、`degraded`／`computation_failed`、`not_computed`，且 current ICHC enum 實際只有 `ok/not_applicable/not_computed/computation_failed/disabled/unavailable`，沒有 literal `available` 或 `degraded`，不能 silent coerce。只有全部 required gates available 且 eligible 才能 enable pipeline/promote；unknown、degraded、failed、not-computed 都要 API 拒絕 promotion，UI 顯示原因、inputs、data window、N/T，不只加警語。

## 必答 5：第三方對照與 TEST_DESIGN_CHARTER 映射

原始文獻（本輪以作者／SSRN 版本為準）：

- Bailey & López de Prado, [The Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)：DSR 處理多重測試 selection bias 與非正態；輸入需觀測 SR、樣本 T、分布形狀與 trials policy。
- Bailey et al., [The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253)：PBO 以 CSCV 對候選策略集合做 IS/OOS 選擇穩定性；不能用單一 champion 序列替代。
- Bailey et al., [Mathematical Appendices to The Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2568435_code434076.pdf?abstractid=2568435&type=2)：可作 PBO 數值／模擬對照來源。
- Bailey et al., [Pseudo-Mathematics and Financial Charlatanism](https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf)：作者明確討論嘗試次數與 MinBTL；公式、rounding、annualization 必須固定版本，不自造表格。

依 `docs/TEST_DESIGN_CHARTER.md`，SPEC 應要求：

- EXACT：N=1、空集合、全 zero、NaN/inf、S=16 時 `C(16,8)=12870`、status/eligibility schema。
- TOLERANCE：固定 returns、T、N、skew/kurtosis、risk-free 與年化 convention，和論文數值或 pinned independent reference implementation 比對；不能只拿被測函式自算 oracle。
- METAMORPHIC：相同 returns 增加候選 N 不得使 DSR 更寬鬆；IS/OOS 對調或候選 label 打亂要改變／破壞 PBO 期待關係；cumsum 與 cumprod 語意 mutation 必須紅。
- STATISTICAL：預先寫 H0/H1、alpha、minimum sample/trade rule、multiple-testing policy、random seed／combination policy；null/alpha synthetic matrix 只作統計形狀測試，不能冒充真實資料 correctness。
- SMOKE／mutation：真實 kline 走 canonical backtest；把 N 固定成 1、把 `>=`／`>`、IS/OOS、NaN→0、periods=730 任一替換都應讓對應測試失敗。F-ST-2、F-ST-3、F-ST-5 與 A15/A21 的成本、時序分割要求需在 SPEC 逐項落地。

## 必答 6：scope/phasing

建議 Phase A 先凍結 reward contract、frequency/periods、MinBTL 的 typed status；Phase B 建立 session-scoped ledger 與 DSR；Phase C 持久化完整 candidate matrix 並實作 CSCV/PBO。Phase B/C 可在設計上並行，但任何沒有 A 的序列語意與沒有 B 的 N 都不能標為 available。跨 symbol/session、IC FDR、XGBoost model counts、ML pipeline publish gate 需在 SPEC 寫清 ownership，避免跨域重算或雙重計數。

## 必答 7：SPEC readiness/blockers

偵察證據足以起草 SPEC；不足以宣稱實作 ready。BLOCKING 是：N SoT/研究邊界與 unknown policy、canonical reward series、PBO candidate matrix、server-side eligibility gate。非阻塞建議是新 contract/wiring check、論文 reference pinning、mutation receipts。

## CODEX-R1-P0-01

**斷言**: 現況沒有可供 DSR/PBO fail-closed 使用的跨研究邊界 N 單一真相源；request N、Optuna rows、completed rows、unique params、retry attempts、IC factor counts 與 XGBoost cases 不是同一計數，將任一個直接當 N 會使 selection-bias correction 不可稽核。

**碼證**: `api/routes/optimization.py:37-53,121-135` 只接收 request N；`momentum/Optimization/optuna_optimizer.py:2374-2381,2414-2422,2530-2582,2595-2639` 同時存在 new target、complete count、duplicate prune/backfill、`len(study.trials)`；`api/services/optimization_task_service.py:248-258,644-666,790-838` 以 per-study SQLite、result snapshot、有限記憶體 registry 分散保存；`api/services/xgboost_batch_service.py:282-327` 的 total_cases 不是 candidate N。重跑 `rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' --glob '*.json' 'DSR|PBO|CSCV|MinBTL|Minimum Backtest' momentum api frontend scripts` 得無輸出、`rg_rc=1`，未找到既有統一三關／ledger 實作。

**來源摘要**: `api/routes/optimization.py#93008df279ae`; `momentum/Optimization/optuna_optimizer.py#eeab4169b1ec`; `api/services/optimization_task_service.py#0d6d02e08bbd`; `api/services/xgboost_batch_service.py#0d11f275806e`

BLOCKING：SPEC 須定義 session/dataset/candidate identity、attempt 與 candidate 的分離、各 N 欄位、lower-bound policy；缺任何必要欄位時只回 unavailable/n_unknown，不猜 N。

## CODEX-R1-P0-02

**斷言**: 平台沒有統一的策略 reward-series contract；`prediction_analyzer` 的 cumulative simple-return `np.cumsum`、vectorized backtest 的 trade-settled `np.cumprod(1+r)`、factor analyzer 的 PIT factor return path 不能直接互餵 DSR/PBO。

**碼證**: `momentum/Analysis/prediction_analyzer.py:152-164` 明確以 `np.cumsum` 產出名為 `strategy_returns` 的 cumulative path；`api/routes/pattern_analysis.py:1047-1051` 對 `actual_return` NaN 填 0；對照 `momentum/Strategy/vectorized_backtest.py:314-339` 以 bar return `np.cumprod(1.0+returns)` 建 equity；`momentum/Strategy/performance_metrics.py:32-36` 再對 equity `pct_change()`。這些實際輸出沒有共同的 unit/frequency/cost/slippage/warmup/empty schema。

**來源摘要**: `momentum/Analysis/prediction_analyzer.py#472c48fe06b6`; `api/routes/pattern_analysis.py#8bc01b6855dd`; `momentum/Strategy/vectorized_backtest.py#ddfa9b52ade8`; `momentum/Strategy/performance_metrics.py#60154cf6f758`

BLOCKING：三關只能接受一條明確 canonical period-return vector；cumsum endpoint 要隔離或另票修復，invalid/empty/constant 不得以正常 0 冒充可計算結果。

## CODEX-R1-P0-03

**斷言**: PBO 的資料前置不存在：optimization output 可列 trial 的標量 params/value/user_attrs 與 champion equity curve，但沒有同一 frozen candidate universe 對每個 CSCV block 的 return matrix、IS winner 與 OOS rank。

**碼證**: `api/services/optimization_output_service.py:150-174,317-350,375-417` 的 summary/trial extraction 只序列化 trial metadata 與 equity curve；`momentum/Optimization/optuna_optimizer.py:2595-2639` 回傳的 `OptimizationResult` 只帶總 trial 數與 champion-oriented result。這不足以依 [PBO/CSCV 原始論文](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253) 重建候選×時間的 IS/OOS 選擇。

**來源摘要**: `api/services/optimization_output_service.py#bc62dc9fbb79`; `momentum/Optimization/optuna_optimizer.py#eeab4169b1ec`

BLOCKING：Phase C 必須明定 candidate universe、block construction、selection metric、OOS rank/logit、failed candidate policy 與持久化位置；只對全樣本 top-K 重算不可作為完整 PBO。

## CODEX-R1-P1-04

**斷言**: 現有 Sharpe 不能不加 adapter 就作 DSR/MinBTL observed SR；實際 strategy objective 使用寫死的 `periods_per_year=730`，且空／零波動回傳 0.0，與 factor analyzer 的另一套年化／std 語意不一致。

**碼證**: `momentum/Strategy/performance_metrics.py:19-36,77-86` 是 730、ddof=0、empty/zero-vol→0.0；`momentum/Optimization/objectives/strategy_backtest.py:112-121` 建構 metrics 時未傳 data-derived periods；`momentum/Analysis/factor_return_analyzer.py:133-147,175-270` 使用另一套 factor return risk metrics。資料 timeframe 未由單一 config 傳入時，T、SR 與 MinBTL 會跨路徑不可比。

**來源摘要**: `momentum/Strategy/performance_metrics.py#60154cf6f758`; `momentum/Optimization/objectives/strategy_backtest.py#940991442f4a`; `momentum/Analysis/factor_return_analyzer.py#a46784f18ea0`

MAJOR：SPEC 須固定 frequency→periods、risk-free、ddof、T（bar／trade／effective observations）與 zero/NaN policy；未滿足時回 unavailable，不用既有 0.0 當 oracle。

## CODEX-R1-P1-05

**斷言**: `CombinatorialPurgedCV` 不能直接宣稱完成 PBO CSCV；它是 ML model-fit/AUC validator，不是對多策略報酬矩陣執行 IS/OOS selection stability。

**碼證**: `momentum/Analysis/model_validation/combinatorial_purged_cv.py:41-82` 的 API 接收 X/y 並產 train/test indices；`:84-165` 對每 path `model.fit`、計 `roc_auc`、feature stability 與 path AUC，沒有策略 candidate matrix、IS champion、OOS percentile。可複用的最多是經測試的 group/purge/embargo primitive，不能直接接 PBO。

**來源摘要**: `momentum/Analysis/model_validation/combinatorial_purged_cv.py#08ac8896b686`; `docs/IC_QUANT_GAP_REGISTRY.md#18f5f08ee8c0`（來源 hash 以本輪 `shasum -a 256` 實跑取得）

MAJOR：新增 strategy-validation CSCV adapter/module，並以 mutation 驗證 IS/OOS 對調、block leakage、組合數與候選排序；不得以 CPCV 類名冒充 PBO。

## CODEX-R1-P1-06

**斷言**: 現有 output contract、wiring checker 與 pipeline API 沒有策略三關的可用性／降級／promotion hard gate；只在 UI 顯示 recommendation 會讓未計算或 degraded 結果仍可建立 pipeline。

**碼證**: `momentum/Analysis/contracts/ic_report_contract.json` 的 sections/status 是 IC；`scripts/ic_wiring_check.py:30-36` 本輪只檢查 5 個 IC sections 且 `bash scripts/ic_wiring_check.sh` 輸出全綠、`ic_wiring_rc=0`；`api/services/optimization_output_service.py:183-213,502-522` 的 action 只看一般 metrics；`api/routes/ml_pipeline.py:124-245` 未檢查三關 eligibility。`frontend/src/app/strategy-test/page.tsx:1085-1102` 的 disabled 狀態只是本地提交保護。

**來源摘要**: `momentum/Analysis/contracts/ic_report_contract.json#6937da262f34`; `scripts/ic_wiring_check.py#bdf0f75f427b`; `api/services/optimization_output_service.py#bc62dc9fbb79`; `api/routes/ml_pipeline.py#df139c6a0fae`; `frontend/src/app/strategy-test/page.tsx#5dc1d358dc70`

MAJOR：另立 strategy validation contract 或 optimization 平行 section；API 只有 all-required-gates available/eligible 才允許 promote/create pipeline。`ok`、`available`、`degraded` 的詞彙須在 schema 一次定義，不能把 current ICHC enum 靜默轉義。

## 收尾驗證與工作區

- 讀取：`HANDOFF.md`、`CLAUDE.md`、`handoffs/20260817-gap1-recon-BRIEF.md`、其指定 seed/registry/template/charter；無 STAMP-BLOCK 觸發，brief 為 read-only consult。
- 只改產出：`handoffs/20260817-gap1-recon-codex.md`；未改 source/test、`data_cache/`、`.git/`、根 `HANDOFF.md`。
- `/tmp/workdir` 本輪檢查不存在；`/tmp` shallow inventory 無項目，因此沒有可刪的本任務 workdir，也沒有 `claude-501` 可被誤刪。需保留的名稱未遭移除。
- 來源摘要 hash 以 `shasum -a 256` 實跑取得；三件套檢索與 IC wiring 命令的 stdout/rc 已在本檔記錄。

ASSUMPTIONS_VERIFIED: N 計數面分裂；reward 語意不一致；PBO matrix 未持久化；CPCV 不是 PBO；IC wiring 不覆蓋策略三關；本輪無既有三件套命中
TESTS_RUN: `rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' --glob '*.json' 'DSR|PBO|CSCV|MinBTL|Minimum Backtest' momentum api frontend scripts` → no matches, rc=1；`bash scripts/ic_wiring_check.sh` → 5 sections 全綠，rc=0；交件檢查另依使用者指定命令執行並記錄於最終回覆
FAILURES_SEEN: none
SCOPE_CHANGES: none；read-only consult，只新增指定 report
NUMERIC_OR_SCHEMA_IMPACT: 未改程式數值或 schema；本報告提出 contract/schema 建議但未實作
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-recon-codex.md`
