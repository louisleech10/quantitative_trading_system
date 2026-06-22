# 特徵管線「上線須留存參數」盤點 — R2 整合清單（待 R3 收斂）
> Opus+Codex+Composer 三家 R1 各自產 → R2 雙家交叉審(兩家一致)。本檔=R2 整合。日期 2026-06-22。
> 判準:A=校準樣本搜/擬/全樣本統計(須留存或改causal);A-schema=全run決定欄存在(須pin特徵清單);B=從起點累積不收斂(一致reset+state);D′=因果遞推收斂(只須足夠burn-in,上線可重算);C=peer依賴;D=固定窗rolling/純函數安全。

## A — 擬合/搜尋/全樣本統計（須留存或改 causal）
| # | 項 | 層 | 機制 | 現況 | 嚴重度 | R2 共識 |
|---|---|---|---|---|---|---|
| A1 | **fracdiff d\*** (+Hurst-prior 子機制 `_hurst_prior.py:36-77`) | L6.5 | ADF二分搜最小平穩d,前500校準 | ⚠️共用快取未綁run/model | **高**(實證漂) | 三家 |
| A2 | ADF integer diff (`chosen_diff`) | L6.5 | 前500 ADF每欄差分階 | ❌無持久化;**預設OFF**,僅 professional_full/golden 開 | 高(僅啟用時) | 兩家R2 |
| A3 | non_stationary 分類 | L6.5 | ADF前500→欄集合 | 記憶體cache | 中(同A2路徑) | Composer |
| A4 | L2 safe_denominator | L2 | **全欄median×1e-6**(`numeric_guards.py:48`) | 即時算 | 低 | 兩家R2→**建議改causal/rolling robust scale,不留存** |
| A5 | labels winsorized | labels | 全樣本quantile+未來shift(-h)(`label_generator.py:78`) | **opt-in**(IC-First預設label=pct_change.shift(-1)不走) | 中(啟用時=look-ahead偏置IC/ML評估,命中(d)) | 兩家R2 |

## A-schema — 全 run 決定欄存在（上線須 pin 特徵清單）
| S1 | dead/drop + L3 variance_filter | L3/L7 | 全run nunique/std/nan_rate/valid_count 決定欄存在 (`dead_feature_filter.py:44-92`,`rolling_aggregator.py:799-827`) | 兩家R2 |
| S2 | L3 skew/kurt low-card skip | L3 | 全欄nunique決定生成 (`rolling_aggregator.py:773-789`) | 兩家R2 |
→ 漏 pin → 訓練 vs 上線特徵清單漂移(缺欄/多欄)。

## B — 路徑依賴不收斂（一致 reset/burn-in + 帶 state）
| B1 | OBV/AD | L1 | 純累加器,絕對level永不收斂 | 三家 |
| B2 | ADOSC | L1 | cumulative+EMA混合,須一致起點 | 兩家R2 |
| B3 | **SAR** | L1 | stateful pivot (`warmup_table.yaml:287-294`) | **Composer R2 新增** |

## D′ — 因果遞推收斂（只須足夠 burn-in,上線可重算;非須帶 state）
EMA/MACD/Wilder/Hilbert/KAMA/Klinger:`warmup_table` 標 `all_periods_converged:true`(:106-177)。**R1 Composer 誤列 B → R2 兩家降級 D′**。上線:pin burn-in factor 即可。

## C — peer/universe 依賴
| C1 | L5 cross-sectional | vs `config.reference_symbol`(rolling β/價比,非fit) | 上線須同reference即時資料對齊 | 三家 |

## D — 安全（因果可重算,無須留存）★三家確認
gaussian(rolling rank+ndtri,**非fitted**,修正Opus初版)、VWAP(`rolling(20)`非cumulative,修正yaml)、winsor/zscore/rank(rolling)、entropy R/S(窗內cumsum)、L4 lag、L6 meta(逐列)、native/multi-TF alignment(deterministic,版本須一致)、L7 validation(只寫metadata)。

## 死碼/守衛(現不可達,若重啟用=A)
- polars 非因果 full-column winsor (`polars_adapter.py:426-443`) — causal=True 釘死
- numba `winsorize_array` 全欄quantile + 非因果sigma (`_numba_transforms.py:340-369,428-452`) — causal=True 守衛

## ★R3 待決:範圍是否含 Analysis/IC/ML 層（E3,Codex）
`momentum/Analysis/data_preprocessor.py` 有**自己的全樣本 zscore/winsor/drop gates**(:114-172) + probability calibrator/模型 `.fit()` = 訓練 artifact。**這是 FF 之外、但最直接的「帶入上線」參數**(模型本身+其 scaler)。R3 待:(a)是否納入盤點 (b)若納入,catalog 清單。

## R3 收斂檢查項
1. 確認 SAR(B3)、Hurst-prior(A1子)、ADF預設OFF、A5 opt-in、B2→D′。
2. Analysis/ML 層(E3)是否納入 + catalog。
3. **零新增檢查**:R3 是否還有任一層任一項未列(若零=收斂)。
