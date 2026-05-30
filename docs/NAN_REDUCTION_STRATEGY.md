# NaN 處理策略（First Principle 版）

> **日期**：2026-05-26  
> **取代**：本文件之前所有 v1.0–v2.6 ULTRATHINK 與「乾淨版 v1/v2」。  
> **本版核心**：
> 1. NaN ratio 不是品質指標；不以 NaN ratio 為閾值丟欄位
> 2. 不可能三角：「樣本數不變 + 計算時間不增 + target window 無 warmup NaN」三者只能挑二
> 3. Layer-by-layer 攔檢的真正價值，不是減 NaN，是省「計算了也沒意義」的下游 derivation
> 4. 每個指標、每個 L2 operator 在每條下游路徑都明確分類為：必擋（數學錯誤）/ 可擋（計算冗餘）/ 不擋（IC Gatekeeper 處理）

---

## 1. 從零定義問題

### 1.1 NaN 種類

| 種類 | 成因 | 是否「壞」？ |
|------|------|------------|
| Warmup NaN | 指標需 N 根 bar 才能算第一個值 | 否，物理必然 |
| Cross-TF align NaN | 12h 指標 align 到 1h，warmup × tf_ratio 放大 | 否，同上 |
| Cascade NaN | 上游 NaN 經 rolling/lag/diff 繼承並加 W−1 / k / width−1 | 否，機制必然 |
| Data-gap NaN | OHLCV 真實缺口（交易所維護）| 中性，誠實標註 |
| Math-undefined NaN | 除零、log(0)、corr 於常數序列 | 局部邊緣，誠實標註 |

### 1.2 為何「NaN ratio 高 → 丟欄位」是錯的

EMA(233) 12h 在 20,352 row 1h primary 上若有 14.8% NaN，剩 17,340 row 是**完全正確的長期趨勢值**。XGBoost/LightGBM 原生處理那 14.8% NaN（學最優分裂方向），同時用 85.2% 訊息訓練。**丟此欄 = 丟 85.2% 有效訊號**，違反「不縮減特徵」約束。

→ NaN ratio 在 0%~99% 之間都**不是**丟欄位的理由。只有兩種條件該丟：
- `nunique() < 2`（整欄常數，零信號）
- target window 內 `valid_count < N_min`（樣本不足無法學習，例如 < 100）

### 1.3 「合理的 NaN」標準

可解釋、可預期、不影響下游模型。具體：

| 條件 | 標準 |
|------|------|
| target window 內 warmup-來源 NaN | 視模式而定（見 §2 不可能三角） |
| target window 內 data-gap / math-undef NaN | 保留；XGBoost 處理 |
| 「計算本身錯誤」欄位（CDL rolled、HT_DCPHASE rolled） | **0**（cascade 拒收，不是事後 drop） |
| `nunique<2` 或 `valid<N_min` 欄位 | **0**（L7 drop） |

---

## 2. 不可能三角（核心 trade-off）

實務上 HDF5 通常就是「使用者下載的範圍 = 想要的目標範圍」，前面沒 spare history 可借。在這個約束下：

> **同時做到「樣本數不變 + 計算時間不加 + target window 無 warmup NaN」是物理不可能。**

三個自由度只能挑兩個：

> **⚠️ 命名注意**：本文件「Plan No-Buffer / L7-Trim / Pre-History」是針對 **warmup buffer 處理**。  
> code 內另有一組同名「L6.5 Mode A/B/C」（legacy / ic_first_pre / none）是針對 **L6.5 preprocessing 路由**，兩者完全無關。見 §9。

| Plan | 樣本數 | 計算時間 | target window NaN | buffer 概念 | 適用 |
|------|--------|---------|------------------|------------|------|
| **Plan No-Buffer**（預設，什麼都不多做） | 不變 | 不變 | **前段帶 warmup NaN**，XGBoost 處理 | **不適用**（沒 buffer） | 預設；不想多花時間又不想砍樣本 |
| **Plan L7-Trim**（可選 flag，L7 開頭 trim） | 減少（砍 N row） | 不變 | 乾淨 | buffer = 即將被砍掉的「前 N row」 | 長 dataset 且能接受砍頭 |
| **Plan Pre-History**（使用者工作流，事先多下載 history） | 不變 | 約 ×2 | 乾淨 | buffer = 使用者**自己事先**從交易所多下載的歷史（在 target window 起點之前） | 重要實驗，接受多花時間 |

**關於 Plan No-Buffer 的 warmup NaN**：是的，前段（不同特徵長度不同）會帶 NaN。例如 T3(233) 12h + L3(233) 那欄前 ~19,560 row 是 NaN，EMA(5) 1h 前 4 row 是 NaN，所有特徵的 NaN 都「靠左對齊」散開分佈。XGBoost/LightGBM 原生處理，**沒有問題**。「合理 NaN」對 Plan No-Buffer 的定義就是這種「可解釋的左側 warmup tail」。

