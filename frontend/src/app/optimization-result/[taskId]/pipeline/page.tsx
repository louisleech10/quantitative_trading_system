/**
 * Trial Selection & Pipeline Configuration Page
 * 
 * 功能：
 * 1. 顯示 Optuna 優化結果
 * 2. Trial 比較與選擇
 * 3. 配置多指標 Pipeline
 * 4. 建立 ML Pipeline 配置
 * 
 * 路由: /optimization-result/[taskId]/pipeline
 * 
 * Author: AI Agent
 * Date: 2026-01-11
 */

'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, CheckCircle2, Loader2, AlertCircle } from 'lucide-react'
import TrialComparisonPanel from '@/components/optimization/TrialComparisonPanel'
import TrialSelectionDialog from '@/components/optimization/TrialSelectionDialog'
import MultiIndicatorConfig from '@/components/optimization/MultiIndicatorConfig'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface OptimizationResult {
  task_id: string
  study_name: string
  n_trials: number
  best_trial: {
    number: number
  } | null
  trials: Array<{
    number: number
    value: number
    params: Record<string, unknown>
    user_attrs?: Record<string, unknown>
    state?: string
    duration_seconds?: number
    datetime_start?: string
    datetime_complete?: string | null
  }>
}

interface IndicatorConfig {
  id: string
  indicator: string
  data_source: string
  params: Record<string, unknown>
}

export default function PipelineConfigPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.taskId as string

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<OptimizationResult | null>(null)
  
  // Trial 選擇狀態
  const [selectedTrialNumber, setSelectedTrialNumber] = useState<number | null>(null)
  const [showSelectionDialog, setShowSelectionDialog] = useState(false)
  
  // 配置狀態
  const [configMode, setConfigMode] = useState<'single' | 'multi'>('single')
  const [indicators, setIndicators] = useState<IndicatorConfig[]>([
    {
      id: 'indicator_1',
      indicator: 'ema_three_line',
      data_source: 'close',
      params: { ema_short: 5, ema_mid: 20, ema_long: 60, volume_threshold: 0.6 }
    }
  ])
  
  const [success, setSuccess] = useState(false)

  // 載入優化結果
  useEffect(() => {
    const fetchResult = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/optimization/tasks/${taskId}/result`)
        if (!response.ok) throw new Error('無法載入優化結果')
        const data = await response.json()
        setResult(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '載入失敗')
      } finally {
        setLoading(false)
      }
    }
    
    fetchResult()
  }, [taskId])

  // 處理 Trial 選擇
  const handleSelectTrial = (trialNumber: number) => {
    setSelectedTrialNumber(trialNumber)
    setShowSelectionDialog(true)
  }

  // 確認選擇並建立配置
  const handleSelectionSuccess = async (pipelineId: string) => {
    try {
      setSuccess(true)
      
      // 3 秒後跳轉到配置詳情頁
      setTimeout(() => {
        router.push(`/ml-pipeline/${pipelineId}`)
      }, 3000)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失敗')
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-screen bg-slate-950/40">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto p-6 bg-slate-950/40 min-h-screen">
        <Alert variant="destructive" className="bg-rose-500/10 border-rose-400/30">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>錯誤</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    )
  }

  if (!result) return null

  const selectedTrial = result.trials?.find((trial) => trial.number === selectedTrialNumber)

  return (
    <div className="container mx-auto p-6 space-y-6 min-h-screen bg-slate-950/40">
      {/* 頁首 */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <Link href={`/optimization-result/${taskId}`} className="hover:underline">
              優化結果
            </Link>
            <span>/</span>
            <span>Pipeline 配置</span>
          </div>
          <h1 className="text-3xl font-bold">Pipeline 配置</h1>
          <p className="text-muted-foreground mt-1">
            選擇 Trial 並配置 ML Pipeline
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link href={`/optimization-result/${taskId}`}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回結果頁
          </Link>
        </Button>
      </div>

      {/* 成功提示 */}
      {success && (
        <Alert className="bg-emerald-500/10 border-emerald-400/30">
          <CheckCircle2 className="h-4 w-4 text-emerald-300" />
          <AlertTitle className="text-emerald-200">配置建立成功</AlertTitle>
          <AlertDescription className="text-emerald-200/80">
            正在跳轉到配置詳情頁...
          </AlertDescription>
        </Alert>
      )}

      {/* 優化摘要 */}
      <Card>
        <CardHeader>
          <CardTitle>優化摘要</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Study 名稱</p>
              <p className="font-mono">{result.study_name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">總 Trials 數</p>
              <p className="text-2xl font-bold">{result.n_trials}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">最佳 Trial</p>
              <p className="text-2xl font-bold text-emerald-300">#{result.best_trial?.number}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 主要內容 */}
      <Tabs defaultValue="select" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="select">選擇 Trial</TabsTrigger>
          <TabsTrigger value="configure">配置指標</TabsTrigger>
        </TabsList>

        {/* Tab 1: 選擇 Trial */}
        <TabsContent value="select" className="space-y-6">
          <TrialComparisonPanel
            taskId={taskId}
            studyName={result.study_name}
            allTrials={result.trials?.map((trial) => trial.number) || []}
            onSelectTrial={handleSelectTrial}
          />
        </TabsContent>

        {/* Tab 2: 配置指標 */}
        <TabsContent value="configure" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>配置模式</CardTitle>
              <CardDescription>
                選擇使用單一指標或多指標組合
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <Button
                  variant={configMode === 'single' ? 'default' : 'outline'}
                  onClick={() => setConfigMode('single')}
                >
                  單一指標
                </Button>
                <Button
                  variant={configMode === 'multi' ? 'default' : 'outline'}
                  onClick={() => setConfigMode('multi')}
                >
                  多指標組合
                </Button>
              </div>
            </CardContent>
          </Card>

          {configMode === 'single' && (
            <Alert>
              <AlertDescription>
                單一指標模式將使用 Trial 中的指標配置（從 Optuna 參數繼承）
              </AlertDescription>
            </Alert>
          )}

          {configMode === 'multi' && (
            <Card>
              <CardHeader>
                <CardTitle>多指標配置</CardTitle>
                <CardDescription>
                  配置多個指標組合，例如 EMA + RSI + MACD
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MultiIndicatorConfig
                  value={indicators}
                  onChange={setIndicators}
                />
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Trial 選擇對話框 */}
      {selectedTrial && (
        <TrialSelectionDialog
          open={showSelectionDialog}
          onClose={() => setShowSelectionDialog(false)}
          studyName={result.study_name}
          selectedTrial={{
            number: selectedTrial.number,
            value: selectedTrial.value,
            params: selectedTrial.params,
            state: selectedTrial.state || 'COMPLETE',
            duration_seconds: selectedTrial.duration_seconds || 0,
            user_attrs: selectedTrial.user_attrs || {},
          }}
          strategyType={
            typeof selectedTrial.user_attrs?.strategy_type === 'string'
              ? selectedTrial.user_attrs.strategy_type
              : 'ema_three_line'
          }
          onSuccess={handleSelectionSuccess}
        />
      )}
    </div>
  )
}
