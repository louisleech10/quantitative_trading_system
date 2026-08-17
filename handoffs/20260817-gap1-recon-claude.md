# GAP-1 偵察 — Claude 完整版（DSR/PBO/MinBTL 策略層防過擬合）

task-id: 20260817-GAP1-X-CONSULT-R1 ｜ family=claude（主委自產版）｜ 2026-08-17
票：`docs/IC_QUANT_GAP_REGISTRY.md` #1 ｜ 種子：`handoffs/GAP1-KICKOFF-SEED.md`（候選，非裁決）
證據方法：逐檔讀碼 + grep + 真實資料實跑（receipt 見 §7）。`未查`＝time-box 內未驗，**非**「沒問題」。

---

## 0. 總判（一句）

三件套**在數學上都可做**，但**平台現況的三個輸入面都不合格**：
① N 有機器帳本（Optuna SQLite，含 per-trial Sharpe）但**只在單一 study 內誠實**，跨 study／跨 session 無彙總、
且 TPE 自適應搜尋使「N 個獨立候選」的前提本身失真；
② 策略報酬序列有**三套互斥語意**（cumprod 交易結算式／cumsum 單利式／因子層 cumprod），
且年化係數 `periods_per_year=730` 在兩個實際呼叫點**寫死、與資料 timeframe 脫鉤**；
③ PBO 需要 N×T 的**逐配置報酬矩陣**，平台目前**只持久化冠軍那一條** equity curve。

而 MinBTL 用**真實資料實跑**的結論最刺眼：全庫歷史僅 **2.32 年**（三個 timeframe 皆同期間），
在平台預設 `n_trials=100` 下，MinBTL 要求年化 SR **≥ 1.99** 才有資格下結論——
亦即**預設配置下絕大多數策略會被判「無資格」**。這是正確答案而非缺陷，但它決定產品形態：
本票的主要輸出不會是「漂亮的機率數字」，而是**大量的「不合格／unknown」誠實標記**。
SPEC 必須先接受這個現實，否則做出來的三個數字會被誤讀成背書。

---

## 1. 必答 1：N 帳本盤點（本票最難點）

### 1.1 現存計數面逐個盤點

| # | 計數面 | 位置 | 已持久化? | 機器可讀? | 漏記/繞過路徑 |
|---|---|---|---|---|---|
| A | Optuna study trials（含 pruned） | `momentum/Optimization/optuna_optimizer.py:364` `storage="sqlite:///data/optuna_study.db"`；task 層改為 per-task `sqlite:///data/optuna_{study_name}.db`（`api/services/optimization_task_service.py:251`） | ✅ SQLite | ✅ `len(study.trials)` | **跨 study 不彙總**：每個 task 一個 .db 檔；同一研究者連跑 20 個 task＝20 個獨立 N |
| B | 續跑累積 trials | `optuna_optimizer.py:711/730/745` `create_study(..., load_if_exists=True)`，log `previous trials: {len(study.trials)}` | ✅ | ✅ | 同名 study 續跑會累積（**這點是對的**）；但改 study_name 即歸零 |
| C | per-trial 全指標（含 sharpe_ratio） | `objectives/strategy_backtest.py:146-153` `_record_trial_metrics` → `trial.set_user_attr(key, value)`；trial 綁定於 :87 | ✅（隨 trial 進 SQLite） | ✅ `trial.user_attrs["sharpe_ratio"]` | 只有 `strategy_backtest` 目標寫全指標；`model_hyperparam.py:184-187` 只寫 AUC 類 |
| D | 每 task 的 N 快照 | `optimization_task_service.py:_save_result`（:653-666）寫 `{task_id}_result.json`，含 `n_trials` | ✅ JSON 落地 | ✅ | **失敗/取消的 task 不寫**（`_save_result` 只在成功路徑）；`n_trials` 取 `result.total_trials or result.n_trials`＝**請求數**語意，未必＝實際完成數 |
| E | 記憶體 task registry | `optimization_task_service.py:159` `self.tasks` + `_cleanup_old_tasks(keep_latest=100)`（:790-830） | ❌ 記憶體 | — | **超過 100 個完成 task 即刪最舊者**；重啟即全失。`data/optuna_*.db` 與 result.json 留著，故彙總須掃檔案系統，不可依賴此 registry |
| F | XGBoost 批次（模型數） | `api/services/xgboost_batch_service.py:292` `create_task(task_id, len(all_cases))` | 部分 | 部分 | 屬 **ML/因子層** 多重檢定，非策略層 N；混算會重複計數 |
| G | IC 因子篩選次數 | `momentum/Analysis/ic_filter_orchestrator.py`（FDR/HAC 已上線） | — | — | **已被 FDR 覆蓋**；不得再計入策略層 N（否則雙重罰） |
| H | 人手迭代（改參數範圍重跑、換 symbol/timeframe 重試） | 無 | ❌ | ❌ | **本票最大漏洞**：這才是真實的 N 膨脹源，任何自動帳本都抓不到「研究者換了三次搜尋空間」 |