**buffer 計算公式（Plan L7-Trim / Plan Pre-History 才用得到）**：

```
buffer_in_primary_tf = max over 所有實際存在的 (ind, tf, period, downstream_W, downstream_k):
    [warmup_bars(ind, period) + L3_rolling_W + L4_lag_k + (fracdiff_width − 1 if enabled)] × tf_ratio(tf → primary)
```

- `warmup_bars(ind, period)` 查 `momentum/FeatureEngineering/atomic/warmup_table.yaml`（**per-indicator**，已實作）
- `tf_ratio = tf_minutes / primary_minutes`
- 兩個 TF 都從同一 wall-clock start 讀，bar 數因 TF 而異

**多 symbol**：每個 symbol 獨立 buffer，獨立 fallback。**絕不為對齊所有 symbol 而砍老幣的 target window**（Lopez de Prado 明確反對）。

**決議：預設 Plan No-Buffer**。Plan L7-Trim / Plan Pre-History 為 opt-in。

---

## 3. Layer-by-Layer 攔檢的真實價值

**不是減 NaN（不可能三角告訴我們減不了）**。  
是清掉「**計算下去既沒意義、又浪費 CPU**」的下游 derivation，順便去掉「**數學錯誤值**」。

對每條 cascade 路徑，每個 L1 指標 / L2 operator 都會落在三類之一：

| 類別 | 該怎麼做 | 例子 |
|------|---------|------|
| **(a) 必擋 — 計算本身錯誤** | cascade block；上游 L1 仍保留於 feature store | CDL rolled、HT_DCPHASE rolled |
| **(b) 可擋 — 計算冗餘 / 數學對但低資訊密度** | 視乎省時/省空間需求；可擋可不擋 | rank of binary, fracdiff of I(0), rolling mean of HT_SINE |
| **(c) 不擋 — 計算對且可能有 IC** | 全部送下去，IC Gatekeeper 評估 | RSI rolling slope, EMA distance |

---

## 4. 各層詳細盤點

### 4.1 L1 → 下游：依「統計性質」分類

| L1 類別 | scan_config 中的指標 | I(0)/I(1) | L2 ops | L3 rolling | L4 lag | L6 meta | L6.5 fracdiff | L6.5 rank/zscore |
|---------|---------------------|-----------|--------|-----------|--------|---------|--------------|-----------------|
| **趨勢追蹤型** | EMA, SMA, WMA, DEMA, TEMA, TRIMA, KAMA, T3, MAMA, HT_TRENDLINE, MIDPOINT, MIDPRICE, SAR, SAREXT, BBANDS-{U,M,L}, MAVP, MA, LINEARREG, LINEARREG_INTERCEPT, TSF, Keltner-{U,M,L}, Donchian-{U,M,L}, VWAP | I(1) 跟價格 | ✅ 全部 | ✅ 全部 | ✅ | ✅ | ✅ **語義正確**（I(1) → fracdiff 使其 stationary 保留 memory）| ✅ |
| **累積型 volume** | OBV, AD | I(1) | ✅ 全部 | ✅ 全部 | ✅ | ✅ | ✅ **語義正確** | ✅ |
| **絕對波動率** | ATR, Parkinson_Vol, GarmanKlass_Vol | I(1) 量級 | ✅ 全部 | ✅ 全部 | ✅ | ✅ | ✅ **語義正確** | ✅ |
| **正規化波動率** | NATR | I(0) | ✅ 全部 | ✅ 全部 | ✅ | ✅ | **(b) 可擋**：ADF 必判 I(0) → 不執行 fracdiff，但 ADF 測試本身仍跑（每欄一次 ADF≈幾 ms × 數十萬欄 = 顯著浪費）| ✅ |
| **I(0) 有界振盪器** | RSI, CCI, CMO, ADX, ADXR, DX, WILLR, MFI, AROON, AROONOSC, ULTOSC, STOCH-{k,d}, STOCHF-{k,d}, STOCHRSI-{k,d}, BOP, LINEARREG_ANGLE, CORREL | I(0) 有界 | ✅ 全部 | ✅ 全部 | ✅ | ✅ | **(b) 可擋**：同上 ADF 浪費 | ✅ |
| **I(0) 無界差分/震盪** | MOM, ROC, ROCP, ROCR, ROCR100, MACD-{Line,Hist,Signal}, MACDEXT-{...}, MACDFIX-{...}, APO, PPO, TRIX, LINEARREG_SLOPE, STDDEV, VAR, BETA, PLUS_DI, MINUS_DI, PLUS_DM, MINUS_DM, TRANGE, ADOSC, Force_Index, Klinger_Volume_Osc, Volume_MA_Ratio, Ease_of_Movement | I(0) | ✅ 全部 | ✅ 全部 | ✅ | ✅ | **(b) 可擋**：同上 ADF 浪費 | ✅ |
| **循環相位（math wrong）** | HT_DCPHASE | 0–360° wrap | **(a) 必擋全部**：rolling/diff/lag/distance 在 359→1° 翻轉處算出錯誤值 | (a) 必擋 | (a) 必擋 | (a) 必擋 | (a) 必擋 | (a) 必擋 |
| **週期 sinusoid** | HT_SINE, HT_LEADSINE, HT_PHASOR-{inphase, quadrature} | 有界 oscillator | ✅ 全部 | ✅ 全部 | ✅ | ✅ | **僅 ADF safe-skip**（HT_SINE/LEADSINE 已嚴格有界 → §4.5 whitelist；HT_PHASOR 保留 ADF）| ✅ |
| **週期 period scalar** | HT_DCPERIOD | 正值，semi-stationary | ✅ 全部 | ✅ 全部 | ✅ | ✅ | 保留 ADF（無數學硬限）| ✅ |
| **二元 regime** | HT_TRENDMODE | {0,1} 稀疏 | ✅ 全部（lag of binary、% trend time 都有資訊；rank of binary 雖 trivial 但無害，IC Gatekeeper 處理）| ✅ 全部 | ✅ | ✅ | **僅 ADF safe-skip** | ✅ |
| **稀疏離散形態（已由程式碼層守護）** | CDL2CROWS … CDLXSIDEGAP3METHODS（共 61 個）| {−100, 0, +100} 97%+ 為 0 | **(a) 必擋全部**：97% 0 的衍生 ≈ 全 0 / 全錯。`RATIO_UNSAFE_CATEGORIES = {"pattern"}` 已守 L2 Distance/Momentum/Ratio/SignedStrength/WorldQuant；BinarySignal 規則未涵蓋（安全）| (a) 必擋（程式碼層 ✓）| **(a) 必擋**（L4 non-CGSA 路徑要補強守護）| (a) 必擋 | (a) 必擋 | (a) 必擋 |

