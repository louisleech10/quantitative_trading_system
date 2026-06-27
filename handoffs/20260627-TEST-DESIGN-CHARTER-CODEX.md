以下是補全版章程，可作為草稿 v0 的替換/合併基礎。已讀 `HANDOFF.md`、`CLAUDE.md`、指定 handoff 草稿，並抽查 Feature Factory、IC Gatekeeper、回測、d-star cache、pytest 設定與代表性測試。

**測試設計 & 驗證審查章程 v1**
**§0 分級原則**
所有測試先標註保證等級：
- `correctness`: 可證明數值/資料/防洩漏正確，必須有反例或 mutation 證明改壞會 fail。
- `contract`: 驗 API/schema/解耦/相容性，不宣稱量化正確。
- `regression`: golden 或快照，需有版本、來源、再生腳本。
- `smoke`: 只驗路徑不炸，不得算入正確性簽核。
- `perf`: 效能回歸，除非同時驗輸出等價，否則不得替代 correctness。

**§A 測試類別地圖**
1. `資料真實性/完整性`
測 schema、dtype、timestamp 單位、OHLCV 合法性、缺口、重複、排序、symbol/timeframe 隔離、真實來源。
過關：真 kline 路徑跑過；metadata 含 source/version/row_count/time_range/schema hash；OHLC 約束全量掃描；無 fake/hardcoded prices；資料缺口策略明確為 fail-closed 或可追溯 fallback。

2. `防洩漏/PIT/OOS`
測 train/test chronological split、purge >= label horizon、embargo、fit-on-train、label shift、rolling/window 僅用過去、test 只用一次。
過關：對 test 區注入極端值，不影響 train fit 參數與 train 指標；對 purge gap 內資料擾動不影響 test label；打亂未來資料不影響過去信號；所有 OOS 報告 metadata 明示 `scope` 與 `oos_guarantees`。

3. `數值正確性/golden`
測 deterministic output、NaN/inf gate、float32/float64/float16 轉換、全表 hash、容差。
過關：非隨機欄位 byte-equal；浮點只允許經審查的 `atol/rtol`，並按尺度寫明來源；NaN/inf 數量、位置、warmup 區間必比較；輸出大小/schema 改變必在報告標紅。

4. `Property-based / Hypothesis`
測一般性質而非單例：單調性、冪等、排序不變性、尺度不變性、邊界穩定、cache key collision resistance。
過關：固定 seed、最小反例可重現、生成策略覆蓋空/單列/全 NaN/常數/極端值/亂序/重複 timestamp。現況 `requirements.txt` 未見 Hypothesis，應作為測試基礎設施補項。

5. `Metamorphic testing`
測沒有 oracle 時的關係：價格乘常數後 return/IC rank 不變；feature 欄位順序改變不影響結果；symbol 順序改變不影響 cross-symbol aggregate；新增無關未來資料不改過去輸出。
過關：每個高風險模組至少 2 條 metamorphic relation，且有負例能 fail。

6. `Fuzzing / robustness`
測 API payload、HDF5/manifest/parquet、config_override、feature names、symbol/timeframe token、NaN/inf payload、corrupt cache。
過關：無 silent success；錯誤分類 retryable/non-retryable 正確；corrupt artifact 不污染下一 run；fuzz case 保存為 regression fixture。

7. `邊界/退化`
測 empty、single row、短於 rolling window、全常數、全 NaN、零 volume、負價格、timestamp gap、duplicate、non-monotonic、多 timeframe 缺一腿。
過關：預期結果逐條寫明：raise、skip、fallback 或 empty report；不得用 broad `except` 吃掉資料錯誤。

8. `整合/真實管線`
測 materialized service/full run，不只 unit fixture。
過關：走真實 ingestion/storage/Feature Factory/IC path；至少 BTC/ETH + 1h/4h；真實 `data_cache/feature_klines/kline_cache.h5` 可用時跑 blocking，缺失時明確 skip reason。

9. `Cache / artifact / resume`
測 config hash、schema hash、data fingerprint、symbol/timeframe isolation、atomic write、stale invalidation、legacy migration、partial run status、resume。
過關：改資料 fingerprint 必 miss；跨 symbol/timeframe 不共享；corrupt manifest 不假成功；atomic temp 不殘留；resume 後與 fresh run 等價。

10. `多 symbol / cross-sectional`
測 symbol isolation、MultiIndex 對齊、label 對齊、symbol 順序不變性、cross-symbol sign conflict、缺 symbol/time slice。
過關：同一 timestamp 只跨當下 symbols；label 不可由單幣 timestamp reindex 誤貼；任一 symbol 缺失不改其他 symbol IC；報告列出每 symbol n、coverage、IC dispersion。

11. `回測真實性`
測交易會計、成本、滑價、entry/exit 時點、同 bar stop/take-profit 優先序、未平倉、MAE/MFE、position sizing、equity curve。
過關：手算小表逐 trade 精確比對；成本雙邊扣除；不能用 exit timestamp 找不到就 silent skip；每個 exit_reason 有 deterministic oracle；禁止未來 bar 影響 entry。

12. `統計/量化嚴謹`
測 IC、ICIR、t-stat、CI、FDR、bootstrap、regime stability、PBO/DSR、turnover、capacity。
過關：門檻有來源；多重比較必校正；小樣本標 low-confidence 或 skip；顯著性與 effect size 同時報告；不能只看 p-value。

