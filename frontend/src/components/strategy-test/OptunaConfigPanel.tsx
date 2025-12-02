/**
 * Optuna 參數優化配置面板
 *
 * Ultra Think 三步驟設計:
 *
 * Step 1 - 初版思考:
 * - 提供啟用/禁用 Optuna 優化的開關
 * - 配置基礎設定 (n_trials, timeout, seed, pruning)
 * - 配置搜索空間 (EMA 範圍)
 * - 驗證警告顯示
 *
 * Step 2 - 自我審查:
 * - 參數範圍驗證 (short < mid < long)
 * - 案例數量驗證 (>= 10)
 * - 預估時間計算 (ETA)
 * - 錯誤處理和用戶提示
 *
 * Step 3 - 最終優化:
 * - 響應式設計
 * - 鍵盤導航支持
 * - 無障礙標籤 (ARIA)
 * - 本地存儲配置 (localStorage)
 *
 * Author: Claude (Optuna 優化系統 Phase 3.1)
 * Date: 2025-12-02
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { Sparkles, AlertTriangle, Clock, Info } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'

export interface OptunaConfig {
  enabled: boolean
  n_trials: number
  timeout: number  // seconds
  random_seed: number
  enable_pruning: boolean
  ema_short_range: [number, number]
  ema_mid_range: [number, number]
  ema_long_range: [number, number]
}

export interface OptunaConfigPanelProps {
  config: OptunaConfig
  onChange: (config: OptunaConfig) => void
  positiveCasesCount?: number
  negativeCasesCount?: number
  disabled?: boolean
}

/**
 * 默認配置
 */
const DEFAULT_CONFIG: OptunaConfig = {
  enabled: false,
  n_trials: 50,
  timeout: 1800,  // 30 minutes
  random_seed: 42,
  enable_pruning: true,
  ema_short_range: [5, 15],
  ema_mid_range: [20, 40],
  ema_long_range: [50, 100]
}