**L1 路徑總結**：
- 唯一 **(a) 必擋**：CDL_PATTERN_ALL（程式碼已守，需補強 L4 non-CGSA / L5 / L6 / L6.5）+ HT_DCPHASE（需新增 config 黑名單覆蓋所有下游）
- **(b) 可擋以省時**的主要熱點：**ADF 測試在所有 I(0) 欄位上的計算浪費**（這是 §4.5 重點）
- 其他都是 **(c) 不擋**：交給 IC Gatekeeper

### 4.2 L2 operators → 下游：依 operator 性質分類

L2 七個 category 的輸出：

| L2 category | 輸出性質 | 下游路徑 | L4 (non-CGSA) | L6 meta | L6.5 fracdiff | L6.5 rank/zscore/gaussian |
|------------|---------|---------|--------------|---------|--------------|-------------------------|
| **Distance**（MA1 − MA2 / price − MA）| I(0) 連續，圍繞 0 | ✅ ✅ ✅ ✅ | ✅ | ✅ | **(b) 可擋**：ADF 必 skip | ✅ |
| **Cross**（MA1 vs MA2 上下穿越）| 0/1 二元 | — | ✅ lag of binary 有資訊 | ✅ | **僅 ADF safe-skip**（§4.5 whitelist）| rank/gaussian 雖 trivial 但無害，不擋；IC Gatekeeper 處理 |
| **Ratio**（MA1 / MA2）| I(0) 圍繞 1 | ✅ | ✅ | ✅ | **(b) 可擋**：ADF skip | ✅ |
| **Momentum**（lag / ROC of L1）| I(0) | ✅ | ✅ | ✅ | **(b) 可擋**：ADF skip | ✅ |
| **BinarySignal**（RSI>70 等 7 條規則）| 0/1 二元 | ✅ lag 有資訊 | ✅ | **僅 ADF safe-skip** | 不擋；IC Gatekeeper 處理 |
| **SignedStrength**（sign × magnitude）| 視 L1 base：I(0) base → I(0)；I(1) base → I(1) | ✅ | ✅ | 保留 ADF（依 base 而定）| ✅ |
| **WorldQuant** — `ts_rank` | 有界 [0,1] | ✅ | ✅ | **僅 ADF safe-skip** | 不擋 |
| **WorldQuant** — `ts_argmax` / `ts_argmin` | 離散整數 [0, W−1] | ✅ | ✅ | **僅 ADF safe-skip** | 不擋 |
| **WorldQuant** — `ts_corr` | 有界 [−1, +1] | ✅ | ✅ | **僅 ADF safe-skip** | ✅ |
| **WorldQuant** — `decay_linear` | I(1) 若 input 是 I(1) MA | ✅ | ✅ | ✅ **語義正確**（應執行 fracdiff）| ✅ |
| **WorldQuant** — `sign` | {−1, 0, +1} 離散 | ✅ | ✅ | **僅 ADF safe-skip** | 不擋 |
| **WorldQuant** — `log1p` / `abs` / `clip` | 視輸入 | ✅ | ✅ | 保留 ADF | ✅ |

