# GAP-1 偵察 — DSR/PBO/MinBTL 策略層防過擬合 — composer R1

**task-id**: `20260817-GAP1-X-CONSULT-R1` | **family**: COMPOSER | **brief**: `handoffs/20260817-gap1-recon-BRIEF.md`  
**scope**: 只讀偵察；**禁改碼**。輪次=R1。

---

## Verdict：可進 SPEC 起草（附 BLOCKING 清單）

證據足以起草 SPEC，但開工前須在 SPEC §0 收斂兩項 **BLOCKING**：（1）**N 帳本**無統一 SoT，DSR 在 N 不可知時必須 `unavailable` 拒答，不得裝飾；（2）**報酬序列輸入契約**須先統一（`prediction_analyzer` 單利 cumsum vs `vectorized_backtest`/`factor_return_analyzer` 複利語意），否則三關 Sharpe/DSR 輸入不可比。建議分期：**Phase A＝MinBTL＋報酬契約統一**；**Phase B＝N 帳本＋DSR**；**Phase C＝PBO**（需多策略報酬矩陣，依賴 Optuna trial 歷史或等價持久化）。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 判定 | 碼證 |
|---|---|---|
| fact-verified: repo 無 DSR/PBO/CSCV/MinBTL 實作 | **本輪複驗通過** | `grep -rn "deflated\|DSR\|PBO\|CSCV\|MinBTL\|min_btl" --include="*.py" momentum api` → 0 命中，`grep_rc=1` |
| assumed: 「嘗試次數 N」無機器化統一帳本 | **確認成立** | 見必答 1 表；Optuna 僅 per-study SQLite；IC `n_tests` 為因子層；無跨域累計器 |
| assumed: 三件套只吃「報酬序列＋N」可獨立模組 | **部分推翻** | PBO 需 **多候選策略報酬矩陣**（≥2 組參數），非單條序列；見 P1-01 |
| assumed: `ic_report_contract.json` 擴 `report_sections` 即可 | **部分推翻** | 契約枚舉與 section 皆 IC 語意；策略三關應獨立 `strategy_validation_contract.json` 或 optimization 產物欄位，見 P1-03 |
| assumed: MinBTL→PBO→DSR 順序正確 | **本輪支持** | MinBTL 僅需 T（樣本長）可先跑；DSR 需 N；PBO 需多路徑——順序合理但 **PBO 與 DSR 可並行**，非嚴格串行依賴 |

---

## 必答 1：N 帳本盤點

| 計數面 | 位置 | 已持久化 | 機器可讀 | 可繞過路徑 | DSR 相關 N 語意 |
|---|---|---|---|---|---|
| Optuna `n_trials`（單次 study 目標） | `api/routes/optimization.py:48-49,130`；`optimization_task_service.py:246,251` | 是（task config + `sqlite:///data/optuna_{study_name}.db`） | 是（`study.trials`） | **新 `study_name` 重開 study**；前端可改 `n_trials`（`page.tsx:238,376`） | 單 study 內有效 N；**不跨 study/任務累計** |
| Optuna 已完成 trial 數 | `optuna_optimizer.py:2142,2530`；`optimization_output_service.py:64-65`（`trials.csv`） | 是（SQLite + 輸出 CSV） | 是 | Pruned trial 是否計入 N 需 SPEC 定義；resume 後 `len(study.trials)` 含歷史 | 實際執行次數，但僅綁定單 study |
| Optimization checkpoint | `checkpoint_manager.py:37-44,70-80` | 是（`data/checkpoints/` pickle） | 是 | 與 Optuna SQLite **雙寫**，無全域索引 | 備份層，非 N SoT |
| IC FDR `n_tests` | `statistical_validator.py:203`；`ic_filter_orchestrator.py:1440,1502` | 是（report `metadata.significance.n_tests`） | 是 | **因子層** finite p 個數，≠策略參數掃描 | **不可當策略 N**（層級錯誤） |
| IC `top_n` / stage5 候選數 | `factor_return_analyzer.py:281`；`ic_config_schema.py:161` | 部分（config 快照） | 是 | UI 改 `top_n_features` 即變 | 因子篩選，非回測策略試驗 |
| XGBoost 批次 | `xgboost_batch_service.py`（無 `n_trials`） | batch checkpoint | 間接 | 每 symbol 一次訓練，**無超參 trial 帳本** | 若算「模型嘗試」需另定義 |
| Strategy registry 策略數 | `strategy_registry.py:47`（YAML 靜態清單） | 是（YAML） | 是 | 靜態配置，不含參數組合爆炸 | 策略 **模板** 數，非優化 N |
| 前端重複送單 | API 層無 dedup key | 否 | 否 | 使用者多次 POST `/optimization/tasks` 各建獨立 task | **完全漏記** |

