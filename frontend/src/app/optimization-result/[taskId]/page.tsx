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

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  BestResultCard,
  ParamImportanceChart,
  ParamHeatmap,
  ConvergencePlot,
  StabilityChart,
  TrialRankingTable,
  TrialStatsCard
} from '@/components/optimization-results'
import {
  OptimizationResultDetail,
  ParameterImportance,
  HeatmapData,
  ConvergenceAnalysis,
  StabilityAnalysis,
  TrialDetail,
  TrialStats,
  OptimizationResultResponse,
  HeatmapResponse,
  ConvergenceResponse,
  StabilityResponse,
  TrialsResponse
} from '@/types/optimization'
import { Loader2, AlertCircle, Home, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import ExportButton from '@/components/common/ExportButton'

// API Base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface TaskProgress {
  completed_trials?: number
  total_trials?: number
  best_value?: number
}

// ==================== API 調用函數 ====================

async function fetchOptimizationResult(taskId: string): Promise<OptimizationResultResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/result`)
  if (!response.ok) {
    throw new Error(`Failed to fetch optimization result: ${response.statusText}`)
  }
  const data: OptimizationResultResponse = await response.json()
  return data
}

async function fetchParamImportance(taskId: string): Promise<ParameterImportance[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/importance`)
  if (!response.ok) {
    const errorText = await response.text()
    console.error('Parameter importance API error:', response.status, errorText)
    throw new Error(`Failed to fetch parameter importance: ${response.statusText}`)
  }
  const data = await response.json()
  // API 回傳結構: { success, task_id, study_name, n_trials, importances, evaluator }
  // importances 在根層級，不是 data.importances
  return data.importances || []
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
  // 使用按案例月份的穩定性分析（而非Trial執行時間）
  // 這是真正的策略穩定性分析，測量最佳參數在不同月份案例上的表現
  const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/analysis/stability-by-case-month`)
  if (!response.ok) {
    throw new Error(`Failed to fetch stability: ${response.statusText}`)
  }
  const data: StabilityResponse = await response.json()
  return data.data
}

async function fetchTopTrials(taskId: string, topN: number = 20, includeAllStates: boolean = false): Promise<TrialDetail[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/trials?top_n=${topN}&include_all_states=${includeAllStates}`
  )
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
  const [trialStats, setTrialStats] = useState<TrialStats | null>(null)
  const [importances, setImportances] = useState<ParameterImportance[]>([])
  const [importanceError, setImportanceError] = useState<string | null>(null)  // 追蹤參數重要性載入錯誤
  const [heatmapData, setHeatmapData] = useState<HeatmapData | null>(null)
  const [convergenceData, setConvergenceData] = useState<ConvergenceAnalysis | null>(null)
  const [stabilityData, setStabilityData] = useState<StabilityAnalysis | null>(null)
  const [topTrials, setTopTrials] = useState<TrialDetail[]>([])

  // 實時進度狀態
  const [taskStatus, setTaskStatus] = useState<string>('unknown')
  const [progress, setProgress] = useState<TaskProgress | null>(null)

  /**
   * Ultra Think Step 3 優化: 並行載入所有數據
   */
  const loadAllData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Step 0: 先檢查任務狀態
      const statusResponse = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}`)
      if (!statusResponse.ok) {
        throw new Error('無法獲取任務狀態')
      }
      const statusData = await statusResponse.json()
      const taskStatus = statusData.data?.status || 'unknown'

      // 如果任務失敗，顯示錯誤
      if (taskStatus === 'failed') {
        const errorMsg = statusData.data?.error_message || '優化任務失敗'
        throw new Error(`任務失敗: ${errorMsg}`)
      }

      // 如果任務還在運行，等待完成
      if (taskStatus === 'running' || taskStatus === 'pending') {
        throw new Error('任務仍在執行中，請稍後重試')
      }

      // 如果任務未完成，不能獲取結果
      if (taskStatus !== 'completed') {
        throw new Error(`任務狀態異常: ${taskStatus}`)
      }

      // Step 1: 獲取基本結果（必須成功）
      const resultResponse = await fetchOptimizationResult(taskId)
      setResult(resultResponse.result)
      if (resultResponse.trial_stats) {
        setTrialStats(resultResponse.trial_stats)
      }

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
        fetchTopTrials(taskId, -1, true) // 獲取所有 trials，包含所有狀態
      ])

      // 處理參數重要性
      setImportanceError(null)  // 重置錯誤狀態
      if (importancesResult.status === 'fulfilled') {
        const importancesData = importancesResult.value
        setImportances(importancesData)

        // Step 3: 自動選擇前兩個參數用於熱力圖
        if (importancesData.length >= 2) {
          const topTwo = [...importancesData].sort((a, b) => b.importance - a.importance).slice(0, 2)
          const paramX = topTwo[0].parameter_name
          const paramY = topTwo[1].parameter_name

          // 獲取熱力圖數據
          try {
            const heatmap = await fetchHeatmap(taskId, paramX, paramY)
            setHeatmapData(heatmap)
          } catch (err) {
            console.warn('Failed to load heatmap:', err)
          }
        }
      } else {
        // 參數重要性載入失敗，記錄錯誤訊息
        const reason = importancesResult.reason as Error
        const errorMsg = reason?.message || '未知錯誤'
        console.warn('Failed to load parameter importance:', errorMsg)
        
        // 判斷是否為試驗次數不足的錯誤
        if (errorMsg.includes('at least 2') || errorMsg.includes('2 completed trials')) {
          setImportanceError('需要至少 2 次完成的試驗才能計算參數重要性')
        } else {
          setImportanceError(`無法載入參數重要性: ${errorMsg}`)
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
  }, [taskId])

  /**
   * 重新載入熱力圖
   */
  const reloadHeatmap = async (paramX: string, paramY: string) => {
    if (!paramX || !paramY || paramX === paramY) return

    try {
      const heatmap = await fetchHeatmap(taskId, paramX, paramY)
      setHeatmapData(heatmap)
    } catch (err) {
      console.error('Failed to reload heatmap:', err)
    }
  }

  /**
   * 輪詢任務狀態（用於實時進度顯示）
   */
  useEffect(() => {
    if (!taskId) return

    const pollStatus = async () => {
      try {
        const statusResponse = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}`)
        if (statusResponse.ok) {
          const statusData = await statusResponse.json()
          const status = statusData.data?.status || 'unknown'
          const progressData = statusData.data?.progress || null

          setTaskStatus(status)
          setProgress(progressData)

          // 如果任務完成，載入結果
          if (status === 'completed') {
            loadAllData()
          }
        }
      } catch (err) {
        console.error('Failed to poll task status:', err)
      }
    }

    // 立即執行一次
    pollStatus()

    // 如果任務還在執行，每 3 秒輪詢一次
    const intervalId = setInterval(() => {
      if (taskStatus === 'running' || taskStatus === 'pending' || taskStatus === 'unknown') {
        pollStatus()
      } else {
        clearInterval(intervalId)
      }
    }, 3000)

    return () => clearInterval(intervalId)
  }, [loadAllData, taskId, taskStatus])

  // ==================== 渲染 ====================

  // 進行中狀態 - 顯示實時進度
  if (taskStatus === 'running' || taskStatus === 'pending') {
    const completedTrials = progress?.completed_trials || 0
    const totalTrials = progress?.total_trials || 0
    const percentage = totalTrials > 0 ? (completedTrials / totalTrials * 100) : 0
    const bestValue = progress?.best_value

    return (
      <div className="min-h-screen bg-background p-6">
        <div className="max-w-2xl mx-auto">
          {/* 頁面標題 */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold mb-2">優化進行中</h1>
            <p className="text-muted-foreground">Task ID: {taskId}</p>
          </div>

          {/* 進度卡片 */}
          <div className="bg-card border rounded-lg p-6 space-y-6">
            {/* 進度條 */}
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium">優化進度</span>
                <span className="text-sm text-muted-foreground">
                  {completedTrials} / {totalTrials} trials ({percentage.toFixed(1)}%)
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full transition-all duration-500 ease-out"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>

            {/* 當前最佳值 */}
            {bestValue !== null && bestValue !== undefined && (
              <div className="flex items-center justify-between p-4 bg-muted rounded-md">
                <span className="text-sm font-medium">當前最佳值</span>
                <span className="text-lg font-bold text-emerald-300">{bestValue.toFixed(4)}</span>
              </div>
            )}

            {/* 狀態指示 */}
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>優化正在進行中，頁面會自動更新...</span>
            </div>

            {/* 提示信息 */}
            <div className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
              💡 優化可能需要幾分鐘到幾十分鐘，具體取決於 trial 數量和案例複雜度。
              完成後會自動顯示結果，無需手動刷新。
            </div>
          </div>

          {/* 返回按鈕 */}
          <div className="mt-6 text-center">
            <Button variant="outline" asChild>
              <Link href="/strategy-test">
                返回策略測試
              </Link>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // Loading 狀態
  if (loading && taskStatus === 'completed') {
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
    const isTaskRunning = error?.includes('仍在執行中')
    const isTaskFailed = error?.includes('任務失敗')

    return (
      <div className="min-h-screen bg-background p-6 flex items-center justify-center">
        <div className="max-w-md w-full space-y-4">
          <Alert variant={isTaskRunning ? "default" : "destructive"}>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>{isTaskRunning ? '任務進行中' : '載入失敗'}</AlertTitle>
            <AlertDescription>
              {error || '無法載入優化結果，請稍後再試'}
            </AlertDescription>
          </Alert>

          {isTaskRunning && (
            <div className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
              💡 提示：優化任務通常需要幾分鐘到幾十分鐘，具體取決於 trial 數量和案例數量。請稍後重新整理此頁面查看結果。
            </div>
          )}

          {isTaskFailed && (
            <div className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
              ⚠️ 常見原因：
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>參數範圍設置過窄，所有 trials 都被過濾</li>
                <li>案例數據不符合策略要求</li>
                <li>訓練窗口配置錯誤</li>
              </ul>
            </div>
          )}

          <div className="flex gap-3">
            <Button onClick={loadAllData} className="flex-1">
              <RefreshCw className="h-4 w-4 mr-2" />
              重試
            </Button>
            <Button variant="outline" asChild className="flex-1">
              <Link href="/strategy-test">
                <Home className="h-4 w-4 mr-2" />
                返回策略測試
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
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">優化結果</h1>
            <p className="text-muted-foreground">
              Task ID: {taskId} · Study: {result.study_direction}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <ExportButton
              modelTaskId={taskId}
              scope="optimization"
              availableFormats={['csv', 'json', 'markdown']}
            />
            <Button asChild size="lg">
              <Link href={`/optimization-result/${taskId}/pipeline`}>
                <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                配置 Pipeline
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* 內容區域 */}
      <div className="space-y-8">
        {/* Section 1: 最佳結果總覽 */}
        <section>
          <h2 className="text-2xl font-semibold mb-4">最佳結果</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <BestResultCard result={result} />
            {trialStats && <TrialStatsCard stats={trialStats} />}
          </div>
        </section>

        {/* Section 2: 參數重要性與熱力圖 */}
        <section>
          <h2 className="text-2xl font-semibold mb-4">參數分析</h2>
          
          {/* 有資料時顯示圖表 */}
          {importances.length > 0 ? (
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
          ) : (
            /* 無資料時顯示友善提示 */
            <div className="bg-card border rounded-lg p-6">
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-full bg-amber-100 dark:bg-amber-900">
                  <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-foreground mb-2">
                    無法顯示參數重要性分析
                  </h3>
                  <p className="text-sm text-muted-foreground mb-3">
                    {importanceError || '參數重要性資料尚未載入'}
                  </p>
                  <div className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
                    <p className="font-medium mb-2">💡 可能原因：</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>試驗次數不足（需要至少 2 次完成的試驗）</li>
                      <li>所有試驗都被剪枝（Pruned）或失敗</li>
                      <li>參數數量不足以進行重要性分析</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>

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