**重點**：L2 沒有 (a) **必擋** 案例（CDL 已由 RATIO_UNSAFE_CATEGORIES 程式碼層守於 L2 入口）。`§8.2` 已決議「rank of binary、gaussian of discrete」這類數學對但低資訊的衍生**不擋**，全部交給 IC Gatekeeper。唯一干預的是 §4.5 的 ADF safe-skip（純省時，不改變欄位數量）。

### 4.3 L3 → L4：rolling aggregator 輸出

L3 輸出**只**流向 L4（non-CGSA 路徑），不進 L5/L6/L6.5（程式碼驗證 §2 之前已 cite）。

| L3 aggregator | 輸出性質 | L4 lag 是否有意義 |
|---------------|---------|------------------|
| slope, std, mean, rank, zscore, skew, kurt, min, max, range | 對絕大多數 L1 都有資訊 | ✅ lag of L3 有資訊（前一段時間的 rolling 統計） |

L3 → L4 沒有 (a)/(b) 案例。L3 階段的 (a)/(b) 已在 L1→L3 input 那關處理（即 CDL/HT_DCPHASE 已不會出現在 L3 input）。

### 4.4 L6 meta features

scan_config 中 `meta_features`：trend_consensus, momentum_divergence, volume_price_divergence, time_features, volatility_regime

這些是**特定組合**（不是 cartesian），讀取特定欄位類別。需驗證實作是否會踩到 CDL/HT_DCPHASE（理應不會，因 meta 設計就是針對連續型 L1）。

**驗證需求**（T6 任務）：grep meta_features.py 確認其讀取的欄位 list 不含 CDL/HT_DCPHASE。

### 4.5 L6.5 fracdiff / ADF：**最大計算浪費熱點**

當前 scan_config：`fractional_differencing.enabled: false`、`adf_differencing.enabled: false`。但若使用者啟用，需理解這裡是最大的浪費點。

**機制**：fracdiff 對每欄先跑 ADF 測試判定 I(0) 或 I(1)。若 I(0) → 跳過 fracdiff；若 I(1) → 執行 fracdiff。

**問題**：ADF 測試本身對每欄都跑（不論最終是否執行 fracdiff），對數十萬欄是顯著 CPU 浪費。

**By-name fast-skip 的數學依據**：

要讓「不跑 ADF、直接判 I(0)」這個 skip 安全，欄位必須滿足下面任一條件：
- **(a) 嚴格有界**：公式硬限其取值範圍 → 數學上不可能有單位根 → 必為 I(0)
- **(b) 一階差分 / 共整合差**：構造上就是 I(0)（差分 I(1) 給 I(0) 是定義）

「實務上看起來 I(0) 但無數學保證」（如 STDDEV、CCI、PLUS_DM 等）**不符合**這個標準，因為 regime change 時可 spike，雖然 ADF 通常仍判 I(0)，但 finite-sample power 偶會誤判 — 對這些**應該保留 ADF 測試**而非 skip。

**Safe-skip whitelist（已通過上述 (a)/(b) 驗證）**：

| 來源 | 名稱 pattern | 數學依據 |
|------|------------|---------|
| L1 嚴格有界振盪器 | `_RSI_*`, `_ADX_*`, `_ADXR_*`, `_DX_*`, `_WILLR_*`, `_MFI_*`, `_AROON_aroonup_*`, `_AROON_aroondown_*`, `_AROONOSC_*`, `_ULTOSC_*`, `_STOCH_slowk_*`, `_STOCH_slowd_*`, `_STOCHF_fastk_*`, `_STOCHF_fastd_*`, `_STOCHRSI_fastk_*`, `_STOCHRSI_fastd_*`, `_BOP`, `_CORREL_*`, `_CMO_*`, `_LINEARREG_ANGLE_*`, `_PLUS_DI_*`, `_MINUS_DI_*` | (a) 公式硬限 [0,100] / [−100,100] / [−1,1] / [−90,90] |
| L1 normalized | `_NATR_*` | (a) % 比例，實質有界 |
| L1 一階差分 / 共整合差 | `_MOM_*`, `_ROC_*`, `_ROCP_*`, `_ROCR_*`, `_ROCR100_*`, `_TRIX_*`, `_MACD_Line_*`, `_MACD_Signal_*`, `_MACD_Hist_*`, `_MACDEXT_Line_*`, `_MACDEXT_Signal_*`, `_MACDEXT_Hist_*`, `_MACDFIX_Line_*`, `_MACDFIX_Signal_*`, `_MACDFIX_Hist_*`, `_APO_*`, `_PPO_*` | (b) 數學差分 / 共整合差 |
| L1 binary / sinusoid | `_HT_TRENDMODE`, `_HT_SINE_*`, `_HT_LEADSINE_*` | (a) {0,1} 或 [−1,1] |
| L2 構造性離散/有界 | `*_Cross_*`, `*_BinarySignal_*`, `*_Sign_*`, `*_TsRank_*`, `*_TsArgMax_*`, `*_TsArgMin_*`, `*_TsCorr_*` | (a) 二元 / 離散整數 / [0,1] / [−1,1] |
| L2 共整合差 / 共整合比 / 數學差分（且 L1 base 屬於 I(1) 趨勢追蹤型）| `{TREND_BASE}_Distance_*`, `{TREND_BASE}_Ratio_*`, `{TREND_BASE}_Momentum_*` | (b) 共整合差 / 比 / 差分 |

