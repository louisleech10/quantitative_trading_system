'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import ParameterRangeSlider from '@/components/optimization/common/ParameterRangeSlider'
import type { ExecutionOptimizationConfig, TargetMetric } from '@/lib/types/optimization'

interface ExecutionConfigFormProps {
  configSchema?: Record<string, unknown>
  onSubmit: (config: ExecutionOptimizationConfig) => Promise<void>
  isSubmitting: boolean
}

export default function ExecutionConfigForm({
  configSchema,
  onSubmit,
  isSubmitting,
}: ExecutionConfigFormProps) {
  const defaultPredictionPath = 'model_predictions_{task_id}.csv'
  const [modelPredictionsPath, setModelPredictionsPath] = useState('')
  const [dataSourceMode, setDataSourceMode] = useState('manual')
  const [targetMetric, setTargetMetric] = useState<TargetMetric>('expectancy')
  const [nTrials, setNTrials] = useState(100)
  const [timeoutSeconds, setTimeoutSeconds] = useState(300)
  const [positionSizingMethod, setPositionSizingMethod] = useState('fixed')
  const [maxDrawdown, setMaxDrawdown] = useState(-0.3)
  const [minWinRate, setMinWinRate] = useState(0.4)
  const [minTrades, setMinTrades] = useState(10)
  const [multiObjective, setMultiObjective] = useState(false)
  const [commission, setCommission] = useState(0.001)
  const [slippage, setSlippage] = useState(0.0005)
  const [searchSpaceOverrideText, setSearchSpaceOverrideText] = useState('{}')
  const [searchSpaceError, setSearchSpaceError] = useState<string | null>(null)

  const schemaText = useMemo(() => {
    if (!configSchema) {
      return '尚未載入搜索空間設定'
    }
    return JSON.stringify(configSchema.search_space || configSchema, null, 2)
  }, [configSchema])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()

    let searchSpaceOverride: Record<string, unknown> = {
      position_sizing_method: positionSizingMethod,
    }

    try {
      const parsed = JSON.parse(searchSpaceOverrideText)
      if (parsed && typeof parsed === 'object') {
        searchSpaceOverride = {
          ...searchSpaceOverride,
          ...parsed,
        }
      }
      setSearchSpaceError(null)
    } catch {
      setSearchSpaceError('search_space_override JSON 格式錯誤')
      return
    }

    const resolvedPath = dataSourceMode === 'template' ? defaultPredictionPath : modelPredictionsPath

    await onSubmit({
      model_predictions_path: resolvedPath,
      target_metric: targetMetric,
      n_trials: nTrials,
      timeout_seconds: timeoutSeconds,
      constraints: {
        max_drawdown: maxDrawdown,
        min_win_rate: minWinRate,
        min_trades: minTrades,
      },
      backtest_config: {
        commission,
        slippage,
      },
      search_space_override: searchSpaceOverride,
      multi_objective: multiObjective,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>策略執行優化配置</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <p className="mb-2 text-sm text-slate-300">數據源選擇（模型訓練任務）</p>
            <Select value={dataSourceMode} onValueChange={setDataSourceMode}>
              <SelectTrigger>
                <SelectValue placeholder="選擇數據源模式" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual">手動輸入路徑</SelectItem>
                <SelectItem value="template">使用契約範本路徑</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <p className="mb-2 text-sm text-slate-300">model_predictions_path</p>
            <Input
              value={modelPredictionsPath}
              onChange={(event) => setModelPredictionsPath(event.target.value)}
              disabled={dataSourceMode === 'template'}
              placeholder={defaultPredictionPath}
              required={dataSourceMode !== 'template'}
            />
            {dataSourceMode === 'template' && (
              <p className="mt-1 text-xs text-slate-400">目前使用：{defaultPredictionPath}</p>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <ParameterRangeSlider label="n_trials" min={1} max={1000} value={nTrials} onChange={setNTrials} />
            <ParameterRangeSlider
              label="timeout_seconds"
              min={30}
              max={7200}
              step={30}
              value={timeoutSeconds}
              onChange={setTimeoutSeconds}
            />
            <div className="space-y-2">
              <p className="text-sm text-slate-300">優化目標（5 種）</p>
              <div className="grid grid-cols-1 gap-2 rounded-md border border-white/10 bg-white/5 p-3 text-sm text-slate-300">
                {(['expectancy', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'sqn'] as const).map((metric) => (
                  <label key={metric} className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="target_metric"
                      value={metric}
                      checked={targetMetric === metric}
                      onChange={() => setTargetMetric(metric)}
                    />
                    <span>{metric}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <p className="text-sm text-slate-300">倉位管理方法</p>
              <Select value={positionSizingMethod} onValueChange={setPositionSizingMethod}>
                <SelectTrigger>
                  <SelectValue placeholder="選擇倉位管理" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fixed">fixed</SelectItem>
                  <SelectItem value="kelly">kelly</SelectItem>
                  <SelectItem value="probability_scaled">probability_scaled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-slate-300">多目標優化</p>
              <div className="flex items-center gap-3 rounded-md border border-white/10 bg-white/5 p-3">
                <Switch checked={multiObjective} onCheckedChange={setMultiObjective} />
                <span className="text-sm text-slate-300">啟用 Pareto 前沿</span>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <ParameterRangeSlider
              label="max_drawdown"
              min={-0.9}
              max={0}
              step={0.01}
              value={maxDrawdown}
              onChange={setMaxDrawdown}
            />
            <ParameterRangeSlider
              label="min_win_rate"
              min={0}
              max={1}
              step={0.01}
              value={minWinRate}
              onChange={setMinWinRate}
            />
            <ParameterRangeSlider
              label="min_trades"
              min={1}
              max={200}
              value={minTrades}
              onChange={setMinTrades}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <ParameterRangeSlider
              label="commission"
              min={0}
              max={0.01}
              step={0.0001}
              value={commission}
              onChange={setCommission}
            />
            <ParameterRangeSlider
              label="slippage"
              min={0}
              max={0.01}
              step={0.0001}
              value={slippage}
              onChange={setSlippage}
            />
          </div>

          <div>
            <p className="mb-2 text-sm text-slate-300">搜索空間（由 API 配置）</p>
            <pre className="max-h-60 overflow-auto rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
              {schemaText}
            </pre>
          </div>

          <div>
            <p className="mb-2 text-sm text-slate-300">可編輯搜索空間覆寫（JSON）</p>
            <Textarea
              value={searchSpaceOverrideText}
              onChange={(event) => setSearchSpaceOverrideText(event.target.value)}
              rows={6}
            />
            {searchSpaceError && <p className="mt-1 text-xs text-red-400">{searchSpaceError}</p>}
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? '啟動中...' : '啟動策略執行優化'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
