# 任務3.4：圖表信號箭頭系統 - 實作計劃

## 文檔資訊
- **任務編號**: Phase 3 任務3.4
- **優先級**: 🔥🔥 P1 (高)
- **預估時間**: 2-3天
- **前置需求**: 
  - 任務3.1完成（指標計算引擎）
  - 任務3.2完成（信號密度分析系統）
  - 任務3.3部分完成（策略配置UI，至少完成策略選擇邏輯）
- **創建日期**: 2025-10-31

---

## 核心目標

**目標**: 在現有圖表系統上疊加策略信號標記，視覺化展示每根K線是否符合策略邏輯

**關鍵功能**:
- 在符合策略的K線上方顯示藍色向下箭頭（⬇️）
- 懸停箭頭顯示詳細資訊（信號類型、策略名稱、參數設定）
- 三個圖表同步標記（Price/Volume/TakerRatio）
- 支援多種策略邏輯（EMA三線排列/短長交叉/中長交叉）
- 實時計算和渲染（配置變更後即時更新）

**視覺效果**:
```
價格圖表：
  ⬇️        ⬇️  ⬇️              ⬇️
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  │    │    │  │    │    │    │
  K線  K線  K線 K線  K線  K線  K線
  
  藍色箭頭 = 該K線符合策略（如EMA短>中>長）
```

---

## STEP 1: 後端信號計算API

**目標**: 提供API端點，根據策略配置計算每根K線的信號狀態

### 1.1 信號計算請求模型

**修改文件**: `api/models/strategy_config.py`

**新增模型**:

1. **`SignalCalculationRequest`**: 信號計算請求
   - `symbol`: 交易對（如BTCUSDT）
   - `timeframe`: 時間框架（如12h）
   - `start_time`: 起始時間戳（Unix秒）
   - `end_time`: 結束時間戳（Unix秒）
   - `strategy_config`: 策略配置（數據源、指標、策略邏輯、參數）
   - 範例：
     ```json
     {
       "symbol": "BTCUSDT",
       "timeframe": "12h",
       "start_time": 1609459200,
       "end_time": 1612137600,
       "strategy_config": {
         "data_source": "close",
         "indicator_type": "EMA",
         "strategy_logic": "three_line",
         "params": {
           "ema_short": 7,
           "ema_mid": 18,
           "ema_long": 35
         }
       }
     }
     ```

2. **`SignalCalculationResponse`**: 信號計算結果
   - `signals`: 信號列表
     - `timestamp`: K線時間戳
     - `has_signal`: 是否有信號（True/False）
     - `signal_type`: 信號類型（"three_line_aligned" / "short_long_cross" / "mid_long_cross"）
     - `indicator_values`: 指標值（如 {ema_short: 45000, ema_mid: 44000, ema_long: 43000}）
     - `signal_density`: 當前K線的信號密度（TO前N根的累積密度，可選）
   - `total_signals`: 總信號數量
   - `signal_density`: 整體信號密度（符合策略的K線占比）
   - `strategy_summary`: 策略摘要（如 "EMA(7,18,35) 三線排列"）

**驗收標準**:
- ✅ Pydantic模型定義完整
- ✅ 時間範圍驗證（start_time < end_time）
- ✅ 策略配置驗證（參數合理性）
- ✅ 類型提示完整

---

### 1.2 信號計算服務

**新增文件**: `api/services/signal_calculation_service.py`

**核心類**: `SignalCalculationService`

**關鍵方法**:

1. **`calculate_signals()`**: 主計算方法
   - 輸入：SignalCalculationRequest
   - 流程：
     - 調用`kline_data_service`讀取K線數據
     - 調用任務3.1的`indicator_engine`計算指標
     - 調用`_evaluate_strategy_logic()`判斷每根K線是否符合策略
     - 組裝SignalCalculationResponse
   - 錯誤處理：try-catch，K線數據不足時返回空信號

2. **`_evaluate_strategy_logic()`**: 策略邏輯評估（核心算法）
   - 輸入：K線數據、指標數據、策略邏輯類型
   - 策略實作：
     - **三線排列**: 檢查 `ema_short[i] > ema_mid[i] > ema_long[i]`
     - **短長交叉**: 檢查 `ema_short[i] > ema_long[i]`
     - **中長交叉**: 檢查 `ema_mid[i] > ema_long[i]`
   - 輸出：布林陣列（每根K線True/False）
   - 向量化計算：使用numpy布林索引

