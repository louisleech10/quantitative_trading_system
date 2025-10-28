# Pattern發現系統開發路線圖

## 文檔資訊
- **版本**: 2.0
- **最後更新**: 2025-10-28
- **核心理念**: 從已知結果反推共同特徵(Pattern Discovery),非預測未來漲跌
- **開發模式**: AI驅動開發(Claude Code CLI)

---

## 核心方法論

### Pattern發現 vs 預測系統

| 項目 | Pattern發現(本系統) | 預測系統(傳統) |
|------|---------------------|----------------|
| 輸入 | 已知正反例 | 未知結果案例 |
| 目標 | 找共同特徵 | 預測漲跌 |
| 方法 | 特徵顯著性分析 | 機器學習預測 |
| 評估指標 | 信號密度差異、Cohen's d | 預測準確率 |

### 關鍵概念澄清

**信號密度(正確)**:
- 計算TO前24根K線中,符合策略的K線占比
- 範例: 24根中18根符合 → 密度75%
- 統計單位: K線級別

**信號有無(錯誤)**:
- 只看案例是否出現過信號(二元)
- 無法反映策略強度

**Optuna優化目標**:
- ✅ 最大化: 正例平均密度 - 反例平均密度
- ❌ 不是: Win Rate或有信號案例比例

**XGBoost使用方式**:
- ✅ 分析正例的共同特徵(feature_importances_)
- ❌ 不是: 預測案例是否會漲

---

## 開發階段總覽

```
Phase 1: 數據基礎層 [✅ 100%]
Phase 2: 圖表視覺化 [✅ 100%]
Phase 3: 策略特徵評估 [⏳ 0%]  ← 當前階段
Phase 4: Pattern發現分析 [📋 0%]
Phase 5: 回測驗證 [📋 0%]
```

---

## Phase 1: 數據基礎層 ✅ 已完成

### 完成項目
- HDF5存儲系統(多層級結構,symbol/timeframe分層)
- K線批量下載(幣安Provider,速率限制,錯誤重試)
- 數據整合服務(智能快取,增量更新)
- 案例CSV導入(多格式,多編碼,欄位標準化)
- 批量下載API(異步任務,進度追蹤,並行下載)

### 交付成果
- 完整數據流: CSV導入 → 批量下載 → HDF5存儲 → 數據讀取
- 測試通過: 12個案例CSV導入、批量下載、圖表顯示

---

## Phase 2: 圖表視覺化 ✅ 已完成

### 完成項目
- Lightweight Charts整合(Price/Volume/TakerRatio三層圖表)
- TO/TC雙標記系統(藍色TO↑,橙色TC↑)
- 三圖表同步(時間軸、CrossHair、縮放、拖曳)
- 圖表數據API(以T為中心裁切,center_index計算)
- 案例選擇器(下拉選單,快速切換)

### 交付成果
- TradingView風格專業圖表
- 三層圖表流暢同步(60fps)
- 案例時間點清晰標記

---

## Phase 3: 策略特徵評估 ⏳ 當前階段

### 階段目標
找出正例的顯著特徵,評估不同策略/指標在正反例中的表現差異

### 時間規劃
- 總時長: 2週
- 優先級: 🔥🔥🔥 P0(最高)

---

### 任務3.1: 多數據源指標計算引擎

**目標**: 建立靈活的指標計算系統

**數據源**(7種):
- close, open, high, low
- volume, taker_volume, taker_ratio

**指標類型**(20+種):
- 趨勢類: EMA, SMA, DEMA, TEMA
- 動能類: RSI, MACD, Stochastic, CCI, Williams %R
- 波動類: ATR, BB(Bollinger Bands), Keltner Channel
- 成交量類: OBV, Volume_MA, VWAP
- 籌碼類: Taker_Ratio_MA, Taker_Strength

**技術要點**:
- 向量化計算(pandas/numba)
- 參數可配置(period, multiplier等)
- 缺失值處理
- 避免未來函數

**涉及模組**:
- 新增: momentum/Indicator/indicator_engine.py
- 新增: momentum/Indicator/trend_indicators.py
- 新增: momentum/Indicator/momentum_indicators.py
- 新增: momentum/Indicator/volatility_indicators.py
- 新增: momentum/Indicator/volume_indicators.py

