# 任務3.6：優化結果展示UI - 實作計劃

## 文檔資訊
- **任務編號**: Phase 3 任務3.6
- **優先級**: 🔥🔥 P1 (高)
- **預估時間**: 4-5天
- **前置需求**: 
  - 任務3.2完成（信號密度分析系統）
  - 任務3.5完成（Optuna參數優化系統）
- **創建日期**: 2025-10-31
- **最後更新**: 2025-10-31

---

## 核心目標

**目標**: 建立清晰、專業的優化結果展示介面，輔助使用者理解策略評估結果並快速做出決策

**關鍵功能**:
- 核心指標總覽（separation、p-value、Cohen's d）
- 最佳參數展示與快速應用
- 密度對比視覺化（箱型圖、直方圖、小提琴圖）
- 穩定性分析（時間序列、CV分析）
- Optuna優化歷程視覺化（收斂曲線、參數重要性）
- 試驗歷史表格（排序、篩選、匯出）
- 多策略對比工具（雷達圖、並列表格）
- 報告匯出（PDF、CSV、PNG）

**整合點**:
- 承接任務3.5的Optuna優化結果
- 承接任務3.5的高級視覺化功能（2D熱力圖、3D散點、Pareto前沿）
- 提供策略評估的完整視覺化呈現

---

## STEP 1: TypeScript類型定義與API整合

**目標**: 擴展前端類型系統，支援優化結果的完整數據結構

### 1.1 優化結果類型定義

**修改文件**: `frontend/src/lib/types.ts`

**新增接口**:

```typescript
// 優化結果核心數據
interface OptimizationResult {
  task_id: string;
  best_value: number;                    // 最佳separation
  best_params: StrategyParameters;        // 最佳參數
  best_trial_number: number;
  total_trials: number;
  optimization_time: number;              // 秒
  convergence_history: number[];          // 收斂曲線數據
  trials_summary: TrialSummary[];
  param_importances?: ParamImportance[];  // 參數重要性（Optuna計算）
  
  // 信號密度分析結果（來自任務3.2）
  density_analysis: SignalDensityResult;
  
  // 穩定性分析（按月分組）
  stability_analysis?: StabilityAnalysis;
  
  // Pareto前沿數據（多目標優化）
  pareto_front?: ParetoSolution[];
}

// 策略參數
interface StrategyParameters {
  data_source: string;                    // close/open/high/low等
  indicator_type: string;                 // EMA/SMA等
  strategy_logic: string;                 // three_line等
  ema_short?: number;
  ema_mid?: number;
  ema_long?: number;
  // ... 其他參數
}

// 試驗摘要
interface TrialSummary {
  trial_number: number;
  params: StrategyParameters;
  value: number;                          // separation值
  state: 'COMPLETE' | 'PRUNED' | 'FAIL';
  datetime: string;
  intermediate_values?: number[];         // 中間值（用於剪枝）
}

// 參數重要性
interface ParamImportance {
  param_name: string;
  importance: number;                     // 0-1
}

// 信號密度分析結果
interface SignalDensityResult {
  positive_avg_density: number;           // 0-1
  negative_avg_density: number;           // 0-1
  separation: number;                     // 密度差異
  p_value: number;                        // 統計顯著性
  cohens_d: number;                       // 效果量
  positive_case_count: number;
  negative_case_count: number;
  positive_densities: number[];           // 所有正例的密度值
  negative_densities: number[];           // 所有反例的密度值
}

// 穩定性分析
interface StabilityAnalysis {
  monthly_separations: MonthlyData[];
  mean_separation: number;
  std_separation: number;
  cv: number;                             // 變異係數
  positive_ratio: number;                 // 正值比例
  worst_month: MonthlyData;
  best_month: MonthlyData;
}

interface MonthlyData {
  month: string;                          // YYYY-MM
  separation: number;
  positive_density: number;
  negative_density: number;
  case_count: number;
}

// Pareto前沿解（多目標優化）
interface ParetoSolution {
  trial_number: number;
  params: StrategyParameters;
  separation: number;
  stability_score: number;                // 1 - CV
  is_recommended: boolean;                // 推薦解
}
```