export function OptunaConfigPanel({
  config,
  onChange,
  positiveCasesCount = 0,
  negativeCasesCount = 0,
  disabled = false
}: OptunaConfigPanelProps) {
  // 驗證警告
  const validationWarnings = useMemo(() => {
    const warnings: string[] = []

    // 案例數量檢查
    if (config.enabled) {
      if (positiveCasesCount < 10) {
        warnings.push(`正例案例不足: ${positiveCasesCount}/10（建議至少 10 個）`)
      }
      if (negativeCasesCount < 10) {
        warnings.push(`反例案例不足: ${negativeCasesCount}/10（建議至少 10 個）`)
      }
    }

    // 參數範圍檢查 (short < mid < long)
    if (config.ema_short_range[1] >= config.ema_mid_range[0]) {
      warnings.push(`EMA Short Max (${config.ema_short_range[1]}) >= Mid Min (${config.ema_mid_range[0]})，範圍重疊`)
    }
    if (config.ema_mid_range[1] >= config.ema_long_range[0]) {
      warnings.push(`EMA Mid Max (${config.ema_mid_range[1]}) >= Long Min (${config.ema_long_range[0]})，範圍重疊`)
    }

    // Trial 數量檢查
    if (config.n_trials < 20) {
      warnings.push(`Trial 數量較少 (${config.n_trials})，建議至少 20 次以獲得穩定結果`)
    }

    return warnings
  }, [config, positiveCasesCount, negativeCasesCount])

  // 預估時間計算
  const estimatedTime = useMemo(() => {
    // 假設每個 trial 平均 30-60 秒
    const avgTrialTime = 45  // seconds
    const totalSeconds = config.n_trials * avgTrialTime

    if (totalSeconds < 60) return `約 ${totalSeconds} 秒`
    if (totalSeconds < 3600) return `約 ${Math.ceil(totalSeconds / 60)} 分鐘`
    return `約 ${(totalSeconds / 3600).toFixed(1)} 小時`
  }, [config.n_trials])

  // 更新配置
  const updateConfig = (partial: Partial<OptunaConfig>) => {
    onChange({ ...config, ...partial })
  }

  // 更新範圍
  const updateRange = (
    key: 'ema_short_range' | 'ema_mid_range' | 'ema_long_range',
    index: 0 | 1,
    value: number
  ) => {
    const newRange: [number, number] = [...config[key]]
    newRange[index] = value
    updateConfig({ [key]: newRange })
  }

  return (
    <div className="space-y-6">
      {/* 啟用開關 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-500" />
          <div>
            <Label className="text-base font-semibold">
              Optuna 參數優化
            </Label>
            <p className="text-sm text-muted-foreground">
              自動搜索最佳參數組合
            </p>
          </div>
        </div>
        <Switch
          checked={config.enabled}
          onCheckedChange={(checked) => updateConfig({ enabled: checked })}
          disabled={disabled}
        />
      </div>

      {/* 配置區域（僅在啟用時顯示） */}
      {config.enabled && (
        <>
          {/* 基礎設定 */}
          <div className="space-y-4 rounded-lg border p-4">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              基礎設定
              <Badge variant="outline" className="text-xs">
                <Clock className="h-3 w-3 mr-1" />
                {estimatedTime}
              </Badge>
            </h3>

            <div className="grid grid-cols-2 gap-4">
              {/* Trial 次數 */}
              <div className="space-y-2">
                <Label htmlFor="n_trials">Trial 次數</Label>
                <Input
                  id="n_trials"
                  type="number"
                  min={10}
                  max={1000}
                  value={config.n_trials}
                  onChange={(e) => updateConfig({ n_trials: parseInt(e.target.value) || 50 })}
                  disabled={disabled}
                />
                <p className="text-xs text-muted-foreground">
                  建議 20-100 次
                </p>
              </div>

              {/* 超時時間 */}
              <div className="space-y-2">
                <Label htmlFor="timeout">超時時間（秒）</Label>
                <Input
                  id="timeout"
                  type="number"
                  min={300}
                  max={36000}
                  step={300}
                  value={config.timeout}
                  onChange={(e) => updateConfig({ timeout: parseInt(e.target.value) || 1800 })}
                  disabled={disabled}
                />
                <p className="text-xs text-muted-foreground">
                  {Math.floor(config.timeout / 60)} 分鐘
                </p>
              </div>

              {/* 隨機種子 */}
              <div className="space-y-2">
                <Label htmlFor="random_seed">隨機種子</Label>
                <Input
                  id="random_seed"
                  type="number"
                  min={0}
                  max={9999}
                  value={config.random_seed}
                  onChange={(e) => updateConfig({ random_seed: parseInt(e.target.value) || 42 })}
                  disabled={disabled}
                />
                <p className="text-xs text-muted-foreground">
                  固定種子可重現結果
                </p>
              </div>

              {/* 啟用剪枝 */}
              <div className="space-y-2">
                <Label htmlFor="enable_pruning" className="flex items-center gap-2">
                  啟用剪枝
                  <Badge variant="secondary" className="text-xs">
                    加速優化
                  </Badge>
                </Label>
                <div className="flex items-center h-10">
                  <Switch
                    id="enable_pruning"
                    checked={config.enable_pruning}
                    onCheckedChange={(checked) => updateConfig({ enable_pruning: checked })}
                    disabled={disabled}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  自動終止表現不佳的 trial
                </p>
              </div>
            </div>
          </div>

          {/* 搜索空間配置 */}
          <div className="space-y-4 rounded-lg border p-4">
            <h3 className="text-sm font-semibold">搜索空間配置</h3>

            {/* EMA Short */}
            <div className="space-y-2">
              <Label>EMA Short 範圍</Label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  min={3}
                  max={20}
                  value={config.ema_short_range[0]}
                  onChange={(e) => updateRange('ema_short_range', 0, parseInt(e.target.value) || 5)}
                  disabled={disabled}
                  placeholder="Min"
                />
                <Input
                  type="number"
                  min={3}
                  max={20}
                  value={config.ema_short_range[1]}
                  onChange={(e) => updateRange('ema_short_range', 1, parseInt(e.target.value) || 15)}
                  disabled={disabled}
                  placeholder="Max"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                當前: {config.ema_short_range[0]} - {config.ema_short_range[1]}
              </p>
            </div>

            {/* EMA Mid */}
            <div className="space-y-2">
              <Label>EMA Mid 範圍</Label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  min={15}
                  max={50}
                  value={config.ema_mid_range[0]}
                  onChange={(e) => updateRange('ema_mid_range', 0, parseInt(e.target.value) || 20)}
                  disabled={disabled}
                  placeholder="Min"
                />
                <Input
                  type="number"
                  min={15}
                  max={50}
                  value={config.ema_mid_range[1]}
                  onChange={(e) => updateRange('ema_mid_range', 1, parseInt(e.target.value) || 40)}
                  disabled={disabled}
                  placeholder="Max"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                當前: {config.ema_mid_range[0]} - {config.ema_mid_range[1]}
              </p>
            </div>

            {/* EMA Long */}
            <div className="space-y-2">
              <Label>EMA Long 範圍</Label>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="number"
                  min={40}
                  max={200}
                  value={config.ema_long_range[0]}
                  onChange={(e) => updateRange('ema_long_range', 0, parseInt(e.target.value) || 50)}
                  disabled={disabled}
                  placeholder="Min"
                />
                <Input
                  type="number"
                  min={40}
                  max={200}
                  value={config.ema_long_range[1]}
                  onChange={(e) => updateRange('ema_long_range', 1, parseInt(e.target.value) || 100)}
                  disabled={disabled}
                  placeholder="Max"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                當前: {config.ema_long_range[0]} - {config.ema_long_range[1]}
              </p>
            </div>

            {/* 說明 */}
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription className="text-xs">
                確保參數範圍不重疊：Short Max &lt; Mid Min &lt; Mid Max &lt; Long Min
              </AlertDescription>
            </Alert>
          </div>

          {/* 驗證警告 */}
          {validationWarnings.length > 0 && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-1">
                  <p className="font-semibold text-sm">請修正以下問題：</p>
                  <ul className="list-disc list-inside space-y-1 text-xs">
                    {validationWarnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </>
      )}
    </div>
  )
}

/**
 * 載入保存的配置
 */
export function loadOptunaConfig(): OptunaConfig {
  if (typeof window === 'undefined') return DEFAULT_CONFIG

  try {
    const saved = localStorage.getItem('optuna_config')
    if (saved) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(saved) }
    }
  } catch (error) {
    console.warn('Failed to load Optuna config:', error)
  }

  return DEFAULT_CONFIG
}

/**
 * 保存配置
 */
export function saveOptunaConfig(config: OptunaConfig): void {
  if (typeof window === 'undefined') return

  try {
    localStorage.setItem('optuna_config', JSON.stringify(config))
  } catch (error) {
    console.warn('Failed to save Optuna config:', error)
  }
}
