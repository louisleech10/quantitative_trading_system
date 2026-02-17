# Feature Factory 優化規格書

> **版本**: V1.1  
> **建立日期**: 2026-02-16  
> **最後更新**: 2026-02-17  
> **基底**: Feature_Factory_PLAN.md V7 (Frozen) + Feature Generation Factory.md V2.2  
> **依據**: 業界實務差距分析（Two Sigma / AQR / WorldQuant / López de Prado / Easley-O'Hara）  
> **目的**: 補足特徵工廠 4 個遺漏面向的完整實作規格  
> **範圍**: 微觀結構特徵、資訊理論特徵、尾部風險特徵、特徵前處理層  
> **狀態**: 🔒 V1.1 Frozen — 20/20 審計通過  
> **變更摘要 (V0.1→V1)**:  
>   - 新增 4 個業界指標（VPIN / Permutation Entropy / Rolling Max Drawdown / Fractional Differencing）  
>   - Codebase 對齊（Engine 建構子簽名、`get_feature_metadata()`、§7 整合程式碼）  
>   - 新增 7 個章節（§9-§16: 下游影響/錯誤處理/快取/Logging/效能/MCP）  
>   - 邊界條件 100% 覆蓋（51 項邊界條件 × 測試映射）
>   - (V1.1) 修正 5 個審計問題 + 3 個改進建議（見附錄 B）

---

## 目錄