**N SoT 設計建議（fail-closed）**：
1. 新增 `HypothesisLedger`（建議 `momentum/Analysis/strategy_validation/ledger.py`）：每次「可改變策略/參數並產出可比 Sharpe」的動作寫入 `{ledger_id, scope, hypothesis_key, ts, source}`；`hypothesis_key` = hash(symbol_set, timeframe, objective_family, param_vector)。
2. DSR 消費 `N_effective` = **同一 research_session_id 下 distinct hypothesis_key 數**；缺 `research_session_id` 或 ledger 不可讀 → status=`unavailable`，reason=`n_unknown`（**拒答，不猜**）。
3. Optuna study 作為 **子帳本**：`N_study = len(complete_trials)` 僅在 `ledger.scope=optuna_study` 內有效；跨 study 合併須顯式 `parent_session_id`。
4. IC `n_tests` **禁止**映射為策略 N（層級標註在契約）。

---

## 必答 2：報酬序列輸入契約

| 產出點 | 序列定義 | 頻率/單位 | 成本/滑價 | NaN/空態 |
|---|---|---|---|---|
| `vectorized_backtest.py:314-339` | bar 級 `pnl_pct` → `cumprod(1+r)` 權益 | 與 `prices` 同頻；比例 | `commission+slippage` 扣於進出場 `:41-47,247,286` | 無交易→ flat 1.0；驗證失敗→空結果 `:355-362` |
| `strategy_backtest.py:105-113` | 同上（委託 backtest engine） | 同上 | 同上 | Optuna trial metrics 寫 user_attr |
| `prediction_analyzer.py:152-156` | `strategy_returns = actual_returns * position`；**`np.cumsum` 單利累加** | 與輸入對齊；輸出為 **累加和** 非權益 | **無** 成本欄 | 長度不一致→`ValueError` |
| `factor_return_analyzer.py:133,240` | LS `position * returns_w`；指標用 `cumprod` | 推斷 `periods_per_year` `:386-394`（預設 365） | turnover 語意標註，非 full backtest cost | `SkippedResult` 路徑 |
| `performance_metrics.py:32-36,77-86` | `equity_curve.pct_change()` → Sharpe | 預設 `periods_per_year=730` `:20` | 間接（取決於輸入 equity） | 空→0.0 |

**語意不一致**：三條主路徑（回測複利 / 預測分析單利 cumsum / 因子 LS）**不可直接互換**作 DSR 輸入。

**`np.cumsum` 前置修復判定**：**BLOCKING（可與 MinBTL 並行，不可與 DSR 並行）**。若 DSR 消費 `prediction_analyzer` 路徑，cumsum 產物非報酬率序列，Sharpe/DSR 公式前提不成立。修復方向：改輸出 per-period returns（或 `cumprod` 權益 + 明確 schema 標 `return_semantics`），並在契約區分 `additive_cumsum` vs `compound_equity`。

---

## 必答 3：落點與複用

