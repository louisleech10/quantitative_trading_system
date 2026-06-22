# 上線須留存參數 — 三方三輪權威清單（FINAL）
> Opus + GPT-5.5(Codex) + Composer2.5,各自產 R1 → R2 交叉審 → R3 最終收斂。三輪,作者非自審。
> **收斂**:R3 兩家一致確認 FF 特徵管線 **CONVERGED**(零新增生產項);E3 訓練 artifact 已 catalog;周邊(Optimization)已納。日期 2026-06-23。
> 判準:A=校準/搜尋/全樣本統計(上線無法因果重算,須留存或改causal);A-schema=全run決定欄存在(須pin特徵清單);B=累積不收斂(一致reset+state);D′=因果遞推收斂(只須足夠burn-in);C=peer依賴;D=固定窗rolling/純函數(安全,無須留存)。

## 一、FF 特徵管線（CONVERGED）

### A — 擬合/搜尋/全樣本統計（須留存或改 causal）
| # | 項 | 層 | 現況 | 嚴重度 | 上線處置 |
|---|---|---|---|---|---|
| A1 | **fracdiff d\*** (+ Hurst-prior 子機制) | L6.5 | 共用快取未綁 run/model | **高**(實證換窗漂 0.13↔0.81) | **持久化綁 run/model**(固定參考 epic) |
| A2 | ADF integer diff (`chosen_diff`) | L6.5 | 無持久化;**預設 OFF**,僅 professional_full/golden 開 | 高(僅啟用時) | 啟用則須留存每欄差分階 |
| A3 | non_stationary 欄集合 | L6.5 | 記憶體 cache | 中(同 A2 路徑) | 同 A2 |
| A4 | L2 safe_denominator | L2 | 全欄 median×1e-6,即時算 | 低 | **改 causal/rolling robust scale**(不留存) |
| A5 | labels winsorized | labels | **opt-in**(預設 label=pct_change.shift(-1) 不走) | 中(啟用=look-ahead 偏置 IC/ML 評估) | 改 train-split 內分位 或棄用 |

### A-schema — 全 run 決定欄存在（須 pin 特徵清單）
- **S1** dead/drop + L3 variance_filter:全 run nunique/std/nan_rate/valid_count 決定欄存在。
- **S2** L3 skew/kurt low-card skip:全欄 nunique 決定生成。
- 上線:模型期望欄位集合須與訓練一致(缺欄/多欄會壞)。

### B — 路徑依賴不收斂（一致 reset/burn-in + 帶 state）
- **B1** OBV/AD(純累加器永不收斂)、**B2** ADOSC(cumulative+EMA,須一致起點)、**B3** SAR/**SAREXT**(stateful pivot)。

### D′ — 因果遞推收斂（只須足夠 burn-in,上線可重算）
- EMA/MACD/Wilder/Hilbert/KAMA/Klinger(`all_periods_converged:true`)。上線 pin burn-in factor 即可。

### C — peer 依賴
- **C1** L5 cross-sectional:vs `config.reference_symbol`,上線須同 reference 即時資料對齊。

### D — 安全（因果可重算,無須留存）★三家確認
gaussian(rolling rank+ndtri,非fitted)、VWAP(rolling20 非cumulative)、winsor/zscore/rank(rolling)、entropy R/S(窗內)、L4 lag、L6 meta、native/multi-TF alignment(deterministic,版本一致)、L7 validation(只寫metadata)、position_sizing(純公式)。
**死碼守衛**:polars/numba 非因果全樣本 winsor(causal=True 釘死,重啟用則=A)。

## 二、Analysis / IC / ML 層（E3,訓練 artifact,上線推論必帶）
- **DataPreprocessor 全樣本**:覆蓋率/常數丟欄、time_series_zscore mean/std、winsor 分位/MAD/zscore(`data_preprocessor.py:113-172`)→ 類 A,須 pin 或改 causal。
- **選中特徵集**:IC `ic_selected_features_{sym}_{tf}.json`(`ic_engine.py:146`)、redundancy filter 選/棄欄。
- **模型權重**:LGBM(`lightgbm_analyzer.py:237`)/XGB(`xgboost_analyzer.py:437`)+`feature_names`。
- **校準映射**:probability_calibrator Isotonic/Platt/beta 擬合係數(`:267-285`)。
- **診斷-only(非預設推論熱路)**:PCA/KMeans factor centrality、regime detector、VIF。

## 三、Optimization 層（部署策略須帶）
- Optuna best params/study/sampler/checkpoint(`optuna_optimizer.py:2133-2164`)——部署即帶。
- ⚠️ sample_weight `compute_time_decay` 用 `parsed.max()`(全樣本)→ 須限 train split 內算(`sample_weight_calculator.py:50-68`)。

## 四、確認安全（無洩漏/無須留存）
CPCV/walk-forward split:purge+embargo 設計,方法論非 state,無洩漏(`combinatorial_purged_cv.py:50-82,181-195`)。Strategy 回測累積值=評估輸出非上線參數。

## 五、結論
- **FF 特徵管線三輪 CONVERGED**。上線須留存核心 = **A1 d\*(最高優先)** + A2/A3(若開 ADF) + A-schema 特徵清單 + B 累積起點 + C reference。A4/A5 建議改 causal/限 train-split。
- **完整上線=三層**:FF 參數(本表一) + IC/ML 訓練 artifact(表二) + Optimization 部署參數(表三)。
- **修法=productionization epic**(大,命中(d)),範圍由使用者定(FF-only / +Analysis / 全棧)。本盤點=精確範圍清單,三方簽核無遺漏。