### 1.2 判斷

- **可機器化的部分**：A+B+C+D 已足以在**單一 study 範圍**內誠實計 N，且**連 per-trial Sharpe 都有**
  （這比種子預期的樂觀——DSR 需要 trial 間 SR 變異數 V[SR]，C 提供了）。
- **不可機器化的部分**：H（跨 study／人手迭代）。**任何聲稱「平台已誠實計 N」的設計都是假的**，
  除非把「同一資料集上的所有 study」納入彙總。
- **建議的 N SoT 設計**（SPEC 起草時的候選，交委員推翻）：
  1. 新增 **append-only trial ledger**（`data/trial_ledger/`，一行一 trial：
     `{ts, study_name, task_id, dataset_key(symbol+tf+期間+label), params_hash, sharpe, state}`），
     由 objective 的 `_record_trial_metrics` 同一處寫（**產出端**，不靠事後掃描）。
  2. N 的查詢 key＝`dataset_key`，**不是** task_id ⇒ 同一資料集上跨 study 的 trial 自動彙總，
     直接堵住 A 的漏洞。
  3. **fail-closed**：ledger 不可讀／`dataset_key` 對不上 ⇒ DSR/PBO 輸出 `status=unavailable,
     reason=n_ledger_missing`，**禁用預設值（如 N=1）**——N 低報＝三關全失真，比不輸出更危險。
  4. H 的誠實出路＝**顯式下限語意**：ledger 給的是 `N_observed`（下限），報告欄位須命名為
     `n_trials_observed` 並在契約層標 `n_is_lower_bound: true`；UI 文案必須寫「至少試過 N 次」。
     ✅ 這是本票可以做到的最高誠實度；聲稱能拿到「真 N」就是造假。

---

## 2. 必答 2：報酬序列輸入契約（三套互斥語意）

| 產出點 | 序列語意 | 累積法 | 年化 | 問題 |
|---|---|---|---|---|
| `momentum/Strategy/vectorized_backtest.py:314-339` `_calculate_equity_curve` | **交易結算式**：只在 `trade.exit_time` 的 bar 記 `pnl_pct`，其餘 bar 為 0 | `np.cumprod(1+returns)`（:338，正確複利） | 由 `PerformanceMetrics` 決定 | 序列 T＝**bar 數**（含大量 0），非交易數 ⇒ 見 §2.2 |
| `momentum/Analysis/prediction_analyzer.py:154-155` | **bar 級持倉式**：`actual_returns * (proba>threshold)` | `np.cumsum`（**單利加總，非複利**） | 無 | 與上表語意衝突；票 A 前置疑慮**成立但可繞**（見下） |
| `momentum/Analysis/factor_return_analyzer.py:239` | 因子層擇時報酬 | `(1+clean).cumprod()`（正確） | `periods = periods_per_year or 365`（:195），由 `_infer_periods_per_year(frame.index)` 推導（:146） | **這裡是對的做法**——策略層反而沒學到 |

### 2.1 年化係數寫死（P1，直接影響 DSR/MinBTL）

`PerformanceMetrics.__init__` 預設 `periods_per_year=730`、`risk_free_rate=0.02`
（`performance_metrics.py:20`），而**兩個實際呼叫點都不傳**：
- `vectorized_backtest.py:84` → `PerformanceMetrics(equity_curve, trades)`
- `objectives/strategy_backtest.py:113` → 同上

