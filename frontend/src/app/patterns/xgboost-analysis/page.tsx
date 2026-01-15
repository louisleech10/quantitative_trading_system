/**
 * XGBoost 批量分析頁面 v2
 * 
 * 功能改進：
 * 1. 輸入框文字顏色加深
 * 2. 交易對支援多選 + 全選功能
 * 3. K 線時間週期獨立於案例 timeframe（可選 1h, 4h, 12h 等）
 * 4. 回看 K 線數量加上說明（T0 往前）
 * 5. 指標配置讀取動態配置
 * 
 * UI 設計：白色背景、深色字體
 * 
 * Author: AI Agent
 * Date: 2026-01-13
 */

'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import MultiIndicatorConfig from '@/components/optimization/MultiIndicatorConfig'
import { 
  Play, CheckCircle, AlertCircle, Loader2, Database, 
  TrendingUp, List, Brain, CheckSquare, Square, Info
} from 'lucide-react'

// ==================== Types ====================

interface IndicatorConfig {
  id: string
  indicator: string
  data_source: string
  params: Record<string, any>
}

interface CaseSummary {
  total_cases: number
  positive_cases: number
  negative_cases: number
  symbols: string[]
  timeframes: string[]
}

interface TaskStatus {
  status: 'running' | 'completed' | 'failed'
  progress: number
  current_step: string
  message: string
  total_cases: number
  processed_cases: number
  result?: AnalysisResult
  error?: string
}

interface FeatureImportance {
  feature: string
  importance: number
  rank: number
  method: string
}

interface DecisionRule {
  rule_id: number
  condition: string
  support: number
  confidence: number
  lift: number
}

interface ModelPerformance {
  train_auc: number
  cv_auc_mean: number
  cv_auc_std: number
  precision: number
  recall: number
  f1_score: number
  overfitting_score: number
}

interface AnalysisResult {
  symbol: string
  timeframe: string
  total_cases: number
  valid_cases: number
  positive_cases: number
  negative_cases: number
  features_generated: number
  feature_names: string[]
  model_performance: ModelPerformance
  feature_importance: FeatureImportance[]
  decision_rules: DecisionRule[]
  model_saved: boolean
  model_path?: string
}

// ==================== Constants ====================

// 可用的 K 線時間週期（獨立於案例搜尋的 timeframe）
const AVAILABLE_KLINE_TIMEFRAMES = [
  { value: '1h', label: '1 小時' },
  { value: '4h', label: '4 小時' },
  { value: '12h', label: '12 小時' },
  { value: '1d', label: '1 天' },
]

// ==================== API Functions ====================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function getCaseSummary(symbol?: string, timeframe?: string): Promise<CaseSummary> {
  const params = new URLSearchParams()
  if (symbol) params.append('symbol', symbol)
  if (timeframe) params.append('timeframe', timeframe)
  
  const response = await fetch(`${API_BASE}/api/v1/pattern-analysis/cases/summary?${params}`)
  if (!response.ok) throw new Error('Failed to fetch case summary')
  return response.json()
}

async function startBatchAnalysis(config: {
  symbol: string
  timeframe: string
  indicators: IndicatorConfig[]
  lookback_bars: number
  xgboost_params?: Record<string, any>
  cv_folds: number
}): Promise<{ task_id: string }> {
  const response = await fetch(`${API_BASE}/api/v1/pattern-analysis/xgboost/batch/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbol: config.symbol,
      timeframe: config.timeframe,
      indicators: config.indicators.map(i => ({
        indicator: i.indicator,
        data_source: i.data_source,
        params: i.params
      })),
      lookback_bars: config.lookback_bars,
      xgboost_params: config.xgboost_params,
      cv_folds: config.cv_folds
    })
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to start analysis')
  }
  return response.json()
}

async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE}/api/v1/pattern-analysis/xgboost/batch/task/${taskId}`)
  if (!response.ok) throw new Error('Failed to fetch task status')
  return response.json()
}

// ==================== Components ====================