| 項目 | 建議 | 理由 |
|---|---|---|
| 新模組路徑 | `momentum/Analysis/strategy_validation/`（`min_btl.py`, `deflated_sharpe.py`, `pbo_cscv.py`, `ledger.py`） | 與 IC 解耦；工廠 `create_*` 掛 `factories.py`；不 import `api/` |
| CPCV 複用 PBO | **不可直接複用** | `combinatorial_purged_cv.py:41-73` 產 sklearn `(train_idx, test_idx)` 給 **特徵矩陣 X**；PBO CSCV 需 **策略報酬向量/矩陣** 的 combinatorial IS/OOS **排名穩定性**。Purging/embargo 邏輯可 **抽取共用 util**，分割器須另寫 |
| `sharpe_ratio()` 作 DSR 輸入 | **條件可用** | `performance_metrics.py:77-86` 用 `ddof=0`、年化 `*sqrt(periods_per_year)`；DSR 文獻常用 sample Sharpe + 獨立估 skew/kurtosis。預設 **730**（約 1h×2）與 `factor_return_analyzer` 推斷 365 **不一致** → SPEC 須鎖 `periods_per_year` 來源（timeframe config），否則 DSR 跨模組不可比 |
| MinBTL | 獨立純函式，輸入 `(T, N, target_sharpe, ...)` | 不需報酬序列，僅樣本長資格閘 |

---

## 必答 4：產出契約與可見性

| 項目 | 建議 |
|---|---|
| 產物落點 | **首選**：optimization 任務結果 JSON + `trials.csv` 增欄 `min_btl_status`, `dsr`, `pbo`, `n_effective`；**次選**：新 `strategy_validation_contract.json`（平行 ICHC 模式） |
| status 枚舉 | 沿用 ICHC `capability_status` 子集：`ok` / `not_computed` / `unavailable` / `computation_failed`；MinBTL 不合格→`unavailable` + reason=`insufficient_btl` |
| `ic_wiring_check.sh` | **不會自動盯到**策略欄位；`ic_wiring_check.py:30-36` 僅 IC report 五節。策略三關須 **新 wiring check** 或擴 allowlist（另票） |
| UI 擋住 vs 標註 | MinBTL fail → **API 層拒絕標記 champion**（`best_trial` 設 `eligible=false`）；前端 optimization 結果頁 **disable「採用此參數」**；僅 banner 標註＝不合格 |

---

## 必答 5：測試策略

**第三方對照（禁自造 golden 主 oracle）**：

| 檢定 | 對照來源 | 可驗案例 |
|---|---|---|
| MinBTL | Bailey & López de Prado (2014) 式 (1) 臨界 T | 文獻表格：給定 N=100, SR*=1, 查最小 T；實作後 `assert T_min == literature_table[N,SR]` |
| DSR | Harvey & Liu (2015) / Bailey (2014) 附錄；`mlfinlab` 或 `pypbo` 公開實作 | 固定 returns 向量 + N=10 → 比對 `DSR` 至 1e-4（獨立套件非自寫） |
| PBO | Bailey et al. (2015) CSCV 演算法；`pypbo` | 已知 16 策略×16 區塊 toy matrix → PBO 點估與論文 Figure 範例一致 |

**對照 `docs/TEST_DESIGN_CHARTER.md`**：

| Charter 條目 | 本票對應 | mutation 可證偽 |
|---|---|---|
| F-ST-2 Deflated Sharpe | DSR 模組 P0 | 改 N 不影響輸出→FAIL |
| F-ST-3 PBO/CSCV | PBO 模組 P0 | 改 IS/OOS 排名邏輯→PBO 變化 |
| F-ST-5 n_trades<30 | MinBTL 可疊加 | 縮短 T→`unavailable` |
| STATISTICAL 類 | 三關皆屬 | 須預註 α、N、T_min |
| B1.2 oracle 獨立性 | 禁止用 `sharpe_ratio()` 自身當 DSR oracle | 須第三方或手算表 |