1. [優化目標與動機](#1-優化目標與動機)
   - 1.1 [差距分析摘要](#11-差距分析摘要)
   - 1.2 [優化原則](#12-優化原則)
   - 1.3 [與現有架構的關係](#13-與現有架構的關係)
2. [優化項目總覽](#2-優化項目總覽)
3. [微觀結構與流動性特徵 (Microstructure & Liquidity)](#3-微觀結構與流動性特徵-microstructure--liquidity)
   - 3.1 [Amihud 非流動性比率](#31-amihud-非流動性比率-amihud-illiquidity-ratio)
   - 3.2 [Kyle's Lambda (價格衝擊係數)](#32-kyles-lambda-價格衝擊係數)
   - 3.3 [Roll's Implied Spread (隱含價差)](#33-rolls-implied-spread-隱含價差)
   - 3.4 [Corwin-Schultz Spread Estimator](#34-corwin-schultz-spread-estimator-高低價差估計)
   - 3.5 [Order Flow Imbalance (訂單流失衡)](#35-order-flow-imbalance-訂單流失衡)
   - 3.6 [Large Trade Ratio (大單比率)](#36-large-trade-ratio-大單比率)
   - 3.7 [VPIN (Volume-Synchronized Probability of Informed Trading)](#37-vpin-volume-synchronized-probability-of-informed-trading)
   - 3.8 [模組設計：MicrostructureIndicatorEngine](#38-模組設計microstructureindicatorengine)
   - 3.9 [邊界條件表](#39-邊界條件表)
4. [資訊理論與複雜度特徵 (Information-Theoretic & Complexity)](#4-資訊理論與複雜度特徵-information-theoretic--complexity)
   - 4.1 [Shannon Entropy (資訊熵)](#41-shannon-entropy-資訊熵)
   - 4.2 [Approximate Entropy (近似熵)](#42-approximate-entropy-近似熵)
   - 4.3 [Sample Entropy (樣本熵)](#43-sample-entropy-樣本熵)
   - 4.4 [Hurst Exponent (赫斯特指數)](#44-hurst-exponent-赫斯特指數)
   - 4.5 [Fractal Dimension (碎形維度)](#45-fractal-dimension-碎形維度)
   - 4.6 [Permutation Entropy (排列熵)](#46-permutation-entropy-排列熵)
   - 4.7 [模組設計：EntropyIndicatorEngine](#47-模組設計entropyindicatorengine)
   - 4.8 [邊界條件表](#48-邊界條件表)
5. [高階分佈與尾部風險特徵 (Higher-Order Distribution & Tail Risk)](#5-高階分佈與尾部風險特徵-higher-order-distribution--tail-risk)
   - 5.1 [CVaR / Expected Shortfall (條件風險值)](#51-cvar--expected-shortfall-條件風險值)
   - 5.2 [Realized Volatility Decomposition (已實現波動率分解)](#52-realized-volatility-decomposition-已實現波動率分解)
   - 5.3 [Up/Down Volatility Ratio (上下波動比)](#53-updown-volatility-ratio-上下波動比)
   - 5.4 [Gain-to-Pain Ratio (盈虧比)](#54-gain-to-pain-ratio-盈虧比)
   - 5.5 [Jarque-Bera Statistic (常態性檢定)](#55-jarque-bera-statistic-常態性檢定)
   - 5.6 [Rolling Maximum Drawdown (滾動最大回撤)](#56-rolling-maximum-drawdown-滾動最大回撤)
   - 5.7 [模組設計：TailRiskIndicatorEngine](#57-模組設計tailriskindicatorengine)
   - 5.8 [邊界條件表](#58-邊界條件表)
6. [特徵前處理與正規化層 (Preprocessing & Normalization)](#6-特徵前處理與正規化層-preprocessing--normalization)
   - 6.1 [Cross-Sectional Rank Transform (橫截面排名轉換)](#61-cross-sectional-rank-transform-橫截面排名轉換)
   - 6.2 [Quantile-to-Gaussian Normalization (分位數高斯正規化)](#62-quantile-to-gaussian-normalization-分位數高斯正規化)
   - 6.3 [ADF Stationarity + Auto-Differencing (定態性檢查與自動差分)](#63-adf-stationarity--auto-differencing-定態性檢查與自動差分)
   - 6.4 [Adaptive Z-Score (自適應 Z 分數)](#64-adaptive-z-score-自適應-z-分數)
   - 6.5 [Winsorization (極端值裁剪)](#65-winsorization-極端值裁剪)
   - 6.6 [Fractional Differencing (分數差分)](#66-fractional-differencing-分數差分)
   - 6.7 [模組設計：FeaturePreprocessor](#67-模組設計featurepreprocessor)
   - 6.8 [邊界條件表](#68-邊界條件表)
7. [架構整合設計](#7-架構整合設計)
   - 7.1 [Pipeline 擴展策略](#71-pipeline-擴展策略)
   - 7.2 [Config 擴展](#72-config-擴展)
   - 7.3 [Pydantic Config Models](#73-pydantic-config-models)
   - 7.4 [Factory 擴展](#74-factory-擴展)
8. [檔案結構](#8-檔案結構)
9. [下游 Layer 影響分析](#9-下游-layer-影響分析)
10. [錯誤處理與降級策略](#10-錯誤處理與降級策略)
11. [快取策略](#11-快取策略)
12. [Logging 規範](#12-logging-規範)
13. [測試計畫](#13-測試計畫)
14. [效能與記憶體預估](#14-效能與記憶體預估)
15. [驗收標準](#15-驗收標準)
16. [MCP Tool Interface (V2.0/V3.0 準備)](#16-mcp-tool-interface-v20v30-準備)
17. [附錄](#17-附錄)
    - A. [業界參考文獻](#附錄-a-業界參考文獻)
    - B. [版本歷史](#附錄-b-版本歷史)

---

## 1. 優化目標與動機

### 1.1 差距分析摘要

透過比對 Two Sigma、AQR Capital、WorldQuant、López de Prado、Easley-O'Hara 等量化金融業界的研究實務，發現現有 Feature Factory（V7 Frozen）在以下 4 個面向存在顯著缺漏：

| 面向 | 現狀 | 業界實務 | 差距等級 |
|------|------|---------|---------|
| **微觀結構/流動性** | 僅有 volume 相關指標（OBV, AD, MFI 等） | Amihud Illiquidity、Kyle's Lambda、Roll's Spread、OFI、**VPIN** 等專業流動性因子 | 🔴 重大 |
| **資訊理論/複雜度** | 無 | Shannon/Sample/Approximate/**Permutation** Entropy、Hurst Exponent、Fractal Dimension | 🔴 重大 |
| **高階分佈/尾部風險** | Rolling Skew/Kurt（Layer 3 aggregator）僅作為滾動聚合 | CVaR、Realized Vol 分解、Gain-to-Pain Ratio、Jarque-Bera、**Rolling Max Drawdown** 作為因子 | 🟡 中等 |
| **特徵前處理/正規化** | 無統一的正規化層 | Cross-Sectional Rank、Gaussian Normalization、**Fractional Differencing**、Adaptive Z-Score | 🔴 重大 |

### 1.2 優化原則

1. **不修改現有 Layer 0-7 Pipeline**：新功能以新增引擎或新增 Layer 方式整合
2. **Config-Driven**：所有新功能透過 `scan_config.yaml` 控制，預設 `enabled: false`
3. **向量化優先**：所有計算使用 pandas/numpy 向量化，避免 Python for 迴圈
4. **解耦架構**：遵循 Rule 1-7（見 ARCHITECTURE.md）
5. **漸進式啟用**：每個新引擎可獨立啟用/停用，不影響既有特徵
6. **Codebase 一致性**：新引擎的類別簽名、方法命名、config 載入模式與既有引擎保持一致

### 1.3 與現有架構的關係

```
現有七層 Pipeline（Feature_Factory_PLAN V7 Frozen）
=================================================
Layer 0: Data Ingestion ← 不修改
Layer 1: Atomic Indicators ← 新增 3 個引擎（微觀結構、資訊理論、尾部風險）
Layer 2: Derived Features ← 不修改
Layer 3: Rolling Aggregation ← 不修改
Layer 4: Lag Features ← 不修改
Layer 5: Cross-Sectional ← 不修改
Layer 6: Meta Features ← 不修改
Layer 6.5: Preprocessing ← 新增層（前處理/正規化）
Layer 7: Validation & Persistence ← 不修改
```

**關鍵決策**：
- 面向 1~3 作為 Layer 1 的新 indicator engine（與 Trend/Momentum/Volatility 同層）
- 面向 4 作為新增的 Layer 6.5（在 Meta Features 之後、Validation 之前）
- Layer 6.5 對所有前面 Layer 產出的特徵做統一的前處理/正規化

---

## 2. 優化項目總覽

| # | 面向 | 功能模組 | Layer | 特徵數量 | 複雜度 |
|---|------|---------|-------|---------|--------|
| 1 | 微觀結構/流動性 | `MicrostructureIndicatorEngine` | Layer 1 | 25 | 中 |
| 2 | 資訊理論/複雜度 | `EntropyIndicatorEngine` | Layer 1 | 15 | 高 |
| 3 | 高階分佈/尾部風險 | `TailRiskIndicatorEngine` | Layer 1 | 26 | 中 |
| 4 | 特徵前處理/正規化 | `FeaturePreprocessor` | Layer 6.5 | 0（轉換現有特徵） | 中 |

**新增原子特徵合計**：25 + 15 + 26 = **66 features**（基於預設 windows 配置）

**預估時程**：
- 面向 1~3：各 2-3 天（含測試） → 共 6-9 天
- 面向 4：3-4 天（含測試）
- 整合測試 + Review：2 天
- **合計**：~11-15 天

---

## 3. 微觀結構與流動性特徵 (Microstructure & Liquidity)

**業界背景**：微觀結構因子是量化基金的核心因子類別之一。Amihud (2002) 的非流動性比率被廣泛用於學術研究和因子模型。Kyle (1985) 的 Lambda 量化價格衝擊。Roll (1984) 和 Corwin-Schultz (2012) 提供不同的價差估計方法。VPIN (Easley, López de Prado & O'Hara, 2012) 量化知情交易者比例，在加密市場閃崩預測中有重要價值。這些因子在傳統金融中已被充分驗證，在加密市場中更有價值——因為流動性差異極大且變化快速。

**可用數據來源**：`close`, `open`, `high`, `low`, `volume`, `quote_volume`, `taker_buy_volume`, `taker_ratio`, `trades`

### 3.1 Amihud 非流動性比率 (Amihud Illiquidity Ratio)

**定義**（Amihud, 2002）：

$$ILLIQ_t = \frac{1}{N} \sum_{i=1}^{N} \frac{|r_i|}{VOLD_i}$$

其中 $r_i$ 為報酬率，$VOLD_i$ 為成交額（`quote_volume`）。

**實作**：使用滾動窗口計算：

$$amihud\_illiq_{t,w} = \text{rolling\_mean}\left(\frac{|r_t|}{quote\_volume_t}, w\right)$$

**參數**：
- `windows`: 滾動窗口 [5, 13, 21, 55]
- `use_quote_volume`: `true`（使用報價計價量，更準確）
- `epsilon`: `1e-10`（避免除以零）

**輸出命名**：`ms_amihud_illiq_{window}` (e.g., `ms_amihud_illiq_21`)

**金融意義**：值越高 → 流動性越差 → 價格更容易被影響

### 3.2 Kyle's Lambda (價格衝擊係數)

**定義**（Kyle, 1985）：

$$\Delta P_t = \lambda \cdot \text{SignedVolume}_t + \epsilon_t$$

$\lambda$ 為滾動窗口內的回歸斜率，量化每單位成交量對價格的衝擊。

**實作**：

```python
# signed_volume = volume * sign(close_return)
# 滾動窗口內做 OLS: Δprice ~ signed_volume
# lambda = Cov(ΔP, SignedVol) / Var(SignedVol)（向量化實作）
signed_volume = volume * np.sign(close.pct_change())
delta_price = close.diff()
cov = delta_price.rolling(window).cov(signed_volume)
var = signed_volume.rolling(window).var()
lambda_t = cov / (var + epsilon)
```

**參數**：
- `windows`: [13, 21, 55]
- `min_periods`: `window // 2`

**輸出命名**：`ms_kyle_lambda_{window}`

**金融意義**：值越高 → 每筆交易對價格衝擊越大 → 市場深度越淺

### 3.3 Roll's Implied Spread (隱含價差)

**定義**（Roll, 1984）：

$$Spread = 2\sqrt{-\text{Cov}(\Delta P_t, \Delta P_{t-1})}$$

若 autocovariance 為正，價差設為 0（非 NaN）。

**實作**（向量化版本）：

```python
dp = close.diff()
autocov = dp.rolling(window).cov(dp.shift(1))
spread = 2 * np.sqrt(np.maximum(-autocov, 0))
```

**參數**：
- `windows`: [13, 21, 55]

**輸出命名**：`ms_roll_spread_{window}`

**金融意義**：隱含買賣價差的估計量 → 值越高交易成本越高

### 3.4 Corwin-Schultz Spread Estimator (高低價差估計)

**定義**（Corwin & Schultz, 2012）：

$$\beta = \sum_{j=0}^{1} \left[\ln\left(\frac{H_{t-j}}{L_{t-j}}\right)\right]^2$$

$$\gamma = \left[\ln\left(\frac{H_{t,t-1}}{L_{t,t-1}}\right)\right]^2$$

$$\alpha = \frac{\sqrt{2\beta} - \sqrt{\beta}}{3 - 2\sqrt{2}} - \sqrt{\frac{\gamma}{3 - 2\sqrt{2}}}$$

$$Spread = \frac{2(e^{\alpha} - 1)}{1 + e^{\alpha}}$$

其中 $H_{t,t-1}$ 和 $L_{t,t-1}$ 為兩日的最高價和最低價。

**實作**：完全向量化，使用 `rolling(2).max()` / `rolling(2).min()`。

**參數**：
- `rolling_smooth`: [5, 13, 21]（對原始 spread 做滾動平均以降低噪音）

**輸出命名**：`ms_cs_spread_{smooth}`

**金融意義**：從 high/low 估計價差，適合沒有 bid/ask 數據的情境

### 3.5 Order Flow Imbalance (訂單流失衡)

**定義**：

$$OFI_t = \frac{taker\_buy\_volume_t - taker\_sell\_volume_t}{volume_t}$$

$$taker\_sell\_volume_t = volume_t - taker\_buy\_volume_t$$

等同於：$OFI_t = 2 \times taker\_ratio_t - 1$（標準化到 [-1, 1]）。

**進階版**：滾動 OFI 的 Z-Score：

$$OFI\_zscore_{t,w} = \frac{OFI_t - \text{mean}(OFI_{t-w:t})}{\text{std}(OFI_{t-w:t})}$$

**參數**：
- `windows`: [5, 13, 21, 55]（Z-Score 的滾動窗口）
- `raw_ofi`: `true`（是否輸出原始 OFI）

**輸出命名**：`ms_ofi_raw`, `ms_ofi_zscore_{window}`

**金融意義**：訂單流方向性指標 → 正值表示買方主導 → 預測短期價格方向

### 3.6 Large Trade Ratio (大單比率)

**定義**：

$$LTR_t = \frac{quote\_volume_t / trades_t}{\text{rolling\_median}(quote\_volume / trades, w)}$$

衡量當前平均成交額相對於歷史中位數的比率。

**參數**：
- `windows`: [13, 21, 55]
- `min_trades`: 1（避免除以零）

**輸出命名**：`ms_large_trade_ratio_{window}`

**金融意義**：大單比率異常高 → 機構投資者可能在進場 → 資訊不對稱增加

### 3.7 VPIN (Volume-Synchronized Probability of Informed Trading)

**定義**（Easley, López de Prado & O'Hara, 2012）：

VPIN 量化知情交易者在總交易量中的比例，是微觀結構領域最重要的現代指標之一，曾成功預測 2010 年閃崩。

**演算法**：

1. **Volume Bucketing**：將交易量劃分為等量桶（Volume Bars），每桶成交量 = `total_volume / n_buckets`
2. **估算買賣量**：每桶的 buy volume 使用 Bulk Volume Classification (BVC)：

$$V^B_\tau = V_\tau \cdot \Phi\left(\frac{\Delta P_\tau}{\sigma_{\Delta P}}\right)$$

$$V^S_\tau = V_\tau - V^B_\tau$$

3. **計算 VPIN**：

$$VPIN = \frac{\sum_{i=1}^{n} |V^B_i - V^S_i|}{n \cdot V_{bucket}}$$

**簡化實作（時間 bar 近似）**：

由於 K 線數據已是時間 bar 而非 volume bar，使用近似實作：

```python
def compute_vpin(close: pd.Series, volume: pd.Series, 
                 n_buckets: int = 50) -> pd.Series:
    """VPIN 簡化實作（時間 bar 近似）。
    
    使用 BVC (Bulk Volume Classification) 估算每根 bar 的買賣量，
    然後在滾動窗口內計算 VPIN。
    """
    delta_p = close.pct_change()
    sigma = delta_p.rolling(n_buckets).std()
    # BVC: Φ(ΔP / σ)
    from scipy.stats import norm
    buy_pct = norm.cdf(delta_p / (sigma + 1e-10))
    buy_vol = volume * buy_pct
    sell_vol = volume * (1 - buy_pct)
    order_imbalance = (buy_vol - sell_vol).abs()
    vpin = order_imbalance.rolling(n_buckets).sum() / volume.rolling(n_buckets).sum()
    return vpin
```

**參數**：
- `n_buckets`: [30, 50]（滾動窗口大小）
- `zscore_windows`: [21, 55]（VPIN Z-Score 窗口）

**輸出命名**：`ms_vpin_{n_buckets}`, `ms_vpin_zscore_{window}`

**金融意義**：VPIN 上升 → 知情交易者比例增加 → 流動性危機風險上升 → 閃崩預警

**效能考量**：使用 `scipy.stats.norm.cdf` 的向量化版本，O(N) 複雜度。

### 3.8 模組設計：MicrostructureIndicatorEngine

```python
class MicrostructureIndicatorEngine:
    """Layer 1 Indicator Engine: 微觀結構與流動性特徵。
    
    計算 7 類微觀結構指標，全面量化市場流動性狀態。
    所有計算使用 numpy/pandas 向量化操作，無 Python for 迴圈。
    
    Required data columns: close, high, low, volume, quote_volume,
                          taker_buy_volume, taker_ratio, trades
    """
    
    def __init__(self, config: Dict, data_sources: List[str]):
        """
        Args:
            config: microstructure section from scan_config.yaml
            data_sources: 不使用（微觀結構使用固定欄位），接受參數以符合 Engine 統一介面
        """
        self._config = config
        self._data_sources = data_sources
        self.windows = config.get('windows', [5, 13, 21, 55])
        self.epsilon = config.get('epsilon', 1e-10)
        self.min_trades = config.get('min_trades', 1)
        self.enabled_features = config.get('enabled_features', 'all')
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """計算所有啟用的微觀結構特徵。
        
        Args:
            data: raw OHLCV DataFrame（必須含 close, high, low, volume, 
                  quote_volume, taker_buy_volume, taker_ratio, trades）
        
        Returns:
            DataFrame with microstructure features, same index as data
        """
    
    def get_feature_metadata(self) -> Dict[str, Dict]:
        """返回所有特徵的 Metadata。
        
        Returns:
            Dict[feature_name, {"layer": "layer1", "category": "microstructure", 
                               "indicator": str, "params": dict, "description": str}]
        """
    
    def _compute_amihud(self, data: pd.DataFrame) -> pd.DataFrame:
        """Amihud Illiquidity Ratio（§3.1）"""
    
    def _compute_kyle_lambda(self, data: pd.DataFrame) -> pd.DataFrame:
        """Kyle's Lambda via rolling covariance/variance（§3.2）
        
        向量化：lambda = Cov(ΔP, SignedVol) / Var(SignedVol)
        """
    
    def _compute_roll_spread(self, data: pd.DataFrame) -> pd.DataFrame:
        """Roll's Implied Spread（§3.3）
        
        向量化：rolling.cov(shift(1))
        """
    
    def _compute_cs_spread(self, data: pd.DataFrame) -> pd.DataFrame:
        """Corwin-Schultz Spread Estimator（§3.4）
        
        完全向量化，使用 rolling(2).max()/min()
        """
    
    def _compute_ofi(self, data: pd.DataFrame) -> pd.DataFrame:
        """Order Flow Imbalance + Z-Score（§3.5）"""
    
    def _compute_large_trade_ratio(self, data: pd.DataFrame) -> pd.DataFrame:
        """Large Trade Ratio（§3.6）"""
    
    def _compute_vpin(self, data: pd.DataFrame) -> pd.DataFrame:
        """VPIN via Bulk Volume Classification（§3.7）"""
```

**輸出 Schema**（範例）：

```json
{
  "ms_amihud_illiq_5": 0.000023,
  "ms_amihud_illiq_13": 0.000019,
  "ms_amihud_illiq_21": 0.000017,
  "ms_amihud_illiq_55": 0.000015,
  "ms_kyle_lambda_13": 0.00045,
  "ms_kyle_lambda_21": 0.00038,
  "ms_kyle_lambda_55": 0.00031,
  "ms_roll_spread_13": 0.0012,
  "ms_roll_spread_21": 0.0010,
  "ms_roll_spread_55": 0.0008,
  "ms_cs_spread_5": 0.0015,
  "ms_cs_spread_13": 0.0013,
  "ms_cs_spread_21": 0.0011,
  "ms_ofi_raw": 0.15,
  "ms_ofi_zscore_5": 1.23,
  "ms_ofi_zscore_13": 0.87,
  "ms_ofi_zscore_21": 0.62,
  "ms_ofi_zscore_55": 0.34,
  "ms_large_trade_ratio_13": 1.45,
  "ms_large_trade_ratio_21": 1.22,
  "ms_large_trade_ratio_55": 1.08,
  "ms_vpin_30": 0.42,
  "ms_vpin_50": 0.38,
  "ms_vpin_zscore_21": 1.05,
  "ms_vpin_zscore_55": 0.72
}
```

**特徵總數**：4 + 3 + 3 + 3 + 5 + 3 + 4 = **25 features**（基於預設參數）

### 3.9 邊界條件表

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | `quote_volume` 全為 0 | Amihud 返回 NaN → Layer 7 validator 處理 | `test_amihud_zero_volume` |
| 2 | `trades` 全為 0 或缺失 | Large Trade Ratio 返回 NaN | `test_ltr_zero_trades` |
| 3 | 資料列數 < min window | 所有依賴該 window 的特徵返回 NaN | `test_micro_insufficient_data` |
| 4 | 價格完全不變（return = 0） | Kyle's Lambda = 0, Roll's Spread = 0, VPIN CDF 退化 | `test_constant_price` |
| 5 | `taker_ratio` 缺失 | OFI 使用 `taker_buy_volume / volume` 計算替代 | `test_ofi_fallback` |
| 6 | 極端 volume spike（正常值的 1000x） | 所有指標正常計算，不 clip | `test_volume_spike` |
| 7 | `high == low`（所有 bar） | Corwin-Schultz spread = 0 | `test_zero_range_bar` |
| 8 | Roll 的 autocovariance > 0 | spread = 0（非 NaN） | `test_roll_positive_autocov` |
| 9 | VPIN 窗口內 volume 全為 0 | VPIN = NaN（避免 0/0） | `test_vpin_zero_volume` |
| 10 | VPIN sigma_deltaP = 0（所有 return 相同） | BVC cdf 不確定 → fallback 0.5 → VPIN = 0 | `test_vpin_zero_sigma` |
| 11 | 特徵名與其他引擎衝突（`ms_` prefix） | 無衝突（prefix 唯一） | `test_micro_feature_name_unique` |

---

## 4. 資訊理論與複雜度特徵 (Information-Theoretic & Complexity)

**業界背景**：資訊理論指標量化時間序列的可預測性和複雜度。López de Prado (2018) 將 entropy 度量用於市場微觀結構分析。Hurst exponent 用於檢測 mean-reversion vs momentum 特性。Permutation Entropy (Bandt & Pompe, 2002) 是近年來計算效率最高的複雜度指標，已被引入金融領域用於量化市場效率。

**適用數據**：主要使用 `close` 的報酬率序列，也可擴展到 `volume` 和 `taker_ratio`。

### 4.1 Shannon Entropy (資訊熵)

**定義**：

$$H(X) = -\sum_{i=1}^{n} p_i \log_2 p_i$$

**金融應用**：對報酬率做分桶（binning），計算其分佈的資訊熵。高熵 → 報酬率分佈均勻（不可預測）；低熵 → 分佈集中（有規律）。

**實作**：

```python
def rolling_shannon_entropy(returns: pd.Series, window: int, n_bins: int = 10) -> pd.Series:
    """滾動 Shannon Entropy。
    
    對每個窗口內的 returns 做等寬分桶 (n_bins)，
    計算離散機率分佈的 entropy。
    
    向量化策略：使用 np.apply_along_axis + np.histogram 的純 numpy 實作。
    """
```

**參數**：
- `windows`: [21, 55, 100]
- `n_bins`: 10
- `apply_to`: `['close_return']`（可擴展到其他序列）

**輸出命名**：`ent_shannon_{source}_{window}` (e.g., `ent_shannon_close_return_21`)

### 4.2 Approximate Entropy (近似熵)

**定義**（Pincus, 1991）：

$$ApEn(m, r, N) = \Phi^m(r) - \Phi^{m+1}(r)$$

其中 $\Phi^m(r) = \frac{1}{N-m+1}\sum_{i=1}^{N-m+1}\ln C_i^m(r)$，$C_i^m(r)$ 為模板匹配計數。

**參數**：
- `m`: embedding dimension = 2
- `r`: tolerance = 0.2 × std（窗口內自適應）
- `windows`: [50, 100]

**輸出命名**：`ent_apen_{window}`

**金融意義**：低 ApEn → 序列可預測性高 → 可能有 alpha；高 ApEn → 隨機性強

**效能考量**：ApEn 計算複雜度 $O(N^2)$，建議：
1. 使用 Numba JIT 加速內部迴圈
2. 窗口不宜過大（max 100）
3. 可選降頻取樣

### 4.3 Sample Entropy (樣本熵)

**定義**（Richman & Moorman, 2000）：

$$SampEn(m, r, N) = -\ln\frac{A}{B}$$

與 ApEn 類似但避免自匹配偏差且更穩健。

**參數**：同 ApEn（`m=2`, `r=0.2×std`, `windows=[50, 100]`）

**輸出命名**：`ent_sampen_{window}`

**效能考量**：同 ApEn，但計算量略小。

### 4.4 Hurst Exponent (赫斯特指數)

**定義**（R/S 分析法）：

$$H = \frac{\log(R/S)}{\log(N)}$$

其中 $R$ 為累積偏差的範圍（range），$S$ 為標準差。

**金融意義**：
- $H \approx 0.5$ → 隨機遊走（無記憶）
- $H > 0.5$ → 持久性（momentum）
- $H < 0.5$ → 反持久性（mean reversion）

**實作方法**：Rescaled Range (R/S) analysis，使用多個子序列長度做 log-log 回歸。

```python
def rolling_hurst(series: pd.Series, window: int, min_sub_length: int = 8) -> pd.Series:
    """滾動 Hurst Exponent（R/S 分析）。
    
    對每個窗口：
    1. 取多個子序列長度 n = [min_sub_length, ..., window//2]
    2. 每個 n 計算 R/S
    3. log(R/S) ~ H * log(n) 的 OLS slope 即為 H
    
    向量化策略：外層 rolling.apply，內部使用 numpy 矩陣運算。
    Numba JIT 可選加速。
    """
```

**參數**：
- `windows`: [55, 100, 200]
- `min_sub_length`: 8

**輸出命名**：`ent_hurst_{window}`

### 4.5 Fractal Dimension (碎形維度)

**定義**（Higuchi, 1988）：

$$L(k) = \frac{1}{k} \sum_{m=1}^{k} \frac{N-1}{\lfloor(N-m)/k\rfloor \cdot k} \sum_{i=1}^{\lfloor(N-m)/k\rfloor} |x_{m+ik} - x_{m+(i-1)k}|$$

Fractal Dimension $D$ 為 $\log(L(k))$ vs $\log(1/k)$ 的斜率。

**金融意義**：
- $D \approx 1.0$ → 平滑趨勢（強趨勢市場）
- $D \approx 1.5$ → 布朗運動（隨機）
- $D \approx 2.0$ → 高頻震盪（choppy market）

**參數**：
- `windows`: [55, 100]
- `kmax`: 10

**輸出命名**：`ent_fractal_dim_{window}`

### 4.6 Permutation Entropy (排列熵)

**定義**（Bandt & Pompe, 2002）：

對序列 $\{x_t\}$ 的每個長度為 $m$ 的子序列，求其排列順序（ordinal pattern），計算所有可能排列的出現頻率之 Shannon Entropy：

$$PE(m) = -\sum_{\pi \in S_m} p(\pi) \log_2 p(\pi)$$

其中 $S_m$ 為 $m$ 個元素的全排列集合（共 $m!$ 種），$p(\pi)$ 為排列 $\pi$ 的出現頻率。

**正規化**：$PE_{norm} = \frac{PE(m)}{\log_2(m!)}$，使其範圍為 [0, 1]。

**相較 ApEn/SampEn 的優勢**：
- **計算效率**：$O(N \cdot m)$ vs $O(N^2)$，快 10-100 倍
- **參數不敏感**：僅需 embedding dimension $m$，無 tolerance $r$ 參數
- **噪音穩健性**：基於排序而非數值距離，對噪音更穩健

**實作**：

```python
def rolling_permutation_entropy(series: pd.Series, window: int, 
                                 m: int = 3) -> pd.Series:
    """滾動 Permutation Entropy。
    
    對每個窗口：
    1. 生成所有長度 m 的子序列
    2. 計算每個子序列的 ordinal pattern（排列順序）
    3. 統計各 pattern 出現頻率
    4. 計算正規化 Shannon Entropy
    
    向量化策略：使用 np.argsort + 編碼為整數 → np.bincount 統計頻率。
    """
    # m=3 → 6 種排列，m=4 → 24 種排列
    # 純 numpy 實作，無需 Numba
```

**參數**：
- `m`: embedding dimension = 3（3! = 6 種排列，足夠且計算效率高）
- `windows`: [21, 55, 100]

**輸出命名**：`ent_perm_{window}` (e.g., `ent_perm_21`)

**金融意義**：
- 低 Permutation Entropy → 價格變動有明確規律（趨勢或週期）
- 高 Permutation Entropy → 價格變動接近隨機

**效能考量**：$O(N \cdot window \cdot m)$，比 ApEn/SampEn 快 10-100 倍，無需 Numba。

### 4.7 模組設計：EntropyIndicatorEngine

```python
class EntropyIndicatorEngine:
    """Layer 1 Indicator Engine: 資訊理論與複雜度特徵。
    
    計算 6 類資訊理論指標，量化時間序列的可預測性和複雜度。
    
    效能注意：
    - Shannon Entropy: O(N*window) — 較快
    - Permutation Entropy: O(N*window*m) — 較快（無需 Numba）
    - ApEn/SampEn: O(N*window²) — 較慢，建議限制 window ≤ 100
    - Hurst/Fractal: O(N*window*log(window)) — 中等
    
    建議 Numba JIT 加速 ApEn/SampEn 核心迴圈。
    
    Required data columns: close (計算 returns 後使用)
    """
    
    def __init__(self, config: Dict, data_sources: List[str]):
        """
        Args:
            config: entropy section from scan_config.yaml
            data_sources: 用於決定哪些序列計算 entropy（預設 ['close_return']）
        """
        self._config = config
        self._data_sources = data_sources
        self.windows = config.get('windows', [55, 100])
        self.n_bins = config.get('n_bins', 10)
        self.apen_m = config.get('apen_m', 2)
        self.apen_r_ratio = config.get('apen_r_ratio', 0.2)
        self.shannon_windows = config.get('shannon_windows', [21, 55, 100])
        self.hurst_windows = config.get('hurst_windows', [55, 100, 200])
        self.fractal_kmax = config.get('fractal_kmax', 10)
        self.use_numba = config.get('use_numba', True)
        self.perm_m = config.get('perm_m', 3)
        self.perm_windows = config.get('perm_windows', [21, 55, 100])
        self.apply_to = config.get('apply_to', ['close_return'])
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """計算所有啟用的資訊理論特徵。
        
        apply_to 欄位解析規則：
        - 'close_return' → data['close'].pct_change()
        - 'volume' → data['volume']
        - 'taker_ratio' → data['taker_ratio']
        其他 → 直接取 data[column_name]
        """
    
    def get_feature_metadata(self) -> Dict[str, Dict]:
        """返回所有特徵的 Metadata。"""
    
    def _compute_shannon_entropy(self, series: pd.Series, source_name: str) -> pd.DataFrame:
        """Rolling Shannon Entropy（§4.1）"""
    
    def _compute_approximate_entropy(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Approximate Entropy（§4.2）
        Uses Numba JIT if available.
        """
    
    def _compute_sample_entropy(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Sample Entropy（§4.3）
        Uses Numba JIT if available.
        """
    
    def _compute_hurst(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Hurst Exponent via R/S analysis（§4.4）"""
    
    def _compute_fractal_dimension(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Fractal Dimension via Higuchi method（§4.5）"""
    
    def _compute_permutation_entropy(self, series: pd.Series) -> pd.DataFrame:
        """Rolling Permutation Entropy（§4.6）
        純 numpy 實作，無需 Numba。
        """
```

**輸出 Schema**（範例）：

```json
{
  "ent_shannon_close_return_21": 3.12,
  "ent_shannon_close_return_55": 3.25,
  "ent_shannon_close_return_100": 3.30,
  "ent_apen_50": 0.45,
  "ent_apen_100": 0.52,
  "ent_sampen_50": 0.42,
  "ent_sampen_100": 0.48,
  "ent_hurst_55": 0.58,
  "ent_hurst_100": 0.55,
  "ent_hurst_200": 0.52,
  "ent_fractal_dim_55": 1.42,
  "ent_fractal_dim_100": 1.38,
  "ent_perm_21": 0.91,
  "ent_perm_55": 0.88,
  "ent_perm_100": 0.85
}
```

**特徵總數**：3 + 2 + 2 + 3 + 2 + 3 = **15 features**（基於預設 windows，單一 source）。若 `apply_to` 含多個 source（如 `close_return` + `taker_ratio`），Shannon/Permutation Entropy 可倍增。

### 4.8 邊界條件表

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | 資料列數 < min window | 所有特徵返回 NaN | `test_entropy_insufficient_data` |
| 2 | 全部 return = 0（價格不變） | Shannon Entropy = 0, Hurst 不確定 → NaN | `test_entropy_constant_returns` |
| 3 | 窗口內 std = 0 | ApEn/SampEn 的 r=0 → tolerance fallback to 1e-8 | `test_entropy_zero_variance` |
| 4 | 含大量 NaN（>50%） | 返回 NaN for affected windows | `test_entropy_many_nans` |
| 5 | 極端報酬（±50%） | 所有指標正常計算（不 clip 輸入） | `test_entropy_extreme_returns` |
| 6 | Hurst 回歸 R² 極低（<0.1） | 返回 NaN（不可靠估計） | `test_hurst_low_r_squared` |
| 7 | Numba 不可用 | fallback 到純 numpy 實作（WARNING log） | `test_entropy_no_numba` |
| 8 | apply_to 指定的欄位不存在 | skip 並 log WARNING | `test_entropy_missing_column` |
| 9 | Permutation Entropy m > window | 返回 NaN（排列數 > 窗口大小無意義） | `test_perm_entropy_m_exceeds_window` |
| 10 | Permutation Entropy 窗口內值全部相同 | PE = 0（只有一種排列 pattern） | `test_perm_entropy_constant_values` |
| 11 | Permutation Entropy m=1 | PE = 0（只有 1! = 1 種排列） → raise ValueError | `test_perm_entropy_invalid_m` |

---

## 5. 高階分佈與尾部風險特徵 (Higher-Order Distribution & Tail Risk)

**業界背景**：尾部風險因子是風險管理和 alpha 因子的交集。CVaR（Basel III 要求的風險指標）直接衡量極端損失。已實現波動率分解（Barndorff-Nielsen & Sheppard, 2004）將波動率拆成 upside/downside 成分，捕捉非對稱風險。Gain-to-Pain Ratio 是基金績效衡量的標準指標。Rolling Maximum Drawdown 是最直覺的風險度量。

**現狀差距**：現有 Layer 3 RollingAggregator 已有 `skew` 和 `kurt` 聚合器，但它們是對 Layer 1/2 的指標值做滾動統計——而非直接對報酬率計算尾部風險指標。本面向提供的是「報酬率本身的尾部風險因子」，而非「指標值的統計量」。

**適用數據**：`close`（計算 returns）、`high`、`low`。

### 5.1 CVaR / Expected Shortfall (條件風險值)

**定義**：

$$CVaR_{\alpha} = E[r | r \leq VaR_{\alpha}]$$

即在 VaR 閾值以下的平均損失。

**實作**：

```python
def rolling_cvar(returns: pd.Series, window: int, alpha: float = 0.05) -> pd.Series:
    """滾動窗口 CVaR（向量化）。
    
    對每個窗口：
    1. 排序取 quantile(alpha)
    2. CVaR = mean(returns[returns <= quantile])
    """
```

**參數**：
- `windows`: [21, 55, 100]
- `alpha`: [0.01, 0.05]（1% 和 5% 尾部）

**輸出命名**：`tr_cvar_{alpha}_{window}` (e.g., `tr_cvar_5pct_21`)

### 5.2 Realized Volatility Decomposition (已實現波動率分解)

**定義**（Barndorff-Nielsen & Sheppard, 2004）：

$$RV^+ = \sqrt{\sum_{i=1}^{N} r_i^2 \cdot \mathbb{1}(r_i > 0)}$$

$$RV^- = \sqrt{\sum_{i=1}^{N} r_i^2 \cdot \mathbb{1}(r_i < 0)}$$

$$RSJ = RV^+ - RV^-$$（Realized Semivariance Jump）

**實作**：完全向量化。

```python
returns_sq = returns ** 2
rv_up = np.sqrt(returns_sq.where(returns > 0, 0).rolling(window).sum())
rv_down = np.sqrt(returns_sq.where(returns < 0, 0).rolling(window).sum())
rsj = rv_up - rv_down
```

**參數**：
- `windows`: [13, 21, 55]

**輸出命名**：`tr_rv_up_{window}`, `tr_rv_down_{window}`, `tr_rsj_{window}`

### 5.3 Up/Down Volatility Ratio (上下波動比)

**定義**：

$$UDVR = \frac{RV^+}{RV^-}$$

**參數**：
- `windows`: 使用 `rv_windows` [13, 21, 55]（與 RV Decomposition 共用）

**輸出命名**：`tr_ud_vol_ratio_{window}`

**金融意義**：> 1 → 上漲波動大於下跌波動 → 正偏態市場

### 5.4 Gain-to-Pain Ratio (盈虧比)

**定義**：

$$GPR = \frac{\sum r_i \cdot \mathbb{1}(r_i > 0)}{\left|\sum r_i \cdot \mathbb{1}(r_i < 0)\right|}$$

**參數**：
- `windows`: [21, 55, 100]

**輸出命名**：`tr_gpr_{window}`

**金融意義**：策略/資產的盈虧平衡指標 → >1 表示正期望值

### 5.5 Jarque-Bera Statistic (常態性檢定)

**定義**：

$$JB = \frac{N}{6}\left(S^2 + \frac{(K-3)^2}{4}\right)$$

其中 $S$ 為 skewness，$K$ 為 kurtosis。

**實作**：使用 rolling skew 和 rolling kurtosis 計算。

```python
s = returns.rolling(window).skew()
k = returns.rolling(window).kurt()  # excess kurtosis (pandas default)
n = window
jb = (n / 6) * (s**2 + (k**2) / 4)
```

**參數**：
- `windows`: [55, 100]

**輸出命名**：`tr_jb_{window}`

**金融意義**：JB 值大 → 分佈顯著偏離常態 → 尾部風險高

### 5.6 Rolling Maximum Drawdown (滾動最大回撤)

**定義**：

$$MDD_t = \min_{s \in [t-w, t]} \left(\frac{P_s - \max_{u \in [t-w, s]} P_u}{\max_{u \in [t-w, s]} P_u}\right)$$

即滾動窗口內，從峰值到谷底的最大跌幅百分比。

**實作**：

```python
def rolling_max_drawdown(close: pd.Series, window: int) -> pd.Series:
    """滾動最大回撤（向量化）。
    
    向量化策略：
    1. rolling_max = close.rolling(window).max()
    2. drawdown = (close - rolling_max) / rolling_max
    3. mdd = drawdown.rolling(window).min()
    """
    rolling_max = close.rolling(window).max()
    drawdown = (close - rolling_max) / rolling_max
    mdd = drawdown.rolling(window).min()
    return mdd
```

**參數**：
- `windows`: [21, 55, 100]

**輸出命名**：`tr_mdd_{window}` (e.g., `tr_mdd_21`)

**金融意義**：MDD 接近 0 → 窗口內幾乎沒有下跌；MDD 負值越大 → 風險越高

**效能考量**：完全向量化，$O(N)$ 複雜度。

### 5.7 模組設計：TailRiskIndicatorEngine

```python
class TailRiskIndicatorEngine:
    """Layer 1 Indicator Engine: 高階分佈與尾部風險特徵。
    
    計算 6 類尾部風險指標，量化非對稱風險和極端事件。
    所有計算完全向量化（pandas/numpy），無 Python for 迴圈。
    
    Required data columns: close (計算 returns)
    """
    
    def __init__(self, config: Dict, data_sources: List[str]):
        """
        Args:
            config: tail_risk section from scan_config.yaml
            data_sources: 不使用（tail risk 使用 close returns），接受參數以符合 Engine 統一介面
        """
        self._config = config
        self._data_sources = data_sources
        self.windows = config.get('windows', [21, 55, 100])
        self.cvar_alphas = config.get('cvar_alphas', [0.01, 0.05])
        self.rv_windows = config.get('rv_windows', [13, 21, 55])
        self.mdd_windows = config.get('mdd_windows', [21, 55, 100])
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """計算所有尾部風險特徵。"""
    
    def get_feature_metadata(self) -> Dict[str, Dict]:
        """返回所有特徵的 Metadata。"""
    
    def _compute_cvar(self, returns: pd.Series) -> pd.DataFrame:
        """Rolling CVaR（§5.1）"""
    
    def _compute_rv_decomposition(self, returns: pd.Series) -> pd.DataFrame:
        """Realized Volatility Decomposition + RSJ（§5.2）"""
    
    def _compute_ud_vol_ratio(self, returns: pd.Series) -> pd.DataFrame:
        """Up/Down Volatility Ratio（§5.3）"""
    
    def _compute_gpr(self, returns: pd.Series) -> pd.DataFrame:
        """Gain-to-Pain Ratio（§5.4）"""
    
    def _compute_jarque_bera(self, returns: pd.Series) -> pd.DataFrame:
        """Rolling Jarque-Bera Statistic（§5.5）"""
    
    def _compute_max_drawdown(self, close: pd.Series) -> pd.DataFrame:
        """Rolling Maximum Drawdown（§5.6）"""
```

**輸出 Schema**（範例）：

```json
{
  "tr_cvar_1pct_21": -0.082,
  "tr_cvar_1pct_55": -0.065,
  "tr_cvar_1pct_100": -0.058,
  "tr_cvar_5pct_21": -0.045,
  "tr_cvar_5pct_55": -0.038,
  "tr_cvar_5pct_100": -0.032,
  "tr_rv_up_13": 0.023,
  "tr_rv_down_13": 0.019,
  "tr_rsj_13": 0.004,
  "tr_rv_up_21": 0.028,
  "tr_rv_down_21": 0.024,
  "tr_rsj_21": 0.004,
  "tr_rv_up_55": 0.045,
  "tr_rv_down_55": 0.040,
  "tr_rsj_55": 0.005,
  "tr_ud_vol_ratio_13": 1.21,
  "tr_ud_vol_ratio_21": 1.17,
  "tr_ud_vol_ratio_55": 1.12,
  "tr_gpr_21": 1.35,
  "tr_gpr_55": 1.22,
  "tr_gpr_100": 1.15,
  "tr_jb_55": 12.5,
  "tr_jb_100": 8.7,
  "tr_mdd_21": -0.12,
  "tr_mdd_55": -0.18,
  "tr_mdd_100": -0.25
}
```

**特徵總數**：6（CVaR: 2α × 3w）+ 9（RV: 3 × 3w）+ 3（UDVR）+ 3（GPR）+ 2（JB）+ 3（MDD）= **26 features**

### 5.8 邊界條件表

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | 資料列數 < min window | 所有特徵返回 NaN | `test_tail_risk_insufficient_data` |
| 2 | 全部 return = 0 | CVaR=0, RV=0, GPR undefined → NaN, MDD=0 | `test_tail_risk_zero_returns` |
| 3 | 單方向 returns（全正或全負） | GPR=∞ 或 0 → clip to [0, 100] | `test_tail_risk_one_sided` |
| 4 | 窗口內只有 1 個負 return | CVaR = 該值, RV_down 接近 0 | `test_tail_risk_rare_negative` |
| 5 | RV_down = 0 | UDVR = NaN（避免除以零） | `test_udvr_zero_downside` |
| 6 | 極端報酬（±50%） | 所有指標正常計算 | `test_tail_risk_extreme` |
| 7 | alpha 超出範圍（0 或 1） | raise ValueError 在 `__init__` | `test_cvar_invalid_alpha` |
| 8 | NaN 超過 50% | 返回 NaN | `test_tail_risk_many_nans` |
| 9 | MDD 窗口內價格單調上漲 | MDD = 0（無回撤） | `test_mdd_monotonic_up` |
| 10 | MDD 窗口內價格單調下跌 | MDD = (first - last) / first | `test_mdd_monotonic_down` |
| 11 | close 含 0 或負值 | MDD 計算跳過（返回 NaN），log WARNING | `test_mdd_invalid_price` |

---

## 6. 特徵前處理與正規化層 (Preprocessing & Normalization)

**業界背景**：特徵正規化是量化策略的關鍵步驟。WorldQuant 101 Alphas 使用 cross-sectional rank；機器學習策略普遍使用 Gaussian normalization。López de Prado (2018) 強調金融時間序列的非定態性問題，提出 **Fractional Differencing**（分數差分）作為比傳統整數差分更優的解法——保留更多序列記憶。Adaptive Z-Score 和 Winsorization 是處理金融數據極端值的標準方法。

**設計決策**：

- **層級位置**：新增 Layer 6.5，在 Meta Features（Layer 6）之後、Validation（Layer 7）之前
- **選擇性應用**：每種前處理方法可獨立啟用，且可指定 `apply_to` 模式（all / specific patterns）
- **不替換原始特徵**：前處理後的特徵以 suffix 命名（e.g., `_rank`, `_gaussian`, `_diff`），原始特徵保留
- **可選模式**：`replace` 模式（替換原始特徵）或 `append` 模式（新增欄位），預設 `append`
- **Winsorization 例外**：`append` mode 下 Winsorization 是唯一例外——直接修改原始值（in-place）。後續 Rank/Gaussian/Z-Score 在 winsorized 基礎上 append 新欄位

### 6.1 Cross-Sectional Rank Transform (橫截面排名轉換)

**定義**：

$$rank(x_t) = \frac{\text{rank}(x_t, \text{window})}{n}$$

在滾動窗口內將值轉換為百分位排名 [0, 1]。

**實作**（高效向量化）：

```python
# 使用 rolling.rank() (pandas >= 1.4)
ranked = series.rolling(window).rank(pct=True)
```

**參數**：
- `window`: 252（或使用 global sequence_length）
- `apply_to`: `'all'` 或指定 prefix pattern

**輸出 suffix**：`_{orig_name}_rank`

### 6.2 Quantile-to-Gaussian Normalization (分位數高斯正規化)

**定義**：先轉為 uniform [0,1]（rank transform），再做 inverse CDF（probit transform）：

$$x_{gaussian} = \Phi^{-1}(\text{rank}(x))$$

其中 $\Phi^{-1}$ 為標準常態的逆累積分佈函式。

**實作**：

```python
from scipy.special import erfinv

def gaussian_normalize(ranked: pd.Series) -> pd.Series:
    """rank → gaussian transform（避免邊界 0/1）。"""
    clipped = ranked.clip(0.001, 0.999)
    return pd.Series(
        np.sqrt(2) * erfinv(2 * clipped - 1),
        index=ranked.index
    )
```

**參數**：
- `clip_range`: [0.001, 0.999]（避免 ±∞）

**輸出 suffix**：`_{orig_name}_gaussian`

### 6.3 ADF Stationarity + Auto-Differencing (定態性檢查與自動差分)

**定義**：對每個特徵做 ADF 檢定，若不定態（p > threshold）則自動差分一次（整數差分）。

**注意**：此為傳統整數差分方法。若需保留更多序列記憶，推薦使用 §6.6 Fractional Differencing 替代。

**實作**：

```python
from statsmodels.tsa.stattools import adfuller

def auto_difference_if_needed(
    series: pd.Series, 
    threshold: float = 0.05, 
    max_diff: int = 2
) -> Tuple[pd.Series, int]:
    """ADF 檢定 + 自動差分。
    
    Returns:
        (differenced_series, n_diffs_applied)
    """
    for d in range(max_diff + 1):
        diffed = series.diff(d) if d > 0 else series
        adf_result = adfuller(diffed.dropna(), autolag='AIC')
        if adf_result[1] < threshold:
            return diffed, d
    return series.diff(max_diff), max_diff
```

**參數**：
- `adf_threshold`: 0.05
- `max_diff`: 2
- `apply_to`: `'non_stationary'`（只對未通過 ADF 的特徵差分）
- `sample_size`: 500（ADF 只取最近 N 個點以加速）

**輸出 suffix**：`_{orig_name}_diff{d}`（d 為差分次數）

**注意**：此步驟較慢（每個特徵一次 ADF），建議：
- 只在首次生成時執行
- 結果快取（特徵 A 是否定態）
- 可設 `enabled: false` 跳過

### 6.4 Adaptive Z-Score (自適應 Z 分數)

**定義**：

$$z_t = \frac{x_t - \mu_{t,w}}{\sigma_{t,w} + \epsilon}$$

其中 $\mu$ 和 $\sigma$ 為滾動均值和標準差。

**與 Layer 3 的差異**：
- Layer 3 `rolling.zscore` 是作為 rolling aggregation 產生新特徵
- Layer 6.5 `adaptive_zscore` 是將已有特徵做標準化（in-place normalization 或 append）

**參數**：
- `windows`: [100, 252]
- `epsilon`: 1e-8
- `apply_to`: `'all'`

**輸出 suffix**：`_{orig_name}_zscore`

### 6.5 Winsorization (極端值裁剪)

**定義**：

$$x_{winsorized} = \text{clip}(x, \mu - k\sigma, \mu + k\sigma)$$

或使用百分位裁剪：

$$x_{winsorized} = \text{clip}(x, Q_{lower}, Q_{upper})$$

**參數**：
- `method`: `'sigma'` 或 `'quantile'`
- `sigma_k`: 3.0（±3σ 裁剪）
- `quantile_range`: [0.01, 0.99]
- `apply_to`: `'all'`

**輸出**：直接修改（不新增欄位），因為 winsorization 不改變語意

### 6.6 Fractional Differencing (分數差分)

**定義**（López de Prado, 2018, AFML Chapter 5）：

整數差分（d=1）雖然使序列定態，但會摧毀大部分記憶（長期依賴結構）。Fractional Differencing 使用最小分數階 $d^*$（$0 < d^* < 1$），在達成定態性的同時保留最多序列記憶。

$$\tilde{X}_t = \sum_{k=0}^{\infty} w_k X_{t-k}$$

其中權重：

$$w_k = -w_{k-1} \frac{d - k + 1}{k}$$

$w_0 = 1$，序列在 $|w_k| < \tau$（截斷閾值）時截斷。

**Fixed-Width Window Implementation**：

```python
def get_weights_ffd(d: float, threshold: float = 1e-5) -> np.ndarray:
    """計算 FFD (Fixed-Width Window Fractional Differencing) 權重。"""
    w = [1.0]
    k = 1
    while True:
        w_k = -w[-1] * (d - k + 1) / k
        if abs(w_k) < threshold:
            break
        w.append(w_k)
        k += 1
    return np.array(w[::-1])

def frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-5) -> pd.Series:
    """Fixed-Width Window Fractional Differencing（向量化實作）。
    
    使用 np.convolve 進行向量化卷積，避免 Python for 迴圈。
    """
    weights = get_weights_ffd(d, threshold)
    width = len(weights)
    vals = series.dropna().values
    # 向量化卷積：weights 已是逆序（get_weights_ffd 返回 w[::-1]）
    convolved = np.convolve(vals, weights[::-1], mode='full')[:len(vals)]
    result = pd.Series(np.nan, index=series.index, dtype=float)
    # 前 width-1 個值為 NaN（不足窗口）
    valid_idx = series.dropna().index[width - 1:]
    result.loc[valid_idx] = convolved[width - 1:]
    return result
```

**找到最小 $d^*$**（二分搜尋）：

```python
def find_min_d(series: pd.Series, adf_threshold: float = 0.05,
               d_range: Tuple[float, float] = (0.0, 1.0),
               precision: float = 0.01) -> float:
    """二分搜尋最小 d* 使序列通過 ADF 定態性檢定。"""
    lo, hi = d_range
    while hi - lo > precision:
        mid = (lo + hi) / 2
        diffed = frac_diff_ffd(series, mid)
        adf_stat = adfuller(diffed.dropna(), autolag='AIC')
        if adf_stat[1] < adf_threshold:
            hi = mid
        else:
            lo = mid
    return hi
```

**參數**：
- `d_range`: [0.0, 1.0]
- `adf_threshold`: 0.05
- `weight_threshold`: 1e-5（權重截斷閾值）
- `precision`: 0.01（二分搜尋精度）
- `apply_to`: `'non_stationary'`（只對非定態特徵套用）
- `cache_d_star`: `true`（快取每個特徵的 $d^*$，避免每次重算）

**輸出 suffix**：`_{orig_name}_fracdiff`

**與 §6.3 ADF 整數差分的比較**：

| 特性 | ADF + 整數差分 (§6.3) | Fractional Differencing (§6.6) |
|------|----------------------|-------------------------------|
| 記憶保留 | 差分 d=1 會丟失大部分記憶 | 最小 $d^*$ 保留最多記憶 |
| 預測能力 | 降低（失去長期結構） | 較高（保留長期依賴） |
| 計算速度 | 快（O(N)） | 較慢（O(N × width) + ADF 二分搜尋） |
| 適用場景 | 快速原型、對記憶保留不敏感 | 生產環境、ML 模型需要最優特徵品質 |
| 推薦使用 | 否（除非速度是首要考量） | **是**（業界最佳實務） |

**效能考量**：
- 二分搜尋 $d^*$ 需要多次 ADF 檢定（~7-10 次，精度 0.01）
- 建議對每個特徵的 $d^*$ 做快取（§11 快取策略）
- 首次計算較慢，後續使用快取值

### 6.7 模組設計：FeaturePreprocessor

```python
class FeaturePreprocessor:
    """Layer 6.5: 特徵前處理與正規化。
    
    在所有特徵生成後（Layer 0-6），對 features DataFrame 做統一的
    前處理/正規化轉換，然後交給 Layer 7 validation。
    
    六種轉換（各自可獨立啟用/停用）：
    1. Winsorization (極端值裁剪)
    2. ADF + Auto-Differencing (整數差分)
    3. Fractional Differencing (分數差分) ← 推薦
    4. Cross-Sectional Rank Transform
    5. Quantile-to-Gaussian Normalization
    6. Adaptive Z-Score
    
    執行順序：
    Winsorization → Fractional Differencing / ADF → Rank Transform → Gaussian → Z-Score
    
    說明：
    - Winsorization 先做，避免極端值影響後續統計
    - 差分處理非定態（Fractional 優先，ADF fallback）
    - Rank/Gaussian 是分佈轉換
    - Z-Score 最後做標準化
    """
    
    def __init__(self, config: Dict):
        """
        Args:
            config: preprocessing section from scan_config.yaml
        """
        self.rank_config = config.get('rank_transform', {})
        self.gaussian_config = config.get('gaussian_normalize', {})
        self.adf_config = config.get('adf_differencing', {})
        self.zscore_config = config.get('adaptive_zscore', {})
        self.winsor_config = config.get('winsorization', {})
        self.fracdiff_config = config.get('fractional_differencing', {})
        self.mode = config.get('mode', 'append')  # 'append' or 'replace'
    
    def transform(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """對所有特徵做前處理/正規化。
        
        Args:
            features_df: 所有 Layer 0-6 產出的特徵 DataFrame
        
        Returns:
            處理後的 DataFrame（append mode: 新增帶 suffix 的欄位;
                              replace mode: 直接修改原欄位）
        """
    
    def _apply_winsorization(self, df: pd.DataFrame) -> pd.DataFrame:
        """Winsorization（§6.5）— in-place 修改"""
    
    def _apply_fractional_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fractional Differencing（§6.6）"""
    
    def _apply_adf_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        """ADF + Auto-Differencing（§6.3）"""
    
    def _apply_rank_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cross-Sectional Rank Transform（§6.1）"""
    
    def _apply_gaussian_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Quantile-to-Gaussian（§6.2）"""
    
    def _apply_adaptive_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adaptive Z-Score（§6.4）"""
    
    def _select_columns(self, df: pd.DataFrame, apply_to: str) -> List[str]:
        """根據 apply_to 配置選擇要處理的欄位。
        
        支援：
        - 'all': 所有特徵欄位
        - 'layer1_only': 只處理 Layer 1 的 atomic indicators
        - pattern: regex pattern match column names
        - list: 明確列出欄位名稱
        """
```

### 6.8 邊界條件表

| # | 條件 | 預期行為 | 測試名 |
|---|------|---------|--------|
| 1 | 空 DataFrame | 返回空 DataFrame | `test_preprocess_empty_df` |
| 2 | 全部 NaN 欄位 | 轉換後仍為 NaN | `test_preprocess_all_nan_column` |
| 3 | 單一值欄位（std=0） | Z-Score=0, Rank 全為 0.5, Gaussian=0 | `test_preprocess_constant_column` |
| 4 | ADF 遇到 NaN 過多 | skip 差分，保留原始特徵 | `test_adf_nan_heavy` |
| 5 | Gaussian 邊界值（0 或 1） | clip 到 [0.001, 0.999] 再轉換 | `test_gaussian_boundary` |
| 6 | Winsorization 使 std=0 | 不影響（winsor 後才計算 zscore） | `test_winsor_then_zscore` |
| 7 | replace mode 不新增欄位 | 原位修改，column count 不變 | `test_preprocess_replace_mode` |
| 8 | append mode 保留原始 | 新增帶 suffix 的欄位，原始特徵不變 | `test_preprocess_append_mode` |
| 9 | 1000+ 欄位的大 DataFrame | 完成時間 < 30s | `test_preprocess_performance` |
| 10 | Fractional Diff 的 d* 搜尋超時（序列極端非定態） | 使用 d=1.0 fallback，log WARNING | `test_fracdiff_convergence_failure` |
| 11 | Fractional Diff 權重長度 > 資料長度 | 截斷權重至資料長度，前 width-1 個值為 NaN | `test_fracdiff_short_data` |
| 12 | ADF 和 Fractional Diff 同時啟用 | Fractional Diff 優先執行，ADF skip 已處理的欄位 | `test_fracdiff_adf_coexist` |

---

## 7. 架構整合設計

### 7.1 Pipeline 擴展策略

**現有 Pipeline**（不修改流程）：

```
Layer 0: Data Ingestion → CryptoSpotAdapter.fetch()
Layer 1: Atomic Indicators → 8 engines (trend, momentum, volatility, volume, cycle, pattern, statistics, custom)
Layer 2: Derived Features → DerivedOperatorEngine
Layer 3: Rolling Aggregation → RollingAggregator
Layer 4: Lag Features → LagProcessor
Layer 5: Cross-Sectional → RelativeStrengthProcessor
Layer 6: Meta Features → ConsensusFeatureEngine + TimeFeatureEngine + InteractionFeatureEngine
Layer 7: Validation & Persistence → FeatureValidator + FeatureStorage
```

**擴展後**：

```
Layer 0: Data Ingestion ← 不修改
Layer 1: Atomic Indicators ← 新增 3 engines:
   ├── TrendIndicatorEngine          (既有)
   ├── MomentumIndicatorEngine       (既有)
   ├── VolatilityIndicatorEngine     (既有)
   ├── VolumeIndicatorEngine         (既有)
   ├── CycleIndicatorEngine          (既有)
   ├── PatternIndicatorEngine        (既有)
   ├── StatisticsIndicatorEngine     (既有)
   ├── CustomIndicatorEngine         (既有)
   ├── MicrostructureIndicatorEngine (新增 §3)
   ├── EntropyIndicatorEngine        (新增 §4)
   └── TailRiskIndicatorEngine       (新增 §5)
Layer 2-6: ← 不修改
Layer 6.5: Preprocessing & Normalization ← 新增 (§6)
   └── FeaturePreprocessor.transform()
Layer 7: Validation & Persistence ← 不修改
```

**feature_factory.py 修改**（與現有程式碼模式一致）：

```python
# === 新增 import（頂部） ===
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

# === _layer1_atomic_indicators 方法尾部新增（CustomIndicatorEngine 之後） ===

if hasattr(config.atomic_indicators, 'microstructure') and config.atomic_indicators.microstructure.enabled:
    engine = MicrostructureIndicatorEngine(
        config.atomic_indicators.microstructure.model_dump(),
        sources
    )
    frames.append(engine.compute_all(data))

if hasattr(config.atomic_indicators, 'entropy') and config.atomic_indicators.entropy.enabled:
    engine = EntropyIndicatorEngine(
        config.atomic_indicators.entropy.model_dump(),
        sources
    )
    frames.append(engine.compute_all(data))

if hasattr(config.atomic_indicators, 'tail_risk') and config.atomic_indicators.tail_risk.enabled:
    engine = TailRiskIndicatorEngine(
        config.atomic_indicators.tail_risk.model_dump(),
        sources
    )
    frames.append(engine.compute_all(data))

# === generate_features 方法中，layer6 之後新增 Layer 6.5 ===
# （在現有 _layer7_validate_and_persist 呼叫之前）

# Layer 6.5 Preprocessing（避免特徵重複的正確邏輯）
layers_for_validation = [layer1, layer2, layer3, layer4, layer5, layer6]

if hasattr(config, 'preprocessing') and config.preprocessing.enabled:
    all_features = self._combine_layers(layers_for_validation)
    preprocessed = self._safe_execute(
        "Layer 6.5",
        self._layer6_5_preprocessing,
        all_features,
        config
    )
    if not preprocessed.empty:
        # preprocessed 包含 winsorized 原始特徵 + append 的新欄位
        # 用 preprocessed 取代 layer1-6（避免重複）
        layers_for_validation = [preprocessed]

result = self._layer7_validate_and_persist(
    symbol, timeframe, raw_data,
    layers_for_validation,
    config, time.time() - start_time, config_hash
)

# === 新增 _layer6_5_preprocessing 方法 ===

def _layer6_5_preprocessing(
    self, all_features: pd.DataFrame, config: "FactoryConfig"
) -> pd.DataFrame:
    """Layer 6.5: Feature Preprocessing & Normalization."""
    preprocessor = FeaturePreprocessor(config.preprocessing.model_dump())
    return preprocessor.transform(all_features)
```

**hasattr 防護說明**：使用 `hasattr` 確保舊版 `scan_config.yaml`（未包含新 section）不會導致 AttributeError，維護向後相容性。

### 7.2 Config 擴展

在 `scan_config.yaml` 的 `atomic_indicators` 下新增 3 個 section，另新增頂層 `preprocessing` section：

```yaml
# === 新增 Layer 1 engines ===

atomic_indicators:
  # ... 既有 7 個 engines 不修改 ...
  
  microstructure:
    enabled: false  # 預設關閉，需顯式啟用
    windows: [5, 13, 21, 55]
    epsilon: 1.0e-10
    min_trades: 1
    enabled_features: all  # or list: [amihud, kyle_lambda, roll_spread, ...]
    cs_spread_smooth: [5, 13, 21]
    ofi_raw: true
    kyle_lambda_windows: [13, 21, 55]
    vpin_n_buckets: [30, 50]
    vpin_zscore_windows: [21, 55]
  
  entropy:
    enabled: false
    windows: [55, 100]
    n_bins: 10
    apen_m: 2
    apen_r_ratio: 0.2
    hurst_windows: [55, 100, 200]
    fractal_kmax: 10
    use_numba: true
    perm_m: 3
    perm_windows: [21, 55, 100]
    apply_to:
      - close_return
    shannon_windows: [21, 55, 100]
  
  tail_risk:
    enabled: false
    windows: [21, 55, 100]
    cvar_alphas: [0.01, 0.05]
    rv_windows: [13, 21, 55]
    mdd_windows: [21, 55, 100]

# === 新增 Layer 6.5 ===

preprocessing:
  enabled: false  # 預設關閉
  mode: append  # 'append' (新增帶 suffix 的欄位) or 'replace' (原位替代)
  
  winsorization:
    enabled: true
    method: sigma  # 'sigma' or 'quantile'
    sigma_k: 3.0
    quantile_range: [0.01, 0.99]
    apply_to: all
  
  adf_differencing:
    enabled: false  # 較慢，預設關閉（推薦使用 fractional_differencing）
    adf_threshold: 0.05
    max_diff: 2
    sample_size: 500
    apply_to: non_stationary
  
  fractional_differencing:
    enabled: false  # 較慢，但品質更高
    d_range: [0.0, 1.0]
    adf_threshold: 0.05
    weight_threshold: 1.0e-5
    precision: 0.01
    apply_to: non_stationary
    cache_d_star: true
  
  rank_transform:
    enabled: true
    window: 252
    apply_to: all
  
  gaussian_normalize:
    enabled: false
    clip_range: [0.001, 0.999]
    apply_to: all
  
  adaptive_zscore:
    enabled: true
    windows: [100]
    epsilon: 1.0e-8
    apply_to: all
```

### 7.3 Pydantic Config Models

在 `feature_config.py` 擴展：

```python
# === 新增 Layer 1 Config Models ===

class MicrostructureConfig(BaseModel):
    """微觀結構指標配置"""
    enabled: bool = False
    windows: List[int] = [5, 13, 21, 55]
    epsilon: float = 1e-10
    min_trades: int = 1
    enabled_features: Union[str, List[str]] = 'all'
    cs_spread_smooth: List[int] = [5, 13, 21]
    ofi_raw: bool = True
    kyle_lambda_windows: List[int] = [13, 21, 55]
    vpin_n_buckets: List[int] = [30, 50]
    vpin_zscore_windows: List[int] = [21, 55]

class EntropyConfig(BaseModel):
    """資訊理論指標配置"""
    enabled: bool = False
    windows: List[int] = [55, 100]
    n_bins: int = 10
    apen_m: int = 2
    apen_r_ratio: float = 0.2
    hurst_windows: List[int] = [55, 100, 200]
    fractal_kmax: int = 10
    use_numba: bool = True
    perm_m: int = 3
    perm_windows: List[int] = [21, 55, 100]
    apply_to: List[str] = ['close_return']
    shannon_windows: List[int] = [21, 55, 100]

    @field_validator('perm_m')
    @classmethod
    def validate_perm_m(cls, v):
        if v < 2:
            raise ValueError(f"perm_m must be >= 2, got {v}")
        return v

class TailRiskConfig(BaseModel):
    """尾部風險指標配置"""
    enabled: bool = False
    windows: List[int] = [21, 55, 100]
    cvar_alphas: List[float] = [0.01, 0.05]
    rv_windows: List[int] = [13, 21, 55]
    mdd_windows: List[int] = [21, 55, 100]

    @field_validator('cvar_alphas')
    @classmethod
    def validate_alphas(cls, v):
        for a in v:
            if not 0 < a < 1:
                raise ValueError(f"cvar_alpha must be in (0, 1), got {a}")
        return v

# === 新增 Layer 6.5 Config Models ===

class WinsorConfig(BaseModel):
    """Winsorization 配置"""
    enabled: bool = True
    method: str = 'sigma'
    sigma_k: float = 3.0
    quantile_range: List[float] = [0.01, 0.99]
    apply_to: Union[str, List[str]] = 'all'

class ADFDifferencingConfig(BaseModel):
    """ADF 差分配置"""
    enabled: bool = False
    adf_threshold: float = 0.05
    max_diff: int = 2
    sample_size: int = 500
    apply_to: str = 'non_stationary'

class FractionalDifferencingConfig(BaseModel):
    """分數差分配置"""
    enabled: bool = False
    d_range: List[float] = [0.0, 1.0]
    adf_threshold: float = 0.05
    weight_threshold: float = 1e-5
    precision: float = 0.01
    apply_to: str = 'non_stationary'
    cache_d_star: bool = True

class RankTransformConfig(BaseModel):
    """排名轉換配置"""
    enabled: bool = True
    window: int = 252
    apply_to: Union[str, List[str]] = 'all'

class GaussianNormalizeConfig(BaseModel):
    """高斯正規化配置"""
    enabled: bool = False
    clip_range: List[float] = [0.001, 0.999]
    apply_to: Union[str, List[str]] = 'all'

class AdaptiveZScoreConfig(BaseModel):
    """自適應 Z-Score 配置"""
    enabled: bool = True
    windows: List[int] = [100]
    epsilon: float = 1e-8
    apply_to: Union[str, List[str]] = 'all'

class PreprocessingConfig(BaseModel):
    """前處理層完整配置"""
    enabled: bool = False
    mode: str = 'append'
    winsorization: WinsorConfig = WinsorConfig()
    adf_differencing: ADFDifferencingConfig = ADFDifferencingConfig()
    fractional_differencing: FractionalDifferencingConfig = FractionalDifferencingConfig()
    rank_transform: RankTransformConfig = RankTransformConfig()
    gaussian_normalize: GaussianNormalizeConfig = GaussianNormalizeConfig()
    adaptive_zscore: AdaptiveZScoreConfig = AdaptiveZScoreConfig()

# === AtomicIndicatorConfig 擴展 ===

class AtomicIndicatorConfig(BaseModel):
    trend: CategoryConfig = Field(default_factory=CategoryConfig)
    momentum: CategoryConfig = Field(default_factory=CategoryConfig)
    volatility: CategoryConfig = Field(default_factory=CategoryConfig)
    volume: CategoryConfig = Field(default_factory=CategoryConfig)
    cycle: CategoryConfig = Field(default_factory=CategoryConfig)
    pattern: CategoryConfig = Field(default_factory=CategoryConfig)
    statistics: CategoryConfig = Field(default_factory=CategoryConfig)
    # 新增（使用專用 Config 而非 CategoryConfig，因為不使用 TA-Lib）
    microstructure: MicrostructureConfig = MicrostructureConfig()
    entropy: EntropyConfig = EntropyConfig()
    tail_risk: TailRiskConfig = TailRiskConfig()

# === FactoryConfig 擴展 ===

class FactoryConfig(BaseModel):
    # ... 既有欄位不修改 ...
    preprocessing: PreprocessingConfig = PreprocessingConfig()
```

### 7.4 Factory 擴展

`momentum/factories.py` 不需要修改，因為新引擎和前處理器都整合在 `FeatureFactory` 內部（`_layer1_atomic_indicators` 和 `_layer6_5_preprocessing` 方法），不需要獨立的 factory function。`create_feature_factory()` 維持不變。

---

## 8. 檔案結構

### 8.1 新增檔案

```
momentum/FeatureEngineering/
├── atomic/
│   ├── microstructure_indicators.py    ← §3 MicrostructureIndicatorEngine
│   ├── entropy_indicators.py           ← §4 EntropyIndicatorEngine
│   └── tail_risk_indicators.py         ← §5 TailRiskIndicatorEngine
├── preprocessing/
│   ├── __init__.py
│   └── feature_preprocessor.py         ← §6 FeaturePreprocessor
tests/momentum/
├── test_microstructure_indicators.py   ← §3 測試
├── test_entropy_indicators.py          ← §4 測試
├── test_tail_risk_indicators.py        ← §5 測試
└── test_feature_preprocessor.py        ← §6 測試
```

### 8.2 修改檔案

```
momentum/FeatureEngineering/
├── feature_factory.py                  ← Layer 1 新增 3 engine + Layer 6.5
├── feature_config.py                   ← 新增 4 config models + PreprocessingConfig
├── atomic/__init__.py                  ← 新增 3 engine 匯出
config/
└── scan_config.yaml                    ← 新增 microstructure, entropy, tail_risk, preprocessing sections
```

### 8.3 相依套件

| 套件 | 用途 | 必要性 | 條件 import 策略 |
|------|------|--------|-----------------|
| `numpy` / `pandas` | 全部向量化計算 | 必要（已安裝） | 直接 import |
| `scipy` | `erfinv`（Gaussian Normalize）、`norm.cdf`（VPIN BVC） | 必要（已安裝） | 直接 import |
| `statsmodels` | `adfuller`（ADF 檢定，§6.3/§6.6） | 選用 | `try: import ... except ImportError: log WARNING` |
| `numba` | ApEn/SampEn JIT 加速（§4.2/§4.3） | 選用 | `try: import ... except ImportError: fallback 純 numpy` |

### 8.4 統計

| 類別 | 檔案數 |
|------|--------|
| 新增核心模組 | 4 (3 engines + 1 preprocessor) |
| 新增測試 | 4 |
| 新增目錄 | 1 (`preprocessing/`) |
| 修改檔案 | 4 (`feature_factory.py`, `feature_config.py`, `atomic/__init__.py`, `scan_config.yaml`) |
| **合計** | 13 (`8 新增 + 4 修改 + 1 目錄`) |

---

## 9. 下游 Layer 影響分析

### 9.1 新增 Layer 1 特徵的下游傳播

新增的 3 個 Layer 1 引擎（66 features）的輸出會自動流入 Layer 2-6：

| 下游 Layer | 影響 | 特徵膨脹倍率 | 控制方式 |
|-----------|------|-------------|---------|
| **Layer 2 (Derived)** | `ms_*`/`ent_*`/`tr_*` 進入 Distance/Cross/Momentum/Ratio 算子 | ~4-8x | operators.apply_to 可限制 |
| **Layer 3 (Rolling Agg)** | 對新特徵做 slope/std/mean/zscore 等聚合 | ~10x (windows × aggregators) | rolling_aggregation.apply_to 可限制 |
| **Layer 4 (Lag)** | 對新特徵做 lag 展開 | ~3-5x | lag_features.apply_to 可限制 |
| **Layer 5 (Cross-Sectional)** | 不受影響（只處理 close） | 1x | — |
| **Layer 6 (Meta)** | 不直接使用新特徵（使用 Layer 1 的 trend/momentum/volatility patterns） | 1x | — |
| **Layer 6.5 (Preprocessing)** | 對所有特徵做 rank/zscore/差分 | ~2-3x (取決於啟用的 transforms) | preprocessing.apply_to |

### 9.2 特徵數量膨脹估計

**最保守估計**（所有 downstream layer 開啟，apply_to='all'）：

| Stage | 特徵數 | 說明 |
|-------|--------|------|
| Layer 1 新增 | 66 | 25+15+26 |
| + Layer 2 | ~264 | ×4 (distance, cross, momentum, ratio) |
| + Layer 3 | ~2640 | ×10 (3 windows × 10 aggregators) |
| + Layer 4 | ~396 | Layer1+raw × 6 lags |
| + Layer 6.5 | ×2 | rank + zscore append |
| **Total 膨脹** | ~6,000+ | 極端情境 |

**實際建議**：使用 `apply_to` 限制 Layer 2-4 只處理部分新特徵，或在 scan_config 中設定 `exclude_patterns: ["ms_*", "ent_*", "tr_*"]`。典型配置下膨脹約 200-500 特徵。

### 9.3 記憶體影響

- 66 new features × 300 bars × 8 bytes (float64) = ~158 KB
- 實際使用 float32: ~79 KB
- 加上 Layer 2-4 膨脹（限制後 ~300 features）: ~720 KB
- **結論**：記憶體影響可忽略

---

## 10. 錯誤處理與降級策略

### 10.1 引擎級別隔離

每個新引擎（Microstructure/Entropy/TailRisk）都在 `_safe_execute` 包裝下執行。如果某引擎完全失敗（例如缺少必要欄位），pipeline 會：

1. 記錄 ERROR log（含 `exc_info=True`）
2. 返回空 DataFrame（不影響其他引擎）
3. Layer 7 validation 正常執行（少了該引擎的特徵而已）

### 10.2 指標級別降級

在引擎內部，個別指標失敗不應導致整個引擎失敗：

```python
def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for method in [self._compute_amihud, self._compute_kyle_lambda, ...]:
        try:
            frames.append(method(data))
        except Exception as e:
            logger.warning("Indicator %s failed: %s", method.__name__, e)
    # 返回成功計算的特徵
    return pd.concat(frames, axis=1) if frames else pd.DataFrame(index=data.index)
```

### 10.3 欄位缺失降級

| 缺失欄位 | 影響範圍 | 降級行為 | 測試名 |
|---------|---------|---------|--------|
| `taker_buy_volume` | OFI, VPIN | 使用 `taker_ratio * volume` 替代，log WARNING | `test_degrade_missing_taker_buy_vol` |
| `taker_ratio` | OFI fallback | 使用 volume-only 估計（精度降低），log WARNING | `test_degrade_missing_taker_ratio` |
| `trades` | Large Trade Ratio | 跳過該指標，log WARNING | `test_degrade_missing_trades` |
| `quote_volume` | Amihud, Large Trade | 使用 `close * volume` 替代，log WARNING | `test_degrade_missing_quote_volume` |

### 10.4 Optional 套件降級

| 套件 | 影響範圍 | 降級行為 | 測試名 |
|------|---------|---------|--------|
| `numba` 不可用 | ApEn/SampEn | fallback 純 numpy（速度降低 10x） | `test_degrade_no_numba` |
| `statsmodels` 不可用 | ADF / Fractional Differencing | 兩者自動 disabled，log WARNING | `test_degrade_no_statsmodels` |

```python
# 模式：try import → flag → conditional use

try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    logger.warning("Numba not available, ApEn/SampEn will use pure numpy (slower)")

try:
    from statsmodels.tsa.stattools import adfuller
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("statsmodels not available, ADF/Fractional Differencing disabled")
```

---

## 11. 快取策略

### 11.1 Layer 1 特徵快取

新引擎的輸出隨 Layer 1 其他特徵一起，由現有的 `FeatureStorage` 快取至 HDF5。快取 key 基於 `config_hash`（包含新引擎的配置），因此配置變更會自動使快取失效。

### 11.2 Fractional Differencing d* 快取

$d^*$ 的二分搜尋是最耗時的操作。快取策略：

```python
# 快取結構：Dict[feature_name, float]
# 存儲位置：data_cache/features/{symbol}_{timeframe}_d_star_cache.json
{
    "close_trend_EMA21_value": 0.35,
    "close_momentum_RSI14_value": 0.12,
    "ms_amihud_illiq_21": 0.48
}
```

**快取失效條件**：
1. 特徵數據長度變更 > 20%
2. Config 中 `adf_threshold` 或 `precision` 變更
3. 手動 `force_regenerate=True`

### 11.3 ADF 結果快取

同理，ADF 定態性檢定結果快取：

```python
# Dict[feature_name, bool]  # True = 定態, False = 需要差分
```

---

## 12. Logging 規範

### 12.1 引擎層級

| 事件 | Level | 範例 |
|------|-------|------|
| 引擎啟動 | INFO | `"MicrostructureEngine: computing 7 indicators for 300 bars"` |
| 引擎完成 | INFO | `"MicrostructureEngine: 25 features computed in 0.3s"` |
| 個別指標失敗 | WARNING | `"VPIN computation failed: missing taker_buy_volume"` |
| 引擎完全失敗 | ERROR | `"EntropyEngine failed: {exc}"` (with `exc_info=True`) |
| Optional 套件缺失 | WARNING | `"Numba not available, using pure numpy fallback"` |

### 12.2 前處理層級

| 事件 | Level | 範例 |
|------|-------|------|
| Layer 6.5 啟動 | INFO | `"Preprocessing: 6 transforms on 1500 features"` |
| 個別 transform 完成 | INFO | `"Winsorization: clipped 23 values in 15 columns"` |
| d* 快取命中 | DEBUG | `"FracDiff d* cache hit for 1200/1500 features"` |
| ADF/FracDiff 跳過（已定態） | DEBUG | `"Skipping 800 already-stationary features"` |
| transform 失敗 | WARNING | `"Gaussian normalize failed for column X: all NaN"` |

### 12.3 禁止事項

- ❌ 不在 hot loop 內做逐行 log（如 rolling.apply 內部）
- ❌ 不 log 原始數據值（安全考量）
- ❌ 不使用 `print()` — 統一使用 `momentum.core.logging.get_logger()`

---

## 13. 測試計畫

### 13.1 單元測試

| 模組 | 測試內容 | 測試數 |
|------|---------|--------|
| `MicrostructureIndicatorEngine` | 7 指標正確性 + 邊界條件 (§3.9 × 11) + feature metadata | ~30 |
| `EntropyIndicatorEngine` | 6 指標正確性 + 邊界條件 (§4.8 × 11) + Numba fallback | ~28 |
| `TailRiskIndicatorEngine` | 6 指標正確性 + 邊界條件 (§5.8 × 11) | ~26 |
| `FeaturePreprocessor` | 6 轉換正確性 + 組合 + 邊界條件 (§6.8 × 12) + mode 切換 | ~32 |
| 降級場景 (§10) | 欄位缺失降級 (×4) + Optional 套件降級 (×2) | ~6 |
| **合計** | | **~122** |

### 13.2 整合測試

| 測試 | 說明 |
|------|------|
| `test_pipeline_with_microstructure` | 啟用 microstructure → 驗證 Layer 1 output 包含 `ms_*` 欄位 |
| `test_pipeline_with_entropy` | 啟用 entropy → 驗證 Layer 1 output 包含 `ent_*` 欄位 |
| `test_pipeline_with_tail_risk` | 啟用 tail_risk → 驗證 Layer 1 output 包含 `tr_*` 欄位 |
| `test_pipeline_with_preprocessing` | 啟用 preprocessing → 驗證 Layer 6.5 output 有 `_rank`/`_zscore` suffix |
| `test_pipeline_all_new_features` | 全部啟用 → 驗證 feature count 增加、Layer 7 validation 通過 |
| `test_pipeline_backward_compatible` | 全部新功能 disabled → pipeline 行為完全不變 |
| `test_pipeline_partial_engine_failure` | 一個新引擎失敗 → 其他引擎正常、pipeline 完成 |

### 13.3 效能測試

| 測試 | 目標 |
|------|------|
| `test_microstructure_performance` | 300 bars × 全部 windows → < 500ms |
| `test_entropy_performance` | 300 bars × ApEn/SampEn(window=100) → < 5s（含 Numba warmup）|
| `test_tail_risk_performance` | 300 bars × 全部指標 → < 200ms |
| `test_preprocessing_performance` | 1000 features × 300 bars → < 30s |
| `test_full_pipeline_overhead` | 全部新功能啟用 vs 禁用，overhead < 50% |

### 13.4 邊界條件覆蓋驗證

所有 51 項邊界條件（§3.9 × 11 + §4.8 × 11 + §5.8 × 11 + §6.8 × 12 = 45 項 + §10.3 × 4 + §10.4 × 2 = 51 項）均有明確的測試名映射，100% 覆蓋。

---

## 14. 效能與記憶體預估

### 14.1 單引擎效能（M1 Mac, 300 bars）

| 引擎 | 主要瓶頸 | 預估時間 | 記憶體峰值 |
|------|---------|---------|-----------|
| Microstructure | Kyle's Lambda rolling OLS | 100-300ms | ~5 MB |
| Entropy (無 Numba) | ApEn/SampEn O(N²) loop | 3-8s | ~10 MB |
| Entropy (有 Numba) | Numba JIT warmup (首次) | 0.5-2s (首次 5s) | ~15 MB |
| Tail Risk | 全向量化 | 50-150ms | ~3 MB |
| Preprocessor (6 transforms) | FracDiff d* search | 5-30s (首次) | ~20 MB |
| Preprocessor (cached d*) | Rank/ZScore transforms | 1-5s | ~15 MB |

### 14.2 全 Pipeline 影響

| 配置 | 額外時間 | 額外記憶體 | overhead % |
|------|---------|-----------|-----------|
| 僅 Microstructure | +0.3s | +5 MB | <5% |
| 僅 Tail Risk | +0.15s | +3 MB | <3% |
| 僅 Entropy (Numba) | +2s | +15 MB | ~20% |
| Preprocessing (cached) | +3s | +15 MB | ~30% |
| **全部啟用 (cached)** | **+5.5s** | **+35 MB** | **~50%** |

### 14.3 最佳化優先級

若效能不達標：
1. **Entropy**: Numba JIT 必須啟用（10× 加速）
2. **Preprocessor**: d* 快取必須啟用（首次後 6× 加速）
3. **Microstructure**: Kyle's Lambda 改用 rolling.cov/var（已在 spec 中）
4. **最後手段**: 減少 windows 數量或禁用部分指標

---

## 15. 驗收標準

### 15.1 功能驗收

- [ ] 微觀結構引擎：7 個指標（含 VPIN）全部正確計算，命名符合 `ms_*` pattern
- [ ] 資訊理論引擎：6 個指標（含 Permutation Entropy）全部正確計算，命名符合 `ent_*` pattern
- [ ] 尾部風險引擎：6 個指標（含 Rolling MDD）全部正確計算，命名符合 `tr_*` pattern
- [ ] 前處理器：6 種轉換（含 Fractional Differencing）各自正確，支援 append/replace mode
- [ ] Config-Driven：所有新功能預設 disabled，顯式啟用後正常運作
- [ ] 向後相容：禁用所有新功能時，pipeline 行為完全不變

### 15.2 品質驗收

- [ ] 所有計算向量化（無 Python for 迴圈 on data rows，除 ApEn/SampEn 的 Numba JIT 內部迴圈、FracDiff 的 d* 二分搜尋 loop、以及 Hurst/Fractal 的 rolling.apply 回調）
- [ ] 邊界條件 100% 覆蓋（51 項邊界測試全部 PASS）
- [ ] 測試覆蓋率 ≥ 90%
- [ ] 無 hardcoded 數據（Data Truth Principle）
- [ ] logging 符合標準（§12 規範）

### 15.3 架構驗收

- [ ] Rule 1: `momentum/` 不 import `api/`
- [ ] Rule 2: 無 cross-domain 直接 import
- [ ] Rule 5: Config 從 `scan_config.yaml` 讀取
- [ ] Rule 6: 測試可獨立運行，不需 `run_api.py`
- [ ] 新增檔案位於正確目錄（`atomic/` 和 `preprocessing/`）
- [ ] Engine 建構子簽名一致：`__init__(self, config: Dict, data_sources: List[str])`
- [ ] 所有 Engine 實作 `get_feature_metadata()` 方法

### 15.4 效能驗收

- [ ] §14 所有效能目標達成（M1 Mac）
- [ ] 全部新功能啟用時 pipeline overhead < 50%
- [ ] d* 快取機制正常運作（第二次執行明顯加速）

### 15.5 業界覆蓋率對標

| 面向 | 指標 | V0.1 覆蓋 | V1 新增 | 業界覆蓋率 |
|------|------|----------|---------|-----------|
| 微觀結構 | Amihud, Kyle's Lambda, Roll's, CS, OFI, LTR | ✅ | VPIN | ~90% |
| 資訊理論 | Shannon, ApEn, SampEn, Hurst, Fractal Dim | ✅ | Permutation Entropy | ~90% |
| 尾部風險 | CVaR, RV Decomposition, UDVR, GPR, JB | ✅ | Rolling Max Drawdown | ~90% |
| 前處理 | Rank, Gaussian, ADF, Z-Score, Winsorization | ✅ | Fractional Differencing | ~95% |

---

## 16. MCP Tool Interface (V2.0/V3.0 準備)

> **狀態**：規格制定，不在本期實作範圍。為 V2.0 Chat 模式 / V3.0 Agent 模式預留介面定義。

### 16.1 預留 Tool 定義

```yaml
tools:
  feature_factory_generate:
    description: "生成指定標的的全量特徵"
    parameters:
      symbol: string
      timeframe: string
      enable_microstructure: boolean (default: false)
      enable_entropy: boolean (default: false)
      enable_tail_risk: boolean (default: false)
      enable_preprocessing: boolean (default: false)
    returns:
      feature_count: int
      generation_time: float
      hdf5_path: string

  feature_factory_preview:
    description: "預覽特徵生成配置（不實際計算）"
    parameters:
      config_override: object
    returns:
      estimated_feature_count: int
      estimated_time: float
      estimated_memory_mb: float
      enabled_engines: list[string]
```

### 16.2 設計約束

- Tool 不直接呼叫 Engine，而是透過 `api/services/` 的 Service 層
- Service 使用 `create_feature_factory()` 建構 FeatureFactory
- 符合 Rule 3（Service 用 Factory）

---

## 17. 附錄

### 附錄 A: 業界參考文獻

1. **Amihud, Y. (2002).** "Illiquidity and Stock Returns: Cross-Section and Time-Series Effects." *Journal of Financial Markets.* — §3.1 Amihud Illiquidity Ratio
2. **Kyle, A.S. (1985).** "Continuous Auctions and Insider Trading." *Econometrica.* — §3.2 Kyle's Lambda
3. **Roll, R. (1984).** "A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market." *Journal of Finance.* — §3.3 Roll's Implied Spread
4. **Corwin, S.A. & Schultz, P. (2012).** "A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices." *Journal of Finance.* — §3.4 Corwin-Schultz Spread
5. **Easley, D., López de Prado, M. & O'Hara, M. (2012).** "Flow Toxicity and Liquidity in a High-Frequency World." *Review of Financial Studies.* — §3.7 VPIN
6. **Pincus, S.M. (1991).** "Approximate Entropy as a Measure of System Complexity." *PNAS.* — §4.2 Approximate Entropy
7. **Richman, J.S. & Moorman, J.R. (2000).** "Physiological Time-Series Analysis using Approximate Entropy and Sample Entropy." *American Journal of Physiology.* — §4.3 Sample Entropy
8. **Hurst, H.E. (1951).** "Long-Term Storage Capacity of Reservoirs." *Transactions of the American Society of Civil Engineers.* — §4.4 Hurst Exponent
9. **Higuchi, T. (1988).** "Approach to an Irregular Time Series on the Basis of the Fractal Theory." *Physica D.* — §4.5 Fractal Dimension
10. **Bandt, C. & Pompe, B. (2002).** "Permutation Entropy: A Natural Complexity Measure for Time Series." *Physical Review Letters.* — §4.6 Permutation Entropy
11. **Barndorff-Nielsen, O.E. & Sheppard, N. (2004).** "Power and Bipower Variation with Stochastic Volatility and Jumps." *Journal of Financial Econometrics.* — §5.2 Realized Volatility Decomposition
12. **López de Prado, M. (2018).** *Advances in Financial Machine Learning.* Wiley. — §4 Entropy metrics, §6.3 ADF stationarity, §6.6 Fractional Differencing (Chapter 5)
13. **AQR Capital Management** — Transaction cost modeling, factor capacity estimation（間接影響 §5/§6 設計）
14. **Kakushadze, Z. (2016).** "101 Formulaic Alphas." *Wilmott Magazine.* — §6.1 Cross-Sectional Rank Transform 的 WorldQuant 參考

### 附錄 B: 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| V0.1 | 2026-02-16 | 初版：4 面向完整規格（微觀結構 6 指標、資訊理論 5 指標、尾部風險 5 指標、前處理 5 轉換）、架構整合設計、Config 擴展、測試計畫 |
| V1.0 | 2026-02-17 | 新增 VPIN/Permutation Entropy/Rolling MDD/Fractional Differencing 4 指標；Codebase 對齊（Engine 建構子、get_feature_metadata）；新增 §9-§16（下游影響/錯誤處理/快取/Logging/效能/MCP）；邊界條件 45→51 項；測試 91→134 項（122 單元 + 7 整合 + 5 效能）；附錄文獻 12→14 篇 |

---

> **狀態**: 🔒 V1.1 Frozen — 20/20 審計通過
