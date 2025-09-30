# 功能開發路線圖

## 文檔信息
- **版本**: 1.0
- **最後更新**: 2025-01-15
- **規劃週期**: 6個月（24週）
- **開發模式**: AI驅動開發（Claude Code CLI）

---

## 目錄
1. [總覽](#總覽)
2. [階段1：圖表和數據系統](#階段1圖表和數據系統)
3. [階段2：指標測試系統](#階段2指標測試系統)
4. [階段3：ML訓練系統](#階段3ml訓練系統)
5. [階段4：Pattern發現系統](#階段4pattern發現系統)
6. [階段5：回測系統](#階段5回測系統)
7. [階段6：系統優化和完善](#階段6系統優化和完善)
8. [未來擴展](#未來擴展)
9. [里程碑檢查點](#里程碑檢查點)
10. [風險管理](#風險管理)

---

## 總覽

### 開發時間軸
```
月份:    M1-M2      M3-M4      M5-M6      M7+
階段:   階段1      階段2      階段3    階段4+5+6
      圖表數據  指標測試   ML訓練   Pattern+回測+優化

目標:   可視化    發現信號   模型訓練   完整研究流程
```

### 優先級定義
- 🔥🔥🔥 **P0 - 最高**: 核心功能，無此功能系統不完整
- 🔥🔥 **P1 - 高**: 重要功能，顯著提升用戶體驗
- 🔥 **P2 - 中**: 增強功能，錦上添花
- 💡 **P3 - 低**: 優化功能，可延後開發

### 當前系統狀態
```
✅ 已完成：
  - Case Search系統（Web + API）
  - 搜索結果展示和導出
  - 基礎數據管理
  - 狀態管理（Zustand）

⏳ 進行中：
  - 無（等待開始階段1）

❌ 未開始：
  - 圖表系統
  - K線數據批量下載
  - 指標測試
  - ML訓練
  - Pattern發現
  - 回測系統
```

---

## 階段1：圖表和數據系統

### 階段目標
**讓用戶能夠可視化分析搜索到的案例，查看K線圖和技術指標**

### 時間規劃
- **總時長**: 4-6週
- **優先級**: 🔥🔥🔥 P0（最高）
- **依賴**: 無（可立即開始）

### 功能概述
```
輸入: 搜索到的案例列表
     ↓
處理: 批量下載K線數據 → 存儲到HDF5
     ↓
輸出: 多層同步圖表 + 信號箭頭標記
```

---

### 任務1.1：Lightweight Charts基礎圖表 (Week 1-2)

#### 前端任務
```yaml
任務列表:
  - [ ] 安裝和配置Lightweight Charts
  - [ ] 創建TradingChart組件結構
  - [ ] 實現Price K線圖（OHLC）
  - [ ] 實現Volume柱狀圖
  - [ ] 實現Taker_Ratio線圖
  - [ ] 基礎樣式設計

技術要點:
  - 使用lightweight-charts React wrapper
  - 組件Props設計：symbol, caseId, dateRange
  - 響應式佈局（移動端適配）

文件位置:
  - frontend/src/components/charts/TradingChart.tsx
  - frontend/src/components/charts/PriceChart.tsx
  - frontend/src/components/charts/VolumeChart.tsx
  - frontend/src/components/charts/TakerRatioChart.tsx

測試標準:
  ✅ K線圖正確顯示
  ✅ 可以縮放和拖曳
  ✅ 圖表流暢（60fps）
  ✅ 移動端正常顯示
```

#### 後端任務
```yaml
任務列表:
  - [ ] 設計圖表數據API端點
  - [ ] 實現數據格式轉換（HDF5 → JSON）
  - [ ] 添加數據壓縮和優化

API端點設計:
  GET /api/v1/chart/kline/{symbol}/{case_id}
    Response: {
      timestamp: number[],
      open: number[],
      high: number[],
      low: number[],
      close: number[],
      volume: number[],
      taker_ratio: number[]
    }

文件位置:
  - api/routes/chart.py
  - api/services/chart_data_service.py

測試標準:
  ✅ API返回正確格式數據
  ✅ 響應時間 < 500ms
  ✅ 支持分頁加載（可選）
```

---

### 任務1.2：圖表同步和交互 (Week 2-3)

#### 前端任務
```yaml
任務列表:
  - [ ] 實現時間軸同步
  - [ ] 實現CrossHair同步
  - [ ] 實現統一縮放控制
  - [ ] 實現統一拖曳控制
  - [ ] 添加時間範圍選擇器

技術要點:
  - 使用React Context共享時間狀態
  - 監聽所有圖表的時間變化事件
  - 統一的時間軸管理器

代碼示例:
  // TimeAxisContext.tsx
  const TimeAxisContext = createContext({
    visibleRange: { from: 0, to: 0 },
    setVisibleRange: (range) => {}
  });

測試標準:
  ✅ 滾動一個圖表，所有圖表同步
  ✅ CrossHair在所有圖表對齊
  ✅ 縮放比例一致
  ✅ 無明顯延遲（< 100ms）
```

---

### 任務1.3：信號箭頭標記系統 (Week 3-4)

#### 前端任務
```yaml
任務列表:
  - [ ] 設計SignalMarker組件
  - [ ] 實現箭頭圖標渲染
  - [ ] 實現策略選擇器UI
  - [ ] 動態顯示/隱藏標記
  - [ ] 標記懸停提示框

技術要點:
  - 使用Lightweight Charts的Markers API
  - 箭頭位置計算（買入向上↑，賣出向下↓）
  - 支持多策略同時顯示

數據結構:
  interface SignalMarker {
    time: number;              // Unix timestamp
    position: 'aboveBar' | 'belowBar';
    color: string;             // 箭頭顏色
    shape: 'arrowUp' | 'arrowDown';
    text?: string;             // 懸停提示
    strategy: string;          // 策略名稱
    dataSource: 'price' | 'volume' | 'taker_ratio';
  }

測試標準:
  ✅ 箭頭正確顯示在對應K線
  ✅ 選擇策略後箭頭即時更新
  ✅ 懸停顯示策略信息
  ✅ 多策略箭頭不重疊
```

#### 後端任務
```yaml
任務列表:
  - [ ] 實現信號計算邏輯
  - [ ] 設計信號標記API
  - [ ] 緩存常用策略信號

API端點設計:
  GET /api/v1/chart/signals/{case_id}?strategy={strategy_name}
    Response: {
      price_signals: SignalMarker[],
      volume_signals: SignalMarker[],
      taker_ratio_signals: SignalMarker[]
    }

文件位置:
  - api/services/signal_marker_service.py

測試標準:
  ✅ 信號計算正確
  ✅ 響應時間 < 300ms
  ✅ 支持多種策略
```

---

### 任務1.4：案例高亮顯示 (Week 4)

#### 前端任務
```yaml
任務列表:
  - [ ] 實現背景高亮區域
  - [ ] 案例信息提示框
  - [ ] 案例導航功能（上一個/下一個案例）
  - [ ] 案例列表側邊欄

技術要點:
  - 使用Lightweight Charts的PriceLine API
  - 半透明背景區域
  - 案例時間點前後各數根K線高亮

視覺設計:
  - 正例背景：淡綠色 (#E8F5E9, opacity: 0.3)
  - 反例背景：淡紅色 (#FFEBEE, opacity: 0.3)
  - 邊界線：虛線

測試標準:
  ✅ 案例時間點明顯高亮
  ✅ 案例信息提示框顯示完整
  ✅ 導航功能流暢
```

---

### 任務1.5：K線數據批量下載系統 (Week 4-6)

#### 核心邏輯設計
```python
# 工作流程
1. 用戶上傳CSV (symbol, timestamp, label)
2. 系統解析CSV並驗證
3. 計算每個案例的時間範圍 (240前 + 96後)
4. 檢測時間重疊，合併下載請求
5. 批量下載K線數據（處理API限制）
6. 存儲到HDF5（按案例ID組織）
7. 返回下載進度和結果
```

#### 後端任務
```yaml
任務列表:
  - [ ] CSV解析和驗證
  - [ ] 時間範圍計算邏輯
  - [ ] 時間重疊檢測算法
  - [ ] 批量下載引擎（速率限制）
  - [ ] HDF5存儲實現
  - [ ] 下載進度追蹤（WebSocket）
  - [ ] 錯誤處理和重試

技術要點:
  - 使用python-binance批量API
  - 速率限制：1200請求/分鐘
  - 失敗重試：指數退避
  - 並行下載：最多8個worker

文件位置:
  - api/services/kline_download_service.py
  - api/routes/kline_download.py
  - api/utils/hdf5_manager.py

API端點設計:
  POST /api/v1/kline/batch-download
    Request: {
      csv_file: File,
      lookback_bars: 240,
      forward_bars: 96
    }
    Response: {
      task_id: string,
      total_cases: number,
      estimated_time: string
    }
  
  GET /api/v1/kline/download-progress/{task_id}
    Response: {
      status: 'pending' | 'running' | 'completed' | 'failed',
      progress: number,  // 0-100
      downloaded: number,
      total: number,
      errors: string[]
    }

HDF5存儲結構:
  /kline_data/
    /{symbol}/
      /{case_id}/
        /attrs:
          - timestamp: 案例時間點
          - label: 正例(1)/反例(0)
          - lookback_bars: 240
          - forward_bars: 96
        /klines:
          - timestamp: [...]
          - open: [...]
          - high: [...]
          - low: [...]
          - close: [...]
          - volume: [...]
          - taker_volume: [...]
          - taker_ratio: [...]

測試標準:
  ✅ CSV正確解析
  ✅ 時間重疊檢測準確
  ✅ 下載速度符合預期
  ✅ HDF5數據完整
  ✅ 錯誤處理健壯
```

#### 前端任務
```yaml
任務列表:
  - [ ] CSV上傳界面
  - [ ] 參數設定（lookback/forward可調）
  - [ ] 下載進度條
  - [ ] 實時狀態更新（WebSocket）
  - [ ] 錯誤報告展示
  - [ ] 下載完成通知

頁面位置:
  - frontend/src/app/data-preparation/page.tsx

測試標準:
  ✅ CSV上傳流暢
  ✅ 進度實時更新
  ✅ 錯誤信息清晰
  ✅ 完成後自動跳轉到圖表
```

---

### 任務1.6：圖表頁面整合 (Week 6)

#### 前端任務
```yaml
任務列表:
  - [ ] 創建圖表分析主頁面
  - [ ] 整合所有圖表組件
  - [ ] 添加案例列表側邊欄
  - [ ] 策略選擇器
  - [ ] 時間範圍控制器
  - [ ] 圖表配置保存功能

頁面結構:
  ┌────────────────────────────────────────────┐
  │ 案例列表 │        圖表區域                │
  │ 側邊欄   │  ┌──────────────────────┐      │
  │          │  │ Price K線圖          │      │
  │ [案例1]  │  ├──────────────────────┤      │
  │ [案例2]  │  │ Volume柱狀圖         │      │
  │ [案例3]  │  ├──────────────────────┤      │
  │          │  │ Taker_Ratio線圖      │      │
  │ 策略選擇 │  └──────────────────────┘      │
  │ [下拉]   │  控制面板：時間範圍、縮放等    │
  └────────────────────────────────────────────┘

文件位置:
  - frontend/src/app/chart-analysis/page.tsx

測試標準:
  ✅ 所有組件正常工作
  ✅ 案例切換流暢
  ✅ 策略切換即時響應
  ✅ 用戶配置可保存
```

---

### 階段1里程碑檢查

#### Milestone 1.1: 基礎圖表完成 (Week 2)
```
檢查項:
  ✅ K線圖正常顯示
  ✅ Volume圖正常顯示
  ✅ Taker_Ratio圖正常顯示
  ✅ 可以縮放和拖曳
  ✅ 圖表流暢無卡頓

交付物:
  - 可運行的圖表demo
  - 基本API端點
```

#### Milestone 1.2: 同步和交互完成 (Week 3)
```
檢查項:
  ✅ 所有圖表時間軸同步
  ✅ CrossHair對齊
  ✅ 統一縮放控制
  ✅ 無明顯延遲

交付物:
  - 完整的同步圖表系統
```

#### Milestone 1.3: 信號標記完成 (Week 4)
```
檢查項:
  ✅ 箭頭正確顯示
  ✅ 策略選擇功能正常
  ✅ 多策略支持
  ✅ 懸停提示正常

交付物:
  - 完整的信號標記系統
  - 策略選擇器UI
```

#### Milestone 1.4: 數據下載完成 (Week 6)
```
檢查項:
  ✅ CSV上傳正常
  ✅ 批量下載穩定
  ✅ HDF5存儲正確
  ✅ 進度追蹤準確
  ✅ 錯誤處理健壯

交付物:
  - K線數據批量下載系統
  - 完整的圖表分析頁面
```

---

### 階段1風險評估

#### 高風險項
```
風險1: Lightweight Charts性能問題
  - 描述: 大量K線數據（10000+）可能導致卡頓
  - 概率: 中
  - 影響: 高
  - 緩解措施:
    * 實現數據分頁加載
    * 限制單次顯示數據量
    * 使用虛擬滾動

風險2: API速率限制
  - 描述: Binance API限制可能導致下載慢
  - 概率: 高
  - 影響: 中
  - 緩解措施:
    * 實現智能重試
    * 批量請求優化
    * 考慮使用多個API key輪換

風險3: HDF5存儲性能
  - 描述: 大量案例數據可能導致讀寫慢
  - 概率: 低
  - 影響: 中
  - 緩解措施:
    * 使用壓縮
    * 優化數據結構
    * 考慮使用緩存
```

---

## 階段2：指標測試系統

### 階段目標
**讓用戶能夠測試多種技術指標的有效性，並自動優化參數**

### 時間規劃
- **總時長**: 4-5週
- **優先級**: 🔥🔥 P1（高）
- **依賴**: 階段1完成（需要K線數據）

### 功能概述
```
輸入: 已下載的案例K線數據
     ↓
處理: 計算多種指標 × 多數據源 → Optuna優化
     ↓
輸出: 指標評分排名 + 最佳參數
```

---

### 任務2.1：指標計算引擎 (Week 7-8)

#### 後端任務
```yaml
任務列表:
  - [ ] 設計指標計算框架
  - [ ] 整合pandas-ta和ta-lib
  - [ ] 實現多數據源支持
  - [ ] 批量計算優化
  - [ ] 指標結果緩存

支持的數據源:
  - close (收盤價)
  - open (開盤價)
  - high (最高價)
  - low (最低價)
  - volume (成交量)
  - taker_volume (主動買入量)
  - taker_ratio (主動買入比例)

支持的指標:
  移動平均類:
    - SMA (Simple Moving Average)
    - EMA (Exponential Moving Average)
    - DEMA (Double EMA)
    - TEMA (Triple EMA)
    - WMA (Weighted Moving Average)
  
  動量類:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Stochastic (KD指標)
    - CCI (Commodity Channel Index)
  
  波動率類:
    - ATR (Average True Range)
    - Bollinger Bands
    - Keltner Channel
  
  成交量類:
    - OBV (On Balance Volume)
    - VWAP (Volume Weighted Average Price)
    - MFI (Money Flow Index)

代碼結構:
  class IndicatorCalculator:
      def calculate(self, 
                   data: pd.DataFrame,
                   indicator: str,
                   data_source: str,
                   params: dict) -> pd.Series:
          """
          計算指標
          
          Example:
            calc.calculate(
              data=kline_df,
              indicator='EMA',
              data_source='close',
              params={'period': 20}
            )
            → 返回 close_ema_20
          """

文件位置:
  - api/services/indicator_calculator.py
  - api/utils/indicator_registry.py

測試標準:
  ✅ 所有指標計算正確（與TradingView對比）
  ✅ 批量計算速度快（< 1秒/1000案例）
  ✅ 支持自定義參數
```

---

### 任務2.2：Optuna參數優化 (Week 8-9)

#### 後端任務
```yaml
任務列表:
  - [ ] 設計優化目標函數
  - [ ] 定義參數搜索空間
  - [ ] 實現並行優化
  - [ ] 優化進度追蹤
  - [ ] 結果可視化

優化框架:
  import optuna
  
  def objective(trial, indicator, cases, labels):
      # 定義參數空間
      if indicator == 'EMA':
          period = trial.suggest_int('period', 5, 200)
      elif indicator == 'RSI':
          period = trial.suggest_int('period', 7, 21)
      elif indicator == 'MACD':
          fast = trial.suggest_int('fast', 8, 15)
          slow = trial.suggest_int('slow', 20, 30)
          signal = trial.suggest_int('signal', 7, 12)
      
      # 計算指標
      indicator_values = calculate_indicator(cases, indicator, params)
      
      # 生成信號
      signals = generate_signals(indicator_values)
      
      # 評估準確率
      accuracy = evaluate_accuracy(signals, labels)
      
      return accuracy
  
  # 執行優化
  study = optuna.create_study(
      direction='maximize',
      sampler=optuna.samplers.TPESampler(),
      pruner=optuna.pruners.MedianPruner()
  )
  
  study.optimize(
      objective, 
      n_trials=100,
      n_jobs=8  # M1 8核心並行
  )

評估指標:
  1. 正反例分類準確率 (主要目標)
  2. Precision (精確率)
  3. Recall (召回率)
  4. F1 Score
  5. 信號頻率 (不能太少或太多)

文件位置:
  - api/services/indicator_optimizer.py
  - api/models/optimization_config.py

測試標準:
  ✅ 優化收斂（accuracy提升）
  ✅ 並行運行穩定
  ✅ 結果可重現
```

---

### 任務2.3：指標評分系統 (Week 9)

#### 後端任務
```yaml
任務列表:
  - [ ] 設計多維度評分公式
  - [ ] 實現信號密度計算
  - [ ] 實現穩定性評估
  - [ ] 生成排名報告

評分維度:
  1. 分類準確率 (50%)
     - 正反例分類的準確度
  
  2. 信號頻率 (20%)
     - 太少：無法交易
     - 太多：可能過擬合
     - 最佳：5-15%的K線有信號
  
  3. 信號穩定性 (20%)
     - 跨時間段的一致性
     - 不同市場環境的表現
  
  4. 計算效率 (10%)
     - 計算複雜度
     - 實時性要求

評分公式:
  score = (accuracy * 0.5) +
          (frequency_score * 0.2) +
          (stability_score * 0.2) +
          (efficiency_score * 0.1)
  
  frequency_score = {
    1.0 if 5% <= freq <= 15%
    0.5 if freq < 5% or freq > 15%
    0.0 if freq < 1% or freq > 30%
  }

輸出格式:
  {
    "indicator": "close_ema_20",
    "score": 0.85,
    "accuracy": 0.78,
    "frequency": 0.12,
    "stability": 0.82,
    "efficiency": 0.95,
    "best_params": {"period": 20},
    "signal_count": 120,
    "rank": 1
  }

文件位置:
  - api/services/indicator_scorer.py

測試標準:
  ✅ 評分合理（高分指標確實有效）
  ✅ 排名穩定
  ✅ 報告完整
```

---

### 任務2.4：指標測試UI (Week 10-11)

#### 前端任務
```yaml
任務列表:
  - [ ] 創建指標測試主頁面
  - [ ] 數據源選擇器（多選）
  - [ ] 指標選擇器（多選）
  - [ ] 參數配置面板
  - [ ] 優化設定（Optuna配置）
  - [ ] 實時進度顯示
  - [ ] 結果排名表格
  - [ ] 指標詳情頁

頁面結構:
  ┌────────────────────────────────────────────┐
  │ 指標測試                                   │
  ├────────────────────────────────────────────┤
  │ 步驟1: 選擇數據源                          │
  │ ☑ Close  ☑ Volume  ☑ Taker_Ratio         │
  ├────────────────────────────────────────────┤
  │ 步驟2: 選擇指標                            │
  │ ☑ EMA    ☑ RSI    ☑ MACD                 │
  │ 參數: ○ 使用默認  ⚫ 自動優化             │
  ├────────────────────────────────────────────┤
  │ 步驟3: 優化設定                            │
  │ 方法: [Optuna TPE ▼]                      │
  │ 試驗次數: [100]                            │
  │ 並行度: [8]                                │
  ├────────────────────────────────────────────┤
  │ 步驟4: 執行測試                            │
  │ [開始測試]                                 │
  │ 進度: ████████░░░░░░ 50% (50/100)         │
  ├────────────────────────────────────────────┤
  │ 結果排名                                   │
  │ #  │ 指標         │ 評分 │ 準確率│頻率 │  │
  │ 1  │ close_ema_20 │ 0.85 │ 78%  │12% │  │
  │ 2  │ volume_rsi_14│ 0.82 │ 75%  │15% │  │
  │ 3  │ taker_macd   │ 0.79 │ 76%  │10% │  │
  └────────────────────────────────────────────┘

文件位置:
  - frontend/src/app/indicator-testing/page.tsx
  - frontend/src/components/indicator/DataSourceSelector.tsx
  - frontend/src/components/indicator/IndicatorSelector.tsx
  - frontend/src/components/indicator/ResultRanking.tsx

測試標準:
  ✅ UI直觀易用
  ✅ 進度實時更新
  ✅ 結果清晰展示
  ✅ 支持導出報告
```

---

### 階段2里程碑檢查

#### Milestone 2.1: 指標計算完成 (Week 8)
```
檢查項:
  ✅ 所有指標計算正確
  ✅ 多數據源支持
  ✅ 批量計算高效

交付物:
  - 指標計算引擎
  - API端點
```

#### Milestone 2.2: Optuna優化完成 (Week 9)
```
檢查項:
  ✅ 參數優化收斂
  ✅ 並行運行穩定
  ✅ 評分系統合理

交付物:
  - 參數優化系統
  - 評分排名功能
```

#### Milestone 2.3: UI完成 (Week 11)
```
檢查項:
  ✅ 完整的測試流程
  ✅ 結果清晰展示
  ✅ 用戶體驗良好

交付物:
  - 指標測試完整UI
  - 用戶使用文檔
```

---

## 階段3：ML訓練系統

### 階段目標
**使用機器學習模型自動預測案例是否會上漲**

### 時間規劃
- **總時長**: 4-6週
- **優先級**: 🔥🔥 P1（高）
- **依賴**: 階段2完成（需要指標特徵）

### 功能概述
```
輸入: 案例 + 20-30個指標特徵
     ↓
處理: XGBoost/LSTM訓練 → 交叉驗證
     ↓
輸出: 預測概率 + 風險報酬比 + 特徵重要性
```

---

### 任務3.1：特徵工程 (Week 12)

#### 後端任務
```yaml
任務列表:
  - [ ] 設計特徵提取框架
  - [ ] 實現價格特徵計算
  - [ ] 實現成交量特徵計算
  - [ ] 實現籌碼特徵計算
  - [ ] 實現技術指標特徵
  - [ ] 實現時序特徵
  - [ ] 特徵標準化

特徵分類:
  1. 價格特徵 (8個):
     - open, high, low, close
     - price_change, price_volatility
     - price_range, gap
  
  2. 成交量特徵 (6個):
     - volume, volume_ma
     - volume_std, volume_spike
     - volume_trend, volume_ratio
  
  3. 籌碼特徵 (5個):
     - taker_volume, taker_ratio
     - taker_ratio_ma, taker_ratio_change
     - taker_strength
  
  4. 技術指標特徵 (10-15個):
     - 從階段2選出的top指標
     - ema_5, ema_20, ema_50
     - rsi_14, macd, atr
     - bb_upper, bb_lower
     - (根據階段2結果動態調整)
  
  5. 時序特徵 (3個):
     - hour_of_day (0-23)
     - day_of_week (0-6)
     - market_phase (bull/bear/sideways)

總特徵數: 30-35個

特徵工程代碼:
  class FeatureEngineer:
      def extract_features(self, case_data):
          features = {}
          
          # 價格特徵
          features.update(self._price_features(case_data))
          
          # 成交量特徵
          features.update(self._volume_features(case_data))
          
          # 籌碼特徵
          features.update(self._taker_features(case_data))
          
          # 技術指標特徵
          features.update(self._indicator_features(case_data))
          
          # 時序特徵
          features.update(self._temporal_features(case_data))
          
          return pd.DataFrame(features)

文件位置:
  - api/services/feature_engineer.py
  - api/models/feature_config.py

測試標準:
  ✅ 特徵計算正確
  ✅ 無缺失值處理
  ✅ 標準化合理
```

---

### 任務3.2：XGBoost基線模型 (Week 13-14)

#### 後端任務
```yaml
任務列表:
  - [ ] 數據準備pipeline
  - [ ] XGBoost模型訓練
  - [ ] 交叉驗證
  - [ ] 模型評估
  - [ ] 特徵重要性分析
  - [ ] 模型保存和加載

訓練流程:
  # 1. 數據準備
  X_train, X_test, y_train, y_test = prepare_train_test_split(
      positive_cases,  # 正例（會漲）
      negative_cases,  # 反例（不會漲）
      test_size=0.2,
      stratify=True    # 保持正負比例
  )
  
  # 2. 模型訓練
  model = XGBClassifier(
      n_estimators=100,
      max_depth=6,
      learning_rate=0.1,
      subsample=0.8,
      colsample_bytree=0.8,
      random_state=42,
      use_label_encoder=False,
      eval_metric='logloss'
  )
  
  model.fit(
      X_train, y_train,
      eval_set=[(X_test, y_test)],
      early_stopping_rounds=10,
      verbose=True
  )
  
  # 3. 模型評估
  y_pred = model.predict(X_test)
  y_proba = model.predict_proba(X_test)[:, 1]
  
  metrics = {
      'accuracy': accuracy_score(y_test, y_pred),
      'precision': precision_score(y_test, y_pred),
      'recall': recall_score(y_test, y_pred),
      'f1': f1_score(y_test, y_pred),
      'auc': roc_auc_score(y_test, y_proba)
  }
  
  # 4. 特徵重要性
  feature_importance = pd.DataFrame({
      'feature': feature_names,
      'importance': model.feature_importances_
  }).sort_values('importance', ascending=False)

評估標準:
  ✅ Accuracy > 70%
  ✅ Precision > 68%
  ✅ Recall > 72%
  ✅ F1 Score > 0.70
  ✅ AUC > 0.75

文件位置:
  - api/services/ml_training_service.py
  - api/models/xgboost_model.py
  - api/utils/model_evaluator.py

測試標準:
  ✅ 模型訓練成功
  ✅ 評估指標達標
  ✅ 模型可保存加載
```

---

### 任務3.3：Optuna超參數優化 (Week 14)

#### 後端任務
```yaml
任務列表:
  - [ ] 定義超參數搜索空間
  - [ ] 實現自動調參
  - [ ] 交叉驗證整合
  - [ ] 最佳模型選擇

Optuna優化:
  def objective(trial):
      params = {
          'n_estimators': trial.suggest_int('n_estimators', 50, 200),
          'max_depth': trial.suggest_int('max_depth', 3, 10),
          'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
          'subsample': trial.suggest_float('subsample', 0.6, 1.0),
          'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
          'min_child_weight': trial.suggest_int('min_child_weight', 1, 10)
      }
      
      model = XGBClassifier(**params)
      
      # 5-fold交叉驗證
      cv_scores = cross_val_score(
          model, X_train, y_train,
          cv=5, scoring='f1'
      )
      
      return cv_scores.mean()
  
  study = optuna.create_study(direction='maximize')
  study.optimize(objective, n_trials=100, n_jobs=8)
  
  best_params = study.best_params

文件位置:
  - api/services/hyperparameter_tuner.py

測試標準:
  ✅ 參數優化收斂
  ✅ 最佳模型效果提升
```

---

### 任務3.4：預測和風險報酬比 (Week 15)

#### 後端任務
```yaml
任務列表:
  - [ ] 實現預測接口
  - [ ] 計算預測概率
  - [ ] 統計風險報酬比
  - [ ] 生成預測報告

預測接口:
  def predict(model, case_features):
      # 預測
      prediction = model.predict(case_features)[0]  # 0 or 1
      probability = model.predict_proba(case_features)[0, 1]  # 0.0-1.0
      
      # 信心水平
      confidence = 'high' if probability > 0.8 or probability < 0.2 else \
                   'medium' if probability > 0.65 or probability < 0.35 else \
                   'low'
      
      return {
          'prediction': int(prediction),
          'probability': float(probability),
          'confidence': confidence
      }

風險報酬比計算:
  def calculate_risk_reward_ratio(model, historical_cases):
      # 預測所有歷史案例
      predictions = model.predict(historical_cases.features)
      
      # 找出模型預測為"會漲"的案例
      predicted_up_indices = predictions == 1
      predicted_up_cases = historical_cases[predicted_up_indices]
      
      # 計算實際漲跌幅
      actual_returns = predicted_up_cases['future_return']
      
      # 分離盈虧
      profits = actual_returns[actual_returns > 0]
      losses = actual_returns[actual_returns < 0]
      
      # 統計
      stats = {
          'avg_profit': profits.mean(),
          'avg_loss': abs(losses.mean()),
          'win_rate': len(profits) / len(actual_returns),
          'risk_reward_ratio': profits.mean() / abs(losses.mean()),
          'expected_return': actual_returns.mean()
      }
      
      return stats

輸出格式:
  {
    "prediction": 1,              # 0=不漲, 1=會漲
    "probability": 0.78,          # 上漲概率
    "confidence": "high",         # 信心水平
    "expected_return": 0.085,     # 預期收益 8.5%
    "risk_reward_ratio": 2.5,     # 風險報酬比
    "win_rate": 0.68,             # 歷史勝率
    "top_features": [             # 關鍵特徵
        ("close_ema_20", 0.15),
        ("volume_spike", 0.12),
        ("taker_ratio", 0.10)
    ]
  }

API端點:
  POST /api/v1/ml/predict
    Request: {
      case_id: string,
      model_version: string
    }
    Response: PredictionResult

文件位置:
  - api/services/ml_predictor.py
  - api/routes/ml.py

測試標準:
  ✅ 預測準確
  ✅ 風險報酬比合理
  ✅ API響應快速
```

---

### 任務3.5：ML訓練UI (Week 16-17)

#### 前端任務
```yaml
任務列表:
  - [ ] ML訓練主頁面
  - [ ] 數據準備界面
  - [ ] 模型選擇和配置
  - [ ] 訓練進度追蹤
  - [ ] 評估指標展示
  - [ ] 特徵重要性圖表
  - [ ] 預測測試界面

頁面結構:
  ┌────────────────────────────────────────────┐
  │ ML模型訓練                                 │
  ├────────────────────────────────────────────┤
  │ 步驟1: 數據準備                            │
  │ 正例案例: [1000] 個 (已下載K線數據)       │
  │ 反例案例: [3000] 個 (已下載K線數據)       │
  │ 特徵數量: [32] 個                          │
  │ 訓練集/測試集: [80%/20%]                  │
  ├────────────────────────────────────────────┤
  │ 步驟2: 模型選擇                            │
  │ ⚫ XGBoost  ○ LightGBM  ○ LSTM            │
  │ [使用Optuna自動調參] ☑                    │
  ├────────────────────────────────────────────┤
  │ 步驟3: 開始訓練                            │
  │ [開始訓練]                                 │
  │ 進度: ████████████████ 100%               │
  │ 時間: 5分鐘 / 預計8分鐘                    │
  ├────────────────────────────────────────────┤
  │ 模型評估                                   │
  │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
  │ │準確率│ │精確率│ │召回率│ │ F1   │     │
  │ │ 78% │ │ 76% │ │ 81% │ │ 0.78│     │
  │ └──────┘ └──────┘ └──────┘ └──────┘     │
  │ 風險報酬比: 2.5:1                          │
  │ 歷史勝率: 68%                              │
  ├────────────────────────────────────────────┤
  │ 特徵重要性                                 │
  │ 1. close_ema_20      ████████░░ 15%       │
  │ 2. volume_spike      ██████░░░░ 12%       │
  │ 3. taker_ratio       █████░░░░░ 10%       │
  │ 4. rsi_14            ████░░░░░░ 8%        │
  ├────────────────────────────────────────────┤
  │ 操作                                       │
  │ [保存模型] [測試預測] [導出報告]          │
  └────────────────────────────────────────────┘

文件位置:
  - frontend/src/app/ml-training/page.tsx
  - frontend/src/components/ml/DataPrepPanel.tsx
  - frontend/src/components/ml/ModelSelector.tsx
  - frontend/src/components/ml/TrainingProgress.tsx
  - frontend/src/components/ml/EvaluationPanel.tsx
  - frontend/src/components/ml/FeatureImportance.tsx

測試標準:
  ✅ 訓練流程完整
  ✅ 進度實時更新
  ✅ 評估指標清晰
  ✅ 特徵重要性可視化
```

---

### 任務3.6：（可選）LSTM模型 (Week 18)

#### 後端任務
```yaml
任務列表:
  - [ ] PyTorch環境配置（M1 MPS加速）
  - [ ] 時序數據準備
  - [ ] LSTM模型實現
  - [ ] 訓練流程
  - [ ] 模型評估

僅在以下情況開發:
  ✅ XGBoost效果不理想（< 70%準確率）
  ✅ 數據量充足（> 10000案例）
  ✅ 需要捕捉長期時序依賴

LSTM架構:
  class LSTMClassifier(nn.Module):
      def __init__(self, input_size, hidden_size, num_layers):
          super().__init__()
          self.lstm = nn.LSTM(
              input_size, hidden_size, 
              num_layers, batch_first=True
          )
          self.fc = nn.Linear(hidden_size, 1)
          self.sigmoid = nn.Sigmoid()
      
      def forward(self, x):
          # x: (batch, seq_len, features)
          lstm_out, _ = self.lstm(x)
          last_hidden = lstm_out[:, -1, :]
          out = self.fc(last_hidden)
          return self.sigmoid(out)

文件位置:
  - api/services/lstm_model.py

測試標準:
  ✅ 模型收斂
  ✅ 效果優於XGBoost
  ✅ M1 MPS加速生效
```

---

### 階段3里程碑檢查

#### Milestone 3.1: 特徵工程完成 (Week 12)
```
檢查項:
  ✅ 特徵提取正確
  ✅ 30+個特徵
  ✅ 無缺失值

交付物:
  - 特徵工程模組
```

#### Milestone 3.2: XGBoost基線完成 (Week 14)
```
檢查項:
  ✅ 模型訓練成功
  ✅ 準確率 > 70%
  ✅ 特徵重要性分析

交付物:
  - XGBoost訓練pipeline
  - 評估報告
```

#### Milestone 3.3: UI完成 (Week 17)
```
檢查項:
  ✅ 完整訓練流程
  ✅ 評估指標清晰
  ✅ 預測功能正常

交付物:
  - ML訓練完整UI
  - 用戶文檔
```

---

## 階段4：Pattern發現系統

### 時間規劃
- **總時長**: 2-3週
- **優先級**: 🔥 P2（中）
- **依賴**: 階段2完成

### 簡要任務
```
Week 19-20: Pattern發現引擎
  - [ ] 高分指標組合生成
  - [ ] Pattern有效性測試
  - [ ] Pattern排名

Week 21: Pattern UI
  - [ ] Pattern列表展示
  - [ ] Pattern詳情頁
  - [ ] Pattern比較功能
```

---

## 階段5：回測系統

### 時間規劃
- **總時長**: 3-4週
- **優先級**: 🔥 P2（中）
- **依賴**: 階段3或4完成

### 簡要任務
```
Week 22-23: 回測引擎
  - [ ] 核心回測邏輯
  - [ ] 交易執行模擬
  - [ ] 績效指標計算

Week 24: 回測UI
  - [ ] 策略選擇界面
  - [ ] 權益曲線圖
  - [ ] 績效儀表板

Week 25: 報告生成
  - [ ] PDF報告導出
  - [ ] 策略對比分析
```

---

## 階段6：系統優化和完善

### 時間規劃
- **總時長**: 持續進行
- **優先級**: 💡 P3（低）

### 優化方向
```
性能優化:
  - [ ] 圖表渲染優化
  - [ ] 數據加載優化
  - [ ] 緩存策略優化

用戶體驗:
  - [ ] 響應式設計完善
  - [ ] 操作流程優化
  - [ ] 錯誤提示優化
  - [ ] 幫助文檔

系統穩定性:
  - [ ] 錯誤處理完善
  - [ ] 日誌系統優化
  - [ ] 監控告警
  - [ ] 自動化測試
```

---

## 未來擴展

### 實盤交易系統（遠期）
```
階段X: 實盤部署
  - [ ] 雲端部署架構
  - [ ] 實時監控系統
  - [ ] 自動交易執行
  - [ ] 風險控制系統
  - [ ] 告警通知系統
```

### 多市場支持
```
台股支持:
  - [ ] 台股數據源接入
  - [ ] 台股特有指標
  - [ ] 台股交易規則

美股支持:
  - [ ] 美股數據源接入
  - [ ] 美股特有指標
  - [ ] 美股交易規則
```

### 鏈上數據整合
```
鏈上數據:
  - [ ] 鏈上數據API接入
  - [ ] 鏈上指標計算
  - [ ] 鏈上信號整合
```

---

## 里程碑檢查點

### 第一季度（Month 1-3）
```
✅ Milestone Q1: 圖表和指標系統完成
  - 完整的圖表分析功能
  - K線數據批量下載
  - 指標測試和優化

交付物:
  - 可視化分析系統
  - 指標評分報告
  - 用戶使用文檔

成功指標:
  - 圖表流暢（60fps）
  - 指標測試準確
  - 用戶反饋良好
```

### 第二季度（Month 4-6）
```
✅ Milestone Q2: ML和回測系統完成
  - ML分類模型訓練
  - Pattern自動發現
  - 完整回測系統

交付物:
  - ML訓練平台
  - 回測引擎
  - 績效報告系統

成功指標:
  - ML準確率 > 70%
  - 回測結果可信
  - 完整研究工作流
```

---

## 風險管理

### 技術風險
```
風險1: 圖表性能問題
  緩解: 數據分頁、虛擬滾動
  應急: 降低數據精度

風險2: ML模型效果不佳
  緩解: 更多數據、特徵優化
  應急: 使用傳統策略

風險3: API速率限制
  緩解: 多key輪換、請求優化
  應急: 減少下載頻率
```

### 資源風險
```
風險1: 開發時間超預期
  緩解: 階段性檢查、及時調整
  應急: 降低功能範圍

風險2: 硬件性能不足
  緩解: 代碼優化、雲端部署
  應急: 限制數據量
```

---

## 開發模式

### AI驅動開發
```
工作流程:
  1. 人工：確定需求和驗證標準
  2. Claude Code CLI：生成代碼實現
  3. 人工：測試功能、提供錯誤信息
  4. Claude Code CLI：修復bug和優化
  5. 人工：驗收功能

優勢:
  ✅ 開發速度快
  ✅ 代碼質量高
  ✅ 遵循規範一致

挑戰:
  ⚠ 需要清晰的需求描述
  ⚠ 需要人工測試驗證
  ⚠ 需要良好的文檔支持
```

---

## 總結

本路線圖規劃了**24週**的開發計劃，涵蓋從圖表可視化到ML訓練的完整研究工作流。

**關鍵時間點**：
- **Week 6**: 圖表系統完成
- **Week 11**: 指標測試完成
- **Week 17**: ML訓練完成
- **Week 25**: 回測系統完成

**成功標準**：
- 用戶可以完整執行：搜索 → 可視化 → 測試 → 訓練 → 回測
- 系統穩定、性能良好
- 文檔完整、易於使用

---

*文檔版本：1.0*  
*最後更新：2025-01-15*  
*維護者：開發團隊*