**整合測試**：`tests/momentum/helpers/ichc_run.py` 模式可複用 **真實 kline runner**，但本票應新建 `strategy_validation_run.py` helper，跑 `vectorized_backtest`→三關，避免 IC pipeline 污染。

---

## 必答 6：scope 建議

| 分期 | 內容 | 獨立防護價值 |
|---|---|---|
| **A** | 報酬契約統一 + MinBTL | **有**——樣本不足直接拒答，不需 N |
| **B** | HypothesisLedger + DSR | **有**——需 N 帳本；無 ledger 則誠實 `unavailable` |
| **C** | PBO/CSCV | **有**——需多 trial 報酬矩陣；僅在 strategy_backtest Optuna 路徑先上 |

**不建議一次做完**：N 帳本與 PBO 資料準備可並行設計，但實作應 A→B→C，避免 DSR 在 cumsum 與 N 未就緒時假綠。

---

## 必答 7：SPEC 起草充分性

| 問題 | 結論 |
|---|---|
| 足以進 SPEC？ | **是**——N 盤點、報酬契約、落點、測試對照均已具證 |
| BLOCKING？ | （1）N 無 SoT；（2）報酬序列三語意分裂 + `cumsum`；（3）PBO 需多路徑矩陣非單序列——SPEC 須寫清資料前置 |
| 未查 | `xgboost_task_service` 單任務超參掃描面、WebSocket 重試是否重算 trial、跨使用者 session 邊界 |

---

## COMPOSER-R1-P0-01

**斷言**: 平台無跨域「策略假設嘗試次數 N」統一帳本；DSR 若用單一 Optuna study 的 `n_trials` 當全域 N 會系統性低估或高估多重測試偏差。

**碼證**: `optimization_task_service.py:251` 每 task 獨立 `sqlite:///data/optuna_{study_name}.db`；`ic_filter_orchestrator.py:1502` 的 `n_tests` 為因子 FDR 計數；`grep -rn "HypothesisLedger\|hypothesis_ledger\|n_effective" momentum api` → 0 命中（本輪）。

**來源摘要**: api/services/optimization_task_service.py#0d6d02e08bbd

[BLOCKING] 信心度=High；N 漏記→DSR 成裝飾品；SPEC 須定 ledger + `n_unknown` 拒答路徑。

---

## COMPOSER-R1-P0-02

**斷言**: `prediction_analyzer.py` 用 `np.cumsum` 產出與 `vectorized_backtest` 的 `cumprod` 權益語意不一致，不可作為 DSR/策略 Sharpe 的統一輸入。

**碼證**: `prediction_analyzer.py:155-156` `cum_strategy = np.cumsum(strategy_returns)`；對照 `vectorized_backtest.py:338` `equity = np.cumprod(1.0 + returns)`；`strategy_backtest.py:113` 走後者路徑。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#472c48fe06b6

[BLOCKING] 信心度=High；混用會使 DSR 觀測 Sharpe 不可比；修復或契約隔離為 SPEC 前置。

---

## COMPOSER-R1-P1-01

**斷言**: `combinatorial_purged_cv.py` 不能直接供 PBO 的 CSCV 分割；僅 purging 思想可複用，分割 API 與輸入類型不相容。

**碼證**: `combinatorial_purged_cv.py:41-45` `split(X: pd.DataFrame)` 產 index pairs；PBO 需對 **策略績效向量集合** 做 combinatorial IS/OOS 排名（Bailey 2015 §3）。`max_paths` 隨機子樣 `:58-61` 與 PBO 完整 CSCV 組合語意亦不同。

**來源摘要**: momentum/Analysis/model_validation/combinatorial_purged_cv.py#08ac8896b686

[MAJOR] 信心度=High；SPEC 勿寫「複用 CPCV 即完成 PBO」。

---

## COMPOSER-R1-P1-02

