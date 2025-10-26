# Phase 2.3 開發會話記錄
**圖表容器整合與交互操作**

## 會話信息
- **開始時間**: 2025-01-26
- **結束時間**: 2025-01-26
- **階段**: Phase 2.3 - 圖表容器與交互整合
- **狀態**: ✅ 已完成

---

## 任務目標

實現三個圖表組件的統一容器整合，包括：
1. 時間軸同步機制（拖曳、縮放）
2. 十字線貫穿與數值同步
3. 雙擊重置到 TO 中心
4. 響應式佈局（5:3:2 高度比例）

---

## 實現步驟

### ✅ 步驟 1: TimeAxisContext 架構設計
**文件**: `frontend/src/contexts/TimeAxisContext.tsx`

**關鍵設計決策**：
- 使用 **LogicalRange**（邏輯索引）而非 TimeRange（時間戳）
  - 原因：Lightweight Charts 的縮放錨點基於邏輯索引，時間戳會導致對齊偏移
- 訂閱者模式：Map<chartId, callback>
- **移除全局鎖機制**：允許連鎖廣播，依賴各圖表自己的 `isApplyingExternalUpdateRef` 防循環
- RAF 節流：使用 `requestAnimationFrame` 優化性能

**核心 API**:
```typescript
export interface TimeRange {
  from: number;  // 邏輯索引（非時間戳！）
  to: number;    // 邏輯索引
}

export interface TimeAxisContextValue {
  updateVisibleRange: (range: TimeRange, sourceChartId?: string) => void;
  updateCrosshair: (time: number | null, sourceChartId?: string) => void;
  resetToCenter: (toTimestamp: number) => void;
  subscribeVisibleRangeChange: (chartId: string, callback) => () => void;
  subscribeCrosshairChange: (chartId: string, callback) => () => void;
}
```

**重大修復**：
- ❌ 初始設計：Context 使用 `isSyncingRef` 全局鎖 → 導致連鎖廣播失敗
- ✅ 最終方案：移除 Context 鎖，只用 RAF 節流 + 各圖表獨立鎖

---

### ✅ 步驟 2: useChartSync Hook 開發
**文件**: `frontend/src/hooks/useChartSync.ts`

**功能**：
- 包裝 `useChart`，添加 TimeAxisContext 整合
- 訂閱 Context 的範圍/十字線變化
- 監聽本地圖表變化並廣播到 Context
- 雙擊重置功能

**關鍵實現**：
```typescript
// 1. 訂閱其他圖表的範圍變化
useEffect(() => {
  const unsubscribe = subscribeVisibleRangeChange(chartId, (range) => {
    if (isApplyingExternalUpdateRef.current) return; // 防循環
    
    isApplyingExternalUpdateRef.current = true;
    timeScale.setVisibleLogicalRange({ from: range.from, to: range.to });
    chartInstance.timeScale().applyOptions({}); // 強制重繪
    
    // 使用 ref 追蹤 timeout，確保 cleanup 正確
    lockTimeoutRef.current = setTimeout(() => {
      isApplyingExternalUpdateRef.current = false;
    }, 30);
  });
}, [chartInstance, isReady, enableSync, chartId, subscribeVisibleRangeChange]);

// 2. 監聽本地變化並廣播
useEffect(() => {
  const handleVisibleRangeChange = () => {
    if (isApplyingExternalUpdateRef.current) return;
    
    const logicalRange = timeScale.getVisibleLogicalRange();
    updateVisibleRange({ from: logicalRange.from, to: logicalRange.to }, chartId);
  };
  
  timeScale.subscribeVisibleLogicalRangeChange(handleVisibleRangeChange);
  // 使用 LogicalRange 而非 TimeRange！
}, [chartInstance, isReady, enableSync]);
```

