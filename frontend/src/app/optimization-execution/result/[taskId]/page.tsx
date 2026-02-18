'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import html2canvas from 'html2canvas'
import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import OptunaProgressBar from '@/components/optimization/common/OptunaProgressBar'
import TrialComparisonTable from '@/components/optimization/common/TrialComparisonTable'
import EquityCurveChart from '@/components/optimization/execution/EquityCurveChart'
import DrawdownChart from '@/components/optimization/execution/DrawdownChart'
import ParetoFrontChart from '@/components/optimization/execution/ParetoFrontChart'
import ParameterImportanceChart from '@/components/optimization/hyperparameter/ParameterImportanceChart'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  exportOptimizationResult,
  getOptimizationResult,
  getOptimizationTaskStatus,
} from '@/lib/api/optimizationApi'
import type { BacktestProgressEvent, OptimizationResult, TrialRow } from '@/lib/types/optimization'
import { useOptimizationStore } from '@/store/optimizationStore'

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export default function ExecutionOptimizationResultPage() {
  const params = useParams<{ taskId: string }>()
  const taskId = params.taskId
  const chartContainerRef = useRef<HTMLDivElement | null>(null)

  const {
    currentResult,
    setCurrentResult,
    backtestProgress,
    appendBacktestProgress,
    paretoFront,
    setParetoUpdate,
    setError,
    error,
  } = useOptimizationStore()

  const [status, setStatus] = useState('pending')
  const [completedTrials, setCompletedTrials] = useState(0)
  const [totalTrials, setTotalTrials] = useState(0)
  const [bestValue, setBestValue] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws/optimization/${taskId}`)

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as { event?: string; data?: unknown }

        if (message.event === 'backtest_progress' && message.data) {
          appendBacktestProgress(message.data as BacktestProgressEvent)
        }

        if (message.event === 'pareto_update' && message.data) {
          setParetoUpdate(message.data as { pareto_front: Array<{ sharpe: number; max_dd: number }> })
        }

        if (message.event === 'progress_update' && message.data) {
          const payload = message.data as {
            completed_trials?: number
            total_trials?: number
            best_value?: number | null
          }
          setCompletedTrials(payload.completed_trials || 0)
          setTotalTrials(payload.total_trials || 0)
          setBestValue(payload.best_value ?? null)
        }
      } catch (parseError) {
        console.error('[optimization-execution-result] ws parse failed:', parseError)
      }
    }

    ws.onerror = (wsError) => {
      console.error('[optimization-execution-result] ws error:', wsError)
    }

    return () => ws.close()
  }, [appendBacktestProgress, setParetoUpdate, taskId])

  useEffect(() => {
    let cancelled = false

    const poll = async () => {
      setIsLoading(true)
      try {
        const statusResponse = await getOptimizationTaskStatus(taskId)
        const normalizedStatus = statusResponse.data?.status || statusResponse.status || 'unknown'
        if (!cancelled) {
          setStatus(normalizedStatus)
          const progress = statusResponse.data?.progress || statusResponse.progress
          if (progress) {
            setCompletedTrials(progress.completed_trials || 0)
            setTotalTrials(progress.total_trials || 0)
            setBestValue(progress.best_value ?? null)
          }
        }

        if (normalizedStatus === 'completed') {
          const result = await getOptimizationResult(taskId)
          if (!cancelled) {
            setCurrentResult(result)
          }
        }
      } catch (pollError) {
        const message = pollError instanceof Error ? pollError.message : '查詢結果失敗'
        console.error('[optimization-execution-result] poll failed:', pollError)
        if (!cancelled) {
          setError(message)
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void poll()
    const timer = setInterval(() => {
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        return
      }
      void poll()
    }, 2000)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [setCurrentResult, setError, status, taskId])

  const result: OptimizationResult | null = currentResult

  const trialRows: TrialRow[] = useMemo(() => {
    return backtestProgress.map((item) => ({
      trial_number: item.trial_number,
      value: item.expectancy,
      state: 'BACKTEST_PROGRESS',
    }))
  }, [backtestProgress])

  const equityCurveData = useMemo(() => {
    return backtestProgress.map((item, index) => ({
      step: index + 1,
      strategy: item.sharpe,
      buyHold: item.win_rate,
    }))
  }, [backtestProgress])

  const drawdownData = useMemo(() => {
    return backtestProgress.map((item, index) => ({
      step: index + 1,
      drawdown: item.max_dd,
    }))
  }, [backtestProgress])

  const pnlDistributionData = useMemo(() => {
    return backtestProgress.map((item, index) => ({
      bin: `T${index + 1}`,
      pnl_pct: item.expectancy,
    }))
  }, [backtestProgress])

  const benchmarkComparison = useMemo(() => {
    if (!result?.best_trial?.value) {
      return { strategy: 0, benchmark: 0, delta: 0 }
    }

    const strategy = Number(result.best_trial.value)
    const benchmark = 0
    return {
      strategy,
      benchmark,
      delta: strategy - benchmark,
    }
  }, [result])

  const onExportJson = async () => {
    try {
      const payload = await exportOptimizationResult('execution', taskId, 'json')
      if (payload && typeof payload === 'object') {
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = `execution_${taskId}.json`
        anchor.click()
        URL.revokeObjectURL(url)
      }
    } catch (exportError) {
      const message = exportError instanceof Error ? exportError.message : '匯出 JSON 失敗'
      setError(message)
    }
  }

  const onExportCsv = async () => {
    try {
      const blob = await exportOptimizationResult('execution', taskId, 'csv')
      if (blob instanceof Blob) {
        const url = URL.createObjectURL(blob)
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = `execution_${taskId}.csv`
        anchor.click()
        URL.revokeObjectURL(url)
      }
    } catch (exportError) {
      const message = exportError instanceof Error ? exportError.message : '匯出 CSV 失敗'
      setError(message)
    }
  }

  const onExportPng = async () => {
    if (!chartContainerRef.current) {
      return
    }

    try {
      const canvas = await html2canvas(chartContainerRef.current)
      const link = document.createElement('a')
      link.download = `execution_${taskId}.png`
      link.href = canvas.toDataURL('image/png')
      link.click()
    } catch (pngError) {
      const message = pngError instanceof Error ? pngError.message : '匯出 PNG 失敗'
      setError(message)
    }
  }

  return (
    <div className="space-y-4 p-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>錯誤</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>策略執行優化結果：{taskId}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-400">狀態：{status}</p>
          <OptunaProgressBar
            completedTrials={completedTrials}
            totalTrials={totalTrials}
            bestValue={bestValue}
          />
          <div className="flex gap-2">
            <Button variant="outline" onClick={onExportJson}>匯出 JSON</Button>
            <Button variant="outline" onClick={onExportCsv}>匯出 CSV</Button>
            <Button variant="outline" onClick={onExportPng}>匯出 PNG</Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-slate-400">載入結果中...</p>
          </CardContent>
        </Card>
      ) : !result ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-slate-400">暫無結果資料</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card><CardHeader><CardTitle>Task ID</CardTitle></CardHeader><CardContent>{result.task_id}</CardContent></Card>
            <Card><CardHeader><CardTitle>Task Type</CardTitle></CardHeader><CardContent>{result.task_type}</CardContent></Card>
            <Card><CardHeader><CardTitle>Status</CardTitle></CardHeader><CardContent>{result.status}</CardContent></Card>
            <Card><CardHeader><CardTitle>Best Trial #</CardTitle></CardHeader><CardContent>{result.best_trial?.trial_number ?? '-'}</CardContent></Card>
            <Card><CardHeader><CardTitle>Best Value</CardTitle></CardHeader><CardContent>{result.best_trial?.value ?? '-'}</CardContent></Card>
            <Card><CardHeader><CardTitle>Pareto Points</CardTitle></CardHeader><CardContent>{paretoFront.length}</CardContent></Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>最佳參數</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="max-h-60 overflow-auto rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
                {JSON.stringify(result.best_trial?.params || {}, null, 2)}
              </pre>
            </CardContent>
          </Card>

          <div ref={chartContainerRef} className="space-y-4">
            <EquityCurveChart data={equityCurveData} />
            <DrawdownChart data={drawdownData} />
            <Card>
              <CardHeader>
                <CardTitle>交易 PnL% 分佈直方圖</CardTitle>
              </CardHeader>
              <CardContent className="h-80 text-blue-400">
                {pnlDistributionData.length === 0 ? (
                  <p className="text-sm text-slate-400">無可用資料</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pnlDistributionData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="bin" hide />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="pnl_pct" fill="currentColor" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
            <ParameterImportanceChart data={result.parameter_importance || {}} />
            <ParetoFrontChart data={paretoFront} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Benchmark 比較</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm text-slate-300 md:grid-cols-3">
              <div>Strategy: {benchmarkComparison.strategy}</div>
              <div>Benchmark: {benchmarkComparison.benchmark}</div>
              <div>Delta: {benchmarkComparison.delta}</div>
            </CardContent>
          </Card>

          <TrialComparisonTable trials={trialRows} />
        </>
      )}
    </div>
  )
}
