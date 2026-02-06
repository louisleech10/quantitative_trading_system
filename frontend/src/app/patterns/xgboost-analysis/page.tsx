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
import { useRouter } from 'next/navigation'
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
import { createPattern } from '@/lib/api/patternApi'
import type { CreatePatternRequest } from '@/lib/patternTypes'
import { usePatternStore } from '@/store/patternStore'
import { 
  Play, CheckCircle, AlertCircle, Loader2, Database, 
  TrendingUp, List, Brain, CheckSquare, Square, Info, Save, BarChart2
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
  train_auc: number | null
  cv_auc_mean: number | null
  cv_auc_std: number | null
  precision: number | null
  recall: number | null
  f1_score: number | null
  overfitting_score: number | null
  brier_score?: number | null
  ece?: number | null
  calibration_quality?: string | null
  pr_auc?: number | null
  positive_rate?: number | null
}

interface PrecisionAtKResult {
  precision_at_k: Record<number, number>
  threshold_at_k: Record<number, number>
  sample_count_at_k: Record<number, number>
  recommended_k?: number | null
  recommended_threshold?: number | null
  recommended_precision?: number | null
}

interface ExpectancyResult {
  win_rate: number
  avg_win: number
  avg_loss: number
  expectancy: number
  total_trades: number
  threshold: number
  note: string
  sharpe_proxy?: number | null
}

interface BootstrapCIResult {
  metric: string
  point_estimate: number
  ci_lower: number
  ci_upper: number
  confidence_level: number
  n_bootstrap: number
}

interface PermutationImportanceItem {
  feature: string
  importance: number
  std: number
  rank: number
  gain_rank?: number | null
  rank_gap?: number | null
  overfit_flag?: boolean
}

interface PermutationImportanceResult {
  rank_gap_threshold: number
  items: PermutationImportanceItem[]
}

interface FoldImportanceStabilityResult {
  stable_features: string[]
  unstable_features: Array<{ feature: string; cv: number; rank_range: number[] }>
  feature_cv: Record<string, number>
}

interface CrossSymbolValidationResult {
  source_symbol: string
  target_symbol: string
  source_auc: number
  target_auc: number
  generalization_gap: number
  verdict: string
}