⇒ 不論資料是 1h／4h／12h，年化一律用 730（＝12h bar 的年周期數）。
對 1h 資料，真值 8760，SR 被**低估 √(8760/730) ≈ 3.46 倍**；4h 資料真值 2190，低估 1.73 倍。
DSR 比較的是「觀測 SR vs 期望最大 SR」，MinBTL 用**年化 SR 的平方**做分母 ⇒
年化錯誤會直接、非線性地污染兩關結論。**這是本票的前置修復項，且 fix 極小**
（把 timeframe 推導出的 `periods_per_year` 傳進去，作法直接照抄 `factor_return_analyzer._infer_periods_per_year`）。

### 2.2 T 的語意陷阱（P0，DSR 的分母）

DSR 的檢定統計量含 `√(T-1)`（T＝報酬觀測數）與報酬的 skew/kurtosis。
用 §2 表第一列的序列時：T＝bar 數（例：1h、2.32 年 ⇒ T≈20,352），
但其中**只有交易結算的那幾根 bar 非 0**（其餘為結構性 0，不是「該期報酬為 0」）。
後果有二，方向相反且都嚴重：
- `√(T-1)` 被膨脹 ⇒ **顯著性被高估**（DSR 偏樂觀，正是本票要防的方向出錯）；
- kurtosis 因大量 0 + 少數大值而爆高 ⇒ DSR 的 SR 變異數修正項變大 ⇒ 部分抵銷，**但抵銷量不可預測**。

⇒ SPEC 必須**明定 DSR 的輸入序列語意**（三個候選，交委員裁）：
(a) 交易級報酬序列（T＝交易數，年化用「每年交易數」）；
(b) bar 級持倉報酬序列（需回測引擎輸出逐 bar 持倉報酬，現在沒有）；
(c) 沿用現況並在報告中標 `t_semantics=trade_settled_bars` + 明確警語（**我不建議**：等於把已知偏誤留給使用者）。
我的建議＝**(a)**：交易級最貼近「這個策略的報酬觀測」，且不需要動回測引擎輸出結構
（`BacktestResult.trades` 已有 `pnl_pct`）。

### 2.3 `prediction_analyzer.py:154` `np.cumsum` 是否 BLOCKING？

**不是 BLOCKING，但必須具名隔離。** 該函式產的是 **ML 預測診斷用的 equity curve**
（`EquityCurveData`，前端診斷圖），不在 Optuna 策略優化路徑上
（策略路徑＝`StrategyBacktestObjective` → `VectorizedBacktest`，用 cumprod）。
⇒ 本票的三關**不得**吃 `prediction_analyzer` 的序列；SPEC 須在輸入契約明列
「唯一合法報酬來源＝`BacktestResult`（trades/equity_curve）」，並把 cumsum 那條列為
**另票**（診斷圖單利累積，屬名實相符問題，非本票 scope）。

---

## 3. 必答 3：落點與複用

### 3.1 模組落點（建議）

`momentum/Analysis/overfitting_validator.py`（新檔），與既有 `momentum/Analysis/statistical_validator.py`
（因子層 HAC/FDR，`scipy.stats`、fail-closed 全 NaN 回傳）**同層同慣例**。理由：
- 三關是**純統計函式**（吃 returns + N，吐數字＋status），與 `statistical_validator._hac_nan_result`
  的 fail-closed 風格完全同型，複用該檔的錯誤語意可省一套設計；
- 放 `momentum/Strategy/` 會讓策略層 import 統計工具、且 `Strategy/` 現在只有回測執行件；
- 放 `model_validation/`（ML 孤島）會繼承「未接主線」的歷史包袱。

### 3.2 `combinatorial_purged_cv.py` 能否供 PBO 複用？

**不能直接複用，須另寫 CSCV 分割器。** 兩者形似而語意不同：
- CPCV（purged + embargo）目的＝**單一模型**的無洩漏 OOS 估計，切法要 purge 標籤重疊區；
- CSCV（PBO 用）目的＝**選法穩定性**：把 T 切 S 等塊，取 C(S, S/2) 個「一半 IS／一半 OOS」組合，
  對**每個組合**在 N 個配置中選 IS 冠軍，看它的 OOS 排名分位。
  CSCV 的關鍵是**組合窮舉 + 逐配置績效矩陣**，purging 是可加的正確性增強、不是它的核心。