**Phase 1 保守 skip**（最小可動）：先 skip 所有 L1 嚴格有界 + L1 數學差分 + L2 構造性離散/有界。這已涵蓋大部分 ADF 浪費。

**Phase 2 進階 skip**（需 per-L1-base 判斷）：L2 Distance/Ratio/Momentum 在 L1 base 是 I(1) MA 時可 skip；但若 L1 base 本身是 I(0)（如 RSI），則 L2 Distance 是 I(0) 之差，仍是 I(0)，理論上**所有 L2 Distance/Ratio/Momentum 都安全**。可以全部 skip。

**保留 ADF 測試的名單**（謹慎，無數學保證）：

| 來源 | 為何不 skip |
|------|-----------|
| `_CCI_*` | 公式中 0.015 是 normalize const 非 bound，實測偶超 ±400 |
| `_STDDEV_*`, `_VAR_*`, `_BETA_*` | 統計估計，regime change 時可 spike |
| `_LINEARREG_SLOPE_*`, `_LINEARREG_*`, `_LINEARREG_INTERCEPT_*`, `_TSF_*` | I(1) 或 borderline；後三者基本是 I(1) → 該執行 fracdiff |
| `_TRANGE`, `_ATR_*`, `_Parkinson_Vol_*`, `_GarmanKlass_Vol_*` | I(1) 量級，**該執行 fracdiff** |
| `_HT_DCPERIOD`, `_HT_PHASOR_*` | 實務有界但無數學硬限 |
| `_PLUS_DM_*`, `_MINUS_DM_*` | per-bar 方向動量，無硬限 |
| `_ADOSC_*`, `_Force_Index_*`, `_Klinger_*`, `_Ease_of_Movement_*`, `_Volume_MA_Ratio_*` | 衍生 oscillator，likely I(0) 但非數學保證 |
| 所有 L1 I(1) 趨勢追蹤型（EMA/SMA/.../BBANDS/.../VWAP/OBV/AD）| **語義正確**：應執行 fracdiff |
| L2 `decay_linear / log1p / abs / clip / SignedStrength` 套用在 I(1) base 上 | I(1) → 該執行 fracdiff |

**預期效益**：safe-skip whitelist 涵蓋約 50-60% 欄位（保守估計）→ 省下對應比例的 ADF 測試成本。比前一版誇張的「60-80%」更誠實。

---

## 5. 三個獨立干預（refined）

不論 Plan No-Buffer / Plan L7-Trim / Plan Pre-History，以下三件事都該做：

### 5.1 干預一：Cascade 必擋（(a) 類）

**只擋兩種**（其他都 (b) 或 (c)，依「省時」需求決定，可後續加）：

| 欄位 | 攔截範圍 | 程式碼狀態 |
|------|---------|-----------|
| `CDL_PATTERN_ALL`（61 個 CDL）| L2 Distance/Momentum/Ratio/SignedStrength/WorldQuant ✓（已守）；L3 rolling ✓（已守）；**L4 (non-CGSA) / L5 / L6 / L6.5 待補強** | 部分 ✓ |
| `HT_DCPHASE` | **全部下游路徑** | 待新增 |

**重要**：L1 原始 CDL / HT_DCPHASE 欄位**保留**於最終 feature store（供 IC Gatekeeper 評估 raw 信號），被攔的只是它們的下游 derivation。

### 5.2 干預二：L6.5 ADF fast-skip（(b) 類，建議做以省時）

對 §4.5 列的「已知 I(0) name pattern」清單，在 ADF entry 前 by-name skip。

實作位置：`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` ADF 呼叫前。

**前提**：使用者啟用 fracdiff 才需要。當前 disabled，可標為 P2。

### 5.3 干預三：L7 final drop（(c) 死特徵清理）

只丟兩種，**不**依 NaN ratio：

| 條件 | 為何 |
|------|------|
| `nunique() < 2` | 整欄常數，零信號 |
| target window 內 `valid_count < N_min`（建議 100）| 樣本不足，XGBoost 無法學 |

---

## 6. 不會做的事

