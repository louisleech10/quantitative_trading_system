# 跨標的訓練特徵工程指南

**日期**: 2026-01-23  
**作者**: AI Agent  
**版本**: 1.0

---

## 📋 概述

本文件說明量化交易系統如何支援**跨標的（Cross-Symbol）訓練**，這是業界主流做法，用於：
- 增加樣本數量（上百或上千個標的 × 每標的幾十個案例 = 數千樣本）
- 提升模型泛化能力（學習市場共性模式，而非單一標的特性）
- 提高統計顯著性（避免單標的樣本過少導致的過擬合）

---

## ⚠️ 關鍵問題：絕對值特徵的跨標的雜訊

### 問題示例

假設 XGBoost 訓練同時包含 BTCUSDT 和 SOLUSDT 案例：

| 標的 | Close | EMA(5) | Volume | 
|------|-------|--------|--------|
| BTCUSDT | 98000 | 97500 | 7315 |
| SOLUSDT | 127 | 124 | 921029 |

如果使用**絕對值特徵**（如 `close_ema_5 = 97500`），XGBoost 會錯誤學習：
- ❌ "EMA > 90000 → 看漲" （只對 BTC 有效）
- ❌ "Volume > 100000 → 成交量大" （SOL 正常，BTC 異常大）

**結果**：模型完全無法泛化，預測準確度接近隨機。

---

## ✅ 解決方案：標準化特徵工程

### 核心原則

> **所有特徵必須是無量綱的相對值，可在任意價格範圍內使用**

### 特徵分類

#### 1. ✅ **相對百分比特徵**（可跨標的）

| 特徵 | 公式 | 跨標的兼容性 |
|------|------|-------------|
| `price_change_pct` | `(close - open) / open` | ✅ 漲跌幅，量級統一 |
| `ema_distance_short_mid` | `(EMA_short - EMA_mid) / EMA_mid` | ✅ 相對距離 |
| `price_ema_short_distance` | `(price - EMA_short) / EMA_short` | ✅ 價格偏離度 |
| `volume_ma_ratio_5` | `volume / MA(volume, 5)` | ✅ 相對成交量 |
| `ema_short_slope` | `(EMA_t - EMA_t-3) / EMA_t-3` | ✅ 趨勢強度 |

#### 2. ✅ **0-1 標記特徵**（可跨標的）

| 特徵 | 公式 | 跨標的兼容性 |
|------|------|-------------|
| `ema_trend_aligned` | `short > mid > long` | ✅ 布林值 |
| `ema_cross_signal` | 穿越瞬間 = 1 | ✅ 事件標記 |
| `taker_buy_ratio` | 主動買入比例 | ✅ 已標準化 0-1 |
| `close_position_in_range` | `(close - low) / (high - low)` | ✅ 標準化位置 |

#### 3. ❌ **絕對值特徵**（不可跨標的）

| 特徵 | 問題 | 修正方法 |
|------|------|---------|
| `close_ema_5` | BTC 97500 vs SOL 124 | ❌ 移除，改用相對距離 |
| `price_momentum_3` | `close - close.shift(3)` | ✅ 改為 `(close - close.shift(3)) / close.shift(3)` |
| `volume` | 絕對成交量 | ✅ 改為 `volume / MA(volume)` |

---

## 🔧 系統修改摘要

### 修改檔案

#### 1. **`momentum/FeatureEngineering/feature_extractor.py`**

**修改前**：
```python
# ❌ 絕對值特徵
df['close_ema_5'] = df['close'].ewm(span=5).mean()
feature_names.append('close_ema_5')

df['price_momentum_3'] = df['close'] - df['close'].shift(3)
feature_names.append('price_momentum_3')
```

**修改後**：
```python
# ✅ EMA 僅用於計算相對特徵
ema_5 = df['close'].ewm(span=5).mean()
# 不加入 feature_names

# ✅ 價格與 EMA 的相對距離
df['close_price_ema_short_distance'] = (df['close'] - ema_5) / (ema_5 + 1e-10)
feature_names.append('close_price_ema_short_distance')

# ✅ 動量百分比
df['price_momentum_3_pct'] = (df['close'] - df['close'].shift(3)) / (df['close'].shift(3) + 1e-10)
feature_names.append('price_momentum_3_pct')
```

#### 2. **`momentum/FeatureEngineering/indicators/ema_extractor.py`**

**新增特徵**：
- `{data_source}_price_ema_short_distance`：價格與短期 EMA 距離
- `{data_source}_price_ema_mid_distance`：價格與中期 EMA 距離
- `{data_source}_price_ema_long_distance`：價格與長期 EMA 距離
- `{data_source}_ema_short_slope`：短期 EMA 斜率
- `{data_source}_ema_mid_slope`：中期 EMA 斜率