**驗收標準**:
- ✅ 所有接口定義完整且與後端一致
- ✅ 類型安全（無any類型）
- ✅ 註釋清晰易懂

---

### 1.2 API調用函數擴展

**修改文件**: `frontend/src/lib/api.ts`

**新增方法**:

```typescript
class ApiClient {
  // 從任務3.5繼承的優化API（已存在）
  async getOptimizationResult(taskId: string): Promise<ApiResponse<OptimizationResult>>;
  
  // 新增：獲取參數重要性分析
  async getParamImportance(taskId: string): Promise<ApiResponse<ParamImportance[]>>;
  
  // 新增：獲取穩定性分析
  async getStabilityAnalysis(taskId: string): Promise<ApiResponse<StabilityAnalysis>>;
  
  // 新增：對比多個優化結果
  async compareOptimizationResults(
    taskIds: string[]
  ): Promise<ApiResponse<ComparisonResult>>;
  
  // 新增：生成PDF報告（後端生成，前端下載）
  async exportPdfReport(taskId: string): Promise<Blob>;
  
  // 新增：匯出試驗歷史CSV
  async exportTrialsCSV(taskId: string): Promise<Blob>;
}
```

**驗收標準**:
- ✅ API調用正確（正確的endpoint和HTTP方法）
- ✅ 錯誤處理完整（try-catch + 友好錯誤提示）
- ✅ 文件下載處理正確（Blob類型）

---

## STEP 2: 核心指標與最佳參數展示

**目標**: 實作結果總覽面板和最佳參數卡片

### 2.1 核心指標面板

**新增文件**: `frontend/src/components/results/MetricsPanel.tsx`

**UI結構**:
- 2×3網格佈局（響應式）
- 6個核心指標卡片：
  1. **密度差異（Separation）** - 主指標，大字顯示
  2. **正例平均密度** - 綠色主題
  3. **反例平均密度** - 紅色主題
  4. **統計顯著性（p-value）** - 小於0.05標記為顯著
  5. **效果量（Cohen's d）** - 顏色編碼（>0.8=大，>0.5=中，>0.2=小）
  6. **穩定性（CV）** - 變異係數，越小越好

**卡片設計**:
- 大數字主指標（48px字體）
- 指標名稱（16px，灰色）
- 懸停顯示詳細說明（Tooltip）
- 顏色編碼：
  - 綠色：好的值（高separation、低p-value、低CV）
  - 黃色：中等值
  - 紅色：差的值

**技術要點**:
- 使用Tailwind CSS Grid
- 動態顏色類名（根據值變化）
- shadcn/ui Card組件（如可用）
- 懸停效果（scale-105 transform）

**驗收標準**:
- ✅ 6個指標正確顯示
- ✅ 顏色編碼合理且一致
- ✅ 響應式佈局（手機/平板/桌面）
- ✅ 懸停提示清晰

---

### 2.2 最佳參數卡片

**新增文件**: `frontend/src/components/results/BestParamsCard.tsx`

**UI結構**:
- 結構化表格顯示參數
- 參數類別分組：
  - 數據源：Close / Open / High等
  - 指標類型：EMA / SMA等
  - 策略邏輯：三線排列 / 短長交叉等
  - 參數值：EMA(7, 18, 35)等

**操作按鈕**:
- **複製參數**：複製JSON格式參數到剪貼板
- **套用到新測試**：跳轉到策略配置頁（任務3.3），自動填充參數
- **存為範本**：保存到配置範本庫（可選功能）

**顯示資訊**:
- 試驗編號（如 #89）
- 達成時間（格式化顯示）
- 試驗排名（如 Best of 300 trials）

**技術要點**:
- 使用React Clipboard API（navigator.clipboard.writeText）
- Next.js路由導航（useRouter）
- 參數序列化與反序列化

**驗收標準**:
- ✅ 參數清晰結構化展示
- ✅ 複製功能正常運作
- ✅ 套用功能正確跳轉並填充
- ✅ 時間格式化友好

---

## STEP 3: 密度對比視覺化

**目標**: 實作三種圖表展示正反例信號密度分布差異

### 3.1 統一圖表容器

**新增文件**: `frontend/src/components/results/DensityComparisonChart.tsx`

