/**
 * 穩定性分析圖表組件
 *
 * 顯示月度穩定性統計和變異情況
 *
 * Author: Claude (Optuna 優化系統 Phase 3)
 * Date: 2025-12-01
 */

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ErrorBar, Cell } from 'recharts'
import { StabilityAnalysis } from "@/types/optimization"
import { Activity, AlertTriangle } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface StabilityChartProps {
  stabilityData: StabilityAnalysis
}

export function StabilityChart({ stabilityData }: StabilityChartProps) {
  // 自定義 Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-popover border rounded-lg shadow-lg p-3">
          <p className="font-semibold text-sm">{data.month}</p>
          <div className="mt-2 space-y-1 text-xs">
            <p>
              <span className="text-muted-foreground">M Separation:</span>{' '}
              <span className="font-mono font-bold">{data.mean_value.toFixed(6)}</span>
            </p>
            <p>
              <span className="text-muted-foreground">標準差:</span>{' '}
              <span className="font-mono">{data.std_value.toFixed(6)}</span>
            </p>
            <p>
              <span className="text-muted-foreground">案例數:</span>{' '}
              <span className="font-mono">{data.n_trials}</span>
            </p>
            {data.is_worst_month && (
              <p className="pt-1 border-t text-red-600 font-medium">
                ⚠️ 最差月份
              </p>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  // 根據是否為最差月份決定顏色
  const getBarColor = (isWorstMonth: boolean) => {
    return isWorstMonth ? 'hsl(0, 84%, 60%)' : 'hsl(217, 91%, 60%)'
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">穩定性分析</CardTitle>
          </div>
          <Badge variant="outline" className="text-xs">
            CV: {(stabilityData.overall_cv * 100).toFixed(2)}%
          </Badge>
        </div>
        <CardDescription>
          M Separation 月度穩定性分析 - CV 值衡量每月正反例差異的穩定性
          {stabilityData.worst_month && (
            <span className="ml-2 text-red-600 font-medium">
              · 最差月份: {stabilityData.worst_month}
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {stabilityData.monthly_stats.length === 0 ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            暫無數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={stabilityData.monthly_stats}
              margin={{ top: 20, right: 30, left: 20, bottom: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="month"
                angle={-45}
                textAnchor="end"
                height={80}
                className="text-xs"
              />
              <YAxis
                label={{ value: 'M Separation', angle: -90, position: 'left', className: 'text-xs' }}
                className="text-xs"
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="mean_value" radius={[4, 4, 0, 0]}>
                <ErrorBar
                  dataKey="std_value"
                  width={4}
                  strokeWidth={2}
                  stroke="hsl(215, 16%, 47%)"
                />
                {stabilityData.monthly_stats.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getBarColor(entry.is_worst_month)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}

        {/* 說明與警告 */}
        <div className="mt-4 pt-4 border-t space-y-2">
          <p className="text-xs text-muted-foreground">
            💡 CV (變異係數) 越小表示穩定性越好
          </p>
          {stabilityData.overall_cv > 0.3 && (
            <div className="flex items-start gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
              <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">穩定性警告</p>
                <p>CV 值較高 ({(stabilityData.overall_cv * 100).toFixed(2)}%)，結果可能不夠穩定</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