⇒ 建議：新寫 `_cscv_splits(T, S)`，但**沿用** CPCV 既有的 purge/embargo 工具函式處理標籤重疊
（若該檔已有可獨立呼叫的 purge helper——**未查**，SPEC 前須確認）。

### 3.3 PBO 的輸入矩陣不存在（P0）

CSCV 需要 **N（配置）× T（時間塊）的績效矩陣**。現況：
- `api/services/optimization_output_service.py:317-350` `_extract_trials`：每 trial 只有
  `value` / `values` / `params` / `user_attrs`（**純標量**）；
- `_extract_equity_curve`（:375-418）只取 `result.backtest_result.equity_curve`＝**冠軍那一條**。
⇒ 三個可行路徑：
1. **重算**（我建議）：PBO 執行時，用 ledger 裡的 N 組 params 重跑 `VectorizedBacktest`
   並在 S 塊上分段取績效。可行性：`VectorizedBacktest` 為向量化、無狀態、determinstic
   （同 params+同資料 ⇒ 同結果），重算不引入偏誤。成本＝N 次回測（N=100、T=20k bars 級，可接受；
   N≥1000 須分批，屬 registry #6 規模票）。
2. **在 trial 當下持久化逐塊績效**：`_record_trial_metrics` 擴為寫 S 塊的分段 SR 進 `user_attrs`
   ⇒ 但 S 必須在搜尋前就定死，日後改 S 即全部作廢。**不建議**。
3. 只對 top-K 配置做 PBO：**必須否決**——K 是用全樣本績效選的，CSCV 的分母被污染，
   PBO 會系統性偏低（過擬合被藏起來），正好與本票目的相反。SPEC 應把此路徑明文列為禁用。

### 3.4 現有 Sharpe 能否當 DSR 輸入？

`performance_metrics.sharpe_ratio()`（:77-85）公式本身正確
（`(mean - rf/periods)/std(ddof=0) * √periods`），但：
- ddof=0（母體標準差）vs DSR 推導慣例（樣本）差異在 T 大時可忽略，**T 小時不可**（MinBTL 場景恰是 T 小）；
- `periods_per_year` 寫死＝§2.1 的 P1；
- 空/退化情形回傳 **0.0 而非 NaN**（:79-82：`returns.empty` → 0.0；`std==0` → 0.0）
  ⇒ 「無法計算」與「真的是 0」不可分。DSR 若吃到假 0 會輸出「無技巧」的**看似正常**結論。
  ⇒ SPEC 須要求三關**自己**從報酬序列算 SR（fail-closed NaN + status），
  **不得**直接吃 `calculate_all()` 的既有 0.0 語意。

---

## 4. 必答 4：產出契約與可見性

- **不建議塞進 `ic_report_contract.json`**（推翻我自己 brief 的 assumed）：該檔 `_doc` 明寫
  scope＝「IC report 契約單一真相源」，其 `report_sections` 六節全是 IC 分析節
  （`quantile_returns`/`ic_decay`/`grouped_ic`/`turnover_analysis`/`coverage_analysis`/`net_ic_analysis`），
  消費端是 `ic_config_schema.load_report_contract` 與前端 IC 頁 types。
  策略層三關的產物屬**優化結果報告**（`optimization_output_service` / `optimization-result` 頁），
  語意錯位。建議新增 sibling：`momentum/Analysis/contracts/strategy_validation_contract.json`，
  **capability status 枚舉直接沿用**（`ok`/`not_applicable`/`not_computed`/`computation_failed`/`disabled`/`unavailable`），
  以「共用枚舉、分檔 sections」保持一致而不混 scope。
- **wiring 閘門**：`scripts/ic_wiring_check.sh` 只是 `ic_wiring_check.py` 的包裝（該 sh 僅 10 行、
  規則寫在 py 檔頭），其規則面向 IC report ⇒ **不會自動盯到**策略層新契約。
  本票須自帶等價檢查（或把 wiring checker 參數化吃 contract 路徑——**後者較好**，避免長出第二套機制）。
