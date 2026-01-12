/**
 * MultiIndicatorConfig.tsx - 多指標配置組件
 * 
 * 功能：
 * 1. 配置多個指標組合（EMA + RSI + MACD）
 * 2. 動態添加/刪除指標
 * 3. 每個指標獨立配置參數和數據源
 * 4. 預覽生成的特徵名稱
 * 
 * Author: AI Agent
 * Date: 2026-01-11
 */

'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Plus, Trash2, Eye } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface IndicatorConfig {
  id: string
  indicator: string
  data_source: string
  params: Record<string, any>
}

interface MultiIndicatorConfigProps {
  value: IndicatorConfig[]
  onChange: (configs: IndicatorConfig[]) => void
}

// 可用指標定義
const AVAILABLE_INDICATORS = [
  {
    value: 'ema_three_line',
    label: 'EMA 三線順勢',
    params: {
      ema_short: { type: 'number', label: '短期 EMA', default: 5 },
      ema_mid: { type: 'number', label: '中期 EMA', default: 20 },
      ema_long: { type: 'number', label: '長期 EMA', default: 60 },
      volume_threshold: { type: 'number', label: '成交量閾值', default: 0.6, step: 0.1, min: 0, max: 1 }
    }
  },
  {
    value: 'rsi',
    label: 'RSI 指標',
    params: {
      period: { type: 'number', label: '週期', default: 14 },
      overbought: { type: 'number', label: '超買線', default: 70 },
      oversold: { type: 'number', label: '超賣線', default: 30 }
    }
  },
  {
    value: 'macd',
    label: 'MACD 指標',
    params: {
      fast: { type: 'number', label: '快線', default: 12 },
      slow: { type: 'number', label: '慢線', default: 26 },
      signal: { type: 'number', label: '信號線', default: 9 }
    }
  }
]

const DATA_SOURCES = [
  { value: 'close', label: 'Close（收盤價）' },
  { value: 'open', label: 'Open（開盤價）' },
  { value: 'high', label: 'High（最高價）' },
  { value: 'low', label: 'Low（最低價）' },
  { value: 'volume', label: 'Volume（成交量）' },
  { value: 'taker_ratio', label: 'Taker Ratio（主動買入比）' }
]

