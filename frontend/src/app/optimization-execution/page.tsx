'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle } from 'lucide-react'
import ExecutionConfigForm from '@/components/optimization/execution/ExecutionConfigForm'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getOptimizationConfig, startExecutionOptimization } from '@/lib/api/optimizationApi'
import { useOptimizationStore } from '@/store/optimizationStore'
import type { ExecutionOptimizationConfig } from '@/lib/types/optimization'

export default function ExecutionOptimizationPage() {
  const router = useRouter()
  const { setExecutionConfig, setError } = useOptimizationStore()

  const [configSchema, setConfigSchema] = useState<Record<string, unknown> | undefined>(undefined)
  const [isLoadingConfig, setIsLoadingConfig] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const config = await getOptimizationConfig()
        setConfigSchema(config.execution)
      } catch (loadError) {
        const message = loadError instanceof Error ? loadError.message : '載入配置失敗'
        console.error('[optimization-execution] load config failed:', loadError)
        setLocalError(message)
        setError(message)
      } finally {
        setIsLoadingConfig(false)
      }
    }

    void loadConfig()
  }, [setError])

  const handleSubmit = async (config: ExecutionOptimizationConfig) => {
    setIsSubmitting(true)
    setLocalError(null)
    try {
      setExecutionConfig(config)
      const response = await startExecutionOptimization(config)
      router.push(`/optimization-execution/result/${response.task_id}`)
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : '啟動任務失敗'
      console.error('[optimization-execution] start task failed:', submitError)
      setLocalError(message)
      setError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoadingConfig) {
    return (
      <div className="p-6">
        <Card>
          <CardHeader>
            <CardTitle>策略執行優化</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-400">載入配置中...</p>
          </CardContent>
        </Card>
      </div>
    )
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

      <ExecutionConfigForm
        configSchema={configSchema}
        isSubmitting={isSubmitting}
        onSubmit={handleSubmit}
      />
    </div>
  )
}