function CaseSummaryCard({ summary }: { summary: CaseSummary | null }) {
  if (!summary) {
    return (
      <Card className="bg-white border-gray-200">
        <CardContent className="p-6">
          <div className="text-center text-gray-500">載入中...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-white border-gray-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
          <Database className="w-5 h-5" />
          案例資料統計
        </CardTitle>
        <CardDescription className="text-gray-600">
          從 cases.json 載入的案例數據
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-3xl font-bold text-gray-900">{summary.total_cases}</div>
            <div className="text-sm text-gray-600">總案例數</div>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-3xl font-bold text-green-700">{summary.positive_cases}</div>
            <div className="text-sm text-gray-600">正例</div>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <div className="text-3xl font-bold text-red-700">{summary.negative_cases}</div>
            <div className="text-sm text-gray-600">反例</div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-gray-600">可用交易對：</span>
          {summary.symbols.map(s => (
            <Badge key={s} variant="outline" className="text-gray-700 border-gray-300">
              {s}
            </Badge>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="text-sm text-gray-600">案例週期：</span>
          {summary.timeframes.map(t => (
            <Badge key={t} variant="outline" className="text-gray-700 border-gray-300">
              {t}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// 多選交易對組件
function SymbolMultiSelect({ 
  availableSymbols, 
  selectedSymbols, 
  onChange 
}: { 
  availableSymbols: string[]
  selectedSymbols: string[]
  onChange: (symbols: string[]) => void
}) {
  const allSelected = selectedSymbols.length === availableSymbols.length
  const someSelected = selectedSymbols.length > 0 && !allSelected

  const handleSelectAll = () => {
    if (allSelected) {
      onChange([])
    } else {
      onChange([...availableSymbols])
    }
  }

  const handleToggle = (symbol: string) => {
    if (selectedSymbols.includes(symbol)) {
      onChange(selectedSymbols.filter(s => s !== symbol))
    } else {
      onChange([...selectedSymbols, symbol])
    }
  }

  return (
    <div className="space-y-3">
      {/* 全選按鈕 */}
      <div 
        className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 cursor-pointer hover:bg-gray-100"
        onClick={handleSelectAll}
      >
        {allSelected ? (
          <CheckSquare className="w-5 h-5 text-blue-600" />
        ) : someSelected ? (
          <div className="w-5 h-5 border-2 border-blue-600 rounded flex items-center justify-center">
            <div className="w-2 h-2 bg-blue-600 rounded-sm" />
          </div>
        ) : (
          <Square className="w-5 h-5 text-gray-400" />
        )}
        <span className="text-sm font-medium text-gray-900">
          全選 ({selectedSymbols.length}/{availableSymbols.length})
        </span>
      </div>

      {/* 交易對列表 */}
      <div className="max-h-40 overflow-y-auto border rounded-lg">
        {availableSymbols.map(symbol => (
          <div
            key={symbol}
            className="flex items-center gap-2 p-2 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
            onClick={() => handleToggle(symbol)}
          >
            <Checkbox 
              checked={selectedSymbols.includes(symbol)}
              className="pointer-events-none"
            />
            <span className="text-sm text-gray-900">{symbol}</span>
          </div>
        ))}
      </div>

      {/* 已選顯示 */}
      {selectedSymbols.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {selectedSymbols.map(s => (
            <Badge 
              key={s} 
              variant="secondary" 
              className="text-xs bg-blue-100 text-blue-800 cursor-pointer hover:bg-blue-200"
              onClick={() => handleToggle(s)}
            >
              {s} ×
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

function TaskProgressCard({ task }: { task: TaskStatus | null }) {
  if (!task) return null

  const statusColor = {
    running: 'text-blue-600',
    completed: 'text-green-600',
    failed: 'text-red-600'
  }

  const StatusIcon = {
    running: Loader2,
    completed: CheckCircle,
    failed: AlertCircle
  }[task.status]

  return (
    <Card className="bg-white border-gray-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
          <StatusIcon className={`w-5 h-5 ${statusColor[task.status]} ${task.status === 'running' ? 'animate-spin' : ''}`} />
          任務狀態
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-700">{task.current_step}</span>
              <span className="text-sm text-gray-700">{task.progress}%</span>
            </div>
            <Progress value={task.progress} className="h-2" />
          </div>
          <div className="text-sm text-gray-800">{task.message}</div>
          {task.total_cases > 0 && (
            <div className="text-sm text-gray-700">
              處理進度：{task.processed_cases} / {task.total_cases} 個案例
            </div>
          )}
          {task.error && (
            <Alert variant="destructive" className="bg-red-50 border-red-300">
              <AlertDescription className="text-red-900 font-medium">{task.error}</AlertDescription>
            </Alert>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function ModelPerformanceCard({ performance }: { performance: ModelPerformance }) {
  const getAUCColor = (auc: number) => {
    if (auc >= 0.8) return 'text-green-700'
    if (auc >= 0.7) return 'text-yellow-700'
    return 'text-red-700'
  }

  const getOverfitColor = (score: number) => {
    if (score <= 0.05) return 'text-green-700'
    if (score <= 0.1) return 'text-yellow-700'
    return 'text-red-700'
  }

  return (
    <Card className="bg-white border-gray-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          模型性能
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className={`text-2xl font-bold ${getAUCColor(performance.train_auc)}`}>
              {(performance.train_auc * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">訓練 AUC</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className={`text-2xl font-bold ${getAUCColor(performance.cv_auc_mean)}`}>
              {(performance.cv_auc_mean * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">
              CV AUC (±{(performance.cv_auc_std * 100).toFixed(1)}%)
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-2xl font-bold text-gray-900">
              {(performance.precision * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">Precision</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-2xl font-bold text-gray-900">
              {(performance.recall * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">Recall</div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-xl font-bold text-gray-900">
              {(performance.f1_score * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">F1 Score</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className={`text-xl font-bold ${getOverfitColor(performance.overfitting_score)}`}>
              {(performance.overfitting_score * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">過擬合程度</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function FeatureImportanceCard({ features }: { features: FeatureImportance[] }) {
  const topFeatures = features.slice(0, 15)
  const maxImportance = Math.max(...topFeatures.map(f => f.importance))

  return (
    <Card className="bg-white border-gray-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
          <List className="w-5 h-5" />
          特徵重要性 (Top 15)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {topFeatures.map((feature, idx) => (
            <div key={feature.feature} className="flex items-center gap-3">
              <span className="w-6 text-sm text-gray-600">{idx + 1}</span>
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-mono text-gray-900 truncate max-w-[200px]" title={feature.feature}>
                    {feature.feature}
                  </span>
                  <span className="text-sm text-gray-700">
                    {(feature.importance * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${(feature.importance / maxImportance) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function DecisionRulesCard({ rules }: { rules: DecisionRule[] }) {
  return (
    <Card className="bg-white border-gray-200">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-gray-900 flex items-center gap-2">
          <Brain className="w-5 h-5" />
          決策規則 (Top 10)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {rules.map(rule => (
            <div key={rule.rule_id} className="bg-gray-50 rounded-lg p-3">
              <div className="font-mono text-sm text-gray-900 mb-2">
                {rule.condition}
              </div>
              <div className="flex gap-4 text-xs text-gray-700">
                <span>支持度: {rule.support}</span>
                <span>信心度: {(rule.confidence * 100).toFixed(1)}%</span>
                <span>提升度: {rule.lift.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function AnalysisResultView({ result }: { result: AnalysisResult }) {
  return (
    <div className="space-y-6">
      {/* 摘要資訊 */}
      <Card className="bg-white border-gray-200">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg text-gray-900">分析摘要</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            <div>
              <div className="text-xl font-bold text-gray-900">{result.symbol}</div>
              <div className="text-xs text-gray-600">交易對</div>
            </div>
            <div>
              <div className="text-xl font-bold text-gray-900">{result.timeframe}</div>
              <div className="text-xs text-gray-600">K 線週期</div>
            </div>
            <div>
              <div className="text-xl font-bold text-gray-900">{result.valid_cases}</div>
              <div className="text-xs text-gray-600">有效案例</div>
            </div>
            <div>
              <div className="text-xl font-bold text-gray-900">{result.features_generated}</div>
              <div className="text-xs text-gray-600">生成特徵數</div>
            </div>
            <div>
              <div className="text-xl font-bold text-green-700">
                {result.model_saved ? '已儲存' : '未儲存'}
              </div>
              <div className="text-xs text-gray-600">模型狀態</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 模型性能 */}
      <ModelPerformanceCard performance={result.model_performance} />

      {/* 特徵重要性和決策規則 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FeatureImportanceCard features={result.feature_importance} />
        <DecisionRulesCard rules={result.decision_rules} />
      </div>

      {/* 所有特徵名稱 */}
      <Card className="bg-white border-gray-200">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg text-gray-900">所有特徵 ({result.feature_names.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {result.feature_names.map(name => (
              <Badge key={name} variant="outline" className="font-mono text-xs text-gray-800">
                {name}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ==================== Main Page ====================

export default function XGBoostAnalysisPage() {
  // State
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null)
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([])
  const [klineTimeframe, setKlineTimeframe] = useState<string>('12h')
  const [indicators, setIndicators] = useState<IndicatorConfig[]>([])
  const [lookbackBars, setLookbackBars] = useState<number>(200)
  const [cvFolds, setCvFolds] = useState<number>(5)
  
  const [isLoading, setIsLoading] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load case summary on mount
  useEffect(() => {
    loadCaseSummary()
  }, [])

  // Auto-select all symbols when summary loads
  useEffect(() => {
    if (caseSummary && selectedSymbols.length === 0 && caseSummary.symbols.length > 0) {
      setSelectedSymbols([...caseSummary.symbols])
    }
  }, [caseSummary])

  // Poll task status when running
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null

    if (taskId && taskStatus?.status === 'running') {
      interval = setInterval(async () => {
        try {
          const status = await getTaskStatus(taskId)
          setTaskStatus(status)

          if (status.status === 'completed') {
            setResult(status.result || null)
            setIsLoading(false)
          } else if (status.status === 'failed') {
            setError(status.error || '分析失敗')
            setIsLoading(false)
          }
        } catch (e) {
          console.error('Failed to get task status:', e)
        }
      }, 1000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [taskId, taskStatus?.status])

  const loadCaseSummary = async () => {
    try {
      const summary = await getCaseSummary()
      setCaseSummary(summary)
    } catch (e) {
      console.error('Failed to load case summary:', e)
      setError('無法載入案例統計')
    }
  }

  const handleStartAnalysis = async () => {
    if (selectedSymbols.length === 0) {
      setError('請至少選擇一個交易對')
      return
    }
    if (indicators.length === 0) {
      setError('請至少配置一個指標')
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)
    setTaskStatus(null)

    try {
      // 目前 API 只支援單一 symbol，取第一個
      // TODO: 後端支援多 symbol 批量分析
      const response = await startBatchAnalysis({
        symbol: selectedSymbols[0],
        timeframe: klineTimeframe,
        indicators,
        lookback_bars: lookbackBars,
        cv_folds: cvFolds
      })

      setTaskId(response.task_id)
      setTaskStatus({
        status: 'running',
        progress: 0,
        current_step: '初始化',
        message: '任務已啟動',
        total_cases: 0,
        processed_cases: 0
      })
    } catch (e: any) {
      setError(e.message || '啟動分析失敗')
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* 頁面標題 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <h1 className="text-3xl font-bold text-gray-900">XGBoost 批量分析</h1>
          <p className="text-gray-600 mt-1">
            使用指標配置對所有案例進行機器學習分析，發現獲利模式
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左側：配置面板 */}
          <div className="lg:col-span-1 space-y-6">
            {/* 案例統計 */}
            <CaseSummaryCard summary={caseSummary} />

            {/* 數據選擇 */}
            <Card className="bg-white border-gray-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-gray-900">數據選擇</CardTitle>
                <CardDescription className="text-gray-600">
                  選擇要分析的交易對和 K 線時間週期
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 交易對多選 */}
                <div className="space-y-2">
                  <Label className="text-gray-800 font-medium">交易對</Label>
                  <SymbolMultiSelect
                    availableSymbols={caseSummary?.symbols || []}
                    selectedSymbols={selectedSymbols}
                    onChange={setSelectedSymbols}
                  />
                  <p className="text-xs text-gray-500">
                    選擇要納入分析的交易對（目前版本會使用第一個選中的交易對）
                  </p>
                </div>

                {/* K 線時間週期 - 獨立於案例 timeframe */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label className="text-gray-800 font-medium">K 線時間週期</Label>
                    <div className="group relative">
                      <Info className="w-4 h-4 text-gray-400 cursor-help" />
                      <div className="absolute left-0 bottom-6 hidden group-hover:block w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg z-50">
                        此為計算指標所用的 K 線週期，可與案例搜尋的 timeframe 不同。
                        例如：案例以 12h 搜尋，但指標計算可用 1h 或 4h K 線。
                      </div>
                    </div>
                  </div>
                  <Select value={klineTimeframe} onValueChange={setKlineTimeframe}>
                    <SelectTrigger className="bg-white border-gray-300 text-gray-900 [&>span]:text-gray-900">
                      <SelectValue placeholder="選擇 K 線週期" className="text-gray-900" />
                    </SelectTrigger>
                    <SelectContent className="bg-white border border-gray-200 shadow-lg z-50">
                      {AVAILABLE_KLINE_TIMEFRAMES.map(tf => (
                        <SelectItem key={tf.value} value={tf.value} className="text-gray-900 hover:bg-gray-100 cursor-pointer">
                          {tf.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* 回看 K 線數量 */}
                <div className="space-y-2 relative z-0">
                  <div className="flex items-center gap-2">
                    <Label className="text-gray-800 font-medium">回看 K 線數量</Label>
                    <div className="group relative">
                      <Info className="w-4 h-4 text-gray-400 cursor-help" />
                      <div className="absolute left-0 bottom-6 hidden group-hover:block w-72 p-2 bg-gray-900 text-white text-xs rounded shadow-lg z-50">
                        <p className="mb-1"><strong>回看數量 = Warmup + 學習窗口</strong></p>
                        <p className="mb-1">• Warmup：指標穩定所需（如 EMA_60 需 60 根）</p>
                        <p className="mb-1">• 學習窗口：你想分析的 K 線數（如 36 根）</p>
                        <p className="text-yellow-300">範例：EMA_60 + 36 根學習 = 填 100</p>
                      </div>
                    </div>
                  </div>
                  <Input
                    type="number"
                    value={lookbackBars}
                    onChange={(e) => setLookbackBars(parseInt(e.target.value) || 200)}
                    className="bg-white border-gray-300 text-gray-900"
                  />
                  <p className="text-xs text-gray-500">
                    公式：Warmup（最長指標週期）+ 學習窗口（想分析的 K 線數）
                  </p>
                </div>

                {/* 交叉驗證折數 */}
                <div className="space-y-2">
                  <Label className="text-gray-800 font-medium">交叉驗證折數</Label>
                  <Input
                    type="number"
                    value={cvFolds}
                    onChange={(e) => setCvFolds(parseInt(e.target.value) || 5)}
                    className="bg-white border-gray-300 text-gray-900"
                    min={2}
                    max={10}
                  />
                </div>
              </CardContent>
            </Card>

            {/* 指標配置 */}
            <Card className="bg-white border-gray-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-gray-900">指標配置</CardTitle>
                <CardDescription className="text-gray-600">
                  配置用於特徵提取的技術指標。可在 config/indicators.yaml 新增更多指標。
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MultiIndicatorConfig
                  value={indicators}
                  onChange={setIndicators}
                />
              </CardContent>
            </Card>

            {/* 啟動按鈕 */}
            <Button
              onClick={handleStartAnalysis}
              disabled={isLoading || selectedSymbols.length === 0}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white"
              size="lg"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  分析中...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  開始分析
                </>
              )}
            </Button>

            {/* 錯誤訊息 */}
            {error && (
              <Alert variant="destructive" className="bg-red-50 border-red-300">
                <AlertCircle className="w-4 h-4 text-red-700" />
                <AlertDescription className="text-red-900 font-medium">{error}</AlertDescription>
              </Alert>
            )}
          </div>

          {/* 右側：結果面板 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 任務進度 */}
            {taskStatus && <TaskProgressCard task={taskStatus} />}

            {/* 分析結果 */}
            {result && <AnalysisResultView result={result} />}

            {/* 空狀態 */}
            {!result && !taskStatus && (
              <Card className="bg-white border-gray-200">
                <CardContent className="py-12">
                  <div className="text-center">
                    <Brain className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                    <h3 className="text-lg font-semibold text-gray-800 mb-2">
                      尚未執行分析
                    </h3>
                    <p className="text-gray-600">
                      配置指標參數後，點擊「開始分析」執行 XGBoost 批量分析
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
