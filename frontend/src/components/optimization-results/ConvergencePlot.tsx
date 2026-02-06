/**
 * 收斂曲線組件
 *
 * 顯示優化過程中目標值的收斂情況
 *
 * Author: Claude (Optuna 優化系統 Phase 3)
 * Date: 2025-12-01
 */

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts'
import { ConvergenceAnalysis } from "@/types/optimization"
import { TrendingDown, CheckCircle2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface ConvergencePlotProps {
  convergenceData: ConvergenceAnalysis
}

export function ConvergencePlot({ convergenceData }: ConvergencePlotProps) {
  // 自定義 Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-popover border rounded-lg shadow-lg p-3">
          <p className="font-semibold text-sm">Trial #{data.trial}</p>
          <p className="text-xs text-muted-foreground mt-1">
            最佳值: <span className="font-mono font-bold text-emerald-400">{data.value.toFixed(6)}</span>
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">收斂曲線</CardTitle>
          </div>
          {convergenceData.converged && (
            <Badge variant="outline" className="bg-emerald-400/10 text-emerald-300 border-emerald-400/30">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              已收斂
            </Badge>
          )}
        </div>
        <CardDescription>
          {convergenceData.converged
            ? `在 Trial #${convergenceData.convergence_trial} 達到收斂`
            : `改進速度: ${(convergenceData.improvement_rate * 100).toFixed(2)}%`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {convergenceData.best_value_history.length === 0 ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            暫無數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={convergenceData.best_value_history}
              margin={{ top: 5, right: 30, left: 20, bottom: 25 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="trial"
                label={{ value: 'Trial 次數', position: 'bottom', offset: 0, className: 'text-xs' }}
                className="text-xs"
              />
              <YAxis
                label={{ value: '最佳目標值', angle: -90, position: 'left', className: 'text-xs' }}
                className="text-xs"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: '12px' }}
                iconType="line"
              />

              {/* 收斂點參考線 */}
              {convergenceData.converged && convergenceData.convergence_trial !== undefined && (
                <ReferenceLine
                  x={convergenceData.convergence_trial}
                  stroke="#fb7185"
                  strokeDasharray="5 5"
                  label={{
                    value: '收斂點',
                    position: 'top',
                    className: 'text-xs fill-rose-400'
                  }}
                />
              )}

              {/* Best value 演進曲線 */}
              <Line
                type="stepAfter"
                dataKey="value"
                stroke="#34d399"
                strokeWidth={2}
                dot={false}
                name="最佳值演進"
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {/* 說明文字 */}
        <div className="mt-4 pt-4 border-t space-y-1">
          <p className="text-xs text-muted-foreground">
            💡 曲線趨於平穩表示優化已收斂，繼續執行可能無明顯改進
          </p>
          {convergenceData.converged && (
            <p className="text-xs text-emerald-400 font-medium">
              ✓ 優化已達到收斂狀態，建議停止或減少 trial 數量
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