**功能**:
- 圖表切換選項卡（箱型圖 / 直方圖 / 小提琴圖）
- 統一數據源（positive_densities, negative_densities）
- 圖例顯示（正例=綠色，反例=紅色）

---

### 3.2 箱型圖（Box Plot）

**使用圖表庫**: Recharts或Chart.js

**圖表設計**:
- X軸：正例 vs 反例（兩個組別）
- Y軸：信號密度（0-1）
- 顯示元素：
  - 中位數（粗線）
  - 四分位距（盒子範圍）
  - 異常值（散點）
  - 上下鬚（whiskers）

**數據計算**:
```typescript
// 計算箱型圖統計量
function calculateBoxPlotStats(data: number[]) {
  const sorted = [...data].sort((a, b) => a - b);
  const q1 = percentile(sorted, 25);
  const median = percentile(sorted, 50);
  const q3 = percentile(sorted, 75);
  const iqr = q3 - q1;
  const lowerFence = q1 - 1.5 * iqr;
  const upperFence = q3 + 1.5 * iqr;
  const outliers = sorted.filter(v => v < lowerFence || v > upperFence);
  
  return { q1, median, q3, lowerFence, upperFence, outliers };
}
```

**視覺目的**:
- 直觀看出兩組分布的分離度
- 識別異常值
- 比較中位數差異

---

### 3.3 直方圖（Histogram）

**使用圖表庫**: Recharts

**圖表設計**:
- X軸：信號密度（0-1，分為20個bin）
- Y軸：案例數量
- 雙色堆疊/並列顯示：
  - 正例：綠色半透明
  - 反例：紅色半透明

**數據處理**:
```typescript
// 生成直方圖bins
function createHistogramBins(
  positiveData: number[], 
  negativeData: number[], 
  binCount: number = 20
) {
  const binEdges = linspace(0, 1, binCount + 1);
  
  const positiveCounts = binEdges.slice(0, -1).map((edge, i) => {
    const nextEdge = binEdges[i + 1];
    return positiveData.filter(v => v >= edge && v < nextEdge).length;
  });
  
  const negativeCounts = binEdges.slice(0, -1).map((edge, i) => {
    const nextEdge = binEdges[i + 1];
    return negativeData.filter(v => v >= edge && v < nextEdge).length;
  });
  
  return binEdges.slice(0, -1).map((edge, i) => ({
    bin: `${edge.toFixed(2)}-${binEdges[i+1].toFixed(2)}`,
    positive: positiveCounts[i],
    negative: negativeCounts[i]
  }));
}
```

**視覺目的**:
- 看出分布形狀（正態 / 偏態）
- 觀察重疊程度
- 識別峰值位置

---

### 3.4 小提琴圖（Violin Plot）- 可選

**使用圖表庫**: Plotly.js（Recharts不原生支援）

**圖表設計**:
- 結合箱型圖和核密度估計（KDE）
- X軸：正例 vs 反例
- Y軸：信號密度（0-1）
- 顯示完整分布輪廓

**實作方式**:
- 如Plotly.js可用，實作完整小提琴圖
- 如不可用，標記為進階功能（Phase 4）

**驗收標準**:
- ✅ 三種圖表正確渲染
- ✅ 圖表切換流暢
- ✅ 圖例清晰
- ✅ 顏色一致性（正例綠、反例紅）
- ✅ 圖表互動正常（懸停顯示數值）

---

## STEP 4: 穩定性分析與時間序列圖表

**目標**: 展示策略在不同時期的表現穩定性

### 4.1 時間序列圖

**新增文件**: `frontend/src/components/results/StabilityChart.tsx`

**圖表設計**:
- X軸：時間（月份，如2024-01, 2024-02）
- Y軸：密度差異（separation）
- 折線圖顯示趨勢
- 標記：
  - 最佳月份（綠色星號）
  - 最差月份（紅色三角）
  - 零線（灰色虛線，y=0）

**數據源**:
- 來自`StabilityAnalysis.monthly_separations`
- 按時間排序

**互動功能**:
- 懸停顯示該月詳細數據：
  - 月份
  - Separation值
  - 正例密度
  - 反例密度
  - 案例數量

---

### 4.2 穩定性統計指標表格

