'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Line,
  LineChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface EquityCurvePoint {
  step: number
  strategy: number
  buyHold: number
}

interface EquityCurveChartProps {
  data: EquityCurvePoint[]
}

export default function EquityCurveChart({ data }: EquityCurveChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>權益曲線（策略 vs Buy & Hold）</CardTitle>
      </CardHeader>
      <CardContent className="h-80 text-emerald-400">
        {data.length === 0 ? (
          <p className="text-sm text-slate-400">無可用資料</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="strategy" stroke="currentColor" dot={false} />
              <Line type="monotone" dataKey="buyHold" stroke="currentColor" dot={false} strokeOpacity={0.55} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