**驗收標準**:
- 支援7種數據源 × 20+種指標
- 計算結果正確(與TA-Lib對比)
- 向量化計算高效(1000根K線 < 100ms)
- 無未來函數洩漏

---

### 任務3.2: 信號密度統計系統

**目標**: 計算TO前X根K線的信號密度(連續值)

**核心邏輯**:
- 對每個案例,計算TO前X根K線
- 統計符合策略的K線數量
- 計算信號密度 = 符合數量 / X #預設X=24,使用者可以輸入調整
- 分別統計正例和反例的平均密度

**統計指標**:
- 正例平均密度
- 反例平均密度
- 密度差異(separation)
- t檢驗(p-value)
- 效果量(Cohen's d)

**視覺化**:
- 信號密度箱型圖(正例 vs 反例)
- 信號密度直方圖
- 時間分布分析(TO-X到TO的密度變化)

**涉及模組**:
- 新增: momentum/Analysis/signal_density_analyzer.py
- 新增: api/services/signal_analysis_service.py

**驗收標準**:
- 正確計算K線級別信號密度
- t檢驗顯著性計算正確
- Cohen's d效果量計算正確
- 視覺化圖表清晰

---

### 任務3.3: Optuna參數優化系統

**目標**: 自動優化策略參數,最大化正反例信號密度差異

**優化目標函數**:
```
maximize: (正例平均信號密度) - (反例平均信號密度)
```

**搜尋空間範例**:
- EMA週期: 5-200
- RSI週期: 7-28
- RSI閾值: 20-80
- 成交量倍數: 1.5-5.0
- Taker Ratio閾值: 0.4-0.7

**優化策略**:
- 優化器: TPESampler(Tree-structured Parzen Estimator)
- 試驗次數: 100-500次
- 剪枝: 開啟(提前終止差勁試驗)
- 並行: 支援多進程

**評估指標**:
- 主指標: separation(密度差異)
- 輔助指標: Cohen's d, p-value
- 穩定性: 不同時期(如月份)的密度差異

**涉及模組**:
- 新增: momentum/Optimization/optuna_optimizer.py
- 新增: api/services/optimization_service.py

**驗收標準**:
- 優化目標正確(密度差異)
- 優化收斂(100次試驗內)
- 並行運行穩定
- 結果可重現(設定random_seed)

---

---

### 任務3.3補充：容錯與穩健性機制

**目標**: 確保長時間運行的Optuna優化穩定可靠

#### **斷點續跑機制**

**數據庫存儲**:
- 使用SQLite存儲Study狀態（optuna_study.db）
- 每次試驗自動保存到數據庫
- 重新啟動自動從中斷點繼續
- 支持查詢歷史試驗記錄

**檢查點保存**:
- 每50次試驗保存完整檢查點
- 包含當前最佳參數、試驗歷史、統計資訊
- 存儲為pickle檔案（checkpoint_trial_N.pkl）
- 可手動載入任一檢查點恢復

**效果**:
- 電腦當機/斷電後可無縫續跑
- 避免重複計算已完成的試驗
- 保護數小時的計算成果

---

#### **錯誤處理與重試**

**多層錯誤處理**:
- 單次試驗失敗自動重試（最多3次）
- 記憶體不足時觸發垃圾回收
- 數據讀取錯誤時重新載入
- 計算異常時返回極差值或剪枝

**錯誤分類**:
- 可重試錯誤: 暫時性問題（網路、記憶體）
- 不可重試錯誤: 參數問題、數據損壞
- 致命錯誤: 觸發告警並終止

**錯誤日誌**:
- 記錄每個錯誤的試驗編號
- 記錄錯誤類型和堆疊追蹤
- 標記問題參數組合
- 生成錯誤報告摘要

---

#### **進度監控與通知**

**實時進度顯示**:
- 當前完成試驗數/總試驗數
- 完成百分比
- 當前最佳值和參數
- 預計剩餘時間

**階段性通知**:
- 每100次試驗發送進度更新
- 達到新最佳值時即時通知
- 完成階段性里程碑時提醒
- 優化完成後總結報告

**通知管道**（可選）:
- 終端機即時輸出
- 日誌檔案記錄
- Line Notify推送
- Email郵件通知

**監控指標**:
- 試驗完成速度（trials/hour）
- 記憶體使用量
- CPU使用率
- 最佳值收斂曲線

---

#### **自動重啟機制**

**腳本級重啟**:
- 主程式崩潰時自動重啟
- 最多重啟5次
- 重啟前等待10秒冷卻
- 記錄重啟原因和次數

**系統級監控**:
- 偵測程式hang住（無進度超過1小時）
- 偵測記憶體洩漏（記憶體持續增長）
- 偵測異常CPU使用（100%持續30分鐘）
- 觸發條件時自動重啟

**重啟保護**:
- 重啟前保存當前狀態
- 清理暫存資源
- 重新載入預計算數據
- 驗證數據完整性後繼續

---

#### **數據完整性檢查**

**啟動前檢查**:
- 驗證預計算指標檔案存在
- 檢查數據無NaN或缺失值
- 確認數據長度一致性
- 驗證案例索引完整

**運行中檢查**:
- 定期抽樣驗證計算結果
- 檢查信號密度範圍合理（0-1）
- 監控異常值出現頻率
- 驗證正反例標籤正確

**失敗處理**:
- 檢查失敗時記錄詳細資訊
- 嘗試自動修復（重新載入數據）
- 無法修復時終止並告警
- 提供修復建議

**定期驗證**:
- 每500次試驗執行完整性檢查
- 比對數據庫與檢查點一致性
- 驗證統計指標合理性
- 生成健康檢查報告

---

#### **綜合容錯流程**

**優化啟動流程**:
```
1. 數據完整性檢查
   ↓ 通過
2. 載入或創建Optuna Study
   ↓ 偵測歷史記錄
3. 初始化監控和檢查點
   ↓
4. 執行優化（自動容錯）
   ↓ 正常完成或中斷
5. 保存最終結果
   ↓
6. 生成優化報告
```

**容錯優先級**:
- 🔥🔥🔥 斷點續跑（最重要）
- 🔥🔥 錯誤重試和記錄
- 🔥 進度監控
- 💡 自動重啟（可選）

**涉及模組**:
- 修改: momentum/Optimization/optuna_optimizer.py
- 新增: momentum/Optimization/checkpoint_manager.py
- 新增: momentum/Optimization/error_handler.py
- 新增: momentum/Optimization/progress_monitor.py
- 新增: momentum/Utils/data_validator.py

**驗收標準**:
- ✅ 中斷後重啟可自動續跑
- ✅ 錯誤試驗不影響整體進度
- ✅ 進度可視化清晰
- ✅ 數據檢查通過
- ✅ 長時間運行（8小時+）穩定

---

### 任務3.4: 圖表信號箭頭系統

**目標**: 在圖表上標記策略信號,視覺化信號密度

**標記類型**:
- 符合策略邏輯的K線，在K線上方給一個藍色向下箭頭

**懸停資訊**:
- 信號類型
- 信號密度(當下K線)
- 策略名稱
- 參數設定

**涉及模組**:
- 修改: frontend/src/components/charts/PriceChart.tsx
- 新增: frontend/src/components/strategy/SignalMarker.tsx
- 新增: api/routes/strategy.py

**驗收標準**:
- 信號箭頭正確顯示
- 懸停資訊清晰
- 顏色清晰易辨識
- 三個圖表同步標記

---

### 任務3.5: 策略選擇與評估UI

**目標**: 前端策略選擇和結果展示介面

**功能組件**:
- 策略選擇器(下拉選單,預設策略列表)
- 數據源選擇器(7種數據源)
- 指標選擇器(20+種指標)
- 參數輸入框(period, threshold等)
- Optuna優化按鈕
- 評估結果面板

**評估結果展示**:
- 正例平均密度
- 反例平均密度
- 密度差異
- Cohen's d效果量
- p-value顯著性
- 信號密度箱型圖
- 信號密度直方圖

**涉及模組**:
- 新增: frontend/src/components/strategy/StrategySelector.tsx
- 新增: frontend/src/components/strategy/DataSourceSelector.tsx
- 新增: frontend/src/components/strategy/IndicatorSelector.tsx
- 新增: frontend/src/components/strategy/EvaluationPanel.tsx

**驗收標準**:
- UI直觀易用
- 策略選擇流暢
- 評估結果清晰
- 圖表互動良好

---

### Phase 3 Milestone: 策略特徵評估完成

**檢查點**:
- ✅ 指標計算引擎正常運作
- ✅ 信號密度統計正確
- ✅ Optuna優化收斂
- ✅ 圖表信號標記清晰
- ✅ 前端UI完整

**交付成果**:
- 至少10個策略的信號密度分析報告
- 優化後的參數設定
- 正反例信號密度對比圖表

---

## Phase 4: Pattern發現分析

### 階段目標
使用機器學習分析正例的核心特徵組合

### 時間規劃
- 總時長: 2週
- 優先級: 🔥🔥 P1(高)

---

### 任務4.1: 特徵工程系統

**目標**: 在T時刻提取30+個特徵

**特徵分類**:

**1. 價格特徵**(8個):
- open, high, low, close
- price_change, price_volatility
- price_range, gap

**2. 成交量特徵**(6個):
- volume, volume_ma
- volume_std, volume_spike
- volume_trend, volume_ratio

**3. 籌碼特徵**(5個):
- taker_volume, taker_ratio
- taker_ratio_ma, taker_ratio_change
- taker_strength

**4. 技術指標特徵**(10-15個):
- 從Phase 3選出的top指標
- ema_5, ema_20, ema_50
- rsi_14, macd, atr
- bb_upper, bb_lower

**5. 時序特徵**(3個):
- hour_of_day(0-23)
- day_of_week(0-6)
- market_phase(bull/bear/sideways)

**技術要點**:
- 所有特徵基於T時刻(無未來函數)
- 標準化處理(StandardScaler)
- 缺失值處理
- 特徵命名規範(close_t-1格式)

**涉及模組**:
- 新增: momentum/Analysis/feature_engineer.py
- 新增: api/models/feature_config.py

**驗收標準**:
- 特徵提取正確
- 無未來函數洩漏
- 標準化合理
- 特徵數量30-35個

---

### 任務4.2: XGBoost特徵重要性分析

**目標**: 找出正例的共同特徵(不是預測)

**訓練目標**:
- 目標: 區分正反例(已知標籤)
- 不是: 預測未來漲跌

**分析流程**:
- 數據準備(正反例,70/10/20分割)
- XGBoost訓練(分類任務)
- 提取feature_importances_
- SHAP值分析(深度解釋)

**特徵分析**:
- Top 10特徵重要性排名
- 特徵相關性分析
- 特徵組合效果(SHAP interaction)
- 正例共同特徵組合

**涉及模組**:
- 新增: momentum/Analysis/xgboost_analyzer.py
- 新增: momentum/Analysis/shap_analyzer.py
- 新增: api/services/ml_analysis_service.py

**驗收標準**:
- 模型收斂(AUC > 0.7)
- 特徵重要性排名合理
- SHAP值分析清晰
- 正例特徵組合明確

---

### 任務4.2bis: LSTM時序模型分析（可選）

**目標**: 使用LSTM捕捉時序依賴關係，分析正例的時序特徵模式

適用場景:

XGBoost效果不佳時的替代方案
需要捕捉長期時序依賴
分析特徵的時序演變模式

**模型設計**:
**輸入格式**:

- 序列長度: 24根K線（T-24到T-1）
- 特徵數量: 30-35個特徵
- 輸入形狀: (batch_size, 24, 35)

**網路架構**:

- LSTM層: 2-3層，hidden_size=64-128
- Dropout: 0.3-0.5（防過擬合）
- 全連接層: LSTM輸出 → Dense(32) → Dense(1)
- 激活函數: ReLU（隱藏層）、Sigmoid（輸出層）

**訓練策略**:

- 損失函數: BCELoss（二元交叉熵）
- 優化器: Adam（lr=0.001）
- Batch size: 32-64
- Epochs: 50-100（early stopping）
- 設備: M1 MPS加速

**分析輸出**:

- 注意力權重分析（Attention機制）
- 時序特徵重要性（各時間點的梯度）
- 隱藏狀態視覺化（t-SNE）
- 正反例的時序模式差異

**與XGBoost對比**:

- XGBoost: 靜態特徵，特徵重要性明確
- LSTM: 動態時序，捕捉演變模式
- 建議: 先用XGBoost，效果不佳再試LSTM

**涉及模組**:

- 新增: momentum/Analysis/lstm_analyzer.py
- 新增: momentum/Analysis/attention_visualizer.py
- 新增: api/services/lstm_analysis_service.py
- 修改: requirements.txt（新增torch, torchvision）

**驗收標準**:

- 模型收斂（AUC > 0.7）
- M1 MPS加速生效
- 注意力權重可解釋
- 時序模式差異明確
- 效果優於或等於XGBoost

**技術要點**:

- 使用PyTorch原生（避免依賴問題）
- M1 MPS設備檢測: torch.backends.mps.is_available()
- 梯度裁剪（防梯度爆炸）
- 序列padding處理（不同長度序列）
- 時序特徵標準化（按時間點）

**何時使用LSTM**:

✅ 需要分析特徵的時序演變
✅ XGBoost無法捕捉的長期依賴
✅ 想要視覺化時序模式
❌ 特徵靜態性強（用XGBoost即可）
❌ 數據量少（< 500案例，易過擬合）

---

### 任務4.3: Pattern定義與總結

**目標**: 定義3-5個核心Pattern

**Pattern定義格式**:
```
Pattern 1: 量價齊揚 + 籌碼集中
條件:
- volume_spike > 2.0
- taker_ratio > 0.6
- ema_20上穿ema_50
- rsi_14 > 50

覆蓋率: 45%(正例)
誤判率: 15%(反例)
效果量: Cohen's d = 1.2
```

**分析維度**:
- Pattern覆蓋率(正例中的比例)
- Pattern誤判率(反例中的比例)
- Pattern穩定性(不同時期表現)
- Pattern解釋性(是否符合交易邏輯)

**涉及模組**:
- 新增: momentum/Analysis/pattern_analyzer.py
- 新增: api/services/pattern_service.py

**驗收標準**:
- 定義3-5個Pattern
- 每個Pattern有明確條件
- 覆蓋率和誤判率統計正確
- Pattern可解釋

---

### 任務4.4: Pattern評估UI

**目標**: 前端Pattern展示和對比介面

**功能組件**:
- Pattern列表(卡片式展示)
- Pattern詳情(條件、統計、圖表)
- Pattern對比(多個Pattern並列比較)
- Pattern回測結果預覽

**展示內容**:
- Pattern名稱和描述
- 特徵條件組合
- 覆蓋率和誤判率
- 效果量(Cohen's d)
- 正反例密度對比圖
- 特徵重要性圖

**涉及模組**:
- 新增: frontend/src/components/pattern/PatternCard.tsx
- 新增: frontend/src/components/pattern/PatternDetail.tsx
- 新增: frontend/src/components/pattern/PatternComparison.tsx

**驗收標準**:
- UI清晰易懂
- Pattern資訊完整
- 對比功能流暢
- 圖表視覺化良好

---

### 任務4.5: 容錯策略,檢查點,錯誤處理和重試,進度監控和通知,自動重啟腳本,數據完整性檢查

---

### Phase 4 Milestone: Pattern發現完成

**檢查點**:
- ✅ 特徵工程系統正常
- ✅ XGBoost分析完成
- ✅ 定義3-5個Pattern
- ✅ Pattern評估UI完整

**交付成果**:
- Pattern分析報告
- 特徵重要性排名
- SHAP值分析圖表
- Pattern定義文檔

---

## Phase 5: 回測驗證

### 階段目標
驗證Pattern在實際交易中的表現

### 時間規劃
- 總時長: 1週
- 優先級: 🔥 P2(中)

---

### 任務5.1: 簡單回測引擎

**目標**: 實作基礎回測系統

**回測邏輯**:
- 使用發現的Pattern回測歷史數據
- 信號生成: Pattern條件滿足時買入
- 出場策略: 固定持倉時間或止盈止損
- 績效計算: Win Rate, 期望值, Sharpe Ratio

**技術要點**:
- 避免未來函數
- 考慮交易成本
- 滑點模擬
- 資金管理

**涉及模組**:
- 新增: momentum/Backtest/simple_backtest_engine.py
- 新增: api/services/backtest_service.py

**驗收標準**:
- 回測邏輯正確
- 無未來函數
- 績效指標準確
- 支援多個Pattern對比

---

### 任務5.2: 穩定性測試

**目標**: 測試Pattern在不同時期的表現

**測試維度**:
- 不同時間段(月/季/年)
- 不同市場階段(牛市/熊市/盤整)
- 不同交易對
- 樣本外測試

**評估指標**:
- 績效穩定性(標準差)
- 最大回撤
- 勝率一致性
- 夏普比率

**涉及模組**:
- 修改: momentum/Backtest/simple_backtest_engine.py
- 新增: api/services/stability_test_service.py

**驗收標準**:
- 多時期測試完成
- 穩定性指標計算正確
- 異常期表現分析
- 樣本外驗證通過

---

### 任務5.3: 回測結果UI

**目標**: 前端回測結果展示

**功能組件**:
- 權益曲線圖
- 回撤曲線圖
- 績效指標面板
- Pattern對比表格
- 時期穩定性圖表

**展示內容**:
- Win Rate, 期望值
- Sharpe Ratio, Calmar Ratio
- 最大回撤, 平均回撤
- 多時期表現對比
- Pattern排名

**涉及模組**:
- 新增: frontend/src/components/backtest/EquityCurve.tsx
- 新增: frontend/src/components/backtest/PerformancePanel.tsx
- 新增: frontend/src/components/backtest/StabilityChart.tsx

**驗收標準**:
- 圖表清晰
- 績效指標完整
- 對比功能流暢
- 導出報告功能

---

### Phase 5 Milestone: 回測驗證完成

**檢查點**:
- ✅ 回測引擎正常運作
- ✅ 穩定性測試完成
- ✅ 回測UI完整
- ✅ Pattern有效性驗證

**交付成果**:
- 回測報告
- Pattern排名
- 穩定性分析
- 使用建議

---

## 開發規範提醒

### Ultra Think三步驟(必須遵循)

```
步驟1 - 初始生成:
  根據需求生成初版代碼

步驟2 - 自我審查:
  Review代碼,列出優化To-do List

步驟3 - 優化重構:
  根據To-do List生成最終版本
```

### 核心開發原則

**數據真實性**(最重要):
- 嚴禁使用假數據、虛擬數據、硬編碼
- 所有數據必須來自真實數據源或配置檔案

**日誌規範**:
- 關鍵操作記錄INFO級別log
- 錯誤記錄ERROR級別並包含exc_info=True
- 避免在迴圈內大量log

**錯誤處理**:
- 外部API調用必須try-catch
- 區分錯誤類型(可重試 vs 不可重試)
- 給使用者友好的錯誤提示

**性能優化**(M1):
- 優先順序: 向量化 > Numba > 並行 > Python循環
- 使用pandas向量化操作
- 關鍵計算用Numba加速
- 充分利用M1的8核心並行

### 代碼審查Checklist

提交前必須檢查:
- [ ] 沒有假數據/硬編碼
- [ ] 錯誤處理完整
- [ ] log記錄適當
- [ ] 變數命名清晰
- [ ] 沒有重複代碼
- [ ] 性能合理
- [ ] 有類型提示
- [ ] 複雜邏輯有註釋

---

## 總結

本路線圖規劃了**5週**的開發計劃,涵蓋從數據準備到回測驗證的完整Pattern發現工作流。

**關鍵時間點**:
- Week 1-2: Phase 3策略特徵評估完成
- Week 3-4: Phase 4 Pattern發現完成
- Week 5: Phase 5回測驗證完成

**成功標準**:
- 使用者可以完整執行: 數據準備 → 圖表分析 → 策略評估 → Pattern發現 → 回測驗證
- 發現3-5個有效Pattern
- Pattern具備統計顯著性(p < 0.05, Cohen's d > 0.5)
- 回測驗證通過(Win Rate > 60%, Sharpe > 1.0)
- 系統穩定、性能良好

**核心差異**:
- 不是預測系統,是Pattern發現系統
- 不是最大化Win Rate,是最大化信號密度差異
- 不是機器學習預測,是特徵顯著性分析

---

*文檔版本: 2.0*  
*最後更新: 2025-10-28*  
*維護者: 開發團隊*