**UI結構**:
- 表格顯示關鍵統計指標
- 顏色編碼（好/中/差）

**指標列表**:
1. **平均密度差異**：所有月份separation的平均值
2. **標準差**：separation的標準差
3. **變異係數（CV）**：標準差/平均值，越小越穩定
   - <30%：綠色（穩定）
   - 30-50%：黃色（中等）
   - >50%：紅色（不穩定）
4. **正值比例**：separation > 0的月份占比
   - 如：95%的月份密度差 > 0
5. **最差時期表現**：最差月份的separation值

**驗收標準**:
- ✅ 時間序列圖正確顯示
- ✅ 最佳/最差月份標記清晰
- ✅ 統計表格數據準確
- ✅ 顏色編碼合理

---

## STEP 5: Optuna優化歷程視覺化

**目標**: 展示優化過程的收斂情況和參數影響力

### 5.1 優化收斂曲線

**新增文件**: `frontend/src/components/results/OptimizationHistoryChart.tsx`

**圖表設計**:
- X軸：試驗編號（1-300）
- Y軸：目標值（Separation）
- 雙層顯示：
  1. **折線圖**：當前最佳值演進（藍色粗線）
  2. **散點圖**：所有試驗結果（灰色點，透明度50%）

**數據源**:
- 折線圖：`convergence_history`（累積最佳值）
- 散點圖：`trials_summary`中每個試驗的value

**視覺化目的**:
- 觀察收斂速度（何時達到最佳值）
- 識別探索vs利用階段
- 評估試驗次數是否充足

**增強功能**:
- 點擊散點查看該試驗的詳細參數
- 高亮PRUNED狀態的試驗（紅色X）
- 顯示收斂百分比（如：在第89次試驗達到最佳值，29.7%位置）

---

### 5.2 參數重要性條狀圖

**圖表設計**:
- X軸：參數重要性（0-1）
- Y軸：參數名稱（如ema_short, data_source等）
- 水平條狀圖
- 顏色編碼：
  - 重要性 > 0.5：深藍色
  - 重要性 0.2-0.5：淺藍色
  - 重要性 < 0.2：灰色

**數據源**:
- 來自Optuna的`optuna.importance.get_param_importances()`
- 後端API返回`ParamImportance[]`

**排序**:
- 按重要性降序排列

**視覺化目的**:
- 識別關鍵參數（對目標值影響最大）
- 指導後續優化方向
- 簡化參數空間（忽略低重要性參數）

**驗收標準**:
- ✅ 收斂曲線正確顯示
- ✅ 散點圖渲染流暢（300+點）
- ✅ 參數重要性條狀圖清晰
- ✅ 互動功能正常（點擊、懸停）

---

## STEP 6: 試驗歷史表格與對比工具

**目標**: 提供可排序、可篩選的試驗歷史表格和多策略對比功能

### 6.1 試驗歷史表格

**新增文件**: `frontend/src/components/results/TrialHistoryTable.tsx`

**表格欄位**:
1. 試驗編號（#）
2. 數據源（Data Source）
3. 策略類型（Strategy）
4. EMA參數（Short/Mid/Long）- 合併顯示
5. 密度差異（Separation）
6. p-value
7. Cohen's d
8. 穩定性（CV）
9. 狀態（State）- 完成/剪枝/失敗

**功能**:
- **排序**：點擊列標題排序（升序/降序）
- **篩選**：
  - 下拉選單：只看Top 10 / Top 50 / 全部
  - 狀態篩選：只看完成 / 只看剪枝
- **分頁**：每頁顯示50條，支援分頁導航
- **行選擇**：勾選框，選擇多個試驗進行對比

**高亮規則**:
- 最佳試驗：綠色背景
- 剪枝試驗：灰色文字
- 失敗試驗：紅色文字

**技術要點**:
- 使用React Table或手動實作排序邏輯
- 狀態管理（排序方向、篩選條件、選中行）
- 虛擬滾動（如試驗數 > 500）

---

### 6.2 多策略對比工具

**新增文件**: `frontend/src/components/results/ComparisonTool.tsx`

**觸發方式**:
- 從試驗歷史表格勾選2-5個試驗
- 點擊「對比分析」按鈕

**對比視圖**:

**1. 並列表格**:
- 橫向顯示2-5個試驗
- 縱向對比各項指標：
  - Separation
  - 正例密度
  - 反例密度
  - p-value
  - Cohen's d
  - CV（穩定性）
  - 參數組合

**2. 雷達圖（多維指標對比）**:
- 5個維度：
  1. Separation（歸一化到0-1）
  2. 統計顯著性（1 - p_value）
  3. 效果量（Cohen's d歸一化）
  4. 穩定性（1 - CV）
  5. 正值比例
- 每個策略一條折線（不同顏色）

**技術要點**:
- 使用Recharts Radar Chart
- 數據歸一化（不同量綱統一到0-1）
- 顏色區分（最多5個策略，使用預定義色板）

**驗收標準**:
- ✅ 表格排序、篩選正常
- ✅ 分頁功能正常
- ✅ 行選擇正確
- ✅ 對比工具正確顯示
- ✅ 雷達圖渲染清晰

---

## STEP 7: 報告匯出功能

**目標**: 提供PDF、CSV、PNG匯出功能

### 7.1 後端報告生成服務

**新增文件**: `api/services/report_generator.py`

**功能**:
- PDF生成（使用ReportLab或WeasyPrint）
- 包含內容：
  - 執行摘要（最佳參數、關鍵指標）
  - 密度對比圖表（自動截圖或重新繪製）
  - 穩定性分析圖表
  - 試驗歷史表格（Top 20）
  - 建議和結論

**技術要點**:
- Python圖表庫：matplotlib或plotly
- PDF生成：ReportLab（需安裝）
- 圖表嵌入PDF（base64或臨時文件）

---

### 7.2 前端匯出按鈕

**位置**: 頁面頂部工具列

**按鈕**:
1. **匯出PDF報告**：下載完整PDF
2. **匯出CSV數據**：下載試驗歷史CSV
3. **匯出圖表PNG**：下載當前可見圖表

**實作方式**:
- PDF/CSV：調用後端API，下載Blob
- PNG：使用html2canvas截圖前端圖表

**代碼範例**:
```typescript
// 匯出PDF
async function exportPDF(taskId: string) {
  const blob = await apiClient.exportPdfReport(taskId);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `optimization_report_${taskId}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}

// 匯出PNG（使用html2canvas）
async function exportChartPNG(elementId: string) {
  const element = document.getElementById(elementId);
  const canvas = await html2canvas(element);
  canvas.toBlob(blob => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'chart.png';
    link.click();
    URL.revokeObjectURL(url);
  });
}
```

**驗收標準**:
- ✅ PDF匯出正確（格式完整）
- ✅ CSV匯出正確（所有欄位）
- ✅ PNG匯出清晰（高解析度）
- ✅ 下載流程流暢

---

## STEP 8: 主頁面整合與路由配置

**目標**: 整合所有組件到策略結果頁面

### 8.1 主頁面結構

**新增文件**: `frontend/src/app/strategy-results/page.tsx`

**頁面佈局**:
```tsx
<div className="strategy-results-page">
  {/* 頂部工具列 */}
  <header>
    <h1>策略評估結果</h1>
    <div className="actions">
      <button onClick={exportPDF}>匯出PDF報告</button>
      <button onClick={exportCSV}>匯出CSV</button>
      <button onClick={goBack}>返回配置</button>
    </div>
  </header>
  
  {/* 核心指標面板 */}
  <MetricsPanel data={result.density_analysis} />
  
  {/* 最佳參數卡片 */}
  <BestParamsCard 
    params={result.best_params}
    trialNumber={result.best_trial_number}
  />
  
  {/* 密度對比圖表 */}
  <DensityComparisonChart 
    positiveData={result.density_analysis.positive_densities}
    negativeData={result.density_analysis.negative_densities}
  />
  
  {/* 穩定性分析 */}
  <StabilityChart 
    data={result.stability_analysis}
  />
  
  {/* 優化歷程 */}
  <OptimizationHistoryChart 
    convergenceHistory={result.convergence_history}
    trialsSummary={result.trials_summary}
  />
  
  {/* 參數重要性 */}
  <ParamImportanceChart 
    data={result.param_importances}
  />
  
  {/* 試驗歷史表格 */}
  <TrialHistoryTable 
    trials={result.trials_summary}
  />
  
  {/* 對比工具（條件顯示） */}
  {selectedTrials.length >= 2 && (
    <ComparisonTool trials={selectedTrials} />
  )}
