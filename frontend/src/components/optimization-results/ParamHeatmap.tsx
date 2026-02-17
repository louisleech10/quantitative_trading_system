/**
 * 參數空間熱力圖組件
 *
 * 2D 散點圖顯示參數組合與目標值的關係
 *
 * Author: Claude (Optuna 優化系統 Phase 3)
 * Date: 2025-12-01
 */

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis } from 'recharts'
import { HeatmapData, HeatmapDataPoint } from "@/types/optimization"
import { useState } from "react"
import { Map } from "lucide-react"

interface ParamHeatmapProps {
  heatmapData: HeatmapData
  availableParams: string[]
  onParamsChange?: (paramX: string, paramY: string) => void
}

interface CustomTooltipPayloadItem {
  payload: HeatmapDataPoint
}

interface CustomTooltipProps {
  active?: boolean
  payload?: CustomTooltipPayloadItem[]
}

interface ColoredHeatmapPoint extends HeatmapDataPoint {
  fill: string
}

export function ParamHeatmap({ heatmapData, availableParams, onParamsChange }: ParamHeatmapProps) {
  const [paramX, setParamX] = useState(heatmapData.param_x)
  const [paramY, setParamY] = useState(heatmapData.param_y)

  const handleParamXChange = (value: string) => {
    setParamX(value)
    if (onParamsChange) {
      onParamsChange(value, paramY)
    }
  }

  const handleParamYChange = (value: string) => {
    setParamY(value)
    if (onParamsChange) {
      onParamsChange(paramX, value)
    }
  }

  // 將 value 映射到顏色（使用漸變）
  const getPointColor = (value: number) => {
    const [min, max] = heatmapData.value_range
    const normalized = (value - min) / (max - min)

    const clamp = (val: number) => Math.max(0, Math.min(1, val))
    const hexToRgb = (hex: string) => {
      const parsed = hex.replace('#', '')
      const r = parseInt(parsed.slice(0, 2), 16)
      const g = parseInt(parsed.slice(2, 4), 16)
      const b = parseInt(parsed.slice(4, 6), 16)
      return { r, g, b }
    }
    const rgbToHex = (r: number, g: number, b: number) =>
      `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`
    const lerpColor = (start: string, end: string, t: number) => {
      const s = hexToRgb(start)
      const e = hexToRgb(end)
      return rgbToHex(
        Math.round(s.r + (e.r - s.r) * t),
        Math.round(s.g + (e.g - s.g) * t),
        Math.round(s.b + (e.b - s.b) * t)
      )
    }

    const clamped = clamp(normalized)
    if (clamped <= 0.5) {
      return lerpColor('#fb7185', '#fbbf24', clamped / 0.5)
    }
    return lerpColor('#fbbf24', '#34d399', (clamped - 0.5) / 0.5)
  }

  const scatterData: ColoredHeatmapPoint[] = heatmapData.data_points.map((point) => ({
    ...point,
    fill: getPointColor(point.value)
  }))

  // 自定義 Tooltip
  const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload
      return (
        <div className="bg-popover border rounded-lg shadow-lg p-3">
          <p className="font-semibold text-sm">Trial #{data.trial_number}</p>
          <div className="mt-2 space-y-1 text-xs">
            <p>
              <span className="text-muted-foreground">{paramX}:</span>{' '}
              <span className="font-mono font-semibold">{data.x.toFixed(2)}</span>
            </p>
            <p>
              <span className="text-muted-foreground">{paramY}:</span>{' '}
              <span className="font-mono font-semibold">{data.y.toFixed(2)}</span>
            </p>
            <p className="pt-1 border-t">
              <span className="text-muted-foreground">目標值:</span>{' '}
              <span className="font-mono font-bold text-emerald-400">{data.value.toFixed(6)}</span>
            </p>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Map className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">參數空間熱力圖</CardTitle>
        </div>
        <CardDescription>
          2D 參數組合與目標值映射
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 參數選擇器 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">X 軸參數</label>
            <Select value={paramX} onValueChange={handleParamXChange}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {availableParams.map((param) => (
                  <SelectItem key={param} value={param} className="text-sm">
                    {param}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Y 軸參數</label>
            <Select value={paramY} onValueChange={handleParamYChange}>
              <SelectTrigger className="h-9 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {availableParams.map((param) => (
                  <SelectItem key={param} value={param} className="text-sm">
                    {param}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* 散點圖 */}
        {heatmapData.data_points.length === 0 ? (
          <div className="flex items-center justify-center h-[350px] text-muted-foreground">
            暫無數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 60 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                type="number"
                dataKey="x"
                name={paramX}
                label={{ value: paramX, position: 'bottom', className: 'text-xs' }}
                className="text-xs"
              />
              <YAxis
                type="number"
                dataKey="y"
                name={paramY}
                label={{ value: paramY, angle: -90, position: 'left', className: 'text-xs' }}
                className="text-xs"
              />
              <ZAxis type="number" dataKey="value" range={[50, 400]} />
              <Tooltip
                content={({ active, payload }) => (
                  <CustomTooltip
                    active={active}
                    payload={payload as CustomTooltipPayloadItem[] | undefined}
                  />
                )}
              />
              <Scatter
                data={scatterData}
                fill="#60a5fa"
              />
            </ScatterChart>
          </ResponsiveContainer>
        )}

        {/* 顏色圖例 */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-16 h-4 rounded" style={{ background: 'linear-gradient(to right, #fb7185, #fbbf24, #34d399)' }} />
            <span className="text-muted-foreground">
              低 ({heatmapData.value_range[0].toFixed(3)}) → 高 ({heatmapData.value_range[1].toFixed(3)})
            </span>
          </div>
        </div>

        {/* 閱讀指南 */}
        <div className="mt-4 p-3 bg-muted/30 rounded-lg space-y-2">
          <p className="text-xs font-medium text-foreground">📖 如何閱讀熱力圖</p>
          <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
            <li><span className="text-emerald-400">●</span> <strong>綠色點</strong>：該參數組合的目標值較高（表現較好）</li>
            <li><span className="text-amber-400">●</span> <strong>黃色點</strong>：該參數組合的目標值中等</li>
            <li><span className="text-rose-400">●</span> <strong>紅色點</strong>：該參數組合的目標值較低（表現較差）</li>
            <li><strong>點的位置</strong>：代表兩個參數的具體數值組合</li>
            <li><strong>分析技巧</strong>：觀察綠色點的聚集區域，找出最佳參數範圍</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