**斷言**: `PerformanceMetrics.sharpe_ratio` 預設 `periods_per_year=730` 與 `factor_return_analyzer` 推斷年化（預設 365）不一致，直接餵 DSR 會產生跨模組年化偏差。

**碼證**: `performance_metrics.py:20,77-86`；`factor_return_analyzer.py:195,386-394` `_infer_periods_per_year`。

**來源摘要**: momentum/Strategy/performance_metrics.py#60154cf6f758

[MAJOR] 信心度=High；SPEC 須鎖 timeframe→periods_per_year 單一 config 來源（`momentum/core/config.py`）。

---

## COMPOSER-R1-P1-03

**斷言**: 將策略三關硬塞 `ic_report_contract.json` 的 `report_sections` 會造成 IC 與策略產物語意錯位；`ic_wiring_check` 不會覆蓋 optimization 產出。

**碼證**: `ic_report_contract.json:27-42` 僅 IC 分析節；`ic_wiring_check.py:30-36` `REPORT_SECTIONS` 無 strategy 欄；registry #1 明確策略層與因子層分工 `docs/IC_QUANT_GAP_REGISTRY.md:10-11`。

**來源摘要**: momentum/Analysis/contracts/ic_report_contract.json#6937da262f34

[MAJOR] 信心度=Medium；建議獨立 strategy validation 契約 + optimization wiring check。

---

## COMPOSER-R1-P2-01

**斷言**: Optuna N 可透過新 `study_name` 繞過累計——每次優化任務預設獨立 DB 檔，無跨任務 hypothesis 累加。

**碼證**: `optimization_task_service.py:251` `storage=f"sqlite:///data/optuna_{study_name}.db"`；API `study_name` 使用者可控 `optimization.py:58`。

**來源摘要**: api/routes/optimization.py#93008df279ae

[MINOR] 信心度=High；Ledger 須以 `research_session_id` 聚合，非單 study。

---

## COMPOSER-R1-P2-02

**斷言**: brief 假設「三件套只需報酬序列＋N」對 PBO 不成立——PBO 最少需同一資料窗上 **≥2 個候選策略** 的 OOS 績效矩陣，單條 champion 報酬序列不夠。

**碼證**: `optimization_output_service.py:150-171` 可導出 `trials` 列表；`trial_comparison.py:87-113` 支援多 trial 比較——資料存在但未接 PBO；Bailey 2015 CSCV 定義需策略集合。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#18f5f08ee8c0

[MINOR] 信心度=High；SPEC Phase C 須定義「候選矩陣」最小維度與來源（Optuna complete trials）。

---

## §1 必查（11 類摘要）

| 類 | 結論 |
|---|---|
| 1 矛盾 | brief 假設「獨立模組」與 PBO 多矩陣需求矛盾——見 P2-02 |
| 2 漏項 | 無 ledger、無 strategy wiring、無 UI gate |
| 3 不可測 | charter 已有 F-ST-2/3 錨點，可測；缺實作 |
| 4 quant 假設 | cumsum/年化/N 層級——見 P0/P1 |
| 5 過度工程 | 反對先做全域 queue；ledger + 三純函式足夠 |
| 6-11 | 無額外 BLOCKING；PBO 組合數需注意 `max_paths` 規模 |

---

## VERIFY / 收尾

- `grep -rn "deflated|DSR|PBO|CSCV|MinBTL|min_btl" --include="*.py" momentum api` → 0 命中
- `/tmp` 無本任務 workdir（僅保留 `claude-501`）
- 產出：`handoffs/20260817-gap1-recon-composer.md`

---

ASSUMPTIONS_VERIFIED: repo 無三件套實作；N 帳本碎片化；報酬序列三語意；CPCV≠PBO CSCV；ic_wiring 不蓋策略欄位  
TESTS_RUN: `grep` DSR/PBO 零命中；`shasum` 來源摘要；`completeness_check.sh --single`（見下）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（只讀偵察）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）

STATUS: DONE
