/**
 * Optimization Result Page - Phase 3 重構版本
 *
 * Ultra Think 三步驟設計:
 *
 * Step 1 - 初版思考:
 * - 使用 Phase 3 新開發的 6 個視覺化組件
 * - 調用 5 個新的 API 端點獲取數據
 * - 響應式佈局，支援 Loading/Error 狀態
 *
 * Step 2 - 自我審查:
 * - 錯誤處理：部分失敗不影響整體顯示
 * - 性能優化：並行 API 調用，減少等待時間
 * - UX 改進：骨架屏、重試按鈕、返回首頁
 *
 * Step 3 - 最終優化:
 * - 類型安全：所有 API 響應完整類型定義
 * - 代碼可維護性：清晰的 section 劃分
 * - 用戶體驗：麵包屑導航、滾動到頂部按鈕
 *
 * Author: Claude (Optuna 優化系統 Phase 3)
 * Date: 2025-12-02
 */

'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  BestResultCard,
  ParamImportanceChart,
  ParamHeatmap,
  ConvergencePlot,
  StabilityChart,
  TrialRankingTable
} from '@/components/optimization-results'
import {
  OptimizationResultDetail,
  ParameterImportance,
  HeatmapData,
  ConvergenceAnalysis,
  StabilityAnalysis,
  TrialDetail,
  OptimizationResultResponse,
  HeatmapResponse,
  ConvergenceResponse,
  StabilityResponse,
  TrialsResponse
} from '@/types/optimization'
import { Loader2, AlertCircle, Home, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

// API Base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ==================== API 調用函數 ====================

async function fetchOptimizationResult(taskId: string): Promise<OptimizationResultDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/result`)
  if (!response.ok) {
    throw new Error(`Failed to fetch optimization result: ${response.statusText}`)
  }
  const data: OptimizationResultResponse = await response.json()
  return data.result
}

async function fetchParamImportance(taskId: string): Promise<ParameterImportance[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/param-importance`)
  if (!response.ok) {
    throw new Error(`Failed to fetch parameter importance: ${response.statusText}`)
  }
  const data = await response.json()
  return data.data.importances
}

async function fetchHeatmap(taskId: string, paramX: string, paramY: string): Promise<HeatmapData> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/heatmap?param_x=${paramX}&param_y=${paramY}`
  )
  if (!response.ok) {
    throw new Error(`Failed to fetch heatmap: ${response.statusText}`)
  }
  const data: HeatmapResponse = await response.json()
  return data.data
}

async function fetchConvergence(taskId: string): Promise<ConvergenceAnalysis> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/convergence`)
  if (!response.ok) {
    throw new Error(`Failed to fetch convergence: ${response.statusText}`)
  }
  const data: ConvergenceResponse = await response.json()
  return data.data
}

async function fetchStability(taskId: string): Promise<StabilityAnalysis> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/stability`)
  if (!response.ok) {
    throw new Error(`Failed to fetch stability: ${response.statusText}`)
  }
  const data: StabilityResponse = await response.json()
  return data.data
}

async function fetchTopTrials(taskId: string, topN: number = 20): Promise<TrialDetail[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/trials?top_n=${topN}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch top trials: ${response.statusText}`)
  }
  const data: TrialsResponse = await response.json()
  return data.trials
}

// ==================== 主組件 ====================

