# 量化交易策略系統架構文檔

## 文檔版本
- **版本**: 1.0
- **最後更新**: 2025-09-30
- **狀態**: 生產中 + 持續開發

---

## 目錄
1. [系統概覽](#系統概覽)
2. [技術棧](#技術棧)
3. [整體架構](#整體架構)
4. [已實現功能](#已實現功能)
5. [待開發功能](#待開發功能)
6. [數據流設計](#數據流設計)
7. [模組詳細設計](#模組詳細設計)
8. [性能考慮](#性能考慮)
9. [安全性設計](#安全性設計)
10. [擴展性設計](#擴展性設計)

---

## 系統概覽

### 系統定位
**量化研究工作平台（Quantitative Research Platform）**

與傳統量化交易系統的差異：
```
傳統量化: 已知策略 → 優化參數 → 回測 → 實盤
本系統:   探索案例 → 發現Pattern → 驗證策略 → ML優化 → 回測 → (未來)實盤
```

### 核心價值
- **案例發現引擎**: 從歷史數據中找出符合特定模式的交易案例
- **Pattern識別系統**: 自動發現起漲前的共通技術指標特徵
- **ML優化平台**: 使用機器學習優化交易策略參數
- **研究工作流**: 支持完整的量化研究流程

### 系統目標
1. 降低策略發現門檻（無需編程知識）
2. 自動化Pattern識別過程
3. 提供完整的研究到實盤工作流
4. 支持多市場擴展（加密貨幣 → 台股 → 美股）

---

## 技術棧

### 前端技術
```yaml
框架: Next.js 14 (App Router)
語言: TypeScript 5.x
樣式: Tailwind CSS 3.x
狀態管理: Zustand
圖表庫:
  - Lightweight Charts (TradingView開源) - K線圖表
  - Recharts - Dashboard統計圖表
組件庫: shadcn/ui (可選)
HTTP客戶端: Fetch API
```

### 後端技術
```yaml
框架: FastAPI 0.100+
語言: Python 3.11
數據處理:
  - pandas 2.0+ (數據分析)
  - numpy 1.24+ (數值計算)
  - polars (可選，大數據場景)
技術指標:
  - pandas-ta (技術指標庫)
  - ta-lib (經典指標)
API交互:
  - python-binance (幣安API)
  - ccxt (多交易所支持)
機器學習:
  - XGBoost/LightGBM (分類模型)
  - PyTorch (深度學習)
  - Optuna (參數優化)
```

### 數據存儲
```yaml
時序數據: HDF5 (大量K線數據)
結構化數據: CSV (搜索結果、案例數據)
緩存: 內存緩存 (搜索結果臨時存儲)
未來擴展:
  - PostgreSQL (正式數據)
  - Redis (實時緩存)
```

### 開發環境
```yaml
硬件: MacBook M1
Python版本: 3.11+ (M1原生支持)
Node版本: 18+
包管理:
  - Python: pip + requirements.txt
  - Node: npm
版本控制: Git + GitHub
IDE: VS Code
```

---

## 整體架構

### 系統層級架構
```
┌─────────────────────────────────────────────────────────────┐
│                    用戶界面層 (Next.js Web UI)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │案例搜索  │  │圖表分析  │  │指標測試  │  │ML訓練    │   │
│  │界面      │  │界面      │  │界面      │  │界面      │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐   │
│  │回測系統  │  │Dashboard │  │配置管理  │  │結果導出  │   │
│  │界面      │  │界面      │  │界面      │  │界面      │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
┌───────▼─────────────▼─────────────▼─────────────▼──────────┐
│                  API 服務層 (FastAPI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Case      │  │Chart     │  │Indicator │  │ML        │   │
│  │Search    │  │Data      │  │Testing   │  │Training  │   │
│  │Service   │  │Service   │  │Service   │  │Service   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐   │
│  │Backtest  │  │Pattern   │  │Config    │  │Export    │   │
│  │Service   │  │Discovery │  │Service   │  │Service   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
┌───────▼─────────────▼─────────────▼─────────────▼──────────┐
│                    核心業務層 (Python)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  現有核心模組                                         │   │
│  │  - case_search_engine.py      (案例搜索引擎)        │   │
│  │  - signal_analyzer.py          (信號分析器)         │   │
│  │  - data_loader.py              (數據加載器)         │   │
│  │  - indicator modules           (指標計算模組)       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  待開發模組                                           │   │
│  │  - chart_data_manager.py       (圖表數據管理)       │   │
│  │  - ml_training_engine.py       (ML訓練引擎)         │   │
│  │  - backtest_engine.py          (回測引擎)           │   │
│  │  - pattern_discovery.py        (Pattern發現)        │   │
│  └──────────────────────────────────────────────────────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
┌───────▼─────────────▼─────────────▼─────────────▼──────────┐
│                    數據層                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Binance   │  │OKX       │  │本地緩存  │  │HDF5      │   │
│  │API       │  │API       │  │(內存)    │  │存儲      │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  未來擴展: 台股API、美股API、鏈上數據               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 已實現功能

### ✅ 1. Case Search 系統（Web界面 + API）

#### 功能概述
完整的案例搜索系統，支持兩階段正反例搜索。

#### 前端組件
- **路徑**: `frontend/src/app/search/page.tsx`
- **功能**:
  - 20個參數化搜索條件設定
  - 正例搜索條件輸入（價格變化、成交量、Taker比例等）
  - 反例搜索條件設定（正負比例、時間分離）
  - 實時搜索進度顯示
  - 搜索結果預覽

#### 後端API
- **基礎路徑**: `api/routes/`
- **核心端點**:
  ```python
  POST /api/v1/search/execute       # 執行搜索
  GET  /api/v1/search/task/{id}     # 查詢任務狀態
  GET  /api/v1/search/templates     # 獲取搜索模板
  POST /api/v1/config               # 更新配置
  ```

#### 核心業務邏輯
- **文件**: `momentum/DataExtraction/case_search_engine.py`
- **功能**:
  - 20個參數框架（6個觸發條件 + 12個未來表現 + 2個反例參數）
  - 標的內部採樣策略
  - 時間分離驗證
  - 批量搜索優化

#### 數據模型
```python
# 搜索參數（20個）
基礎觸發條件 (6個):
  - timeframe: 時間框架
  - price_change: 觸發漲跌幅
  - closing_strength: 收盤強度
  - price_position: 價格位置
  - volume_multiplier: 成交量倍數
  - taker_buy_ratio: 主動買入比例

未來表現驗證 (12個):
  - future_1bar_return ~ future_12bar_return
  - future_1bar_max_drawdown ~ future_12bar_max_drawdown

反例專用 (2個):
  - positive_negative_ratio: 正負比例
  - time_separation_days: 時間分離天數
```

#### 已實現的搜索策略
1. **條件反轉策略**: 設定與正例相反的市場條件
2. **時間分離策略**: 相同標的不同時間的隨機採樣
3. **標的內部採樣**: 確保正反例來自相同標的池

---

### ✅ 2. 搜索結果系統

#### 功能概述
完整的結果展示、分析和導出系統。

#### 前端組件
- **路徑**: `frontend/src/app/result/page.tsx`
- **功能**:
  - 案例列表展示（可展開表格）
  - 統計圖表（市場階段、小時、星期分布）
  - CSV導出功能
  - 搜索結果篩選

#### 統計圖表
使用Recharts實現：
- 市場階段分布圓餅圖
- 小時分布圓餅圖
- 星期分布圓餅圖
- 雙軸圖表（百分比 + 絕對數量）

#### 數據導出
- **格式**: CSV
- **內容**: 包含所有20個參數計算結果
- **標註**: 正反例標記（1/0）

---

### ✅ 3. 狀態管理系統

#### Zustand Store
- **文件**: `frontend/src/store/searchStore.ts`
- **管理狀態**:
  - 搜索模板列表
  - 當前搜索結果
  - 搜索歷史
  - 加載狀態和錯誤信息

#### 狀態持久化
- 搜索結果在頁面跳轉後保持
- 避免重複搜索
- 改善用戶體驗

---

### ✅ 4. 數據加載系統

#### 核心模組
- **文件**: `momentum/DataExtraction/Momentum_Strategy_Data_Loader.py`
- **功能**:
  - Binance API集成
  - 批量數據下載
  - 數據格式標準化
  - 錯誤處理和重試

#### 數據提供者抽象
- **文件**: `momentum/DataExtraction/data_provider_base.py`
- **設計**: 抽象基類，支持未來擴展多個交易所

---

### ✅ 5. 信號分析系統

#### 核心模組
- **文件**: `momentum/signal_analyzer.py`
- **功能**:
  - 技術指標計算
  - 信號密度分析
  - Pattern識別
  - 時序關係分析

#### 指標支持
- 移動平均線（MA, EMA, DEMA, TEMA）
- 動量指標（RSI, MACD）
- 波動率指標（ATR, Bollinger Bands）
- 成交量指標

---

### ✅ 6. 配置管理系統

#### 系統配置
- **文件**: `api/core/config.py`
- **管理內容**:
  - 數據存儲路徑
  - API密鑰管理
  - 系統參數範圍
  - 環境變量

#### 市場配置
- **文件**: `momentum/DataExtraction/Market_Screener_Configuration.py`
- **功能**:
  - 市場階段定義（牛市/熊市/震盪）
  - 交易對篩選
  - 質量過濾規則

---

### ✅ 7. UI佈局系統

#### 主佈局
- **文件**: `frontend/src/components/layout/MainLayout.tsx`
- **功能**:
  - 左側導航欄
  - 響應式設計
  - 路由高亮
  - 移動端適配

#### 頁面路由
- `/` - 首頁概覽
- `/search` - 案例搜索
- `/result` - 搜索結果
- `/dashboard` - 數據儀表板（規劃中）
- `/settings` - 系統設定

---

## 待開發功能

### ⏳ 1. 圖表分析系統（優先級：🔥 最高）

#### 技術選擇
**Lightweight Charts** (TradingView開源庫)

**選擇原因**:
- ✅ 完全免費開源
- ✅ 性能極佳，流暢度接近專業版TradingView
- ✅ 支持自由捲動XY軸
- ✅ 多圖層同步
- ✅ React整合簡單

#### 圖表佈局設計
```
多層同步圖表：
┌─────────────────────────────────────────────────────┐
│ Price K線圖 (OHLC)                                  │
│ - 標準K線顯示                                       │
│ - 策略信號箭頭標記（買入↑ 賣出↓）                  │
│ - 案例時間點高亮背景                                │
│ - 支持縮放和拖曳                                    │
├─────────────────────────────────────────────────────┤
│ Volume 柱狀圖                                       │
│ - 成交量柱狀圖                                      │
│ - 對應策略信號箭頭                                  │
│ - 異常成交量標記                                    │
├─────────────────────────────────────────────────────┤
│ Taker_Ratio 線圖                                    │
│ - 主動買入比例線圖                                  │
│ - 對應策略信號箭頭                                  │
│ - 關鍵水平線（如50%）                               │
├─────────────────────────────────────────────────────┤
│ 技術指標圖層 (可選多個)                             │
│ - RSI, MACD, EMA等                                  │
│ - 指標信號標記                                      │
│ - 可動態添加/移除                                   │
└─────────────────────────────────────────────────────┘

特性：
✅ 所有圖表共用時間軸
✅ 捲動一個全部跟著動
✅ 同步縮放功能
✅ 案例時間點特殊高亮
```

#### 信號標記系統
**需求**:
- 一個指標策略會產生多組參數結果
- 每個數據源（Price, Volume, Taker_Ratio）都會計算指標
- 用戶選擇策略後，對應箭頭顯示在所有相關圖表

**實現方案**:
```typescript
// 信號數據結構
interface SignalMarker {
  timestamp: number;           // K線時間戳
  signalType: 'buy' | 'sell';  // 信號類型
  strategy: string;            // 策略名稱（如"Price_EMA5>20"）
  dataSource: 'price' | 'volume' | 'taker_ratio';
  value: number;               // 對應數值
  confidence?: number;         // 信號置信度（可選）
}

// 箭頭顯示邏輯
- Price圖: 箭頭指向對應K線的Open/Close
- Volume圖: 箭頭指向對應柱狀圖頂部
- Taker_Ratio圖: 箭頭指向線圖對應點
```

#### 案例高亮
- **背景顏色**: 淡黃色或淡藍色半透明
- **範圍**: 案例時間點前後各數根K線
- **標註**: 顯示案例ID和類型（正例/反例）

#### 開發任務
```
階段1: 基礎圖表（1週）
  - [ ] 安裝Lightweight Charts
  - [ ] 實現Price K線圖
  - [ ] 實現Volume柱狀圖
  - [ ] 實現Taker_Ratio線圖

階段2: 同步和交互（1週）
  - [ ] 實現時間軸同步
  - [ ] 實現縮放和拖曳
  - [ ] 實現CrossHair同步

階段3: 信號標記（1週）
  - [ ] 實現箭頭標記系統
  - [ ] 策略選擇器UI
  - [ ] 動態顯示/隱藏標記

階段4: 案例高亮（3天）
  - [ ] 實現背景高亮
  - [ ] 案例資訊提示框
  - [ ] 案例導航功能
```

---

### ⏳ 2. K線數據批量獲取系統（優先級：🔥 高）

#### 功能需求
從搜索到的案例時間點，批量獲取前後K線數據用於圖表展示和ML訓練。

#### 數據範圍
```
案例時間點
     ↓
[--240根--][案例][--96根--]
     ↑              ↑
  lookback      forward

默認值:
- lookback: 240根（可調整）
- forward: 96根（可調整）

原因:
- 240根足夠計算長週期指標
- 96根足夠觀察未來表現
- 1小時週期: 240hr = 10天歷史
```

#### 工作流程
```
1. 用戶完成搜索 → 獲得案例列表
2. 用戶手動篩選案例 → 標記需要的案例
3. 用戶上傳篩選後的CSV（symbol, timestamp, label）
4. 系統批量下載K線數據
5. 數據存儲到本地（HDF5格式）
```

#### 數據結構
```python
# HDF5存儲結構
/data/klines/
  /{symbol}/
    /{case_id}/
      - timestamp: 案例時間點
      - lookback_bars: 前240根K線
      - forward_bars: 後96根K線
      - metadata: 案例元數據（正反例標記等）
      - indicators: 預計算指標（可選）
```

#### 去重和緩存
```python
# 時間重疊檢測
案例A: 2024-01-01 12:00 (需要: 2023-12-22 ~ 2024-01-05)
案例B: 2024-01-02 12:00 (需要: 2023-12-23 ~ 2024-01-06)
         ↓
檢測到重疊 → 合併下載請求 → 避免重複API調用
```

#### API限制處理
```python
# 速率限制
- Binance: 1200請求/分鐘
- 批量下載: 每次最多100個案例
- 失敗重試: 指數退避策略
- 進度追蹤: WebSocket實時更新
```

#### 開發任務
```
階段1: 核心下載邏輯（1週）
  - [ ] 實現批量下載引擎
  - [ ] CSV解析和驗證
  - [ ] 時間範圍計算
  - [ ] HDF5存儲實現

階段2: 優化和緩存（1週）
  - [ ] 時間重疊檢測
  - [ ] 去重邏輯
  - [ ] 增量下載支持
  - [ ] 錯誤處理和重試

階段3: UI和進度（3天）
  - [ ] 上傳CSV界面
  - [ ] 下載進度顯示
  - [ ] 數據預覽功能
  - [ ] 錯誤報告
```

---

### ⏳ 3. 指標測試系統（優先級：🔥 高）

#### 功能概述
對搜索到的案例，測試多種技術指標的有效性。

#### 多數據源指標系統
```python
# 數據源
data_sources = [
    'close',          # 收盤價
    'open',           # 開盤價
    'high',           # 最高價
    'low',            # 最低價
    'volume',         # 成交量
    'taker_volume',   # 主動買入量
    'taker_ratio'     # 主動買入比例
]

# 指標類型
indicators = [
    'EMA',      # 指數移動平均
    'DEMA',     # 雙重指數移動平均
    'TEMA',     # 三重指數移動平均
    'RSI',      # 相對強弱指標
    'MACD',     # 移動平均收斂發散
    'ATR',      # 平均真實波幅
    'BB',       # 布林帶
    'VWAP',     # 成交量加權平均價
]

# 生成結果示例
close_ema_5, close_ema_20, close_ema_50
volume_rsi_14, volume_rsi_21
taker_ratio_macd_fast12_slow26
```

#### 指標參數優化
使用Optuna進行參數搜索：
```python
# 優化目標
def objective(trial):
    # 參數空間
    ema_period = trial.suggest_int('ema_period', 5, 200)
    rsi_period = trial.suggest_int('rsi_period', 7, 21)
    
    # 計算指標
    signals = calculate_signals(data, ema_period, rsi_period)
    
    # 評估指標（正反例分類準確率）
    accuracy = evaluate_classification(signals, labels)
    
    return accuracy

# 執行優化
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100)
```

#### 指標評分系統
```python
# 評估指標有效性
指標評分維度:
1. 正反例分類準確率
2. 信號出現頻率
3. 信號穩定性
4. 計算複雜度

評分公式:
score = (accuracy * 0.5) + 
        (frequency_score * 0.2) + 
        (stability_score * 0.2) + 
        (efficiency_score * 0.1)
```

#### UI設計
```
指標測試界面：
┌─────────────────────────────────────────────────┐
│ 數據源選擇                                      │
│ ☑ Close  ☑ Volume  ☑ Taker_Ratio              │
├─────────────────────────────────────────────────┤
│ 指標選擇                                        │
│ ☑ EMA (參數: [5, 20, 50])                      │
│ ☑ RSI (參數: [14, 21])                         │
│ ☑ MACD (參數: 自動優化)                        │
├─────────────────────────────────────────────────┤
│ 優化設定                                        │
│ 優化方法: ⚫ Optuna  ○ Grid Search             │
│ 試驗次數: [100]                                 │
├─────────────────────────────────────────────────┤
│ 執行進度                                        │
│ ████████░░░░░░░░ 50% (50/100 trials)           │
├─────────────────────────────────────────────────┤
│ 結果排名                                        │
│ 1. close_ema_20 (準確率: 78%)                  │
│ 2. volume_rsi_14 (準確率: 75%)                 │
│ 3. taker_ratio_macd (準確率: 72%)              │
└─────────────────────────────────────────────────┘
```

#### 開發任務
```
階段1: 指標計算引擎（1週）
  - [ ] 多數據源支持
  - [ ] 指標庫整合
  - [ ] 批量計算優化

階段2: Optuna整合（1週）
  - [ ] 參數空間定義
  - [ ] 目標函數實現
  - [ ] 並行優化支持

階段3: UI開發（1週）
  - [ ] 指標選擇器
  - [ ] 參數設定界面
  - [ ] 結果排名展示
  - [ ] 進度追蹤
```

---

### ⏳ 4. ML訓練系統（優先級：🔥 中高）

#### 訓練目標
**分類模型**：預測起漲前案例是否會在未來上漲

#### ML階梯策略
```
階段1: XGBoost/LightGBM（優先）
  - 適合小數據集（幾千樣本）
  - 訓練快速（分鐘級）
  - 可解釋性強
  - 作為基線模型

階段2: LSTM（可選）
  - 需要時序記憶
  - 適合中等數據集（1萬+）
  - 捕捉短期依賴

階段3: Transformer（未來）
  - 需要大數據集（10萬+）
  - 捕捉長期依賴
  - 計算資源需求高
```

#### 特徵工程
```python
# 特徵類型
features = {
    '價格特徵': [
        'close', 'open', 'high', 'low',
        'price_change', 'price_volatility'
    ],
    '成交量特徵': [
        'volume', 'volume_ma', 'volume_std',
        'volume_spike'
    ],
    '籌碼特徵': [
        'taker_volume', 'taker_ratio',
        'taker_ratio_ma', 'taker_ratio_change'
    ],
    '技術指標特徵': [
        'ema_5', 'ema_20', 'ema_50',
        'rsi_14', 'macd', 'atr',
        'bb_upper', 'bb_lower'
    ],
    '時序特徵': [
        'hour_of_day', 'day_of_week',
        'market_phase'
    ]
}

# 特徵總數：20-30個
```

#### 訓練流程
```python
# 1. 數據準備
X_train, X_test, y_train, y_test = prepare_data(
    positive_cases,  # 正例（會漲）
    negative_cases   # 反例（不會漲）
)

# 2. 特徵工程
features = calculate_all_features(X_train)

# 3. 模型訓練
model = XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1
)
model.fit(features, y_train)

# 4. 模型評估
accuracy = model.score(X_test, y_test)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)

# 5. 特徵重要性分析
feature_importance = model.feature_importances_
```

#### 輸出結果
```python
# 預測結果
{
    'prediction': 1,              # 0=不會漲, 1=會漲
    'probability': 0.78,          # 上漲概率 78%
    'confidence': 'high',         # 信心水平
    'expected_return': 0.085,     # 預期收益 8.5%（統計估算）
    'risk_reward_ratio': 2.5,     # 風險報酬比（統計估算）
    'top_features': [             # 關鍵特徵
        ('close_ema_20', 0.15),
        ('volume_spike', 0.12),
        ('taker_ratio', 0.10)
    ]
}
```

#### 風險報酬比計算
```python
# 從歷史統計計算
def calculate_risk_reward(model, historical_data):
    # 找出模型預測為"會漲"的歷史案例
    predicted_up = historical_data[model.predict(X) == 1]
    
    # 計算實際漲跌幅
    actual_returns = predicted_up['future_return']
    
    # 分離盈虧
    profits = actual_returns[actual_returns > 0]
    losses = actual_returns[actual_returns < 0]
    
    # 計算平均
    avg_profit = profits.mean()
    avg_loss = abs(losses.mean())
    
    # 風險報酬比
    risk_reward_ratio = avg_profit / avg_loss
    
    return risk_reward_ratio
```

#### UI設計
```
ML訓練界面：
┌─────────────────────────────────────────────────┐
│ 數據準備                                        │
│ 正例案例: [1000] 個                             │
│ 反例案例: [3000] 個                             │
│ 特徵數量: [28] 個                               │
├─────────────────────────────────────────────────┤
│ 模型選擇                                        │
│ ⚫ XGBoost  ○ LightGBM  ○ LSTM  ○ Transformer  │
├─────────────────────────────────────────────────┤
│ 訓練進度                                        │
│ ████████████████████ 100% Complete             │
├─────────────────────────────────────────────────┤
│ 模型評估                                        │
│ 準確率: 78.5%                                   │
│ 精確率: 76.2%                                   │
│ 召回率: 81.3%                                   │
│ 風險報酬比: 2.5:1                               │
├─────────────────────────────────────────────────┤
│ 特徵重要性                                      │
│ 1. close_ema_20      ████████░░ 15%            │
│ 2. volume_spike      ██████░░░░ 12%            │
│ 3. taker_ratio       █████░░░░░ 10%            │
└─────────────────────────────────────────────────┘
```

#### 開發任務
```
階段1: XGBoost基線（2週）
  - [ ] 特徵工程實現
  - [ ] XGBoost訓練流程
  - [ ] 模型評估指標
  - [ ] 風險報酬比計算

階段2: Optuna優化（1週）
  - [ ] 超參數空間定義
  - [ ] 自動調參
  - [ ] 交叉驗證

階段3: UI開發（1週）
  - [ ] 訓練配置界面
  - [ ] 進度顯示
  - [ ] 結果可視化
  - [ ] 模型保存/載入
```

---

### ⏳ 5. Pattern發現系統（優先級：🔥 中）

#### 功能概述
自動從高分指標組合中發現交易Pattern。

#### Pattern定義
```python
# Pattern示例
Pattern = {
    'name': 'EMA金叉 + 成交量放大',
    'conditions': [
        'close_ema_5 > close_ema_20',
        'volume > volume_ma_20 * 1.5',
        'taker_ratio > 0.6'
    ],
    'effectiveness': {
        'accuracy': 0.75,
        'sample_size': 150,
        'avg_return': 0.08,
        'win_rate': 0.68
    }
}
```

#### 發現流程
```python
# 1. 指標過濾
high_score_indicators = filter_by_score(all_indicators, min_score=0.7)

# 2. 組合測試
for combo in generate_combinations(high_score_indicators, max_size=3):
    pattern = test_pattern(combo, historical_cases)
    if pattern.accuracy > threshold:
        patterns.append(pattern)

# 3. Pattern排序
patterns.sort(key=lambda x: x.effectiveness['accuracy'], reverse=True)

# 4. Pattern驗證
validated_patterns = cross_validate(patterns, validation_set)
```

#### 開發任務
```
階段1: Pattern發現引擎（2週）
  - [ ] 組合生成邏輯
  - [ ] Pattern測試框架
  - [ ] 有效性評估

階段2: UI開發（1週）
  - [ ] Pattern列表展示
  - [ ] Pattern詳情頁
  - [ ] Pattern比較功能
```

---

### ⏳ 6. 回測系統（優先級：🔥 中）

#### 功能概述
基於發現的Pattern或ML模型，進行歷史回測驗證。

#### 回測引擎
```python
# 回測流程
class BacktestEngine:
    def __init__(self, strategy, initial_capital):
        self.strategy = strategy
        self.capital = initial_capital
        self.positions = []
        self.trades = []
    
    def run(self, historical_data):
        for bar in historical_data:
            # 生成信號
            signal = self.strategy.generate_signal(bar)
            
            # 執行交易
            if signal == 'buy' and not self.has_position():
                self.open_position(bar)
            elif signal == 'sell' and self.has_position():
                self.close_position(bar)
            
            # 記錄
            self.update_metrics(bar)
        
        # 計算績效
        return self.calculate_performance()
```

#### 績效指標
```python
performance_metrics = {
    '報酬指標': {
        'total_return': 0.25,        # 總報酬率 25%
        'annual_return': 0.15,       # 年化報酬率 15%
        'excess_return': 0.10        # 超額報酬 10%
    },
    '風險指標': {
        'sharpe_ratio': 1.8,         # 夏普比率
        'sortino_ratio': 2.2,        # 索提諾比率
        'max_drawdown': -0.15,       # 最大回撤 -15%
        'calmar_ratio': 1.0          # 卡瑪比率
    },
    '交易指標': {
        'win_rate': 0.68,            # 勝率 68%
        'profit_factor': 2.5,        # 賺賠比 2.5
        'avg_holding_period': 48,    # 平均持倉48小時
        'total_trades': 150          # 總交易次數
    },
    '穩定性指標': {
        'volatility': 0.12,          # 報酬標準差 12%
        'max_consecutive_losses': 5, # 最長連敗
        'var_95': -0.08              # 95% VaR
    }
}
```

#### UI設計
```
回測界面：
┌─────────────────────────────────────────────────┐
│ 策略選擇                                        │
│ ⚫ Pattern: EMA金叉+成交量放大                  │
│ ○ ML模型: XGBoost_v1                            │
├─────────────────────────────────────────────────┤
│ 回測設定                                        │
│ 起始資金: [10000] USDT                          │
│ 時間範圍: 2023-01-01 ~ 2024-12-31              │
│ 手續費率: [0.1]%                                │
├─────────────────────────────────────────────────┤
│ 權益曲線圖                                      │
│ (Lightweight Charts顯示)                       │
├─────────────────────────────────────────────────┤
│ 績效指標卡片                                    │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│ │總報酬│ │夏普比│ │勝率  │ │最大  │          │
│ │ 25% │ │ 1.8 │ │ 68% │ │回撤  │          │
│ └──────┘ └──────┘ └──────┘ │-15% │          │
│                             └──────┘          │
├─────────────────────────────────────────────────┤
│ 交易明細表格                                    │
│ 時間       │ 類型 │ 價格  │ 盈虧   │ 累計報酬│
│ 2023-01-05│ 買入 │ 16500│        │         │
│ 2023-01-07│ 賣出 │ 17200│ +4.2% │ +4.2%   │
└─────────────────────────────────────────────────┘
```

#### 開發任務
```
階段1: 回測引擎（2週）
  - [ ] 核心回測邏輯
  - [ ] 交易執行模擬
  - [ ] 績效指標計算

階段2: 可視化（1週）
  - [ ] 權益曲線圖
  - [ ] 回撤圖
  - [ ] 績效儀表板

階段3: 報告生成（1週）
  - [ ] PDF報告導出
  - [ ] 詳細交易記錄
  - [ ] 策略對比分析
```

---

## 數據流設計

### 完整數據流向
```
使用者操作流程：

1️⃣ 案例搜索階段
   用戶輸入搜索條件
        ↓
   Case Search Engine搜索歷史數據
        ↓
   標記符合條件的時間點（symbol + timestamp）
        ↓
   生成案例列表（正例/反例）
        ↓
   存儲到CSV

2️⃣ 數據準備階段
   用戶手動篩選案例
        ↓
   上傳篩選後的CSV
        ↓
   系統批量下載K線數據（240前/96後）
        ↓
   存儲到HDF5（本地）

3️⃣ 指標測試階段
   用戶選擇指標和數據源
        ↓
   系統計算指標（多數據源 × 多參數）
        ↓
   Optuna優化參數
        ↓
   評估指標有效性
        ↓
   生成指標評分排名

4️⃣ 圖表分析階段
   用戶選擇案例查看
        ↓
   從HDF5讀取K線數據
        ↓
   Lightweight Charts渲染多層圖表
        ↓
   用戶選擇策略 → 顯示對應箭頭標記
        ↓
   用戶分析Pattern

5️⃣ Pattern發現階段
   系統自動組合高分指標
        ↓
   測試組合有效性
        ↓
   生成Pattern列表
        ↓
   用戶驗證Pattern

6️⃣ ML訓練階段
   準備特徵數據（20-30個指標）
        ↓
   訓練分類模型（XGBoost）
        ↓
   評估模型績效
        ↓
   輸出預測概率和風險報酬比

7️⃣ 回測驗證階段
   選擇Pattern或ML模型
        ↓
   回測引擎模擬交易
        ↓
   計算績效指標
        ↓
   生成回測報告

8️⃣ （未來）實盤部署
   策略部署到雲端
        ↓
   實時監控市場
        ↓
   自動執行交易
```

---

## 模組詳細設計

### 前端模組

#### 1. 圖表模組（待開發）
```typescript
// frontend/src/components/charts/TradingChart.tsx
interface TradingChartProps {
  symbol: string;
  caseId: string;
  selectedStrategy?: string;
}

// 功能：
// - 多層同步圖表（Price/Volume/Taker_Ratio/Indicators）
// - 信號箭頭標記
// - 案例時間點高亮
// - 縮放和拖曳
// - CrossHair同步
```

#### 2. 指標測試模組（待開發）
```typescript
// frontend/src/app/indicator-testing/page.tsx
// 功能：
// - 數據源選擇器
// - 指標參數配置
// - Optuna優化設定
// - 結果排名展示
// - 進度追蹤
```

#### 3. ML訓練模組（待開發）
```typescript
// frontend/src/app/ml-training/page.tsx
// 功能：
// - 數據準備界面
// - 模型選擇
// - 訓練配置
// - 評估指標顯示
// - 特徵重要性可視化
```

#### 4. 回測模組（待開發）
```typescript
// frontend/src/app/backtest/page.tsx
// 功能：
// - 策略選擇
// - 回測參數設定
// - 權益曲線圖
// - 績效指標卡片
// - 交易明細表格
```

---

### 後端模組

#### 1. 圖表數據服務（待開發）
```python
# api/services/chart_data_service.py
class ChartDataService:
    def get_kline_data(self, symbol, case_id):
        """從HDF5讀取K線數據"""
        
    def get_signal_markers(self, case_id, strategy):
        """獲取策略信號標記"""
        
    def get_case_highlight(self, case_id):
        """獲取案例高亮信息"""
```

#### 2. K線下載服務（待開發）
```python
# api/services/kline_download_service.py
class KlineDownloadService:
    def batch_download(self, cases_csv):
        """批量下載K線數據"""
        
    def check_overlap(self, cases):
        """檢測時間重疊"""
        
    def save_to_hdf5(self, data, case_id):
        """存儲到HDF5"""
```

#### 3. 指標測試服務（待開發）
```python
# api/services/indicator_testing_service.py
class IndicatorTestingService:
    def calculate_indicators(self, data, indicators, data_sources):
        """計算多數據源指標"""
        
    def optimize_parameters(self, indicator, cases):
        """使用Optuna優化參數"""
        
    def evaluate_effectiveness(self, signals, labels):
        """評估指標有效性"""
```

#### 4. ML訓練服務（待開發）
```python
# api/services/ml_training_service.py
class MLTrainingService:
    def prepare_features(self, cases):
        """準備特徵數據"""
        
    def train_model(self, X, y, model_type='xgboost'):
        """訓練分類模型"""
        
    def evaluate_model(self, model, X_test, y_test):
        """評估模型性能"""
        
    def calculate_risk_reward(self, model, historical_data):
        """計算風險報酬比"""
```

#### 5. 回測服務（待開發）
```python
# api/services/backtest_service.py
class BacktestService:
    def run_backtest(self, strategy, historical_data):
        """執行回測"""
        
    def calculate_metrics(self, trades):
        """計算績效指標"""
        
    def generate_report(self, results):
        """生成回測報告"""
```

---

## 性能考慮

### M1優化策略

#### 1. 向量化運算
```python
# 慢（循環）
for i in range(len(df)):
    df.loc[i, 'ma'] = df['close'][i-20:i].mean()

# 快（向量化）- 100倍以上
df['ma'] = df['close'].rolling(20).mean()
```

#### 2. Numba加速
```python
from numba import jit

@jit(nopython=True)
def calculate_signals(prices, ma_short, ma_long):
    signals = np.zeros(len(prices))
    for i in range(len(prices)):
        if ma_short[i] > ma_long[i]:
            signals[i] = 1
    return signals
```

#### 3. 並行處理
```python
from multiprocessing import Pool

# M1有8核心，充分利用
with Pool(8) as p:
    results = p.map(process_case, case_list)
```

#### 4. 數據緩存
```python
# 使用LRU緩存避免重複計算
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_kline_data(symbol, timeframe):
    # 從HDF5讀取數據
    pass
```

---

## 安全性設計

### API密鑰管理
```python
# 使用環境變量
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# 本地加密存儲
from cryptography.fernet import Fernet

def encrypt_api_key(key):
    cipher = Fernet(encryption_key)
    return cipher.encrypt(key.encode())
```

### 風險控制
```python
class RiskManager:
    def __init__(self):
        self.max_position_size = 0.1      # 單筆最大10%資金
        self.max_drawdown_limit = 0.15    # 最大回撤15%停止
        self.daily_loss_limit = 0.05      # 單日最大虧損5%
    
    def check_order_risk(self, order):
        """檢查訂單風險"""
        if order.size > self.max_position_size:
            raise RiskException("Position size too large")
    
    def emergency_stop(self):
        """緊急平倉機制"""
        if self.current_drawdown > self.max_drawdown_limit:
            self.close_all_positions()
```

---

## 擴展性設計

### 多市場支持

#### 數據提供者抽象
```python
from abc import ABC, abstractmethod

class DataProvider(ABC):
    @abstractmethod
    def fetch_ohlcv(self, symbol, timeframe, start, end):
        """獲取OHLCV數據"""
        pass
    
    @abstractmethod
    def fetch_market_info(self, symbol):
        """獲取市場信息"""
        pass

class BinanceProvider(DataProvider):
    """幣安實現（已完成）"""
    pass

class TWStockProvider(DataProvider):
    """台股實現（未來）"""
    pass

class USStockProvider(DataProvider):
    """美股實現（未來）"""
    pass
```

#### 統一數據格式
```python
# 標準OHLCV格式
standard_format = {
    'timestamp': datetime,
    'open': float,
    'high': float,
    'low': float,
    'close': float,
    'volume': float,
    'quote_volume': float,  # USDT成交額
    'taker_volume': float,  # 主動買入量（加密貨幣特有）
    'taker_ratio': float,   # 主動買入比例
    'metadata': dict        # 市場特定數據
}
```

### 策略類型擴展
```python
class StrategyType(Enum):
    MOMENTUM = "momentum"              # 單一商品動能（已實現）
    MEAN_REVERSION = "mean_reversion"  # 均值回歸（未來）
    ARBITRAGE = "arbitrage"            # 跨市場套利（未來）
    GRID_TRADING = "grid_trading"      # 網格交易（未來）
```

---

## 開發優先級總覽

### 階段1：圖表和數據系統（4-6週）
```
優先級：🔥 最高
目標：完成K線圖表展示和數據批量獲取

任務：
1. Lightweight Charts圖表系統（3週）
   - 多層同步圖表
   - 信號箭頭標記
   - 案例高亮

2. K線數據批量下載（2週）
   - CSV上傳和解析
   - 批量下載引擎
   - HDF5存儲

3. 圖表數據API（1週）
   - 數據讀取接口
   - 信號標記API
```

### 階段2：指標測試系統（4-5週）
```
優先級：🔥 高
目標：完成多數據源指標測試和參數優化

任務：
1. 指標計算引擎（2週）
   - 多數據源支持
   - 指標庫整合

2. Optuna參數優化（2週）
   - 參數空間定義
   - 並行優化

3. UI開發（1週）
   - 指標選擇器
   - 結果展示
```

### 階段3：ML訓練系統（4-6週）
```
優先級：🔥 中高
目標：完成分類模型訓練和評估

任務：
1. XGBoost基線模型（2週）
   - 特徵工程
   - 訓練流程

2. Optuna超參數調優（1週）
   - 自動調參
   - 交叉驗證

3. UI和可視化（1週）
   - 訓練界面
   - 結果展示

4. （可選）LSTM模型（2週）
   - PyTorch實現
   - 時序特徵學習
```

### 階段4：Pattern發現（2-3週）
```
優先級：🔥 中
目標：自動發現有效Pattern

任務：
1. Pattern發現引擎（2週）
   - 組合生成
   - 有效性評估

2. UI開發（1週）
   - Pattern展示
   - Pattern比較
```

### 階段5：回測系統（3-4週）
```
優先級：🔥 中
目標：完成策略回測驗證

任務：
1. 回測引擎（2週）
   - 核心邏輯
   - 績效計算

2. 可視化（1週）
   - 權益曲線
   - 績效儀表板

3. 報告生成（1週）
   - PDF導出
   - 策略對比
```

---

## 技術債務和已知限制

### 已知限制
1. **數據量限制**: 受限於M1內存（16GB/32GB），單次處理案例數量有上限
2. **API限制**: Binance API有速率限制，批量下載需要速率控制
3. **圖表性能**: Lightweight Charts在超過10000根K線時可能卡頓
4. **ML數據量**: 深度學習需要大量數據，初期可能樣本不足

### 優化計劃
1. **分批處理**: 大數據集分批加載和處理
2. **懶加載**: 圖表數據按需加載，不一次性加載全部
3. **數據壓縮**: HDF5使用壓縮減少存儲空間
4. **增量訓練**: ML模型支持增量學習

---

## 文檔維護

### 更新頻率
- **重大功能完成後**：更新對應模組描述
- **架構變更時**：更新整體架構圖
- **每月一次**：檢查並更新開發優先級

### 相關文檔
- `FEATURE_ROADMAP.md` - 詳細開發計劃
- `API_SPECIFICATION.md` - API接口文檔
- `DEVELOPMENT_GUIDE.md` - 開發規範
- `PROJECT_STATUS.md` - 項目狀態

---

## 總結

本系統是一個**完整的量化研究工作平台**，不僅僅是交易系統：

**已實現核心價值**：
- ✅ 案例發現引擎（20參數框架）
- ✅ 正反例採樣系統
- ✅ Web化操作界面
- ✅ 數據導出和分析

**未來完整能力**：
- 🎯 專業圖表分析（TradingView風格）
- 🎯 自動化指標測試
- 🎯 機器學習優化
- 🎯 Pattern自動發現
- 🎯 完整回測驗證
- 🎯 （遠期）實盤部署

**技術亮點**：
- M1原生優化
- 模組化設計
- 易於擴展多市場
- 完整的研究工作流

---

*文檔版本：1.0*  
*最後更新：2025-09-30*  
*維護者：開發團隊*