- **UI 現況**：`frontend/src/components/optimization/hyperparameter/OverfittingCheckChart.tsx`
  只畫 train-val gap（ML 層），**沒有任何策略選擇過擬合面板**；落點應在
  `frontend/src/app/optimization-result/[taskId]/page.tsx`。
- **「不合格」必須擋而非標**（對照使用者鐵律「驗過就別預設關閉」的反面：**沒驗過就不得展示為結論**）：
  MinBTL 未達 ⇒ 冠軍參數的績效數字須**降級展示**（不得單獨顯示 SR/equity curve 作為結論），
  UI 須以 blocking banner 呈現，且 `best_params` 的「建議上線」語意必須關閉。
  純標籤（小字警語）等於沒做——這是 registry #5 容量 `unknown` 契約已學到的教訓。

---

## 5. 必答 5：測試策略（禁自造 golden）

| 關卡 | 第三方對照來源 | 具體可驗案例 | 期望值 |
|---|---|---|---|
| DSR | Bailey & López de Prado, *The Deflated Sharpe Ratio*（2014, JPM）論文數值例；`mlfinlab`／作者公開程式碼之 `deflated_sharpe_ratio` | 論文中的 E[max SR] 期望值公式 `E[max SR] ≈ √V[SR]·[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne))]`，γ=0.5772 | 我已實跑三點作對照錨：N=10→1.5746·√v、N=100→2.5306·√v、N=1000→3.2551·√v（receipt §7） |
| DSR 退化性質 | 解析極限 | N=1 時 DSR 應退化為標準 SR 的 PSR（probabilistic Sharpe ratio）；skew=0,kurt=3 時修正項應等於常態情形 | 可證偽：改壞修正項則此等式破 |
| PBO | Bailey et al., *The Probability of Backtest Overfitting*（2015, J. Computational Finance）；作者 CSCV 參考實作 | ① 建構「全部配置都是純噪音」的合成矩陣 ⇒ PBO 應 ≈ 0.5；② 建構「一個配置真的有 alpha、其餘噪音」 ⇒ PBO 應顯著 < 0.5 | ①≈0.5（統計容差內）②<0.5；**這兩條是 mutation 可證偽的核心** |
| PBO 組合數 | 組合數學 | S=16 ⇒ C(16,8)=12870 個組合 | 精確整數，改壞立刻紅 |
| MinBTL | Bailey & LdP, *Pseudo-Mathematics and Financial Charlatanism*（2014, Notices of the AMS）之 `MinBTL ≈ 2·ln(N)/SR²` | N=100, SR=1 ⇒ 9.21 年；N=1000, SR=1.5 ⇒ 6.14 年 | 已實跑對照表（§7） |
| 資格閘行為 | 本專案真實資料 | 1h/4h/12h 皆 2.32 年；N=100 ⇒ 須 SR≥1.99 | 資格判定須回 `not_qualified`，且**不得**同時輸出 DSR 作為結論 |

補充紀律（對照 `docs/TEST_DESIGN_CHARTER.md`）：
- 三關的每個 fail-closed 分支（N 缺、序列太短、std=0、NaN 混入）都須有**獨立**測試，
  且斷言「回傳 status＋NaN」而非「回傳 0」；
- **mutation 自證**：把 `E[max SR]` 的 γ 項刪掉／把 CSCV 的 IS/OOS 對調／把 MinBTL 的 ln(N) 換成 N，
  三者都必須讓既有測試轉紅。若不紅＝測試是裝飾品。
- 真實資料端到端：用 `data_cache/feature_klines/kline_cache.h5`（禁合成 fixture）跑一次
  完整 optimization → 三關，斷言 `n_trials_observed` 與 Optuna study trial 數一致（防 N 低報）。

---

## 6. 必答 6：scope 建議 ／ 必答 7：可否進 SPEC

### 6.1 分期建議（不一次做完，但**不是**按「三件套」切）

按**依賴**切，而非按公式切：

- **B1（前置，小）**：`periods_per_year` 從資料 timeframe 推導並傳入兩個呼叫點；
  `sharpe_ratio` 等退化情形改 NaN+status（不改既有回傳 0 的 caller 契約前先盤 caller）。
  → 沒有這步，後兩批的數字全錯（§2.1）。
