/**
 * TrialComparisonPanel.tsx - Trial 比較面板
 * 
 * 功能：
 * 1. 顯示多個 trials 的統計比較
 * 2. 用戶可選擇要比較的 trials
 * 3. 顯示推薦理由和詳細數據
 * 4. 支援匯出比較結果
 * 
 * Author: AI Agent
 * Date: 2026-01-11
 */

'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Download, TrendingUp, Info, CheckCircle2 } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

interface TrialSummary {
  trial_number: number
  value: number
  params: Record<string, any>
  state: string
  duration: number
  datetime_start: string
  datetime_complete: string | null
  user_attrs: Record<string, any>
}

interface TrialComparisonData {
  study_name: string
  n_trials: number
  trials: TrialSummary[]
  best_trial_number: number
  best_value: number
  value_mean: number
  value_std: number
  value_min: number
  value_max: number
  param_distributions: Record<string, any>
  recommendation: string | null
}

interface TrialComparisonPanelProps {
  taskId: string
  studyName: string
  allTrials: number[]
  onSelectTrial?: (trialNumber: number) => void
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function TrialComparisonPanel({
  taskId,
  studyName,
  allTrials,
  onSelectTrial
}: TrialComparisonPanelProps) {
  const [selectedTrials, setSelectedTrials] = useState<number[]>([])
  const [comparisonData, setComparisonData] = useState<TrialComparisonData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 預選前 5 名
  useEffect(() => {
    if (allTrials && allTrials.length > 0) {
      setSelectedTrials(allTrials.slice(0, Math.min(5, allTrials.length)))
    }
  }, [allTrials])

  // 比較 trials
  const handleCompare = async () => {
    if (selectedTrials.length === 0) {
      setError('請至少選擇一個 trial 進行比較')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/optimization/trials/compare?${new URLSearchParams({
          study_name: studyName,
          trial_numbers: selectedTrials.join(',')
        })}`
      )

      if (!response.ok) {
        throw new Error(`API 錯誤: ${response.statusText}`)
      }

      const data: TrialComparisonData = await response.json()
      setComparisonData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '比較失敗')
    } finally {
      setLoading(false)
    }
  }

  // 切換選擇
  const toggleTrial = (trialNumber: number) => {
    setSelectedTrials(prev =>
      prev.includes(trialNumber)
        ? prev.filter(n => n !== trialNumber)
        : [...prev, trialNumber]
    )
  }

  // 匯出為 CSV
  const handleExportCSV = () => {
    if (!comparisonData) return

    const headers = ['Trial #', 'Value', 'Duration (s)', ...Object.keys(comparisonData.trials[0]?.params || {})]
    const rows = comparisonData.trials.map(t => [
      t.trial_number,
      t.value.toFixed(4),
      t.duration.toFixed(2),
      ...Object.values(t.params)
    ])

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `trial_comparison_${Date.now()}.csv`
    a.click()
  }

  return (
    <div className="space-y-6">
      {/* 選擇 Trials */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" />
            選擇要比較的 Trials
          </CardTitle>
          <CardDescription>
            選擇多個 trials 進行統計比較（已預選前 5 名）
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 mb-4">
            {allTrials && allTrials.slice(0, 20).map(trialNum => (
              <div key={trialNum} className="flex items-center space-x-2">
                <Checkbox
                  id={`trial-${trialNum}`}
                  checked={selectedTrials.includes(trialNum)}
                  onCheckedChange={() => toggleTrial(trialNum)}
                />
                <label
                  htmlFor={`trial-${trialNum}`}
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Trial #{trialNum}
                </label>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={handleCompare} disabled={loading || selectedTrials.length === 0}>
              {loading ? '比較中...' : `比較 ${selectedTrials.length} 個 Trials`}
            </Button>
            <Badge variant="outline">
              已選擇: {selectedTrials.length} / {allTrials.length}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* 錯誤提示 */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>錯誤</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 比較結果 */}
      {comparisonData && (
        <>
          {/* 統計摘要 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  統計摘要
                </span>
                <Button variant="outline" size="sm" onClick={handleExportCSV}>
                  <Download className="h-4 w-4 mr-2" />
                  匯出 CSV
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">最佳 Trial</p>
                  <p className="text-2xl font-bold text-green-600">#{comparisonData.best_trial_number}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">最佳分數</p>
                  <p className="text-2xl font-bold">{comparisonData.best_value.toFixed(4)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">平均分數</p>
                  <p className="text-2xl font-bold">{comparisonData.value_mean.toFixed(4)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">標準差</p>
                  <p className="text-2xl font-bold">{comparisonData.value_std.toFixed(4)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 推薦說明 */}
          {comparisonData.recommendation && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>推薦</AlertTitle>
              <AlertDescription>{comparisonData.recommendation}</AlertDescription>
            </Alert>
          )}

          {/* Trials 詳細比較表 */}
          <Card>
            <CardHeader>
              <CardTitle>Trials 詳細比較</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Trial #</TableHead>
                      <TableHead>分數</TableHead>
                      <TableHead>執行時長</TableHead>
                      <TableHead>狀態</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {comparisonData.trials.map(trial => (
                      <TableRow key={trial.trial_number}>
                        <TableCell className="font-mono">
                          {trial.trial_number === comparisonData.best_trial_number && (
                            <Badge variant="default" className="mr-2">最佳</Badge>
                          )}
                          #{trial.trial_number}
                        </TableCell>
                        <TableCell className="font-mono">{trial.value.toFixed(4)}</TableCell>
                        <TableCell>{trial.duration.toFixed(2)}s</TableCell>
                        <TableCell>
                          <Badge variant={trial.state === 'COMPLETE' ? 'success' : 'secondary'}>
                            {trial.state}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => onSelectTrial && onSelectTrial(trial.trial_number)}
                          >
                            選擇此 Trial
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