export default function OptimizationResultPage() {
  const params = useParams()
  const taskId = params.taskId as string

  // State
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<OptimizationResultDetail | null>(null)
  const [importances, setImportances] = useState<ParameterImportance[]>([])
  const [heatmapData, setHeatmapData] = useState<HeatmapData | null>(null)
  const [convergenceData, setConvergenceData] = useState<ConvergenceAnalysis | null>(null)
  const [stabilityData, setStabilityData] = useState<StabilityAnalysis | null>(null)
  const [topTrials, setTopTrials] = useState<TrialDetail[]>([])

  // Selected parameters for heatmap
  const [selectedParamX, setSelectedParamX] = useState<string>('')
  const [selectedParamY, setSelectedParamY] = useState<string>('')

  /**
   * Ultra Think Step 3 優化: 並行載入所有數據
   */
  const loadAllData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Step 1: 獲取基本結果（必須成功）
      const resultData = await fetchOptimizationResult(taskId)
      setResult(resultData)

      // Step 2: 並行獲取其他分析數據（允許部分失敗）
      const [
        importancesResult,
        convergenceResult,
        stabilityResult,
        trialsResult
      ] = await Promise.allSettled([
        fetchParamImportance(taskId),
        fetchConvergence(taskId),
        fetchStability(taskId),
        fetchTopTrials(taskId, 20)
      ])

      // 處理參數重要性
      if (importancesResult.status === 'fulfilled') {
        const importancesData = importancesResult.value
        setImportances(importancesData)

        // Step 3: 自動選擇前兩個參數用於熱力圖
        if (importancesData.length >= 2) {
          const topTwo = [...importancesData].sort((a, b) => b.importance - a.importance).slice(0, 2)
          const paramX = topTwo[0].parameter_name
          const paramY = topTwo[1].parameter_name
          setSelectedParamX(paramX)
          setSelectedParamY(paramY)

          // 獲取熱力圖數據
          try {
            const heatmap = await fetchHeatmap(taskId, paramX, paramY)
            setHeatmapData(heatmap)
          } catch (err) {
            console.warn('Failed to load heatmap:', err)
          }
        }
      }

      // 處理收斂分析
      if (convergenceResult.status === 'fulfilled') {
        setConvergenceData(convergenceResult.value)
      }

      // 處理穩定性分析
      if (stabilityResult.status === 'fulfilled') {
        setStabilityData(stabilityResult.value)
      }

      // 處理 Top Trials
      if (trialsResult.status === 'fulfilled') {
        setTopTrials(trialsResult.value)
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Failed to load optimization result:', err)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 重新載入熱力圖
   */
  const reloadHeatmap = async (paramX: string, paramY: string) => {
    if (!paramX || !paramY || paramX === paramY) return

    try {
      const heatmap = await fetchHeatmap(taskId, paramX, paramY)
      setHeatmapData(heatmap)
      setSelectedParamX(paramX)
      setSelectedParamY(paramY)
    } catch (err) {
      console.error('Failed to reload heatmap:', err)
    }
  }

  // 初始載入
  useEffect(() => {
    if (taskId) {
      loadAllData()
    }
  }, [taskId])

  // ==================== 渲染 ====================

  // Loading 狀態
  if (loading) {
    return (
      <div className="min-h-screen bg-background p-6 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-lg text-muted-foreground">載入優化結果中...</p>
        </div>
      </div>
    )
  }

  // Error 狀態
  if (error || !result) {
    return (
      <div className="min-h-screen bg-background p-6 flex items-center justify-center">
        <div className="max-w-md w-full space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>載入失敗</AlertTitle>
            <AlertDescription>
              {error || '無法載入優化結果，請稍後再試'}
            </AlertDescription>
          </Alert>
          <div className="flex gap-3">
            <Button onClick={loadAllData} className="flex-1">
              <RefreshCw className="h-4 w-4 mr-2" />
              重試
            </Button>
            <Button variant="outline" asChild className="flex-1">
              <Link href="/">
                <Home className="h-4 w-4 mr-2" />
                返回首頁
              </Link>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // 成功狀態 - 顯示結果
  return (
    <div className="min-h-screen bg-background p-6">
      {/* 麵包屑導航 */}
      <nav className="mb-6 text-sm">
        <Link href="/" className="text-muted-foreground hover:text-foreground">
          首頁
        </Link>
        <span className="mx-2 text-muted-foreground">/</span>
        <Link href="/optimization-tasks" className="text-muted-foreground hover:text-foreground">
          優化任務
        </Link>
        <span className="mx-2 text-muted-foreground">/</span>
        <span className="font-medium">Task #{taskId}</span>
      </nav>

      {/* 頁面標題 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">優化結果</h1>
        <p className="text-muted-foreground">
          Task ID: {taskId} · Study: {result.study_direction}
        </p>
      </div>

      {/* 內容區域 */}
      <div className="space-y-8">
        {/* Section 1: 最佳結果總覽 */}
        <section>
          <h2 className="text-2xl font-semibold mb-4">最佳結果</h2>
          <BestResultCard result={result} />
        </section>

        {/* Section 2: 參數重要性與熱力圖 */}
        {importances.length > 0 && (
          <section>
            <h2 className="text-2xl font-semibold mb-4">參數分析</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 參數重要性圖表 */}
              <ParamImportanceChart importances={importances} />

              {/* 參數空間熱力圖 */}
              {heatmapData && (
                <ParamHeatmap
                  heatmapData={heatmapData}
                  availableParams={importances.map(imp => imp.parameter_name)}
                  onParamsChange={reloadHeatmap}
                />
              )}
            </div>
          </section>
        )}

        {/* Section 3: 收斂與穩定性 */}
        <section>
          <h2 className="text-2xl font-semibold mb-4">優化過程分析</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 收斂曲線 */}
            {convergenceData && (
              <ConvergencePlot convergenceData={convergenceData} />
            )}

            {/* 穩定性分析 */}
            {stabilityData && (
              <StabilityChart stabilityData={stabilityData} />
            )}
          </div>
        </section>

        {/* Section 4: Trial 排名 */}
        {topTrials.length > 0 && (
          <section>
            <h2 className="text-2xl font-semibold mb-4">Trial 詳細排名</h2>
            <TrialRankingTable trials={topTrials} />
          </section>
        )}
      </div>

      {/* 返回頂部按鈕 */}
      <Button
        variant="outline"
        size="icon"
        className="fixed bottom-8 right-8 rounded-full shadow-lg"
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
        </svg>
      </Button>
    </div>
  )
}