- **B2（N 帳本）**：append-only trial ledger（產出端寫入）＋ `dataset_key` 彙總＋fail-closed 查詢 API。
  → **MinBTL 與 DSR 都只吃 N**，此批完成即可同時上兩關。
- **B3（MinBTL + DSR）**：`overfitting_validator.py` 兩個函式 + 契約 + status + UI blocking banner。
  → **單獨上線就有真實防護價值**（資格閘 + 冠軍檢定），且不需要 N×T 矩陣。
- **B4（PBO）**：CSCV 分割器 + 重算式績效矩陣（§3.3 路徑 1）+ top-K 禁用的機械檢查。
  → 成本最高、依賴最多；沒有 B2 也**不是完全沒意義**（PBO 不吃 N），但沒有 B1 的年化修正則排名可能仍有偏。

**沒有 N 帳本（B2）就沒意義的是 MinBTL 與 DSR**；PBO 唯一不吃 N，可獨立成立——
這一點推翻種子「三關順序 MinBTL→PBO→DSR」的隱含假設（順序是**展示順序**，不是**依賴順序**）。

### 6.2 Verdict

**可進 SPEC 起草**，但 SPEC 必須明文承載以下五條，否則做出來是裝飾品：

1. N 只能是 `n_trials_observed`（下限語意），且 fail-closed 禁預設值；人手迭代（H）**具名列為不可觀測殘留**。
2. DSR/MinBTL 的輸入 SR 必須由三關自算（NaN+status），**不得**吃 `calculate_all()` 的 0.0 語意。
3. 報酬序列語意須擇一定死（我建議交易級），且 `periods_per_year` 必須由資料推導（B1 前置）。
4. PBO 禁 top-K 子集；矩陣用重算式取得。
5. 「不合格」在 UI 是 **blocking**，不是小字警語。

**BLOCKING（須在 SPEC 內解決，非阻止起草）**：無「必須先修才能寫 SPEC」的項；
`prediction_analyzer` 的 `np.cumsum` **不擋路**（不在策略路徑，另票）。

---

## 7. 實跑 receipt（真實資料，非推測）

```
$ venv/bin/python scratchpad/span2.py   # h5py 直讀 data_cache/feature_klines/kline_cache.h5
DS ADAUSDT/1h/data (20352,)   DS ADAUSDT/4h/data (5088,)   DS ADAUSDT/12h/data (1696,)
（BTCUSDT/BNBUSDT/BCHUSDT/DOGEUSDT… 同列數）

$ venv/bin/python scratchpad/minbtl.py
1h: bars=20352 years=2.323 ｜ 4h: bars=5088 years=2.323 ｜ 12h: bars=1696 years=2.323
MinBTL(years) = 2*ln(N)/SR_ann^2:
  N=100  SR=1.0 → 9.21 yr    N=100  SR=2.0 → 2.30 yr
  N=1000 SR=1.5 → 6.14 yr    N=10   SR=1.5 → 2.05 yr
以 2.32 年可用歷史反解所需 SR：N=10 → ≥1.41 ／ N=100 → ≥1.99 ／ N=1000 → ≥2.44
E[max SR]/√V[SR]（DSR 基準）：N=10 → 1.5746 ／ N=100 → 2.5306 ／ N=1000 → 3.2551
```

```
$ grep -rn "deflated|DSR|PBO|CSCV|MinBTL" --include="*.py" momentum api   → 0 命中
$ grep -rn "PerformanceMetrics(" --include="*.py" momentum api
momentum/Optimization/objectives/strategy_backtest.py:113  （未傳 periods_per_year）
momentum/Strategy/vectorized_backtest.py:84                （未傳 periods_per_year）
```

---

## 8. canonical findings

## CLAUDE-R1-P0-01

**斷言**: PBO（CSCV）在現況**不可計算**——CSCV 需要 N（配置）×S（時間塊）的績效矩陣，
而平台只持久化冠軍一條 equity curve，per-trial 僅存標量指標。

**碼證**: `api/services/optimization_output_service.py:317-350`（`_extract_trials` 僅
`value`/`values`/`params`/`user_attrs`）；同檔 `:375-418`（`_extract_equity_curve` 取
`result.backtest_result.equity_curve` 單條）；`momentum/Optimization/objectives/strategy_backtest.py:146-153`
（`set_user_attr` 只寫標量）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0001