| 做法 | 為何排除 |
|------|---------|
| 任何形式的 NaN-ratio 閾值丟欄位（10% / 30% / 60%）| 丟掉有效訊號；違反「不縮減特徵」精神 |
| L0 ffill raw OHLCV | 製造假成交價 |
| 預設 buffer preload over 整個 HDF5 | 計算時間 ×2 不合理；HDF5 通常 = 使用者目標範圍，無 spare history 可借 |
| 黑名單擴張到 HT_TRENDMODE / HT_DCPERIOD / HT_SINE / HT_LEADSINE / AROON / 任何「我覺得沒用」的指標 | 它們的計算是對的；預測力交給 IC Gatekeeper |
| 假設 fracdiff 一定執行 | 由使用者實驗 config 決定 |
| 用 NaN ratio 做欄位品質指標 | NaN 不等於壞欄位 |
| 為對齊所有 symbol 而砍老幣 target window | Lopez de Prado 明確反對 |

---

## 7. 實作計畫

### 7.1 任務清單（按優先級 / 時間影響排序）

| # | 任務 | 影響 | 優先級 | 修改位置 | 狀態 |
|---|------|------|--------|---------|------|
| T1 | Cascade 黑名單 `HT_DCPHASE` + `CDL_PATTERN_ALL`（L2 / L3 / L4-CGSA-fast / L4-non-CGSA-fallback / L6.5）| **省計算 + 消除錯誤值** | **P0** | [utils/cascade_blacklist.py](../momentum/FeatureEngineering/utils/cascade_blacklist.py) + feature_factory 5 處 | ✅ **完成**（2026-05-28，5 處整合，30 tests）|
| T2 | L7 final drop：`nunique<2` OR `valid_count<N_min`（N_min=100，frame path only）| 清死特徵 | **P0** | [utils/dead_feature_filter.py](../momentum/FeatureEngineering/utils/dead_feature_filter.py) + `_run_layer6_5_preprocessor` | ✅ **完成**（2026-05-28，29 tests，含 property-based 安全契約）|
| T5 | L6.5 ADF by-name fast-skip（§4.5 名稱 pattern 列表）| 省 ADF CPU + 跨 symbol 一致性 | **P0**（dev 階段一併實作）| [utils/adf_safe_skip.py](../momentum/FeatureEngineering/utils/adf_safe_skip.py) + feature_preprocessor 2 處 | ✅ **完成**（2026-05-28，120 tests）|
| T3 | Plan L7-Trim opt-in flag：`scan_config` 加 `output.trim_leading_warmup: false`；若 true，呼叫 `_compute_warmup_buffer_bars()` 切前 N row | 給長 dataset 使用者選擇 | **P1** | scan_config + L7 寫出 | ⏸️ 延後（per PLAN「不在這版做」）|
| T4 | `_compute_warmup_buffer_bars(config, primary_tf)` helper | 提供 buffer 計算公式 | **P1** | 新檔 `utils/warmup_buffer.py` | ⏸️ 延後（T3 依賴）|
| T6 | 驗證 L6 meta_features 不踩 CDL/HT_DCPHASE；驗證 L4 non-CGSA fallback 路徑黑名單覆蓋 | 確保 T1 覆蓋完整 | **P1** | grep + 加單元測試 | ✅ 已併入 T1 測試（L4 non-CGSA 路徑已整合；L6 經 code review 確認不取用 CDL/HT_DCPHASE 欄位故不需 strip）|
| T7 | Diagnostic：每次 run 後輸出「per-column NaN 來源分類 + drop 原因」報告 | 驗證 T1/T2 行為 | **P2** | 新增 hook | ⏸️ 延後（log 已足夠 dev 期診斷）|
| T8 | 文件：在 Feature Factory UI 顯示「目前 config 的 buffer 需求」與「若啟用 Plan Pre-History 需要的多餘 history」診斷 | 引導使用者選 plan | **P2** | 前端 + API | ⏸️ 延後（UX）|

### 7.2 相依關係

```
T1 ── 獨立，立即可做（最高 ROI）
T2 ── 獨立，立即可做
T4 ──→ T3（B 模式依賴 buffer 計算）
T5 ── 待使用者啟用 fracdiff 時才有意義
T6 ── 驗證 T1
T7 / T8 ── 觀察 / UX
```

### 7.3 驗收標準

| 項目 | 目標 | 驗證 |
|------|------|------|
| CDL/HT_DCPHASE 下游衍生欄位數 | 0 | grep registry schema |
| L1 原始 CDL_xxx 與 HT_DCPHASE | 保留 | Feature Browser 可查到 |
| `nunique<2` 欄位 | 全 drop | T2 log |
| `valid_count<100` 欄位 | 全 drop | T2 log |
| 高 NaN ratio（5-60%）但非 (a)/(b) 來源的欄位 | **保留** | count 應 >> 0 |
| 啟用 Plan L7-Trim：output frame row 數 = 原長 − buffer_bars | ✓ | row 計數 |
| 啟用 Plan Pre-History（HDF5 含 spare history）：target window NaN 為 0 | ✓ | scan target window 首行 |
| 計算時間（預設 Plan No-Buffer）| 不增加；T1 完成後**可能略減**（少做 garbage 計算）| benchmark |
| no fake data | raw OHLCV checksum unchanged | checksum |

