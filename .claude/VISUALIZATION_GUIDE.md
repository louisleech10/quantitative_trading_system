# 優化視覺化指南 (Optimization Visualization Guide)

## 概述

本文檔提供如何使用Phase 3.5的分析API創建前端視覺化組件的指南。所有視覺化都基於3個分析API端點。

## API端點總覽

### 1. 參數重要性分析
```
GET /api/v1/optimization/tasks/{task_id}/analysis/importance
```
- **用途**: 計算每個參數對目標函數的影響程度
- **評估器**: `fanova`(推薦) 或 `mean_decrease_impurity`
- **返回**: 參數重要性列表（降序排序）

### 2. 優化歷史曲線
```
GET /api/v1/optimization/tasks/{task_id}/analysis/history
```
- **用途**: 獲取每次試驗的值和累計最佳值
- **返回**: 試驗歷史點列表（包含參數、值、狀態）

### 3. 參數空間數據
```
GET /api/v1/optimization/tasks/{task_id}/analysis/param-space
```
- **用途**: 獲取參數組合和對應的目標值
- **返回**: 參數空間點列表（用於散點圖）

---

## 視覺化組件實作指南

### 1️⃣ 參數重要性柱狀圖 (Parameter Importance Bar Chart)

**推薦庫**: Recharts / Chart.js

**API調用**:
```typescript
import { ImportanceAnalysisResponse } from '@/types/optimization'

async function fetchParameterImportance(taskId: string): Promise<ImportanceAnalysisResponse> {
  const response = await fetch(
    `http://localhost:8000/api/v1/optimization/tasks/${taskId}/analysis/importance?evaluator=fanova`
  )
  return response.json()
}
```

**數據結構**:
```typescript
{
  "success": true,
  "task_id": "xxx",
  "study_name": "momentum_opt_001",
  "n_trials": 100,
  "importances": [
    {"parameter_name": "threshold", "importance": 0.456, "rank": 1},
    {"parameter_name": "min_candles", "importance": 0.234, "rank": 2},
    {"parameter_name": "smoothing_window", "importance": 0.189, "rank": 3}
  ],
  "evaluator": "fanova"
}
```

**Recharts示例**:
```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function ParameterImportanceChart({ taskId }: { taskId: string }) {
  const [data, setData] = useState<ImportanceAnalysisResponse | null>(null)

  useEffect(() => {
    fetchParameterImportance(taskId).then(setData)
  }, [taskId])

  if (!data) return <div>Loading...</div>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data.importances}>
        <XAxis dataKey="parameter_name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="importance" fill="#8884d8" />
      </BarChart>
    </ResponsiveContainer>
  )
}
```

---

### 2️⃣ 優化歷史曲線圖 (Optimization History Line Chart)

**推薦庫**: Recharts / Chart.js

**API調用**:
```typescript
import { OptimizationHistoryResponse } from '@/types/optimization'

async function fetchOptimizationHistory(taskId: string): Promise<OptimizationHistoryResponse> {
  const response = await fetch(
    `http://localhost:8000/api/v1/optimization/tasks/${taskId}/analysis/history`
  )
  return response.json()
}
```

**數據結構**:
```typescript
{
  "success": true,
  "task_id": "xxx",
  "study_name": "momentum_opt_001",
  "history": [
    {
      "trial_number": 0,
      "value": 0.234,
      "best_value_so_far": 0.234,
      "datetime": "2025-11-02T10:00:00",
      "params": {"threshold": 0.5, "min_candles": 10},
      "state": "COMPLETE"
    },
    // ... more points
  ],
  "total_trials": 100
}
```

**Recharts示例** (雙折線: 當前值 + 最佳值):
```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'