修法＝重算式（用 ledger 的 N 組 params 重跑向量化回測，determinstic 故無偏誤）；
**禁**只對 top-K 做 PBO（K 由全樣本績效選出 ⇒ 分母污染 ⇒ PBO 系統性偏低）。

## CLAUDE-R1-P0-02

**斷言**: DSR 的 T（報酬觀測數）若沿用現況序列會被**結構性膨脹**——序列為「交易結算式」，
僅在 `trade.exit_time` 的 bar 非 0，其餘 bar 是結構性 0 而非「該期報酬為 0」⇒ `√(T-1)` 高估顯著性，
方向正好與本票目的相反。

**碼證**: `momentum/Strategy/vectorized_backtest.py:314-339`（`pnl_map` 只在 exit bar 累加，
`returns` 其餘為 0，`equity = np.cumprod(1.0 + returns)`）；1h 資料 T≈20,352 bar 但交易數為十位數級。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0002

SPEC 須擇一定死輸入語意；建議交易級報酬序列（T＝交易數，年化用每年交易數）。

## CLAUDE-R1-P1-03

**斷言**: 策略層年化係數 `periods_per_year=730` 在**兩個實際呼叫點都未傳入**，與資料 timeframe 脫鉤；
1h 資料的 SR 被低估約 3.46 倍（√(8760/730)），4h 低估 1.73 倍 ⇒ 直接污染 DSR 與 MinBTL（後者用 SR²）。

**碼證**: `momentum/Strategy/performance_metrics.py:20`（預設 730）；
`momentum/Strategy/vectorized_backtest.py:84` 與 `momentum/Optimization/objectives/strategy_backtest.py:113`
（皆 `PerformanceMetrics(equity_curve, trades)`，無 `periods_per_year`）；
對照正確做法 `momentum/Analysis/factor_return_analyzer.py:146`（`_infer_periods_per_year(frame.index)`）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0003

## CLAUDE-R1-P1-04

**斷言**: N 的機器帳本**只在單一 study 內誠實**：每個 optimization task 開自己的 SQLite
（`sqlite:///data/optuna_{study_name}.db`），跨 study／跨 session 無彙總；
且記憶體 task registry 會刪最舊的 100+ 完成 task ⇒ 依賴它彙總 N 必低報。

**碼證**: `api/services/optimization_task_service.py:251`（per-task storage）；同檔 `:790-830`
（`_cleanup_old_tasks(keep_latest=100)` 刪 `self.tasks`/`self.optimizers`）；
`momentum/Optimization/optuna_optimizer.py:711/730/745`（`load_if_exists=True` 只在同名 study 累積）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0004

修法＝append-only trial ledger，查詢 key＝`dataset_key`（symbol+tf+期間+label）而非 task_id；
fail-closed（ledger 缺 ⇒ `status=unavailable`，**禁** N 預設值）。

## CLAUDE-R1-P1-05

**斷言**: 以本專案**真實資料**實跑，可用歷史僅 2.32 年（1h/4h/12h 同期間），在平台預設
`n_trials=100` 下 MinBTL 要求年化 SR ≥ 1.99 ⇒ **預設配置下絕大多數策略會被判無資格**。
這是正確結論，但決定產品形態：本票主要輸出是誠實的「不合格／unknown」，不是漂亮機率。

**碼證**: `h5py` 直讀 `data_cache/feature_klines/kline_cache.h5` ⇒ `1h/data (20352,)`、
`4h/data (5088,)`、`12h/data (1696,)`（皆 848 天）；`api/routes/optimization.py:48`
（`n_trials` 預設 100）；MinBTL 反解 receipt 見 §7。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0005

## CLAUDE-R1-P1-06

**斷言**: `PerformanceMetrics` 在退化情形回傳 **0.0 而非 NaN**（空序列／std=0），
「無法計算」與「真的是 0」不可分；三關若直接吃 `calculate_all()` 會把假 0 當成「無技巧」的正常結論輸出。