---

## 8. 決議

| # | 議題 | 決議 | 依據 |
|---|------|------|------|
| 1 | 預設 buffer plan | **Plan No-Buffer**（什麼都不多做；前段 warmup NaN 留下，XGBoost 處理）| 不可能三角；多數場景對「砍樣本」與「×2 時間」耐受度都低 |
| 2 | `N_min`（valid_count 下限）| **100**（不分 dataset 長度的固定值）| 見下方研究依據 |
| 3 | HT_SINE / HT_LEADSINE / HT_PHASOR 的下游衍生 | **不擋**（只加入 §4.5 的 ADF safe-skip） | 見下方說明 |
| 4 | L4 non-CGSA fallback（tier_xlarge）| **T1 黑名單必須覆蓋**：L4 input 為 [data, layer1, layer2, layer3]，須在 L4 入口從 layer1 剝離 CDL/HT_DCPHASE 欄位；L2 已由 RATIO_UNSAFE 守護；L3 因 input 已剝離故乾淨 | 大 RAM 機器走此路徑，必須等價 |
| 5 | 「完整 buffer」概念釐清 | **僅 Plan L7-Trim / Plan Pre-History 適用**；Plan No-Buffer 沒有 buffer 概念，前段 warmup NaN 是正常輸出 | 見 §2 更新 |
| 6 | T5 by-name skip 是否涵蓋 L1 名稱 | **是**（§4.5 已列 L1 + L2 兩層 pattern） | 使用者已確認 |

### 8.1 N_min = 100 的研究依據

從三個角度交叉驗證：

| 角度 | 最小可學樣本數 | 依據 |
|------|--------------|------|
| **統計推論** | 50–100 | CLT 在 n≈30 後生效；Pearson IC 信賴區間 ~n=30 開始穩定；ADF 測試 power 需 n≥50 |
| **XGBoost / LightGBM 學習** | 20–100 | `min_data_in_leaf` 預設 20；做 5-fold CV 後每 fold 需要 20×5=100 個有效樣本才能讓樹分裂用上該特徵 |
| **Lopez de Prado 金融 ML** | 100+ | Purged CV 每 fold 需 100+；triple-barrier labeling 需 ≥50 events；IC 顯著性需 ~100 paired obs |

→ **100 是三條曲線的下限交集**，且對 20K row dataset 只剔除 NaN > 99.5% 的欄位（極稀疏，幾乎無人會用到），合理。

**不需要 dataset-adaptive**：固定 100 對小 dataset（如 1,000 row）相當於 10% 門檻，這也合理 — 小 dataset 本來就應該對欄位品質更挑剔。

### 8.2 HT_SINE / HT_LEADSINE / HT_PHASOR 不擋的理由

- 它們的下游衍生（如 `rolling_mean(HT_SINE, W=233)` → 趨於 0）**數學上是對的**，只是 IC 期望值低
- 「IC 低」是 IC Gatekeeper 的職責，不是 cascade gate 的職責
- 若全部加 (b) 黑名單會：(i) 增加 config 複雜度；(ii) 計算量節省極微（HT 系列只是少數欄位）；(iii) 萬一某個衍生實際上有 IC（例如 HT_SINE 的 slope 捕捉 phase change rate）反而漏掉
- **唯一加入 ADF safe-skip**：因為 ADF 測試對 sinusoid 是純浪費（必判 I(0)），這個 skip 純省時間，不改變 feature 數量

### 8.3 L4 non-CGSA 黑名單實作要點（補強 T1）

`feature_factory.py:1162` non-CGSA fallback：
```python
base = self._combine_layers([data, layer1, layer2, layer3], context="layer4_input")
```

T1 需在此處新增 filter：
```python
base = base.drop(columns=_match_blacklist(base.columns, CATEGORICAL_BLACKLIST))
# CATEGORICAL_BLACKLIST = {"CDL_PATTERN_ALL", "HT_DCPHASE"} → 展開成具體名稱集合
```

驗證：CGSA path（line 1160）與 non-CGSA path（1162）阻斷的欄位集合應**完全一致**。新增單元測試覆蓋。

---

## 9. 與 L6.5 IC-First Mode 的關係（code 端的另一套 A/B/C）

### 9.1 名稱對照表

