'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface DrawdownPoint {
  step: number
  drawdown: number
}

interface DrawdownChartProps {
  data: DrawdownPoint[]
}

export default function DrawdownChart({ data }: DrawdownChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>回撤曲線</CardTitle>
      </CardHeader>
      <CardContent className="h-80 text-red-400">
        {data.length === 0 ? (
          <p className="text-sm text-slate-400">無可用資料</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="drawdown" stroke="currentColor" fill="currentColor" fillOpacity={0.35} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