**重大修復記錄**：
1. **無限重渲染問題** (嘗試 #1-3)
   - 原因：`log` 函數在 useEffect 依賴項中，每次都是新引用
   - 解決：移除 `log` 依賴，改用內聯 `if (debug) console.log(...)`

2. **鎖未釋放問題** (嘗試 #4-6)
   - 原因：React Strict Mode 雙重執行 useEffect，清除了 setTimeout
   - 解決：使用 `lockTimeoutRef.current` 追蹤 timeout ID，cleanup 時清除

3. **連鎖廣播失敗** (嘗試 #7-8)
   - 原因：Context 的 `isSyncingRef` 鎖住，volume/taker-ratio 無法廣播
   - 解決：移除 Context 全局鎖，只依賴各圖表自己的鎖

---

### ✅ 步驟 3: TradingChartContainer 開發
**文件**: `frontend/src/components/charts/TradingChartContainer.tsx`

**功能**：
- TimeAxisProvider 包裹三個圖表
- 5:3:2 高度佈局（PriceChart 50%, VolumeChart 30%, TakerRatioChart 20%）
- 自定義十字線覆蓋層（container-level mousemove）
- 50ms 初始化延遲（避免刷新佈局歪掉）

**關鍵實現**：
```typescript
// 初始化延遲避免刷新歪掉
const [isInitialized, setIsInitialized] = useState(false);
useEffect(() => {
  const timer = setTimeout(() => setIsInitialized(true), 50);
  return () => clearTimeout(timer);
}, []);

// 自定義十字線疊層
useEffect(() => {
  const handleMouseMove = (e: MouseEvent) => {
    const x = e.clientX - rect.left;
    setCrosshairX(x);
    
    // X 座標 → 估算時間戳
    const ratio = (x - chartStartX) / chartWidth;
    const estimatedTime = firstTime + (lastTime - firstTime) * ratio;
    updateCrosshair(estimatedTime, 'container');
  };
  
  container.addEventListener('mousemove', handleMouseMove);
}, [klines, updateCrosshair]);
```

---

### ✅ 步驟 4: 三個圖表組件轉換
**文件**: 
- `frontend/src/components/charts/PriceChart.tsx`
- `frontend/src/components/charts/VolumeChart.tsx`
- `frontend/src/components/charts/TakerRatioChart.tsx`

**變更**：
```typescript
// ❌ 舊版
import { useChart } from '../../hooks/useChart';
const { chartContainerRef, chartInstance, isReady } = useChart();

// ✅ 新版
import { useChartSync } from '../../hooks/useChartSync';
import { useTimeAxis } from '@/contexts/TimeAxisContext';

const { chartContainerRef, chartInstance, isReady } = useChartSync({
  chartId: 'price-chart',  // 唯一 ID
  toTimestamp,             // 用於重置
  enableSync: true,        // 啟用同步
  debug: true              // 調試模式
});

const { subscribeCrosshairChange } = useTimeAxis();

// Volume/TakerRatio 額外添加 Context crosshair 訂閱
useEffect(() => {
  const unsubscribe = subscribeCrosshairChange(chartId, (time) => {
    const kline = klines.find(k => k.timestamp === time);
    setHoveredVolume(kline?.volume ?? null);
  });
  return unsubscribe;
}, [subscribeCrosshairChange, klines, chartId]);
```

---

### ✅ 步驟 5: chart/page.tsx 整合
**文件**: `frontend/src/app/chart/page.tsx`

**變更**：
```typescript
// ❌ 舊版：三個獨立圖表組件
<PriceChart ... />
<VolumeChart ... />
<TakerRatioChart ... />

// ✅ 新版：使用 TradingChartContainer
<TradingChartContainer
  symbol={selectedSymbol}
  timeframe={selectedTimeframe}
  klines={klineData}
  toTimestamp={alignedCaseTimestamp ?? selectedTimestamp ?? 0}
  tcTimestamp={alignedTcTimestamp ?? undefined}
  totalHeight={640}
  showToMarker={true}
/>
```

---

## 問題排查與修復時間線

### 問題 #1: 刷新後佈局歪掉
**現象**: Cmd+R 刷新後，三個圖表高度不正確  
**原因**: 圖表在 DOM 完全穩定前初始化，尺寸計算錯誤  
**解決**: 50ms 延遲渲染
```typescript
useEffect(() => {
  const timer = setTimeout(() => setIsInitialized(true), 50);
  return () => clearTimeout(timer);
}, []);
```

### 問題 #2: 組件無限重渲染
**現象**: Console 顯示組件反覆初始化，無 "Subscribed to..." 日誌  
**原因**: `log` 函數在 useEffect 依賴項中  
**解決**: 移除 `log` 依賴，改用 `if (debug) console.log(...)`

### 問題 #3: 鎖未釋放（Skipping local change broadcast）
**現象**: 只有 price-chart 能廣播，volume/taker-ratio 一直顯示 "external update in progress"  
**原因**: React Strict Mode 雙重執行 cleanup，清除了 setTimeout  
**解決**: 使用 `lockTimeoutRef.current` 追蹤並正確清理

### 問題 #4: 連鎖廣播失敗
**現象**: price-chart 廣播 → volume/taker-ratio 收到更新但無法再廣播  
**原因**: Context 的 `isSyncingRef` 阻止連鎖廣播  
**解決**: **移除 Context 全局鎖**，只用 RAF 節流

---

## 最終驗收結果

### ✅ DoD 檢查清單

| 功能項 | 狀態 | 驗證方式 |
|--------|------|----------|
| 拖曳同步 | ✅ | 拖動任一圖表，其他兩個立即同步 |
| 縮放同步 | ✅ | 滾輪縮放任一圖表，其他兩個立即同步且對齊 |
| 十字線貫穿 | ✅ | 滑鼠移動，灰色虛線貫穿三個圖表 |
| 十字線數值同步 | ✅ | 滑鼠在 Price 上移動，Volume/TakerRatio 標籤同步更新 |
| 雙擊重置 | ✅ | 雙擊任一圖表，重置到 TO 中心 |
| 刷新佈局穩定 | ✅ | Cmd+R 刷新後，圖表高度正確（5:3:2） |
| 響應式高度 | ✅ | 容器總高度 640px，自動分配 320/192/128px |

### 🎯 Console 日誌驗證
```
[PriceChart] Initializing with: {chartId: 'price-chart', enableSync: true, ...}
[VolumeChart] Initializing with: {chartId: 'volume-chart', enableSync: true, ...}
[TakerRatioChart] Initializing with: {chartId: 'taker-ratio-chart', enableSync: true, ...}

// 拖曳時的連鎖廣播
[TimeAxisContext] Notifying chart volume-chart of range change
[useChartSync:volume-chart] Received logical range update
[useChartSync:volume-chart] Applied logical range with forced update
[useChartSync:volume-chart] Lock released  ← 確認鎖正確釋放
[TimeAxisContext] Sync complete
```

---

## 技術債務與未來優化

### 已知限制
1. **TypeScript 類型警告**: `useChart.ts` 中 `RefObject<HTMLDivElement | null>` 不完全匹配（不影響功能）
2. **Debug 日誌冗長**: 生產環境需要關閉 `debug={true}`

### 性能優化建議
1. **RAF 節流優化**: 目前每次都 `requestAnimationFrame`，可考慮 throttle 限制頻率
2. **LogicalRange 緩存**: 可添加 `useMemo` 避免重複計算
3. **訂閱者去重**: Map 訂閱可能重複註冊，可添加防護

### 架構改進方向
1. **Zustand 替代 Context**: 更好的性能和 devtools 支持
2. **Web Worker**: 大數據集時，範圍計算移到 Worker
3. **虛擬化**: 超長時間序列可考慮虛擬滾動

---

## 關鍵學習點

### 1. Lightweight Charts 的座標系統
- **Time（時間戳）**: 用於數據點，但縮放錨點不準確
- **Logical（邏輯索引）**: 用於範圍同步，縮放錨點穩定
- **Coordinate（像素座標）**: 用於 UI 事件，需轉換為 Logical

### 2. React useEffect 依賴管理
- **穩定引用原則**: 函數/對象必須用 `useCallback`/`useMemo` 或移出依賴
- **Strict Mode 陷阱**: 開發環境雙重執行，必須正確 cleanup
- **Ref 的妙用**: 追蹤 mutable 值，不觸發重渲染

### 3. 同步機制設計模式
- **中心化 vs 去中心化**: Context 只負責廣播，各圖表自己防循環
- **鎖的粒度**: 全局鎖太粗（阻止連鎖），無鎖太細（無限循環），需平衡
- **Timeout 管理**: 必須用 Ref 追蹤，確保 cleanup 正確

---

## 文件清單

### 新增文件
1. `frontend/src/contexts/TimeAxisContext.tsx` (317 行)
2. `frontend/src/hooks/useChartSync.ts` (294 行)
3. `frontend/src/components/charts/TradingChartContainer.tsx` (262 行)

### 修改文件
1. `frontend/src/components/charts/PriceChart.tsx` (+15 行)
2. `frontend/src/components/charts/VolumeChart.tsx` (+28 行)
3. `frontend/src/components/charts/TakerRatioChart.tsx` (+28 行)
4. `frontend/src/app/chart/page.tsx` (-50 行，簡化)

### 總代碼量
- **新增**: ~900 行
- **修改**: ~20 行
- **刪除**: ~50 行（舊的分離圖表邏輯）
- **淨增**: ~870 行

---

## 下一步計劃

### Phase 2.4: 進階交互功能
- [ ] 圖表區間選擇（Shift+拖曳選擇時間範圍）
- [ ] 快捷鍵支持（Space 拖曳、← → 移動）
- [ ] 迷你地圖（Overview Chart）
- [ ] 價格線拖動（調整止損/止盈）

### Phase 3.1: 機器學習整合
- [ ] 特徵工程可視化（在圖表上疊加特徵值）
- [ ] 模型預測結果展示（預測線、置信區間）
- [ ] 案例聚類可視化（t-SNE/PCA 降維圖）

---

## 結論

✅ **Phase 2.3 成功完成**！

經過 8 次重大迭代修復，最終實現了完全同步的三圖表系統：
1. ✅ 拖曳/縮放完美同步且對齊
2. ✅ 十字線貫穿與數值同步
3. ✅ 刷新佈局穩定
4. ✅ 雙擊重置功能

**關鍵突破**：
- 使用 **LogicalRange** 解決縮放對齊問題
- **移除 Context 全局鎖** 實現連鎖廣播
- **Ref 追蹤 timeout** 確保鎖正確釋放

代碼已就緒，可推送到 Git 保存進度！🚀