interface AnalysisResult {
  symbol: string
  symbols?: string[]
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
  precision_at_k?: PrecisionAtKResult | null
  expectancy?: ExpectancyResult | null
  bootstrap_ci?: Record<string, BootstrapCIResult> | null
  permutation_importance?: PermutationImportanceResult | null
  fold_importance_stability?: FoldImportanceStabilityResult | null
  cross_symbol_validation?: CrossSymbolValidationResult[] | null
  model_saved: boolean
  model_path?: string
  metadata?: {
    data_selection?: {
      symbol?: string
      symbols?: string[]
      timeframe: string
      lookback_bars: number
    }
    indicator_config?: Array<{
      indicator: string
      data_source: string
      params: Record<string, any>
    }>
    sequence_config?: {
      sequence_length: number
      sequence_feature_mode: 'aggregate' | 'flatten'
      sequence_stride: number
      aggregation_methods: string[]
      multi_scale_windows: number[]
    }
    training_config?: {
      time_series_split: boolean
      cv_folds: number
    }
  }
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
  symbols: string[]
  timeframe: string
  indicators: IndicatorConfig[]
  lookback_bars: number
  sequence_length?: number | null
  sequence_feature_mode?: 'aggregate' | 'flatten'
  sequence_stride?: number
  aggregation_methods?: string[] | null
  multi_scale_windows?: number[] | null
  time_series_split?: boolean
  xgboost_params?: Record<string, any>
  cv_folds: number
}): Promise<{ task_id: string }> {
  const response = await fetch(`${API_BASE}/api/v1/pattern-analysis/xgboost/batch/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbols: config.symbols,
      timeframe: config.timeframe,
      indicators: config.indicators.map(i => ({
        indicator: i.indicator,
        data_source: i.data_source,
        params: i.params
      })),
      lookback_bars: config.lookback_bars,
      sequence_length: config.sequence_length,
      sequence_feature_mode: config.sequence_feature_mode,
      sequence_stride: config.sequence_stride,
      aggregation_methods: config.aggregation_methods,
      multi_scale_windows: config.multi_scale_windows,
      time_series_split: config.time_series_split,
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
      <Card className="glass-panel border-slate-800/80">
        <CardContent className="p-6">
          <div className="text-center text-slate-400">載入中...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100 flex items-center gap-2">
          <Database className="w-5 h-5" />
          案例資料統計
        </CardTitle>
        <CardDescription className="text-slate-400">
          從 cases.json 載入的案例數據
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800/80">
            <div className="text-3xl font-bold text-slate-100">{summary.total_cases}</div>
            <div className="text-sm text-slate-400">總案例數</div>
          </div>
          <div className="bg-emerald-500/10 rounded-lg p-4 border border-emerald-400/30">
            <div className="text-3xl font-bold text-emerald-200">{summary.positive_cases}</div>
            <div className="text-sm text-slate-400">正例</div>
          </div>
          <div className="bg-rose-500/10 rounded-lg p-4 border border-rose-400/30">
            <div className="text-3xl font-bold text-rose-200">{summary.negative_cases}</div>
            <div className="text-sm text-slate-400">反例</div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-sm text-slate-400">可用交易對：</span>
          {summary.symbols.map(s => (
            <Badge key={s} variant="outline" className="text-slate-200 border-slate-700">
              {s}
            </Badge>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="text-sm text-slate-400">案例週期：</span>
          {summary.timeframes.map(t => (
            <Badge key={t} variant="outline" className="text-slate-200 border-slate-700">
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
        className="flex items-center gap-2 p-2 rounded-lg bg-slate-900/50 cursor-pointer hover:bg-slate-900/70 border border-slate-800/80"
        onClick={handleSelectAll}
      >
        {allSelected ? (
          <CheckSquare className="w-5 h-5 text-emerald-300" />
        ) : someSelected ? (
          <div className="w-5 h-5 border-2 border-emerald-300 rounded flex items-center justify-center">
            <div className="w-2 h-2 bg-emerald-300 rounded-sm" />
          </div>
        ) : (
          <Square className="w-5 h-5 text-slate-500" />
        )}
        <span className="text-sm font-medium text-slate-100">
          全選 ({selectedSymbols.length}/{availableSymbols.length})
        </span>
      </div>

      {/* 交易對列表 */}
      <div className="max-h-40 overflow-y-auto border border-slate-800/80 rounded-lg">
        {availableSymbols.map(symbol => (
          <div
            key={symbol}
            className="flex items-center gap-2 p-2 hover:bg-slate-900/60 cursor-pointer border-b border-slate-800/80 last:border-b-0"
            onClick={() => handleToggle(symbol)}
          >
            <Checkbox 
              checked={selectedSymbols.includes(symbol)}
              className="pointer-events-none"
            />
            <span className="text-sm text-slate-100">{symbol}</span>
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
              className="text-xs bg-emerald-500/10 text-emerald-200 cursor-pointer hover:bg-emerald-500/20 border border-emerald-400/30"
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
    running: 'text-emerald-300',
    completed: 'text-emerald-300',
    failed: 'text-rose-300'
  }

  const StatusIcon = {
    running: Loader2,
    completed: CheckCircle,
    failed: AlertCircle
  }[task.status]

  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100 flex items-center gap-2">
          <StatusIcon className={`w-5 h-5 ${statusColor[task.status]} ${task.status === 'running' ? 'animate-spin' : ''}`} />
          任務狀態
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-slate-300">{task.current_step}</span>
              <span className="text-sm text-slate-300">{task.progress}%</span>
            </div>
            <Progress value={task.progress} className="h-2" />
          </div>
          <div className="text-sm text-slate-200">{task.message}</div>
          {task.total_cases > 0 && (
            <div className="text-sm text-slate-300">
              處理進度：{task.processed_cases} / {task.total_cases} 個案例
            </div>
          )}
          {task.error && (
            <Alert variant="destructive" className="bg-rose-500/10 border-rose-400/30">
              <AlertDescription className="text-rose-200 font-medium">{task.error}</AlertDescription>
            </Alert>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function ModelPerformanceCard({ performance }: { performance: ModelPerformance }) {
  const isValidNumber = (value: number | null) =>
    value !== null && !Number.isNaN(value)

  const formatPercent = (value: number | null, digits = 1) =>
    isValidNumber(value) ? `${(value! * 100).toFixed(digits)}%` : 'N/A'

  const getAUCColor = (auc: number | null) => {
    if (!isValidNumber(auc)) return 'text-slate-400'
    if (auc! >= 0.8) return 'text-emerald-300'
    if (auc! >= 0.7) return 'text-amber-300'
    return 'text-rose-300'
  }

  const getOverfitColor = (score: number | null) => {
    if (!isValidNumber(score)) return 'text-slate-400'
    if (score! <= 0.05) return 'text-emerald-300'
    if (score! <= 0.1) return 'text-amber-300'
    return 'text-rose-300'
  }

  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100 flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          模型性能
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80">
            <div className={`text-2xl font-bold ${getAUCColor(performance.train_auc)}`}>
              {formatPercent(performance.train_auc)}
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              訓練 AUC
              <div className="group relative">
                <Info className="w-3 h-3 text-slate-500 cursor-help" />
                <div className="absolute left-0 bottom-5 hidden group-hover:block w-56 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                  訓練集上的 AUC，越高代表模型在訓練資料的分類能力越好。
                </div>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80">
            <div className={`text-2xl font-bold ${getAUCColor(performance.cv_auc_mean)}`}>
              {formatPercent(performance.cv_auc_mean)}
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              CV AUC (±{isValidNumber(performance.cv_auc_std) ? `${(performance.cv_auc_std! * 100).toFixed(1)}%` : 'N/A'})
              <div className="group relative">
                <Info className="w-3 h-3 text-slate-500 cursor-help" />
                <div className="absolute left-0 bottom-5 hidden group-hover:block w-64 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                  交叉驗證平均 AUC，反映泛化能力；± 為標準差，越小越穩定。
                </div>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80">
            <div className="text-2xl font-bold text-slate-100">
              {formatPercent(performance.precision)}
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              Precision
              <div className="group relative">
                <Info className="w-3 h-3 text-slate-500 cursor-help" />
                <div className="absolute left-0 bottom-5 hidden group-hover:block w-60 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                  判為正例的樣本中，有多少比例是真的正例（準確度）。
                </div>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80">
            <div className="text-2xl font-bold text-slate-100">
              {formatPercent(performance.recall)}
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              Recall
              <div className="group relative">
                <Info className="w-3 h-3 text-slate-500 cursor-help" />
                <div className="absolute left-0 bottom-5 hidden group-hover:block w-56 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                  真正例中，被模型抓到的比例（覆蓋率）。
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4">
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80">
            <div className="text-xl font-bold text-slate-100">
              {formatPercent(performance.f1_score)}
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              F1 Score
              <div className="group relative">
                <Info className="w-3 h-3 text-slate-500 cursor-help" />
                <div className="absolute left-0 bottom-5 hidden group-hover:block w-56 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                  Precision 與 Recall 的調和平均，兼顧準確與覆蓋。
                </div>
              </div>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80">
            <div className={`text-xl font-bold ${getOverfitColor(performance.overfitting_score)}`}>
              {formatPercent(performance.overfitting_score)}
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-1">
              過擬合程度
              <div className="group relative">
                <Info className="w-3 h-3 text-slate-500 cursor-help" />
                <div className="absolute left-0 bottom-5 hidden group-hover:block w-64 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                  訓練 AUC 與 CV AUC 的差距；越大代表過擬合風險越高。
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function AdvancedMetricsCard({ result }: { result: AnalysisResult }) {
  const formatPercent = (value?: number | null, digits = 1) =>
    value === null || value === undefined || Number.isNaN(value)
      ? 'N/A'
      : `${(value * 100).toFixed(digits)}%`

  const formatNumber = (value?: number | null, digits = 4) =>
    value === null || value === undefined || Number.isNaN(value)
      ? 'N/A'
      : value.toFixed(digits)

  const precisionAtK = result.precision_at_k
  const expectancy = result.expectancy
  const bootstrap = result.bootstrap_ci
  const permutation = result.permutation_importance
  const foldStability = result.fold_importance_stability
  const crossSymbol = result.cross_symbol_validation

  const precisionKeys = precisionAtK
    ? Object.keys(precisionAtK.precision_at_k)
        .map(k => Number(k))
        .sort((a, b) => a - b)
    : []

  const topPermutation = permutation?.items?.slice(0, 6) || []

  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100 flex items-center gap-2">
          <BarChart2 className="w-5 h-5" />
          進階指標
        </CardTitle>
        <CardDescription className="text-slate-400">
          Precision@K、期望值、信賴區間與穩定性分析
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800/80">
            <div className="text-sm font-semibold text-slate-100 mb-2">Precision@K</div>
            {precisionKeys.length === 0 ? (
              <div className="text-sm text-slate-400">無資料</div>
            ) : (
              <div className="space-y-2">
                {precisionKeys.map(k => (
                  <div key={k} className="flex items-center justify-between text-sm text-slate-200">
                    <span>P@{k}%</span>
                    <span>
                      {formatPercent(precisionAtK?.precision_at_k[k])} ｜ 閾值 {formatNumber(precisionAtK?.threshold_at_k[k], 3)} ｜ {precisionAtK?.sample_count_at_k[k]} 筆
                    </span>
                  </div>
                ))}
                {precisionAtK?.recommended_k && (
                  <div className="text-xs text-emerald-300 mt-2">
                    推薦 K：{precisionAtK.recommended_k}% ，Precision {formatPercent(precisionAtK.recommended_precision)}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800/80">
            <div className="text-sm font-semibold text-slate-100 mb-2">期望值估算</div>
            {!expectancy ? (
              <div className="text-sm text-slate-400">缺少 Price_Change，暫無估算</div>
            ) : (
              <div className="grid grid-cols-2 gap-2 text-sm text-slate-200">
                <div>勝率：{formatPercent(expectancy.win_rate)}</div>
                <div>期望值：{formatNumber(expectancy.expectancy, 6)}</div>
                <div>平均盈：{formatNumber(expectancy.avg_win, 6)}</div>
                <div>平均虧：{formatNumber(expectancy.avg_loss, 6)}</div>
                <div>交易數：{expectancy.total_trades}</div>
                <div>Sharpe Proxy：{formatNumber(expectancy.sharpe_proxy, 3)}</div>
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800/80">
            <div className="text-sm font-semibold text-slate-100 mb-2">Bootstrap 信賴區間</div>
            {!bootstrap ? (
              <div className="text-sm text-slate-400">無資料</div>
            ) : (
              <div className="space-y-2 text-sm text-slate-200">
                {Object.entries(bootstrap).map(([key, ci]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span>{key.toUpperCase()}</span>
                    <span>
                      {formatNumber(ci.point_estimate, 4)} [{formatNumber(ci.ci_lower, 4)}, {formatNumber(ci.ci_upper, 4)}]
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800/80">
            <div className="text-sm font-semibold text-slate-100 mb-2">Permutation Importance</div>
            {topPermutation.length === 0 ? (
              <div className="text-sm text-slate-400">無資料</div>
            ) : (
              <div className="space-y-1 text-sm text-slate-200">
                {topPermutation.map(item => (
                  <div key={item.feature} className="flex items-center justify-between">
                    <span className="font-mono text-xs break-all text-slate-200">{item.feature}</span>
                    <span>
                      {formatNumber(item.importance, 4)}
                      {item.overfit_flag ? ' ⚠️' : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800/80">
            <div className="text-sm font-semibold text-slate-100 mb-2">Fold-level 穩定性</div>
            {!foldStability ? (
              <div className="text-sm text-slate-400">無資料</div>
            ) : (
              <div className="text-sm text-slate-200 space-y-1">
                <div>穩定特徵：{foldStability.stable_features.length}</div>
                <div>不穩定特徵：{foldStability.unstable_features.length}</div>
              </div>
            )}
          </div>

          <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-800/80">
            <div className="text-sm font-semibold text-slate-100 mb-2">跨幣種泛化</div>
            {!crossSymbol || crossSymbol.length === 0 ? (
              <div className="text-sm text-slate-400">無資料</div>
            ) : (
              <div className="space-y-1 text-sm text-slate-200">
                {crossSymbol.map(item => (
                  <div key={`${item.source_symbol}-${item.target_symbol}`} className="flex items-center justify-between">
                    <span>{item.target_symbol}</span>
                    <span>{formatNumber(item.generalization_gap, 4)} ({item.verdict})</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function FeatureImportanceCard({ features }: { features: FeatureImportance[] }) {
  const topFeatures = features.slice(0, 15)
  const maxImportance = topFeatures.length > 0 ? Math.max(...topFeatures.map(f => f.importance)) : 0

  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100 flex items-center gap-2">
          <List className="w-5 h-5" />
          特徵重要性 (Top 15)
          <div className="group relative">
            <Info className="w-4 h-4 text-slate-500 cursor-help" />
            <div className="absolute left-0 bottom-6 hidden group-hover:block w-72 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
              特徵重要性為模型貢獻比例，% 越高代表模型越依賴此特徵（相對值）。
            </div>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {topFeatures.length === 0 || maxImportance <= 0 ? (
          <div className="text-sm text-slate-400">
            無有效特徵重要性（模型可能未產生分裂或重要性為 0）
          </div>
        ) : (
          <div className="space-y-2">
            {topFeatures.map((feature, idx) => (
              <div key={feature.feature} className="flex items-center gap-3">
                <span className="w-6 text-sm text-slate-400">{idx + 1}</span>
                <div className="flex-1">
                  <div className="grid grid-cols-[1fr_auto] gap-3 mb-1">
                    <span
                      className="text-sm font-mono text-slate-100 break-all whitespace-normal"
                      title={feature.feature}
                    >
                      {feature.feature}
                    </span>
                    <span className="text-sm text-slate-300 whitespace-nowrap">
                      {(feature.importance * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-400 rounded-full"
                      style={{ width: `${(feature.importance / maxImportance) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function DecisionRulesCard({ rules }: { rules: DecisionRule[] }) {
  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100 flex items-center gap-2">
          <Brain className="w-5 h-5" />
          決策規則 (Top 10)
          <div className="group relative">
            <Info className="w-4 h-4 text-slate-500 cursor-help" />
            <div className="absolute left-0 bottom-6 hidden group-hover:block w-80 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
              支持度：符合規則的案例數。信心度：符合規則的案例中為正例的比例。提升度：規則正例率 / 全體正例率（>1 表示優於平均）。
            </div>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {rules.map(rule => (
            <div key={rule.rule_id} className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80">
              <div className="font-mono text-sm text-slate-100 mb-2">
                {rule.condition}
              </div>
              <div className="flex gap-4 text-xs text-slate-300">
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
  const displaySymbols = result.symbols && result.symbols.length > 0
    ? result.symbols.join(', ')
    : result.symbol

  return (
    <div className="space-y-6">
      {/* 摘要資訊 */}
      <Card className="glass-panel border-slate-800/80">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg text-slate-100">分析摘要</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            <div>
              <div className="text-xl font-bold text-slate-100">{displaySymbols}</div>
              <div className="text-xs text-slate-400">交易對</div>
            </div>
            <div>
              <div className="text-xl font-bold text-slate-100">{result.timeframe}</div>
              <div className="text-xs text-slate-400">K 線週期</div>
            </div>
            <div>
              <div className="text-xl font-bold text-slate-100">{result.valid_cases}</div>
              <div className="text-xs text-slate-400">有效案例</div>
            </div>
            <div>
              <div className="text-xl font-bold text-slate-100">{result.features_generated}</div>
              <div className="text-xs text-slate-400">生成特徵數</div>
            </div>
            <div>
              <div className="text-xl font-bold text-emerald-300">
                {result.model_saved ? '已儲存' : '未儲存'}
              </div>
              <div className="text-xs text-slate-400">模型狀態</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 模型性能 */}
      <ModelPerformanceCard performance={result.model_performance} />

      {/* 進階指標 */}
      <AdvancedMetricsCard result={result} />

      {/* 特徵重要性和決策規則 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FeatureImportanceCard features={result.feature_importance} />
        <DecisionRulesCard rules={result.decision_rules} />
      </div>

      {/* 所有特徵名稱 */}
      <Card className="glass-panel border-slate-800/80">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg text-slate-100">所有特徵 ({result.feature_names.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {result.feature_names.map(name => (
              <Badge key={name} variant="outline" className="font-mono text-xs text-slate-200 border-slate-700">
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
  const router = useRouter()
  const { currentAnalysis, setCurrentAnalysis, addPattern } = usePatternStore()
  
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null)
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([])
  const [klineTimeframe, setKlineTimeframe] = useState<string>('12h')
  const [indicators, setIndicators] = useState<IndicatorConfig[]>([])
  const [lookbackBars, setLookbackBars] = useState<number>(200)
  const [sequenceLength, setSequenceLength] = useState<number>(64)
  const [sequenceFeatureMode, setSequenceFeatureMode] = useState<'aggregate' | 'flatten'>('aggregate')
  const [sequenceStride, setSequenceStride] = useState<number>(1)
  const [aggregationMethodsInput, setAggregationMethodsInput] = useState<string>('mean,std,min,max,last,slope')
  const [multiScaleWindowsInput, setMultiScaleWindowsInput] = useState<string>('16,32')
  const [timeSeriesSplit, setTimeSeriesSplit] = useState<boolean>(true)
  const [cvFolds, setCvFolds] = useState<number>(5)
  
  const [isLoading, setIsLoading] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Save pattern state
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [savedPatternId, setSavedPatternId] = useState<string | null>(null)
  
  // Use currentAnalysis from store instead of local state
  const result = currentAnalysis

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

  // Restore configuration from currentAnalysis metadata when returning to page
  useEffect(() => {
    if (currentAnalysis?.metadata) {
      const meta = currentAnalysis.metadata
      
      // 恢復數據選擇配置
      if (meta.data_selection) {
        if (meta.data_selection.symbols && meta.data_selection.symbols.length > 0) {
          setSelectedSymbols([...meta.data_selection.symbols])
        } else if (meta.data_selection.symbol) {
          setSelectedSymbols([meta.data_selection.symbol])
        }
        if (meta.data_selection.timeframe) {
          setKlineTimeframe(meta.data_selection.timeframe)
        }
        if (meta.data_selection.lookback_bars) {
          setLookbackBars(meta.data_selection.lookback_bars)
        }
      }
      
      // 恢復指標配置
      if (meta.indicator_config && meta.indicator_config.length > 0) {
        setIndicators(meta.indicator_config)
      }
      
      // 恢復序列特徵配置
      if (meta.sequence_config) {
        if (meta.sequence_config.sequence_length) {
          setSequenceLength(meta.sequence_config.sequence_length)
        }
        if (meta.sequence_config.sequence_feature_mode) {
          setSequenceFeatureMode(meta.sequence_config.sequence_feature_mode)
        }
        if (meta.sequence_config.sequence_stride) {
          setSequenceStride(meta.sequence_config.sequence_stride)
        }
        if (meta.sequence_config.aggregation_methods) {
          setAggregationMethodsInput(meta.sequence_config.aggregation_methods.join(','))
        }
        if (meta.sequence_config.multi_scale_windows) {
          setMultiScaleWindowsInput(meta.sequence_config.multi_scale_windows.join(','))
        }
      }
      
      // 恢復訓練配置
      if (meta.training_config) {
        if (meta.training_config.time_series_split !== undefined) {
          setTimeSeriesSplit(meta.training_config.time_series_split)
        }
        if (meta.training_config.cv_folds) {
          setCvFolds(meta.training_config.cv_folds)
        }
      }
    }
  }, [currentAnalysis])

  // Poll task status when running
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null

    if (taskId && taskStatus?.status === 'running') {
      interval = setInterval(async () => {
        try {
          const status = await getTaskStatus(taskId)
          setTaskStatus(status)

          if (status.status === 'completed' && status.result) {
            // 將當前的配置信息添加到分析結果中
            const resultWithMetadata: AnalysisResult = {
              ...status.result,
              symbols: status.result.symbols || selectedSymbols,
              metadata: {
                data_selection: {
                  symbol: selectedSymbols[0] || status.result.symbol,
                  symbols: selectedSymbols,
                  timeframe: klineTimeframe,
                  lookback_bars: lookbackBars
                },
                indicator_config: indicators.map(ind => ({
                  indicator: ind.indicator,
                  data_source: ind.data_source,
                  params: ind.params
                })),
                sequence_config: {
                  sequence_length: sequenceLength,
                  sequence_feature_mode: sequenceFeatureMode,
                  sequence_stride: sequenceStride,
                  aggregation_methods: aggregationMethodsInput.split(',').map(m => m.trim()).filter(m => m),
                  multi_scale_windows: multiScaleWindowsInput.split(',').map(w => parseInt(w.trim())).filter(w => !isNaN(w))
                },
                training_config: {
                  time_series_split: timeSeriesSplit,
                  cv_folds: cvFolds
                }
              }
            }
            setCurrentAnalysis(resultWithMetadata)
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
  }, [taskId, taskStatus?.status, selectedSymbols, klineTimeframe, lookbackBars, indicators, sequenceLength, sequenceFeatureMode, sequenceStride, aggregationMethodsInput, multiScaleWindowsInput, timeSeriesSplit, cvFolds])

  const loadCaseSummary = async () => {
    try {
      const summary = await getCaseSummary()
      setCaseSummary(summary)
    } catch (e) {
      console.error('Failed to load case summary:', e)
      setError('無法載入案例統計')
    }
  }

  const handleSavePattern = async () => {
    if (!result) return

    setIsSaving(true)
    setError(null)
    setSaveSuccess(false)

    try {
      const formatMetric = (value: number | null, digits = 4) =>
        value === null || Number.isNaN(value) ? 'N/A' : value.toFixed(digits)
      const safeMetric = (value: number | null) =>
        value === null || Number.isNaN(value) ? 0 : value

      const displaySymbols = result.symbols && result.symbols.length > 0
        ? result.symbols.join('_')
        : result.symbol

      // 將分析結果轉換為 Pattern 格式
      const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace('T', '_').split('.')[0]
      const request: CreatePatternRequest = {
        name: `XGBoost_${displaySymbols}_${result.timeframe}_${timestamp}`,
        description: `XGBoost 分析結果 - ${displaySymbols} ${result.timeframe}\n` +
                     `有效案例: ${result.valid_cases}/${result.total_cases}\n` +
                     `正樣本: ${result.positive_cases}, 負樣本: ${result.negative_cases}\n` +
                     `AUC: ${formatMetric(result.model_performance.cv_auc_mean)} ± ${formatMetric(result.model_performance.cv_auc_std)}\n` +
                     `F1: ${formatMetric(result.model_performance.f1_score)}`,
        rules: result.decision_rules.slice(0, 10).map((rule, index) => {
          // 從 condition 字串抽取第一個單詞作為 feature（如果失敗則使用索引）
          const conditionParts = rule.condition.trim().split(/\s+/)
          const featureName = conditionParts.length > 0 && conditionParts[0] 
            ? conditionParts[0] 
            : `rule_${index + 1}`
          
          return {
            feature: featureName,
            operator: '>=',
            threshold: rule.confidence,
            description: rule.condition || `規則 ${index + 1} (信心度: ${rule.confidence.toFixed(2)})`
          }
        }),
        case_id: `${displaySymbols}_${result.timeframe}`,
        xgboost_importance: result.feature_importance.reduce((acc, feat) => {
          acc[feat.feature] = feat.importance
          return acc
        }, {} as Record<string, number>),
        performance_metrics: {
          precision: safeMetric(result.model_performance.precision),
          recall: safeMetric(result.model_performance.recall),
          f1_score: safeMetric(result.model_performance.f1_score),
          train_auc: safeMetric(result.model_performance.train_auc),
          cv_auc_mean: safeMetric(result.model_performance.cv_auc_mean),
          cv_auc_std: safeMetric(result.model_performance.cv_auc_std),
          overfitting_score: safeMetric(result.model_performance.overfitting_score)
        },
        tags: ['xgboost', ...((result.symbols && result.symbols.length > 0) ? result.symbols : [result.symbol]), result.timeframe, 'auto-generated'],
        metadata: {
          // ===== 結果資料 =====
          total_cases: result.total_cases,
          valid_cases: result.valid_cases,
          features_generated: result.features_generated,
          feature_names: result.feature_names,
          model_saved: result.model_saved,
          model_path: result.model_path,
          created_from: 'xgboost-analysis-page',
          
          // ===== 分析輸入配置參數 =====
          // 數據選擇配置
          data_selection: {
            symbol: result.symbol,
            symbols: result.symbols,
            timeframe: result.timeframe,
            lookback_bars: lookbackBars
          },
          
          // 指標配置
          indicator_config: indicators.map(ind => ({
            indicator: ind.indicator,
            data_source: ind.data_source,
            params: ind.params
          })),
          
          // 序列特徵配置
          sequence_config: {
            sequence_length: sequenceLength,
            sequence_feature_mode: sequenceFeatureMode,
            sequence_stride: sequenceStride,
            aggregation_methods: aggregationMethodsInput.split(',').map(m => m.trim()).filter(m => m),
            multi_scale_windows: multiScaleWindowsInput.split(',').map(w => parseInt(w.trim())).filter(w => !isNaN(w))
          },
          
          // 訓練配置
          training_config: {
            time_series_split: timeSeriesSplit,
            cv_folds: cvFolds
          }
        }
      }

      const response = await createPattern(request)
      
      if (response.success) {
        setSaveSuccess(true)
        setSavedPatternId(response.pattern_id || null)
        
        // 如果返回了完整的 pattern 資料，加入到 store
        if (response.pattern) {
          addPattern(response.pattern)
        }
        
        // 3秒後自動隱藏成功訊息並清理狀態
        setTimeout(() => {
          setSaveSuccess(false)
          setSavedPatternId(null)
        }, 3000)
      } else {
        setError(response.error || '儲存樣式失敗')
      }
    } catch (e: any) {
      // 嘗試從錯誤中提取詳細訊息
      let errorMessage = '儲存樣式失敗'
      if (e.message) {
        errorMessage = e.message
      } else if (typeof e === 'string') {
        errorMessage = e
      }
      setError(errorMessage)
      console.error('儲存樣式錯誤:', e)
    } finally {
      setIsSaving(false)
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
    if (sequenceLength > lookbackBars) {
      setError('序列長度不能大於回看 K 線數量')
      return
    }

    setIsLoading(true)
    setError(null)
    setCurrentAnalysis(null)
    setTaskStatus(null)
    setSaveSuccess(false)
    setSavedPatternId(null)

    try {
      const aggregationMethods = sequenceFeatureMode === 'aggregate'
        ? aggregationMethodsInput
          .split(',')
          .map(method => method.trim())
          .filter(method => method.length > 0)
        : []

      const multiScaleWindows = multiScaleWindowsInput
        .split(',')
        .map(value => parseInt(value.trim(), 10))
        .filter(value => !Number.isNaN(value) && value > 0)

      // 支援多標的跨商品訓練
      const response = await startBatchAnalysis({
        symbols: selectedSymbols,
        timeframe: klineTimeframe,
        indicators,
        lookback_bars: lookbackBars,
        sequence_length: sequenceLength > 0 ? sequenceLength : null,
        sequence_feature_mode: sequenceFeatureMode,
        sequence_stride: sequenceStride,
        aggregation_methods: aggregationMethods.length > 0 ? aggregationMethods : null,
        multi_scale_windows: multiScaleWindows.length > 0 ? multiScaleWindows : null,
        time_series_split: timeSeriesSplit,
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
    <div className="min-h-screen bg-slate-950/40">
      {/* 頁面標題 */}
      <div className="bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <h1 className="text-3xl font-semibold text-slate-100">XGBoost 批量分析</h1>
          <p className="text-slate-400 mt-1">
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
            <Card className="glass-panel border-slate-800/80">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-slate-100">數據選擇</CardTitle>
                <CardDescription className="text-slate-400">
                  選擇要分析的交易對和 K 線時間週期
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 交易對多選 */}
                <div className="space-y-2">
                  <Label className="text-slate-200 font-medium">交易對</Label>
                  <SymbolMultiSelect
                    availableSymbols={caseSummary?.symbols || []}
                    selectedSymbols={selectedSymbols}
                    onChange={setSelectedSymbols}
                  />
                  <p className="text-xs text-slate-500">
                    選擇要納入分析的交易對（將合併所有標的的案例訓練單一跨商品模型）
                  </p>
                </div>

                {/* K 線時間週期 - 獨立於案例 timeframe */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label className="text-slate-200 font-medium">K 線時間週期</Label>
                    <div className="group relative">
                      <Info className="w-4 h-4 text-slate-500 cursor-help" />
                      <div className="absolute left-0 bottom-6 hidden group-hover:block w-64 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                        此為計算指標所用的 K 線週期，可與案例搜尋的 timeframe 不同。
                        例如：案例以 12h 搜尋，但指標計算可用 1h 或 4h K 線。
                      </div>
                    </div>
                  </div>
                  <Select value={klineTimeframe} onValueChange={setKlineTimeframe}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-700 text-slate-100 [&>span]:text-slate-100">
                      <SelectValue placeholder="選擇 K 線週期" className="text-slate-100" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-950 border border-slate-800 shadow-lg z-50">
                      {AVAILABLE_KLINE_TIMEFRAMES.map(tf => (
                        <SelectItem key={tf.value} value={tf.value} className="text-slate-100 hover:bg-slate-900 cursor-pointer">
                          {tf.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* 回看 K 線數量 */}
                <div className="space-y-2 relative z-0">
                  <div className="flex items-center gap-2">
                    <Label className="text-slate-200 font-medium">回看 K 線數量</Label>
                    <div className="group relative">
                      <Info className="w-4 h-4 text-slate-500 cursor-help" />
                      <div className="absolute left-0 bottom-6 hidden group-hover:block w-72 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                        <p className="mb-1"><strong>回看數量 = Warmup + 學習窗口</strong></p>
                        <p className="mb-1">• Warmup：指標穩定所需（如 EMA_60 需 60 根）</p>
                        <p className="mb-1">• 學習窗口：你想分析的 K 線數（如 36 根）</p>
                        <p className="text-amber-300">範例：EMA_60 + 36 根學習 = 填 100</p>
                      </div>
                    </div>
                  </div>
                  <Input
                    type="number"
                    value={lookbackBars}
                    onChange={(e) => setLookbackBars(parseInt(e.target.value) || 200)}
                    className="bg-slate-900/60 border-slate-700 text-slate-100"
                  />
                  <p className="text-xs text-slate-500">
                    公式：Warmup（最長指標週期）+ 學習窗口（想分析的 K 線數）
                  </p>
                </div>

                {/* 序列特徵設定 */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Label className="text-slate-200 font-medium">序列特徵設定</Label>
                    <div className="group relative">
                      <Info className="w-4 h-4 text-slate-500 cursor-help" />
                      <div className="absolute left-0 bottom-6 hidden group-hover:block w-80 p-2 bg-slate-950 text-slate-100 text-xs rounded shadow-lg z-50">
                        <p className="mb-1"><strong>TO 前 N 根序列特徵</strong>，不是只取 T0 單根。</p>
                        <p className="mb-1">• 序列長度：TO 往前 N 根</p>
                        <p className="mb-1">• 步長：序列抽樣間隔</p>
                        <p className="mb-1">• 彙總方法：mean/std/min/max/last/slope</p>
                        <p className="text-amber-300">建議：序列長度 64，步長 1</p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label className="text-slate-200 text-sm">序列長度（N）</Label>
                      <Input
                        type="number"
                        value={sequenceLength}
                        onChange={(e) => setSequenceLength(parseInt(e.target.value) || 0)}
                        className="bg-slate-900/60 border-slate-700 text-slate-100"
                        min={1}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-slate-200 text-sm">序列步長</Label>
                      <Input
                        type="number"
                        value={sequenceStride}
                        onChange={(e) => setSequenceStride(parseInt(e.target.value) || 1)}
                        className="bg-slate-900/60 border-slate-700 text-slate-100"
                        min={1}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-slate-200 text-sm">序列模式</Label>
                    <Select value={sequenceFeatureMode} onValueChange={(value) => setSequenceFeatureMode(value as 'aggregate' | 'flatten')}>
                      <SelectTrigger className="bg-slate-900/60 border-slate-700 text-slate-100 [&>span]:text-slate-100">
                        <SelectValue placeholder="選擇序列模式" className="text-slate-100" />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-950 border border-slate-800 shadow-lg z-50">
                        <SelectItem value="aggregate" className="text-slate-100 hover:bg-slate-900 cursor-pointer">
                          彙總統計（較省資源）
                        </SelectItem>
                        <SelectItem value="flatten" className="text-slate-100 hover:bg-slate-900 cursor-pointer">
                          展平序列（保留形狀）
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {sequenceFeatureMode === 'aggregate' && (
                    <div className="space-y-2">
                      <Label className="text-slate-200 text-sm">彙總方法（逗號分隔）</Label>
                      <Input
                        value={aggregationMethodsInput}
                        onChange={(e) => setAggregationMethodsInput(e.target.value)}
                        className="bg-slate-900/60 border-slate-700 text-slate-100"
                        placeholder="mean,std,min,max,last,slope"
                      />
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label className="text-slate-200 text-sm">多時間尺度窗口（逗號分隔）</Label>
                    <Input
                      value={multiScaleWindowsInput}
                      onChange={(e) => setMultiScaleWindowsInput(e.target.value)}
                      className="bg-slate-900/60 border-slate-700 text-slate-100"
                      placeholder="16,32"
                    />
                    <p className="text-xs text-slate-500">可留空，僅使用序列長度 N</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={timeSeriesSplit}
                      onCheckedChange={(value) => setTimeSeriesSplit(Boolean(value))}
                    />
                    <Label className="text-slate-200 text-sm">啟用時間序列切分（避免洩漏）</Label>
                  </div>
                </div>

                {/* 交叉驗證折數 */}
                <div className="space-y-2">
                  <Label className="text-slate-200 font-medium">交叉驗證折數</Label>
                  <Input
                    type="number"
                    value={cvFolds}
                    onChange={(e) => setCvFolds(parseInt(e.target.value) || 5)}
                    className="bg-slate-900/60 border-slate-700 text-slate-100"
                    min={2}
                    max={10}
                  />
                </div>
              </CardContent>
            </Card>

            {/* 指標配置 */}
            <Card className="glass-panel border-slate-800/80">
              <CardHeader className="pb-3">
                <CardTitle className="text-lg text-slate-100">指標配置</CardTitle>
                <CardDescription className="text-slate-400">
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
              className="w-full bg-emerald-500/20 text-emerald-100 border border-emerald-400/40 hover:bg-emerald-500/30"
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
              <Alert variant="destructive" className="bg-rose-500/10 border-rose-400/30">
                <AlertCircle className="w-4 h-4 text-rose-300" />
                <AlertDescription className="text-rose-200 font-medium">{error}</AlertDescription>
              </Alert>
            )}
          </div>

          {/* 右側：結果面板 */}
          <div className="lg:col-span-2 space-y-6">
            {/* 任務進度 */}
            {taskStatus && <TaskProgressCard task={taskStatus} />}

            {/* 儲存成功訊息 */}
            {saveSuccess && (
              <Alert className="bg-emerald-500/10 border-emerald-400/30">
                <CheckCircle className="w-4 h-4 text-emerald-300" />
                <AlertDescription className="text-emerald-200 font-medium flex items-center justify-between">
                  <span>樣式已成功儲存！</span>
                  {savedPatternId && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => router.push('/patterns')}
                      className="ml-4 border-emerald-400/40 text-emerald-200 hover:bg-emerald-500/20"
                    >
                      前往樣式管理
                    </Button>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {/* 儲存按鈕 */}
            {result && !saveSuccess && (
              <div className="flex gap-3">
                <Button
                  onClick={handleSavePattern}
                  disabled={isSaving}
                  className="bg-emerald-500/20 text-emerald-100 border border-emerald-400/40 hover:bg-emerald-500/30"
                  size="lg"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      儲存中...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      儲存為樣式
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => router.push('/patterns')}
                  className="border-slate-700 text-slate-300 hover:bg-slate-900/60"
                  size="lg"
                >
                  前往樣式管理
                </Button>
                {taskId && (
                  <Button
                    variant="outline"
                    onClick={() => router.push(`/patterns/xgboost-analysis/${taskId}/details`)}
                    className="border-emerald-400/40 text-emerald-200 hover:bg-emerald-500/20"
                    size="lg"
                  >
                    開啟深度分析
                  </Button>
                )}
              </div>
            )}

            {/* 分析結果 */}
            {result && <AnalysisResultView result={result} />}

            {/* 空狀態 */}
            {!result && !taskStatus && (
              <Card className="glass-panel border-slate-800/80">
                <CardContent className="py-12">
                  <div className="text-center">
                    <Brain className="w-16 h-16 mx-auto text-slate-600 mb-4" />
                    <h3 className="text-lg font-semibold text-slate-100 mb-2">
                      尚未執行分析
                    </h3>
                    <p className="text-slate-400">
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