3. **`_calculate_cumulative_density()`**: 累積信號密度（可選）
   - 輸入：信號陣列、窗口大小（如24）
   - 計算：對每根K線，計算其前N根的信號密度
   - 輸出：密度陣列
   - 用途：懸停資訊顯示當前密度

**技術要點**:
- 100%向量化計算（避免Python循環）
- 處理NaN值（指標計算初期可能有NaN）
- 詳細日誌（INFO級別記錄計算統計）
- 性能優化（1000根K線 < 1秒）

**驗收標準**:
- ✅ 策略邏輯評估正確（與手動驗證一致）
- ✅ 支援3種策略邏輯
- ✅ 向量化計算高效
- ✅ NaN值處理正確
- ✅ 日誌記錄清晰

---

### 1.3 API路由端點

**新增文件**: `api/routes/signal_markers.py`

**核心端點**:

1. **`POST /api/v1/chart/signals`**: 計算圖表信號
   - 請求體：SignalCalculationRequest
   - 響應：SignalCalculationResponse
   - 狀態碼：200成功、400參數錯誤、500伺服器錯誤
   - 功能：計算並返回所有符合策略的K線時間戳
   - 用途：前端圖表標記

**路由註冊**:
- 修改：`api/main.py`
- 添加：`app.include_router(signal_markers_router, prefix="/api/v1/chart", tags=["chart"])`

**驗收標準**:
- ✅ 路由註冊成功
- ✅ API文檔自動生成（/docs顯示）
- ✅ 請求驗證正確
- ✅ CORS配置正確

---

## STEP 2: 前端TypeScript類型與API整合

**目標**: 同步後端數據模型到前端，建立API調用函數

### 2.1 TypeScript類型定義

**修改文件**: `frontend/src/lib/types.ts`

**新增接口**:

```typescript
// 信號計算請求
interface SignalCalculationRequest {
  symbol: string;
  timeframe: string;
  start_time: number;
  end_time: number;
  strategy_config: {
    data_source: 'close' | 'open' | 'high' | 'low' | 'volume' | 'taker_volume' | 'taker_ratio';
    indicator_type: 'EMA' | 'SMA' | 'RSI';
    strategy_logic: 'three_line' | 'short_long_cross' | 'mid_long_cross';
    params: {
      ema_short?: number;
      ema_mid?: number;
      ema_long?: number;
    };
  };
}

// 單個信號數據
interface SignalData {
  timestamp: number;
  has_signal: boolean;
  signal_type: string;
  indicator_values: Record<string, number>;
  signal_density?: number;
}

// 信號計算響應
interface SignalCalculationResponse {
  signals: SignalData[];
  total_signals: number;
  signal_density: number;
  strategy_summary: string;
}
```

**驗收標準**:
- ✅ 類型定義與後端一致
- ✅ 欄位命名統一
- ✅ 類型安全

---

### 2.2 API調用函數

**修改文件**: `frontend/src/lib/api.ts`

**新增函數**:

```typescript
/**
 * 計算圖表信號
 */
export async function calculateChartSignals(
  request: SignalCalculationRequest
): Promise<SignalCalculationResponse> {
  const response = await fetch('/api/v1/chart/signals', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Signal calculation failed');
  }
  
  return response.json();
}
```

**驗收標準**:
- ✅ fetch調用正確
- ✅ 錯誤處理完整
- ✅ 類型安全

---

## STEP 3: 圖表標記組件開發

**目標**: 在Lightweight Charts上渲染信號箭頭標記

### 3.1 信號標記渲染邏輯

**修改文件**: `frontend/src/components/charts/PriceChart.tsx`

**新增功能**:

1. **接收策略配置Props**:
   ```typescript
   export interface PriceChartProps {
     // ...現有props
     strategyConfig?: {
       data_source: string;
       indicator_type: string;
       strategy_logic: string;
       params: Record<string, number>;
     };
     showSignalMarkers?: boolean; // 是否顯示信號箭頭
   }
   ```

