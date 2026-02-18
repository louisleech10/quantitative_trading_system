'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import { AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import OptunaProgressBar from '@/components/optimization/common/OptunaProgressBar'
import TrialComparisonTable from '@/components/optimization/common/TrialComparisonTable'
import ParameterImportanceChart from '@/components/optimization/hyperparameter/ParameterImportanceChart'
import OverfittingCheckChart from '@/components/optimization/hyperparameter/OverfittingCheckChart'
import {
  exportOptimizationResult,
  getOptimizationResult,
  getOptimizationTaskStatus,
} from '@/lib/api/optimizationApi'
import type { OptimizationResult, OverfittingAlertEvent, TrialRow } from '@/lib/types/optimization'
import { useOptimizationStore } from '@/store/optimizationStore'

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export default function HyperparameterOptimizationResultPage() {
  const params = useParams<{ taskId: string }>()
  const taskId = params.taskId

  const {
    currentResult,
    setCurrentResult,
    overfittingAlerts,
    appendOverfittingAlert,
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
        if (message.event === 'overfitting_alert' && message.data) {
          appendOverfittingAlert(message.data as OverfittingAlertEvent)
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
        console.error('[optimization-hyperparameter-result] ws parse failed:', parseError)
      }
    }

    ws.onerror = (wsError) => {
      console.error('[optimization-hyperparameter-result] ws error:', wsError)
    }

    return () => ws.close()
  }, [appendOverfittingAlert, taskId])

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
        console.error('[optimization-hyperparameter-result] poll failed:', pollError)
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
    const rows: TrialRow[] = []

    if (result?.best_trial?.trial_number !== null && result?.best_trial?.trial_number !== undefined) {
      rows.push({
        trial_number: result.best_trial.trial_number,
        value: Number(result.best_trial.value || 0),
        state: 'BEST',
        params: result.best_trial.params || {},
      })
    }

    overfittingAlerts.forEach((alert) => {
      rows.push({
        trial_number: alert.trial_number,
        value: alert.train_val_gap,
        state: 'OVERFITTING_ALERT',
      })
    })

    return rows
  }, [overfittingAlerts, result])

  const onExportJson = async () => {
    try {
      const payload = await exportOptimizationResult('hyperparameter', taskId, 'json')
      if (payload && typeof payload === 'object') {
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = `hyperparameter_${taskId}.json`
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
      const blob = await exportOptimizationResult('hyperparameter', taskId, 'csv')
      if (blob instanceof Blob) {
        const url = URL.createObjectURL(blob)
        const anchor = document.createElement('a')
        anchor.href = url
        anchor.download = `hyperparameter_${taskId}.csv`
        anchor.click()
        URL.revokeObjectURL(url)
      }
    } catch (exportError) {
      const message = exportError instanceof Error ? exportError.message : '匯出 CSV 失敗'
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
          <CardTitle>超參數優化結果：{taskId}</CardTitle>
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
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>最佳超參數</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="max-h-60 overflow-auto rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
                  {JSON.stringify(result.best_trial?.params || {}, null, 2)}
                </pre>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>指標摘要</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="max-h-60 overflow-auto rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
                  {JSON.stringify(result.performance_metrics || {}, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </div>

          <ParameterImportanceChart data={result.parameter_importance || {}} />
          <OverfittingCheckChart alerts={overfittingAlerts} />
          <TrialComparisonTable trials={trialRows} />
        </>
      )}
    </div>
  )
}