**移除特徵**：
- ~~`close_ema_5`~~（絕對值）
- ~~`close_ema_20`~~（絕對值）
- ~~`close_ema_60`~~（絕對值）

---

## 📊 特徵數量變化

### EMA 策略特徵（以 `close` 數據源為例）

| 類別 | 修改前 | 修改後 | 變化 |
|------|--------|--------|------|
| EMA 絕對值 | 3 | 0 | -3 |
| 價格與 EMA 距離 | 0 | 3 | +3 |
| EMA 之間距離 | 2 | 2 | 0 |
| EMA 斜率 | 0 | 2 | +2 |
| 趨勢標記 | 2 | 2 | 0 |
| 成交量特徵 | 2 | 2 | 0 |
| **總計** | **9** | **11** | **+2** |

### 基礎特徵

| 類別 | 修改前 | 修改後 | 變化 |
|------|--------|--------|------|
| 價格特徵 | 8 | 8 | 0（改用 `price_momentum_3_pct`） |
| 成交量特徵 | 6 | 6 | 0 |
| **總計** | **14** | **14** | **0** |

---

## 🎯 業界最佳實踐

### 多標的訓練策略

#### 1. **分層抽樣**
```python
# 確保每個標的的正負例比例一致
from sklearn.model_selection import StratifiedGroupKFold

cv = StratifiedGroupKFold(n_splits=5)
for train_idx, test_idx in cv.split(X, y, groups=symbols):
    # groups 確保同一標的不會同時出現在訓練和測試集
    ...
```

#### 2. **標的權重**
```python
# 根據標的流動性或市值加權
sample_weight = df['symbol'].map(symbol_weights)
xgb.train(..., sample_weight=sample_weight)
```

#### 3. **特徵標準化**
```python
# 雖然特徵已是相對值，但可進一步標準化
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```

---

## 🔍 驗證方法

### 1. **特徵分布檢查**

```python
import matplotlib.pyplot as plt

# 檢查不同標的的特徵分布是否一致
for symbol in symbols:
    data = features[features['symbol'] == symbol]
    plt.hist(data['close_price_ema_short_distance'], alpha=0.5, label=symbol)

plt.legend()
plt.title('Price-EMA Distance Distribution Across Symbols')
plt.show()

# ✅ 應該看到：所有標的的分布形狀相似（中心化在 0 附近）
# ❌ 如果看到：不同標的分布完全分離 → 特徵仍有問題
```

### 2. **跨標的預測測試**

```python
# 訓練在 BTC + ETH + BNB
train_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
X_train = features[features['symbol'].isin(train_symbols)]

# 測試在 SOL（未見過的標的）
X_test = features[features['symbol'] == 'SOLUSDT']

model.fit(X_train, y_train)
score = model.score(X_test, y_test)

# ✅ 如果 score > 0.55：特徵可泛化
# ❌ 如果 score ≈ 0.5：特徵無法跨標的
```

---

## 📝 開發檢查清單

在實作新特徵時，檢查以下項目：

- [ ] 特徵是否包含絕對價格？（❌ 不可用）
- [ ] 特徵是否包含絕對成交量？（❌ 不可用）
- [ ] 特徵是否為相對百分比？（✅ 可用）
- [ ] 特徵是否為 0-1 標記？（✅ 可用）
- [ ] 特徵是否為標準化分數？（✅ 可用）
- [ ] 特徵在不同標的上的分布是否相似？（驗證必要）
- [ ] 特徵命名是否清晰表明單位？（如 `_pct`, `_ratio`）

---

## 🚀 未來擴展

### 1. **標的特徵（Meta Features）**

如需區分標的特性，可新增：
```python
# ✅ 可選的標的元特徵
df['symbol_volatility_rank'] = df.groupby('symbol')['price_change_pct'].transform('std').rank(pct=True)
df['symbol_volume_rank'] = df.groupby('symbol')['volume'].transform('mean').rank(pct=True)
```

### 2. **動態數據源**

當前支援 `close`, `open`, `high`, `low` 等，未來可擴展：
- `oi`（未平倉量，期貨專用）
- `funding_rate`（資金費率）
- `basis`（現貨-期貨價差）

---

## 📚 參考資料

- WorldQuant Alpha 101: Cross-sectional factor design
- Numerai Tournament: Stock prediction across global markets
- Andreas Clenow - Following the Trend (CTA 策略跨標的應用)

---

**最後更新**: 2026-01-23  
**相關文件**: 
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md)
- [FEATURE_ROADMAP.md](./FEATURE_ROADMAP.md)