2. **調用信號計算API**:
   - 在`useEffect`中，當`strategyConfig`變更時觸發
   - 調用`calculateChartSignals()`
   - 計算時間範圍：取klines的第一根和最後一根時間戳

3. **渲染信號箭頭**:
   - 使用Lightweight Charts的`setMarkers()`方法
   - 標記格式：
     ```typescript
     {
       time: timestamp,
       position: 'aboveBar', // 在K線上方
       color: '#2962FF', // 藍色
       shape: 'arrowDown', // 向下箭頭
       text: 'S', // 簡寫（Signal）
     }
     ```
   - 與現有TO/TC標記合併（不衝突）

4. **懸停資訊顯示**:
   - 監聽chart的`subscribeCrosshairMove`事件
   - 檢查是否懸停在標記上
   - 顯示tooltip：
     - 信號類型（如 "EMA三線排列"）
     - 參數設定（如 "EMA(7,18,35)"）
     - 指標值（如 "Short: 45000, Mid: 44000, Long: 43000"）
     - 信號密度（可選，如 "當前密度: 75%"）

**技術要點**:
- 避免重複渲染（使用`useMemo`緩存markers）
- 標記與TO/TC標記不衝突（合併陣列）
- 性能優化（限制標記數量，如最多500個）
- 錯誤處理（API失敗時不顯示箭頭）

**驗收標準**:
- ✅ 藍色箭頭正確顯示在符合策略的K線上方
- ✅ 箭頭數量與後端計算一致
- ✅ 懸停資訊清晰顯示
- ✅ 與TO/TC標記不衝突
- ✅ 性能良好（渲染500個標記 < 1秒）

---

### 3.2 三圖表同步標記

**修改文件**: `frontend/src/components/charts/VolumeChart.tsx`, `frontend/src/components/charts/TakerRatioChart.tsx`

**功能**:
- 在Volume圖表和TakerRatio圖表上也顯示相同的信號箭頭
- 標記位置：在對應K線的柱狀圖/線圖上方
- 顏色和形狀：與PriceChart一致（藍色向下箭頭）
- 同步機制：使用相同的`signals`數據源

**實作策略**:
- 將`signals`數據傳遞給Volume和TakerRatio組件
- 在各自的圖表上調用`setMarkers()`
- 保持標記樣式一致

**驗收標準**:
- ✅ 三個圖表的箭頭垂直對齊
- ✅ 標記樣式一致
- ✅ 懸停資訊同步（同一時間點顯示相同資訊）

---

## STEP 4: 策略配置UI整合

**目標**: 在圖表頁面添加策略配置控制面板，實時更新信號標記

### 4.1 圖表頁面策略配置組件

**新增文件**: `frontend/src/components/charts/ChartStrategyConfig.tsx`

**功能**:
- 緊湊型策略配置面板（位於圖表上方或側邊）
- 配置項：
  - 數據源選擇（下拉選單）
  - 指標類型選擇（下拉選單，Phase 3僅EMA）
  - 策略邏輯選擇（Radio按鈕）
  - EMA參數輸入（3個數字輸入框）
  - 顯示/隱藏信號箭頭（切換開關）
- 即時生效：參數變更後自動重新計算信號

**UI設計**:
```
┌─────────────────────────────────────────┐
│ 策略配置                      [顯示信號 ✓] │
├─────────────────────────────────────────┤
│ 數據源: [Close ▾]  指標: [EMA ▾]         │
│ 策略: ○三線排列 ○短長交叉 ○中長交叉      │
│ EMA參數: [7] [18] [35]                   │
│ 信號數: 45 / 100 (45%)                   │
└─────────────────────────────────────────┘
```

**Props**:
- `onConfigChange: (config: StrategyConfig) => void` - 配置變更回調
- `signalStats?: { total: number; density: number }` - 信號統計（顯示用）

**驗收標準**:
- ✅ UI緊湊清晰
- ✅ 參數變更即時觸發
- ✅ 信號統計正確顯示
- ✅ 切換開關控制箭頭顯示/隱藏

---

### 4.2 圖表容器整合

**修改文件**: `frontend/src/components/charts/TradingChartContainer.tsx`