| 概念層級 | 命名 | 對應內容 |
|---------|------|---------|
| 本 doc warmup buffer | Plan No-Buffer / Plan L7-Trim / Plan Pre-History | 處理 warmup NaN 的三種方案 |
| code 內 L6.5 路由 (`_resolve_l65_generation_mode`) | `legacy` / `ic_first_pre` / `none`（注釋稱 Mode A/B/C） | L6.5 preprocessing 的三種執行路徑 |

兩者完全獨立，可任意組合。

### 9.2 L6.5 三種 mode 的實際行為（code-verified）

`feature_factory.py:1779-1804`：

| L6.5 mode | 觸發條件 | pre-IC 階段做什麼 | post-IC 階段做什麼 |
|----------|---------|------------------|------------------|
| **`legacy`** | `preprocessing.enabled=true` + `ic_first_pipeline=false` | — | 對全部特徵：Winsor → ADF → FracDiff → Rank → ZScore → Gaussian（一次到位寫 processed/）|
| **`ic_first_pre`** | `preprocessing.enabled=true` + `ic_first_pipeline=true` | 對全部特徵：Winsor + ADF + FracDiff（**不做** Rank/ZScore/Gaussian）→ 寫 raw/ | 對 IC 篩選後的特徵：Rank + ZScore + Gaussian → 寫 processed/ |
| **`none`** | `preprocessing.enabled=false` | — | 完全跳過 L6.5 |

→ scan_config 當前：`preprocessing.enabled: true`、`ic_first_pipeline: false` → 走 **`legacy`**。

### 9.3 IC 計算為何不需要先做 Rank/ZScore？

`ic_engine.py:99 compute_ic_from_l7_raw` 對 raw（即 pre-IC：Winsor + ADF + FracDiff 後）特徵計算 IC：

- IC = Pearson 或 Spearman correlation between feature 與 future return
- correlation 對任何 affine transform（Pearson）或 monotonic transform（Spearman）**不變**
- 所以 raw EMA(20) on BTC（值 $60K 量級）與 raw EMA(20) on ETH（值 $2K 量級）算出來的 IC **都是 [-1, +1] 的相關係數**，量綱已抵消
- Rank/ZScore/Gaussian 的真正用途是給下游 ML model（特別是 linear / NN）做特徵正規化，**不是給 IC 計算用**

### 9.4 跨 symbol IC 聚合的實際流程

每個 symbol 在 `_compute_single_ic_first` 子進程內獨立跑完 IC-First，產生 per-symbol IC scores。

跨 symbol 聚合（`cross_symbol_validator.py` + 相關模組）常見方法：

| 方法 | 含義 |
|------|------|
| Mean IC across symbols | 平均預測力 |
| Hit rate（IC > τ in ≥X% symbols）| 普適性 |
| IR = mean(IC) / std(IC) | 預測力穩定性 |
| t-stat of mean IC vs 0 | 統計顯著性 |

→ 全部基於「per-symbol IC 是 scalar，直接可比」這個性質。**不需要 cross-symbol 特徵正規化**。

### 9.5 ADF safe-skip 對 IC-First 跨 symbol 一致性的影響

**結論：safe-skip 改善（不傷害）跨 symbol IC 一致性**。

| 階段 | 不 skip | 有 safe-skip |
|------|--------|------------|
| pre-IC BTC RSI | ADF p=0.03 → 判 I(0) → 不 fracdiff | bypass → 不 fracdiff |
| pre-IC ETH RSI（noise 不同） | ADF p=0.11 → **誤判 I(1)** → fracdiff → `fracdiff(RSI)` | bypass → 不 fracdiff → raw RSI |
| IC 計算結果 | BTC 用 raw RSI，ETH 用 `fracdiff(RSI)` — **同名特徵跨 symbol 在不同空間** | 兩者都 raw RSI — **同名特徵跨 symbol 在同一空間** |
| Mean IC 聚合 | 蘋果 + 橘子，失真 | 正確 |

對「數學嚴格 I(0)」的指標（§4.5 whitelist），ADF false-positive 是 finite-sample noise，safe-skip 反而提供 **deterministic、跨 symbol 一致的處理**。

### 9.6 IC-First mode 下 §4.5 ADF safe-skip 的價值放大

`legacy` mode：ADF 跑一次寫一次 processed/ → safe-skip 的省時就是省 ADF 那一次。

`ic_first_pre` mode：ADF + FracDiff **必然跑在全部特徵上**（pre-IC 階段；IC 需要 stationary 特徵才能算出可靠 correlation）→ safe-skip 省下的 ADF CPU 比 legacy mode **更大宗**。

→ 結論：**Phase 1 safe-skip whitelist（§4.5）對 legacy 和 ic_first_pre 兩條 codepath 都直接加分**。實作時要確保 by-name skip 在 `_layer6_5_pre_ic` 和 `_layer6_5_legacy` 兩條路徑都生效（共用同一個 `FeaturePreprocessor` → 改一處覆蓋兩條）。
