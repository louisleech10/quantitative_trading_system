'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import ParameterRangeSlider from '@/components/optimization/common/ParameterRangeSlider'
import SamplerSelector from '@/components/optimization/common/SamplerSelector'
import type { HyperparamOptimizationConfig, ModelType } from '@/lib/types/optimization'

interface HyperparamConfigFormProps {
  configSchema?: Record<string, unknown>
  onSubmit: (config: HyperparamOptimizationConfig) => Promise<void>
  isSubmitting: boolean
}

export default function HyperparamConfigForm({
  configSchema,
  onSubmit,
  isSubmitting,
}: HyperparamConfigFormProps) {
  const [modelType, setModelType] = useState<ModelType>('lightgbm')
  const [featuresPath, setFeaturesPath] = useState('')
  const [labelsPath, setLabelsPath] = useState('')
  const [nTrials, setNTrials] = useState(100)
  const [timeoutSeconds, setTimeoutSeconds] = useState(1800)
  const [maxTrainValGap, setMaxTrainValGap] = useState(0.1)
  const [cvFolds, setCvFolds] = useState(5)
  const [sampler, setSampler] = useState('TPE')

  const schemaText = useMemo(() => {
    if (!configSchema) {
      return '尚未載入搜索空間設定'
    }
    return JSON.stringify(configSchema[modelType] || {}, null, 2)
  }, [configSchema, modelType])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()

    await onSubmit({
      model_type: modelType,
      features_path: featuresPath,
      labels_path: labelsPath,
      n_trials: nTrials,
      timeout_seconds: timeoutSeconds,
      max_train_val_gap: maxTrainValGap,
      cv_folds: cvFolds,
      search_space_override: { sampler },
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>超參數優化配置</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <Tabs value={modelType} onValueChange={(value) => setModelType(value as ModelType)}>
            <TabsList>
              <TabsTrigger value="lightgbm">LightGBM</TabsTrigger>
              <TabsTrigger value="xgboost">XGBoost</TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-sm text-slate-300">features_path</p>
              <Input value={featuresPath} onChange={(event) => setFeaturesPath(event.target.value)} required />
            </div>
            <div>
              <p className="mb-2 text-sm text-slate-300">labels_path</p>
              <Input value={labelsPath} onChange={(event) => setLabelsPath(event.target.value)} required />
            </div>
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
            <ParameterRangeSlider label="cv_folds" min={2} max={20} value={cvFolds} onChange={setCvFolds} />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <ParameterRangeSlider
              label="max_train_val_gap"
              min={0}
              max={0.5}
              step={0.01}
              value={maxTrainValGap}
              onChange={setMaxTrainValGap}
            />
            <SamplerSelector value={sampler} onChange={setSampler} />
          </div>

          <div>
            <p className="mb-2 text-sm text-slate-300">搜索空間（由 API 配置）</p>
            <pre className="max-h-60 overflow-auto rounded-md border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
              {schemaText}
            </pre>
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? '啟動中...' : '啟動超參數優化'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