**整合邏輯**:

1. **添加策略配置狀態**:
   ```typescript
   const [strategyConfig, setStrategyConfig] = useState<StrategyConfig | null>(null);
   const [signals, setSignals] = useState<SignalData[]>([]);
   const [showSignals, setShowSignals] = useState(false);
   ```

2. **調用信號計算API**:
   - 監聽`strategyConfig`變更
   - debounce 500ms後調用`calculateChartSignals()`
   - 更新`signals`狀態

3. **傳遞信號數據到子圖表**:
   ```typescript
   <PriceChart
     {...otherProps}
     signals={showSignals ? signals : []}
     strategyConfig={strategyConfig}
   />
   ```

4. **添加配置面板**:
   ```typescript
   <div className="trading-chart-container">
     <ChartStrategyConfig
       onConfigChange={setStrategyConfig}
       onShowSignalsChange={setShowSignals}
       signalStats={{ total: signals.length, density: ... }}
     />
     {/* 三個圖表 */}
   </div>
   ```

**驗收標準**:
- ✅ 配置變更觸發信號重新計算
- ✅ 信號數據正確傳遞到三個圖表
- ✅ 顯示/隱藏切換正常
- ✅ debounce生效（避免頻繁API調用）

---

## STEP 5: 懸停資訊框組件

**目標**: 實作專業的信號資訊懸停框

### 5.1 信號Tooltip組件

**新增文件**: `frontend/src/components/charts/SignalTooltip.tsx`

**功能**:
- 懸停在信號箭頭上時顯示詳細資訊
- 顯示內容：
  - 信號類型（如 "EMA三線排列"）
  - 策略名稱（如 "EMA(7,18,35)"）
  - 指標數值（如 "Short: 45000, Mid: 44000, Long: 43000"）
  - 信號密度（如 "前24根密度: 75%"）
  - 時間戳（格式化顯示）
- 位置：跟隨滑鼠，避免遮擋K線

**UI設計**:
```
┌───────────────────────────┐
│ EMA三線排列信號             │
├───────────────────────────┤
│ 策略: EMA(7,18,35)         │
│ 短期: 45,230.50            │
│ 中期: 44,120.80            │
│ 長期: 43,050.20            │
│ 信號密度: 75% (18/24)      │
│ 時間: 2024-01-15 12:00     │
└───────────────────────────┘
```

**Props**:
- `signalData: SignalData` - 信號數據
- `strategyConfig: StrategyConfig` - 策略配置
- `position: { x: number; y: number }` - 顯示位置
- `visible: boolean` - 是否顯示

**技術要點**:
- 使用Portal渲染（避免被圖表遮擋）
- 自動調整位置（接近螢幕邊緣時翻轉）
- 動畫效果（淡入淡出）

**驗收標準**:
- ✅ 懸停資訊完整準確
- ✅ 位置跟隨滑鼠
- ✅ 不遮擋K線
- ✅ 動畫流暢

---

### 5.2 整合到PriceChart

**修改文件**: `frontend/src/components/charts/PriceChart.tsx`

**整合邏輯**:

1. **監聽CrosshairMove事件**:
   ```typescript
   chart.subscribeCrosshairMove((param) => {
     // 檢查是否懸停在標記上
     const hoveredMarker = findHoveredMarker(param);
     if (hoveredMarker) {
       setTooltipData(hoveredMarker);
       setTooltipVisible(true);
     } else {
       setTooltipVisible(false);
     }
   });
   ```

2. **渲染Tooltip**:
   ```typescript
   {tooltipVisible && (
     <SignalTooltip
       signalData={tooltipData}
       strategyConfig={strategyConfig}
       position={tooltipPosition}
       visible={tooltipVisible}
     />
   )}
   ```

**驗收標準**:
- ✅ 懸停在箭頭上顯示tooltip
- ✅ 移開箭頭隱藏tooltip
- ✅ tooltip資訊正確

---

## STEP 6: 性能優化與測試

**目標**: 確保大量標記下系統流暢運行

### 6.1 性能優化

**優化項目**:

1. **標記數量限制**:
   - 最多顯示500個標記（避免渲染過載）
   - 超過時智能採樣（保留關鍵標記）
   - 用戶提示：「信號過多，已採樣顯示」