function OptimizationHistoryChart({ taskId }: { taskId: string }) {
  const [data, setData] = useState<OptimizationHistoryResponse | null>(null)

  useEffect(() => {
    fetchOptimizationHistory(taskId).then(setData)
  }, [taskId])

  if (!data) return <div>Loading...</div>

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={data.history}>
        <XAxis dataKey="trial_number" label={{ value: 'Trial Number', position: 'insideBottom', offset: -5 }} />
        <YAxis label={{ value: 'Objective Value', angle: -90, position: 'insideLeft' }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="value" stroke="#82ca9d" name="Trial Value" dot={false} />
        <Line type="monotone" dataKey="best_value_so_far" stroke="#8884d8" name="Best Value" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}
```

---

### 3️⃣ 參數空間散點圖 (Parameter Space Scatter Plot)

**推薦庫**: Recharts (2D) / Plotly.js (3D，進階)

**API調用**:
```typescript
import { ParamSpaceResponse } from '@/types/optimization'

async function fetchParamSpace(taskId: string): Promise<ParamSpaceResponse> {
  const response = await fetch(
    `http://localhost:8000/api/v1/optimization/tasks/${taskId}/analysis/param-space`
  )
  return response.json()
}
```

**數據結構**:
```typescript
{
  "success": true,
  "task_id": "xxx",
  "study_name": "momentum_opt_001",
  "points": [
    {
      "trial_number": 0,
      "value": 0.234,
      "params": {"threshold": 0.5, "min_candles": 10},
      "state": "COMPLETE"
    },
    // ... more points
  ],
  "param_names": ["threshold", "min_candles", "smoothing_window"],
  "total_trials": 100
}
```

**Recharts示例** (2D: threshold vs value):
```tsx
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function ParamSpaceScatter({ taskId }: { taskId: string }) {
  const [data, setData] = useState<ParamSpaceResponse | null>(null)

  useEffect(() => {
    fetchParamSpace(taskId).then(setData)
  }, [taskId])

  if (!data) return <div>Loading...</div>

  // 轉換數據格式（提取threshold參數作為X軸）
  const scatterData = data.points.map(point => ({
    x: point.params.threshold,
    y: point.value,
    trial: point.trial_number
  }))

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart>
        <XAxis dataKey="x" name="Threshold" label={{ value: 'Threshold', position: 'insideBottom', offset: -5 }} />
        <YAxis dataKey="y" name="Objective Value" label={{ value: 'Objective Value', angle: -90, position: 'insideLeft' }} />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} />
        <Scatter name="Trials" data={scatterData} fill="#8884d8" />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
```

**Plotly.js進階示例** (3D: threshold vs min_candles vs value):
```tsx
import Plot from 'react-plotly.js'

function ParamSpace3D({ taskId }: { taskId: string }) {
  const [data, setData] = useState<ParamSpaceResponse | null>(null)

  useEffect(() => {
    fetchParamSpace(taskId).then(setData)
  }, [taskId])

  if (!data) return <div>Loading...</div>

  // 提取3個維度
  const x = data.points.map(p => p.params.threshold)
  const y = data.points.map(p => p.params.min_candles)
  const z = data.points.map(p => p.value)
  const text = data.points.map(p => `Trial ${p.trial_number}`)

  return (
    <Plot
      data={[
        {
          x,
          y,
          z,
          mode: 'markers',
          type: 'scatter3d',
          text,
          marker: {
            size: 5,
            color: z,
            colorscale: 'Viridis',
            showscale: true,
            colorbar: { title: 'Objective Value' }
          }
        }
      ]}
      layout={{
        width: 800,
        height: 600,
        scene: {
          xaxis: { title: 'Threshold' },
          yaxis: { title: 'Min Candles' },
          zaxis: { title: 'Objective Value' }
        }
      }}
    />
  )
}
```

---

## 完整示例頁面

### 優化分析儀表板 (Optimization Analysis Dashboard)

```tsx
import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import ParameterImportanceChart from './ParameterImportanceChart'
import OptimizationHistoryChart from './OptimizationHistoryChart'
import ParamSpaceScatter from './ParamSpaceScatter'

function OptimizationAnalysisDashboard({ taskId }: { taskId: string }) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Optimization Analysis</h1>

      <Tabs defaultValue="history">
        <TabsList>
          <TabsTrigger value="history">Optimization History</TabsTrigger>
          <TabsTrigger value="importance">Parameter Importance</TabsTrigger>
          <TabsTrigger value="space">Parameter Space</TabsTrigger>
        </TabsList>

        <TabsContent value="history" className="mt-6">
          <OptimizationHistoryChart taskId={taskId} />
        </TabsContent>

        <TabsContent value="importance" className="mt-6">
          <ParameterImportanceChart taskId={taskId} />
        </TabsContent>

        <TabsContent value="space" className="mt-6">
          <ParamSpaceScatter taskId={taskId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default OptimizationAnalysisDashboard
```

---

## 安裝依賴

### Recharts（推薦，輕量級）
```bash
npm install recharts
```

### Plotly.js（進階3D視覺化）
```bash
npm install react-plotly.js plotly.js
npm install --save-dev @types/plotly.js
```

---

## API錯誤處理

所有API調用應包含錯誤處理:

```typescript
async function fetchWithErrorHandling<T>(url: string): Promise<T> {
  try {
    const response = await fetch(url)

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

// 使用
try {
  const data = await fetchWithErrorHandling<ImportanceAnalysisResponse>(
    `http://localhost:8000/api/v1/optimization/tasks/${taskId}/analysis/importance`
  )
  setImportanceData(data)
} catch (error) {
  setError(error.message)
}
```

---

## 常見問題 (FAQ)

### Q1: 如何過濾特定狀態的試驗？
A: 在前端過濾 `history` 或 `points` 數據:
```typescript
const completedTrials = data.history.filter(point => point.state === 'COMPLETE')
```

### Q2: 如何只顯示最近50次試驗？
A: 使用 `n_trials` 查詢參數:
```
GET /api/v1/optimization/tasks/{task_id}/analysis/history?n_trials=50
```

### Q3: FANOVA失敗怎麼辦？
A: API會自動回退到 `mean_decrease_impurity` 評估器，檢查 `response.evaluator` 確認使用的評估器。

### Q4: 如何繪製多個參數的重要性比較？
A: 使用堆疊柱狀圖（Stacked Bar Chart）或分組柱狀圖（Grouped Bar Chart）。

---

## 性能優化建議

1. **數據緩存**: 使用 `useSWR` 或 `react-query` 緩存API響應
   ```tsx
   import useSWR from 'swr'

   const { data, error } = useSWR(
     `/api/v1/optimization/tasks/${taskId}/analysis/importance`,
     fetcher
   )
   ```

2. **懶加載**: 僅在用戶切換到對應Tab時加載數據
   ```tsx
   <TabsContent value="importance">
     {activeTab === 'importance' && <ParameterImportanceChart taskId={taskId} />}
   </TabsContent>
   ```

3. **虛擬化**: 對於大量試驗（>1000），使用虛擬化列表（react-window）

---

## 總結

| 視覺化類型 | API端點 | 推薦庫 | 難度 |
|-----------|---------|--------|------|
| 參數重要性柱狀圖 | `/analysis/importance` | Recharts | ⭐ |
| 優化歷史曲線 | `/analysis/history` | Recharts | ⭐ |
| 2D參數空間散點圖 | `/analysis/param-space` | Recharts | ⭐⭐ |
| 3D參數空間散點圖 | `/analysis/param-space` | Plotly.js | ⭐⭐⭐ |

所有視覺化組件都基於**3個分析API端點**，無需額外後端開發。

**開發建議**: 從簡單的Recharts 2D圖表開始，根據需求逐步添加進階功能（3D、交互、動畫）。
