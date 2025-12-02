/**
 * 參數重要性圖表組件
 *
 * 使用橫向柱狀圖顯示參數重要性分析結果
 *
 * Author: Claude (Optuna 優化系統 Phase 3)
 * Date: 2025-12-01
 */

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { ParameterImportance } from "@/types/optimization"
import { TrendingUp } from "lucide-react"

interface ParamImportanceChartProps {
  importances: ParameterImportance[]
  evaluator?: string
}

export function ParamImportanceChart({ importances, evaluator = 'fanova' }: ParamImportanceChartProps) {
  // 按重要性降序排序
  const sortedData = [...importances].sort((a, b) => b.importance - a.importance)

  // 顏色梯度（根據重要性）
  const getColor = (importance: number, index: number) => {
    if (index === 0) return 'hsl(142, 76%, 36%)' // 最重要 - 綠色
    if (importance > 0.5) return 'hsl(217, 91%, 60%)' // 高重要性 - 藍色
    if (importance > 0.2) return 'hsl(47, 96%, 53%)' // 中等重要性 - 黃色
    return 'hsl(215, 16%, 47%)' // 低重要性 - 灰色
  }

  // 自定義 Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-popover border rounded-lg shadow-lg p-3">
          <p className="font-semibold text-sm">{data.parameter_name}</p>
          <p className="text-xs text-muted-foreground mt-1">
            重要性: <span className="font-mono font-bold">{(data.importance * 100).toFixed(1)}%</span>
          </p>
          <p className="text-xs text-muted-foreground">
            排名: #{data.rank}
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">參數重要性分析</CardTitle>
        </div>
        <CardDescription>
          評估方法: {evaluator === 'fanova' ? 'fANOVA' : 'Mean Decrease Impurity'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {sortedData.length === 0 ? (
          <div className="flex items-center justify-center h-[300px] text-muted-foreground">
            暫無數據
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(300, sortedData.length * 40)}>
            <BarChart
              data={sortedData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                type="number"
                domain={[0, 1]}
                tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                className="text-xs"
              />
              <YAxis
                type="category"
                dataKey="parameter_name"
                width={90}
                className="text-xs"
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                {sortedData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getColor(entry.importance, index)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}

        {/* 說明文字 */}
        <div className="mt-4 pt-4 border-t">
          <p className="text-xs text-muted-foreground">
            💡 數值越高表示該參數對優化目標的影響越大
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