</div>
```

**數據載入**:
- 從URL參數獲取task_id
- 調用`apiClient.getOptimizationResult(taskId)`
- 處理載入中、錯誤狀態

**路由整合**:
- URL格式：`/strategy-results?task_id=xxx`
- 來源：
  1. 任務3.5優化進度頁面（優化完成後跳轉）
  2. 任務3.3策略配置頁（單次測試完成後跳轉）

---

### 8.2 整合任務3.5的高級視覺化

**整合點**: 在策略結果頁面新增標籤頁

**標籤頁結構**:
1. **基礎分析**（預設）- 本任務實作的所有組件
2. **參數空間探索** - 任務3.5的高級視覺化
   - 2D熱力圖
   - 3D散點圖
   - 參數切片視圖
   - Pareto前沿（如為多目標優化）

**實作方式**:
- 使用shadcn/ui Tabs組件或自製標籤頁
- 懶加載3D視覺化（Plotly.js較大）

**驗收標準**:
- ✅ 頁面結構清晰
- ✅ 所有組件正確渲染
- ✅ 數據載入正常
- ✅ 路由跳轉正確
- ✅ 高級視覺化整合流暢

---

## STEP 9: 錯誤處理與邊界情況

**目標**: 處理各種異常情況，提升用戶體驗

### 9.1 無結果狀態

**場景**: 用戶直接訪問頁面但無task_id或task_id無效

**處理**:
- 顯示友好提示：「尚無測試結果，請先進行策略測試」
- 提供快速跳轉按鈕：「前往策略配置」
- 引導文字：說明如何開始一次優化

---

### 9.2 載入中狀態

**場景**: 數據正在從後端加載

**處理**:
- 顯示骨架屏（Skeleton Screen）模擬UI結構
- 進度指示器（Spinner）
- 避免閃爍（最小顯示時間500ms）

**骨架屏結構**:
- 指標卡片：矩形灰色塊
- 圖表：空白區域 + Loading文字
- 表格：行列灰色塊

---

### 9.3 數據異常警告

**場景**: 結果數據存在統計問題

**警告類型**:
1. **統計不顯著**（p-value > 0.05）
   - 顯示黃色警告框
   - 文字：「注意：此策略的統計顯著性不足（p-value = 0.12），結果可能不可靠」

2. **效果量太小**（Cohen's d < 0.2）
   - 顯示黃色警告框
   - 文字：「注意：效果量較小（Cohen's d = 0.15），實際應用效果可能有限」

3. **穩定性差**（CV > 50%）
   - 顯示橙色警告框
   - 文字：「警告：策略穩定性差（CV = 65%），在不同時期表現波動大」

**處理方式**:
- 在核心指標面板上方顯示警告
- 可關閉（X按鈕）
- Icon + 文字 + 建議操作

---

### 9.4 試驗數據缺失

**場景**: 某些試驗狀態為FAIL或PRUNED，導致數據不完整

**處理**:
- 在試驗歷史表格中正確顯示狀態
- 統計摘要中標註：「300次試驗中，280次完成，20次剪枝」
- 對比工具中排除失敗試驗

**驗收標準**:
- ✅ 無結果時顯示友好提示
- ✅ 載入中顯示骨架屏
- ✅ 數據異常顯示警告
- ✅ 缺失數據正確處理

---

## STEP 10: 互動功能與用戶體驗優化

**目標**: 提升互動性和決策效率

### 10.1 圖表互動

**標準互動功能**（所有圖表）:
- **懸停提示**：顯示具體數值
- **圖例切換**：點擊圖例隱藏/顯示數據系列
- **縮放**：拖曳選擇區域縮放（適用於時間序列）
- **重置視圖**：雙擊重置到原始視圖

**實作方式**:
- Recharts原生支援大部分互動
- 自定義Tooltip組件（更詳細的資訊）

---

### 10.2 表格互動

**功能**:
- **點擊列標題排序**：切換升序/降序
- **搜尋框**：快速篩選試驗（按參數值、試驗編號等）
- **全選/取消全選**：批量選擇試驗
- **右鍵選單**：複製參數、查看詳情

**技術要點**:
- 排序狀態管理（useState）
- 搜尋防抖（debounce 300ms）
- 鍵盤快捷鍵（Ctrl+C複製）

---

### 10.3 快速操作

**功能**:
1. **參數複製**：
   - 點擊參數卡片右上角複製圖標
   - 成功後顯示Toast提示：「參數已複製到剪貼板」

2. **一鍵重測**：
   - 點擊「套用此參數到新測試」
   - 跳轉到策略配置頁面（任務3.3）
   - 自動填充最佳參數
   - URL參數傳遞：`/strategy-test?preset=best&task_id=xxx`

3. **快速對比**：
   - 在試驗歷史表格，懸停顯示「加入對比」按鈕
   - 最多選擇5個試驗
   - 浮動按鈕顯示已選數量

**驗收標準**:
- ✅ 圖表互動流暢（60fps）
- ✅ 表格排序、搜尋正常
- ✅ 快速操作功能正常
- ✅ Toast提示清晰友好

---

## 整體驗收標準

### 功能完整性
- ✅ 核心指標正確顯示（6個指標）
- ✅ 最佳參數清晰展示（複製、套用功能正常）
- ✅ 三種密度對比圖表正確渲染
- ✅ 穩定性分析完整（時間序列 + 統計表格）
- ✅ 優化歷程可視化（收斂曲線 + 參數重要性）
- ✅ 試驗歷史表格功能完整（排序、篩選、分頁）
- ✅ 對比工具正常運作（2-5個試驗對比）
- ✅ 報告匯出功能正常（PDF、CSV、PNG）

### 視覺化質量
- ✅ 圖表清晰易讀（字體大小、顏色對比）
- ✅ 顏色編碼一致且符合直覺（綠=好，紅=差）
- ✅ 圖表互動流暢（懸停、縮放、重置）
- ✅ 響應式設計（手機/平板/桌面）

### 用戶體驗
- ✅ 資訊層次分明（先總覽再細節）
- ✅ 關鍵結論突出顯示（最佳參數、警告資訊）
- ✅ 操作流程順暢（複製參數 → 套用 → 重測）
- ✅ 錯誤提示友好（無結果、載入中、數據異常）
- ✅ 載入速度快（< 2秒首次渲染）

### 數據正確性
- ✅ 統計指標計算準確（separation、p-value、Cohen's d、CV）
- ✅ 圖表數據與後端一致
- ✅ 試驗歷史完整無遺漏
- ✅ 匯出數據完整準確

### 代碼質量
- ✅ 組件職責單一（每個組件專注一個功能）
- ✅ 類型安全（無any類型）
- ✅ 錯誤處理完整（try-catch + 友好提示）
- ✅ 性能優化（虛擬滾動、懶加載、防抖）
- ✅ 可維護性高（清晰註釋、合理命名）

---

## 依賴關係

### 前置需求
- **任務3.2：信號密度分析系統**（必須完成）
  - 需要：SignalDensityResult數據結構
  - 整合點：核心指標面板、密度對比圖表

- **任務3.5：Optuna參數優化系統**（必須完成）
  - 需要：OptimizationResult完整數據
  - 整合點：所有視覺化組件
  - 需要：參數重要性、收斂歷史、試驗摘要

### 並行開發
- **任務3.3：策略選擇UI**（可同時開發）
  - 整合點：套用參數功能（跳轉並自動填充）

### 後續任務
- **任務4.x：Pattern發現分析**（依賴本任務）
  - 可復用結果展示UI的設計模式
  - 可復用圖表組件（箱型圖、雷達圖等）

---

## 風險與注意事項

### 性能風險
- **風險**：大量試驗（1000+）導致表格渲染卡頓
- **緩解**：
  - 虛擬滾動（react-window或react-virtualized）
  - 分頁限制（每頁最多100條）
  - 懶加載圖表（標籤頁切換時才載入）

### 圖表庫選擇風險
- **風險**：Recharts不支援某些高級圖表（如小提琴圖）
- **緩解**：
  - 優先使用Recharts（已在項目中使用）
  - 需要時引入Plotly.js（僅用於特定圖表）
  - 標記高級圖表為可選功能

### 數據完整性風險
- **風險**：後端API返回數據缺失或格式不一致
- **緩解**：
  - 完整的TypeScript類型檢查
  - 運行時數據驗證（Zod或手動檢查）
  - 降級處理（部分數據缺失時顯示可用部分）

### 瀏覽器兼容性風險
- **風險**：Canvas/WebGL渲染在舊瀏覽器不支援
- **緩解**：
  - 檢測瀏覽器能力（html2canvas, Plotly.js）
  - 降級到靜態圖表（不支援互動）
  - 提示用戶升級瀏覽器

---

## 開發順序建議（4-5天）

**第1天**：STEP 1-2（類型定義 + 核心指標）
- 上午：TypeScript類型定義 + API整合
- 下午：核心指標面板 + 最佳參數卡片

**第2天**：STEP 3（密度對比視覺化）
- 上午：箱型圖 + 直方圖實作
- 下午：圖表容器 + 切換邏輯 + 小提琴圖（可選）

**第3天**：STEP 4-5（穩定性 + 優化歷程）
- 上午：穩定性分析（時間序列圖 + 統計表格）
- 下午：優化歷程（收斂曲線 + 參數重要性）

**第4天**：STEP 6-7（表格 + 匯出）
- 上午：試驗歷史表格（排序、篩選、分頁）
- 下午：對比工具 + 報告匯出功能

**第5天**：STEP 8-10（整合 + 優化）
- 上午：主頁面整合 + 路由配置 + 任務3.5視覺化整合
- 下午：錯誤處理 + 互動優化 + 驗收測試

---

## 成功標準

任務3.6完成的標誌：
- ✅ 策略結果頁面完整可用
- ✅ 所有核心指標正確顯示
- ✅ 6種圖表正確渲染（箱型、直方、時間序列、收斂、參數重要性、雷達）
- ✅ 試驗歷史表格功能完整
- ✅ 對比工具正常運作
- ✅ 報告匯出功能正常（PDF、CSV、PNG）
- ✅ 整合任務3.5的高級視覺化
- ✅ 用戶體驗流暢（載入快、互動順暢）
- ✅ 錯誤處理完整（無結果、載入中、數據異常）
- ✅ 響應式設計正常
- ✅ 文檔更新（STATUS.md標記任務3.6完成）

---

## 參考文檔

- **信號密度分析**：任務3.2計劃 - 數據結構定義
- **Optuna優化系統**：任務3.5計劃 - 優化結果數據結構
- **策略配置UI**：任務3.3計劃 - 參數應用整合點
- **Recharts官方文檔**：https://recharts.org/
- **Plotly.js官方文檔**：https://plotly.com/javascript/
- **React Table文檔**：https://tanstack.com/table/v8
- **html2canvas文檔**：https://html2canvas.hertzen.com/
- **開發規範**：`.claude/GUIDELINES.md` - Ultra Think三步驟
- **技術架構**：`docs/ARCHITECTURE.md` - 前端架構設計

---

## 未來擴展功能（Phase 4+）

### 互動式探索
- 圖表聯動（點擊收斂曲線某點，高亮該試驗在其他圖表中的位置）
- 參數範圍篩選（拖動滑桿篩選特定參數範圍的試驗）
- 實時對比模式（選擇試驗即時更新對比視圖，無需點擊按鈕）

### 智能建議
- 根據結果自動生成策略建議（如：「建議增加試驗次數以探索更大參數空間」）
- 異常試驗自動分析（識別為何某些試驗失敗或被剪枝）
- 參數優化建議（如：「ema_short對結果影響最大，建議縮小搜索範圍」）

### 協作功能
- 結果分享（生成分享連結）
- 註解功能（在圖表上添加備註）
- 版本對比（對比不同時間的優化結果）

### 高級匯出
- 交互式HTML報告（可在瀏覽器中打開的完整報告）
- PowerPoint簡報生成（自動生成匯報材料）
- Excel詳細數據表（多Sheet結構化數據）

---

*文檔版本: 1.0*  
*創建日期: 2025-10-31*  
*維護者: AI Code Agent*
