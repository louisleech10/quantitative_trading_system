'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface ParetoFrontChartProps {
  data: Array<{ sharpe: number; max_dd: number }>
}

export default function ParetoFrontChart({ data }: ParetoFrontChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Pareto 前沿圖</CardTitle>
      </CardHeader>
      <CardContent className="h-80 text-purple-400">
        {data.length === 0 ? (
          <p className="text-sm text-slate-400">無 Pareto 資料（可能未啟用多目標）</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="max_dd" name="max_dd" />
              <YAxis dataKey="sharpe" name="sharpe" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={data} fill="currentColor" />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