2. **API調用優化**:
   - debounce 500ms（避免頻繁計算）
   - 緩存計算結果（相同配置不重複計算）
   - 取消未完成的請求（AbortController）

3. **渲染優化**:
   - 使用`useMemo`緩存markers陣列
   - 避免不必要的重渲染（React.memo）
   - 虛擬化長列表（如信號列表）

4. **向量化計算**:
   - 後端使用numpy布林索引
   - 批量處理K線（避免逐根計算）

**驗收標準**:
- ✅ 1000根K線 + 500個標記渲染 < 2秒
- ✅ 配置變更響應延遲 < 500ms
- ✅ 滾動縮放流暢（60fps）
- ✅ 無記憶體洩漏

---

### 6.2 單元測試

**新增文件**: `tests/test_signal_calculation_service.py`

**測試案例**:

1. **測試1：EMA三線排列策略**
   - 輸入：100根K線 + EMA(7,18,35)三線排列
   - 驗證：信號數量合理（20-40個）
   - 驗證：信號位置正確（手動抽查5個）

2. **測試2：短長交叉策略**
   - 輸入：100根K線 + EMA(7,35)短長交叉
   - 驗證：信號數量 > 三線排列（邏輯更寬鬆）
   - 驗證：信號正確性

3. **測試3：邊界情況**
   - K線數量不足（< 指標週期）
   - 所有K線都符合策略
   - 所有K線都不符合策略
   - 驗證：不崩潰，返回合理結果

4. **測試4：性能測試**
   - 輸入：1000根K線
   - 驗證：計算時間 < 1秒

**驗收標準**:
- ✅ 所有測試通過
- ✅ 邊界情況處理正確
- ✅ 性能達標

---

### 6.3 整合測試

**測試場景**:

1. **端到端測試**:
   - 打開圖表頁面
   - 配置EMA三線排列策略
   - 驗證：藍色箭頭顯示在正確K線上方
   - 懸停箭頭
   - 驗證：tooltip顯示正確資訊
   - 切換策略邏輯
   - 驗證：箭頭位置變更

2. **三圖表同步測試**:
   - 驗證：Price/Volume/TakerRatio三個圖表箭頭垂直對齊
   - 滾動縮放
   - 驗證：箭頭同步移動

3. **配置變更測試**:
   - 修改EMA參數（7→10）
   - 驗證：箭頭位置即時更新
   - 切換數據源（Close→High）
   - 驗證：箭頭重新計算

**驗收標準**:
- ✅ 所有場景通過
- ✅ 無UI錯誤或閃爍
- ✅ 性能流暢

---

## 整體驗收標準

### 功能完整性
- ✅ 信號箭頭正確顯示（藍色向下箭頭）
- ✅ 懸停資訊清晰（信號類型、參數、指標值、密度）
- ✅ 三圖表同步標記（垂直對齊）
- ✅ 支援3種策略邏輯（三線排列/短長交叉/中長交叉）
- ✅ 配置即時生效（debounce 500ms）

### 視覺效果
- ✅ 箭頭顏色易辨識（藍色 #2962FF）
- ✅ 箭頭位置準確（在K線正上方）
- ✅ 與TO/TC標記不衝突（橙色/紫色箭頭）
- ✅ tooltip設計專業（TradingView風格）

### 性能要求
- ✅ 1000根K線 + 500標記渲染 < 2秒
- ✅ 配置變更響應 < 500ms
- ✅ 滾動縮放流暢（60fps）
- ✅ API調用次數合理（debounce生效）

### 用戶體驗
- ✅ 操作直觀（配置面板清晰）
- ✅ 反饋即時（loading狀態、錯誤提示）
- ✅ 信號統計顯示（總數、密度）
- ✅ 切換開關控制顯示/隱藏

### 代碼質量
- ✅ 遵循Ultra Think三步驟
- ✅ 向量化計算（後端numpy）
- ✅ 錯誤處理完整（API失敗、數據不足）
- ✅ 類型安全（Python + TypeScript）
- ✅ 單元測試覆蓋率 > 80%

---

## 依賴關係