**碼證**: `momentum/Strategy/performance_metrics.py:78-82`（`returns.empty → 0.0`、`std_ret==0 → 0.0`）、
`:9-16`（`_safe_float` 把 NaN/inf 一律轉 default 0.0）。對照 fail-closed 正例
`momentum/Analysis/statistical_validator.py:17-32`（`_hac_nan_result` 全 NaN）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0006

## CLAUDE-R1-P1-07

**斷言**: 三關結果**不應**塞進 `ic_report_contract.json`（scope 錯位：該檔六節全為 IC 分析節，
消費端為 IC 頁 types），且 `scripts/ic_wiring_check.sh` 的規則面向 IC report ⇒
**不會自動盯到**策略層新欄位；本票若不處理，就是再造一個「兩端有但沒連」的幽靈 feature。

**碼證**: `momentum/Analysis/contracts/ic_report_contract.json:1`（`_doc` 界定 scope）、
`:27-43`（`report_sections` 六節皆 IC）；`scripts/ic_wiring_check.sh:1-10`（僅 10 行包裝，規則在
`ic_wiring_check.py` 檔頭）；`frontend/src/components/optimization/hyperparameter/OverfittingCheckChart.tsx`
（現有唯一過擬合面板只畫 train-val gap，屬 ML 層）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0007

建議＝新增 sibling 契約 `strategy_validation_contract.json`（共用 capability status 枚舉），
並把 wiring checker **參數化吃 contract 路徑**（避免長出第二套機制）。

## CLAUDE-R1-P2-08

**斷言**: TPE（自適應）搜尋使「N 個獨立候選」的前提失真：trial 的選點依賴先前全樣本結果 ⇒
DSR 的 V[SR]（trial 間 SR 變異數）估計偏誤方向不明，PBO 的配置集本身已是資料依賴。
此為方法論殘留，SPEC 須具名，不可靜默套用論文假設。

**碼證**: `momentum/Optimization/optuna_optimizer.py:425-427`（TPE `n_startup_trials` 自動＝15% n_trials，
其後為自適應）；`objectives/strategy_backtest.py:104-121`（每 trial 的評估用全樣本 `self.prices`）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0008

緩解候選：V[SR] 只用 startup（隨機）階段的 trial 估計，或在報告標 `n_semantics=adaptive_search`。

## CLAUDE-R1-P2-09

**斷言**: `momentum/Analysis/prediction_analyzer.py:154-155` 用 `np.cumsum`（單利加總）產權益曲線，
與策略路徑的 `cumprod` 語意不一致；但它**不在** Optuna 策略路徑上 ⇒ 不構成本票 BLOCKING，屬另票。

**碼證**: `momentum/Analysis/prediction_analyzer.py:154-155`（`np.cumsum(strategy_returns)`）；
策略路徑證據＝`objectives/strategy_backtest.py:105-113` → `VectorizedBacktest.run_backtest`
→ `vectorized_backtest.py:338`（`np.cumprod`）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0009

## CLAUDE-R1-P2-10

**斷言**: 「試了幾次」的其他計數面（XGBoost 批次 case 數、IC 因子篩選數）**不得**計入策略層 N——
因子層多重檢定已由 FDR/HAC 覆蓋，混算＝雙重罰。

**碼證**: `api/services/xgboost_batch_service.py:292`（`create_task(task_id, len(all_cases))`，
屬 ML/因子層）；`momentum/Analysis/statistical_validator.py`（HAC）與 `ic_filter_orchestrator.py`（FDR 已上線）。

**來源摘要**: handoffs/20260817-gap1-recon-claude.md#c1a0de1a0010

## 9. 未查清單（time-box，非「沒問題」）

1. `model_validation/combinatorial_purged_cv.py` 是否有可獨立呼叫的 purge/embargo helper（§3.2 依賴此）。
2. `optimization-result/[taskId]/page.tsx` 現有欄位與 store 形狀（UI blocking banner 落點細節）。
3. `execution_optimization.py` 路徑（`task_type="strategy_backtest"`）是否走同一 objective ／ 另有 N 面。
4. Optuna pruned trial 是否應計入 N（我傾向**應計**：pruned 也是一次評估）——待委員裁。
5. `data/optuna_*.db` 與 `results/optimization_results/*_result.json` 的實際落地情形（未實查檔案系統）。