13. `ML 訓練/模型驗證`
測 time-series CV、purged/embargo CV、walk-forward、class imbalance、calibration、feature importance stability、SHAP sanity、train/val/test 隔離。
過關：random split 禁用於時間序列主 gate；test set 只用一次；model artifact 帶 train window/config/data hash；label leakage adversarial 必 fail。

14. `API/contract/typing`
測 Pydantic ↔ TypeScript schema、flag default、backward compatibility、error payload、WebSocket progress。
過關：新增欄位有 default/migration；flag-off deep-equal 舊行為；DTO 不跨域；`./scripts/check_decoupling_phase4.sh` pass。

15. `CI flaky 隔離`
測試分層：`smoke` blocking、`correctness-real-data` blocking on data host、`slow/perf` opt-in、`network` quarantined。
過關：flaky 不得直接 xfail 掩蓋；需有 issue/owner/last_seen/retry budget；CI 報告區分 product fail vs infra fail；同一 flaky 連續 3 次進 quarantine，不可刪斷言。

16. `Test data 版本化`
所有 golden/fixture 必有 manifest：source、生成命令、code commit、schema hash、row count、time range、symbol/tf、sha256、是否 synthetic。
過關：再生腳本存在；golden 更新需 diff 摘要與理由；synthetic fixture 只能測邊界/contract，不能替代真實資料正確性。

**§B 本專案具體必測清單**
- Feature Factory：7 層每層 row/index 守恆、L6.5 winsor/rank/zscore/fracdiff causality、warmup trim、L7 raw/processed manifest、CGSA sharding/resume、multi-TF align、NaN/inf gate、float16 fallback、progress/fail-open/fail-closed 語義。
- IC Gatekeeper：`analyze()` 已有 holdout/purge/train mask 接線，需持續測 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:168) 與 stage1 `fit_mask` [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:405)；`analyze_cross_sectional()` 目前 `p_value=None`，需補 cross-sectional label alignment、per-timestamp rank corr、symbol matrix 統計檢定 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:630)。
- Cache：d-star context 包含 symbol/timeframe/config/data/schema/time_range/row_count/source version [\_d_star_cache.py](/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/preprocessing/_d_star_cache.py:31)，必測 strong/weak fingerprint 與 exact column fingerprint [\_d_star_cache.py](/Users/louis/Desktop/quantitative_trading_system/momentum/FeatureEngineering/preprocessing/_d_star_cache.py:245)。
- 回測：目前 long-only event loop，stop_loss 優先於 take_profit，equity 只在 exit bar realized PnL [vectorized_backtest.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Strategy/vectorized_backtest.py:217)。必補同 bar ambiguity、unknown exit timestamp 不可 silent、position size 上限、成本與 MAE/MFE 手算 oracle。
- CI：`pytest.ini` 已有 `slow/perf/analyze_real_run` 等 marker [pytest.ini](/Users/louis/Desktop/quantitative_trading_system/pytest.ini:23)，需新增 `real_data`, `network`, `flaky_quarantine`, `property`, `metamorphic` 分層。

**§C 量化/統計檢定清單**
- IC/Rank IC：Spearman/Pearson、rolling IC、ICIR、hit rate、Newey-West 或 block bootstrap CI（處理 autocorrelation）。
- 顯著性：one-sample t-test 只作 baseline；補 sign test、Wilcoxon、permutation test。
- 多重比較：FDR-BH 必做；高維 feature mining 加 Bonferroni/Holm 作敏感性；報 adjusted p-value。
- 穩健性：regime split、rolling OOS、walk-forward、subsample bootstrap、symbol leave-one-out、time block leave-one-out。
- 過擬合：Deflated Sharpe Ratio、Probabilistic Sharpe Ratio、PBO/Combinatorial Purged CV、White Reality Check 或 SPA（策略/因子多重試驗時）。
- 回測：Sharpe/Sortino/Calmar CI、max drawdown bootstrap、turnover/cost sensitivity、capacity/slippage stress、trade duration distribution、exposure-adjusted return。
- 分布：Jarque-Bera/normality 僅診斷；ADF/KPSS/Hurst 用於 stationarity；tail risk 用 CVaR/expected shortfall。
- 分類模型：AUC/PR-AUC、Brier score、calibration curve、ECE、threshold stability、confusion matrix by regime。

**§D 審查紀律**
每個 SPEC 必含「測試章程」：選哪些類別、不選原因、每條 property/metamorphic relation、真實路徑命令、golden 更新策略、mutation 反例。  
Code review 必審測試本身：是否測錯路徑、是否 sanitized fixture、是否只查 shape、是否放寬舊斷言、是否把 perf 當 correctness。  
正確性簽核條件：資料/洩漏/數值類需真實 run + mutation + 三方獨立 review；任一缺失只能標 `partial confidence`。

HANDOFF_NOT_UPDATED: read-only sandbox；依本任務要求未改檔，補全版已在回覆輸出。  
ASSUMPTIONS_VERIFIED: 已確認 IC holdout/purge/train-mask 接線、cross-sectional p_value 缺失、回測交易會計路徑、d-star cache context/fingerprint、pytest marker 現況、requirements 未含 Hypothesis。  
TESTS_RUN: 未跑 pytest；本任務是 read-only 測試章程審查。執行了 `sed`/`rg`/`nl` 讀取指定 handoff、規範、核心碼與代表性測試。  
FAILURES_SEEN: `rg` 查詢因不存在 `pyproject.toml/setup.cfg` 回傳非零，但已用 `ls/find` 確認專案有 `pytest.ini` 與 `requirements.txt`。  
SCOPE_CHANGES: none。  
NUMERIC_OR_SCHEMA_IMPACT: none，未改程式或資料。  
STATUS: DONE