### 前置需求
- **任務3.1：指標計算引擎**（必須完成）
  - 需要：EMA計算函數
  - 整合點：`calculate_signals()`調用指標引擎

- **任務3.2：信號密度分析系統**（必須完成）
  - 需要：信號密度計算邏輯
  - 整合點：累積密度顯示在tooltip

- **任務3.3：策略選擇UI**（部分完成）
  - 需要：策略配置數據模型
  - 整合點：策略配置傳遞到圖表

### 並行開發
- **任務3.5：Optuna優化系統**（可同時開發）
  - 本任務提供：實時信號視覺化
  - 用途：驗證優化後的參數效果

### 後續任務
- **任務3.6：結果展示UI**
  - 依賴：本任務的信號計算API
  - 用途：結果頁面顯示策略信號統計

---

## 風險與注意事項

### 性能風險
- **風險**：大量標記（500+）導致渲染卡頓
- **緩解**：
  - 限制標記數量（最多500個）
  - 智能採樣（保留關鍵標記）
  - 虛擬化渲染（按視窗顯示）

### 視覺衝突風險
- **風險**：信號箭頭與TO/TC標記重疊
- **緩解**：
  - 不同顏色（藍色 vs 橙色/紫色）
  - 不同形狀（向下 vs 向上）
  - 位置微調（略微偏移）

### API調用頻率風險
- **風險**：頻繁配置變更導致過多API調用
- **緩解**：
  - debounce 500ms
  - 取消未完成請求（AbortController）
  - 緩存計算結果

### Tooltip定位風險
- **風險**：tooltip超出螢幕邊界
- **緩解**：
  - 自動翻轉位置（接近邊緣時）
  - Portal渲染（避免父容器overflow隱藏）

---

## 開發順序建議

**第1天**：STEP 1-2（後端信號計算 + 前端API整合）
- 上午：後端數據模型 + 信號計算服務
- 下午：API路由 + TypeScript類型 + API函數

**第2天**：STEP 3-4（圖表標記渲染 + 配置UI）
- 上午：PriceChart信號箭頭渲染
- 下午：三圖表同步 + 策略配置面板

**第3天**：STEP 5-6（懸停資訊 + 優化測試）
- 上午：SignalTooltip組件 + 整合
- 下午：性能優化 + 單元測試 + 整合測試

---

## 成功標準

任務3.4完成的標誌：
- ✅ 後端API可計算並返回策略信號（POST /api/v1/chart/signals）
- ✅ 前端圖表顯示藍色信號箭頭（符合策略的K線）
- ✅ 懸停箭頭顯示詳細資訊（策略、參數、指標值、密度）
- ✅ 三圖表同步標記（Price/Volume/TakerRatio）
- ✅ 配置面板即時更新信號
- ✅ 性能達標（1000根K線 + 500標記 < 2秒）
- ✅ 單元測試全部通過（> 80%覆蓋率）
- ✅ 文檔更新（STATUS.md標記任務3.4完成）

---

## 參考文檔

- **圖表系統**：現有PriceChart.tsx - Lightweight Charts標記機制
- **策略配置**：任務3.3計劃 - 策略配置數據模型
- **信號密度**：任務3.2計劃 - 信號密度計算邏輯
- **指標計算**：任務3.1 - 指標計算引擎API
- **開發規範**：`.claude/GUIDELINES.md` - Ultra Think三步驟
- **技術架構**：`docs/ARCHITECTURE.md` - 系統架構設計

---

## 額外功能（可選，Phase 4+）

### 進階標記樣式
- 不同策略不同顏色（三線排列=藍色，短長交叉=綠色）
- 信號強度可視化（箭頭大小反映密度）
- 動畫效果（新信號出現時閃爍）

### 信號過濾器
- 按信號密度過濾（只顯示密度 > 70%的）
- 按信號類型過濾（只顯示三線排列）
- 時間範圍過濾（只顯示TO前N根）

### 信號統計圖表
- 信號密度時間序列圖
- 信號分布直方圖
- 策略效果對比圖

### 批量標記匯出
- 導出信號列表為CSV
- 包含時間戳、指標值、密度
- 用於後續分析

---

*文檔版本: 1.0*  
*創建日期: 2025-10-31*  
*維護者: AI Code Agent*