export default function MultiIndicatorConfig({ value = [], onChange }: MultiIndicatorConfigProps) {
  const [previewFeatures, setPreviewFeatures] = useState<string[]>([])
  const [showPreview, setShowPreview] = useState(false)

  // 初始化：如果 value 是空的，添加一個預設指標
  useEffect(() => {
    if (value.length === 0) {
      const defaultIndicator: IndicatorConfig = {
        id: `indicator_${Date.now()}`,
        indicator: 'ema_three_line',
        data_source: 'close',
        params: {
          ema_short: 5,
          ema_mid: 20,
          ema_long: 60,
          volume_threshold: 0.6
        }
      }
      onChange([defaultIndicator])
    }
  }, [])

  // 添加指標
  const handleAddIndicator = () => {
    const newIndicator: IndicatorConfig = {
      id: `indicator_${Date.now()}`,
      indicator: 'ema_three_line',
      data_source: 'close',
      params: {
        ema_short: 5,
        ema_mid: 20,
        ema_long: 60,
        volume_threshold: 0.6
      }
    }
    onChange([...value, newIndicator])
  }

  // 刪除指標
  const handleRemoveIndicator = (id: string) => {
    onChange(value.filter(config => config.id !== id))
  }

  // 更新指標類型
  const handleIndicatorChange = (id: string, indicator: string) => {
    const indicatorDef = AVAILABLE_INDICATORS.find(i => i.value === indicator)
    if (!indicatorDef) return

    // 生成默認參數
    const defaultParams: Record<string, any> = {}
    Object.entries(indicatorDef.params).forEach(([key, config]) => {
      defaultParams[key] = config.default
    })

    onChange(value.map(config =>
      config.id === id
        ? { ...config, indicator, params: defaultParams }
        : config
    ))
  }

  // 更新數據源
  const handleDataSourceChange = (id: string, dataSource: string) => {
    onChange(value.map(config =>
      config.id === id
        ? { ...config, data_source: dataSource }
        : config
    ))
  }

  // 更新參數
  const handleParamChange = (id: string, paramKey: string, paramValue: any) => {
    onChange(value.map(config =>
      config.id === id
        ? { ...config, params: { ...config.params, [paramKey]: paramValue } }
        : config
    ))
  }

  // 預覽特徵名稱
  const handlePreview = () => {
    const features: string[] = []
    
    value.forEach(config => {
      const { indicator, data_source, params } = config
      
      if (indicator === 'ema_three_line') {
        features.push(`${data_source}_ema${params.ema_short}_value`)
        features.push(`${data_source}_ema${params.ema_mid}_value`)
        features.push(`${data_source}_ema${params.ema_long}_value`)
        features.push(`${data_source}_ema${params.ema_short}_${params.ema_mid}_distance`)
        features.push(`${data_source}_ema_trend_aligned`)
      } else if (indicator === 'rsi') {
        features.push(`${data_source}_rsi${params.period}_value`)
        features.push(`${data_source}_rsi${params.period}_${params.overbought}_signal`)
        features.push(`${data_source}_rsi${params.period}_${params.oversold}_signal`)
      } else if (indicator === 'macd') {
        features.push(`${data_source}_macd${params.fast}_${params.slow}_line`)
        features.push(`${data_source}_macd${params.fast}_${params.slow}_${params.signal}_signal`)
        features.push(`${data_source}_macd${params.fast}_${params.slow}_${params.signal}_histogram`)
      }
    })
    
    setPreviewFeatures(features)
    setShowPreview(true)
  }

  return (
    <div className="space-y-4">
      {/* 指標列表 */}
      {value.map((config, index) => {
        const indicatorDef = AVAILABLE_INDICATORS.find(i => i.value === config.indicator)
        
        return (
          <Card key={config.id}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="text-base">指標 #{index + 1}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRemoveIndicator(config.id)}
                  disabled={value.length === 1}
                >
                  <Trash2 className="h-4 w-4 text-red-500" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 指標類型 */}
              <div className="space-y-2">
                <Label>指標類型</Label>
                <Select
                  value={config.indicator}
                  onValueChange={(val) => handleIndicatorChange(config.id, val)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AVAILABLE_INDICATORS.map(indicator => (
                      <SelectItem key={indicator.value} value={indicator.value}>
                        {indicator.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* 數據源 */}
              <div className="space-y-2">
                <Label>數據源</Label>
                <Select
                  value={config.data_source}
                  onValueChange={(val) => handleDataSourceChange(config.id, val)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DATA_SOURCES.map(source => (
                      <SelectItem key={source.value} value={source.value}>
                        {source.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* 參數配置 */}
              {indicatorDef && (
                <div className="space-y-3">
                  <Label>參數配置</Label>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(indicatorDef.params).map(([paramKey, paramConfig]) => (
                      <div key={paramKey} className="space-y-1">
                        <Label className="text-xs">{paramConfig.label}</Label>
                        <Input
                          type="number"
                          value={config.params[paramKey] || paramConfig.default}
                          onChange={(e) => handleParamChange(
                            config.id,
                            paramKey,
                            paramConfig.type === 'number' ? parseFloat(e.target.value) : e.target.value
                          )}
                          step={paramConfig.step || 1}
                          min={paramConfig.min}
                          max={paramConfig.max}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}

      {/* 操作按鈕 */}
      <div className="flex gap-2">
        <Button onClick={handleAddIndicator} variant="outline">
          <Plus className="h-4 w-4 mr-2" />
          添加指標
        </Button>
        <Button onClick={handlePreview} variant="outline">
          <Eye className="h-4 w-4 mr-2" />
          預覽特徵
        </Button>
      </div>

      {/* 特徵預覽 */}
      {showPreview && (
        <Alert>
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold">將生成 {previewFeatures.length} 個特徵：</p>
              <div className="flex flex-wrap gap-2">
                {previewFeatures.map(feature => (
                  <Badge key={feature} variant="secondary" className="font-mono text-xs">
                    {feature}
                  </Badge>
                ))}
              </div>
            </div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
