'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface ParameterImportanceChartProps {
  data: Record<string, number>
}

export default function ParameterImportanceChart({ data }: ParameterImportanceChartProps) {
  const chartData = Object.entries(data).map(([parameter, importance]) => ({
    parameter,
    importance,
  }))

  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Parameter Importance</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-400">無可用資料</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Parameter Importance</CardTitle>
      </CardHeader>
      <CardContent className="h-80 text-blue-400">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="parameter" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="importance" fill="currentColor" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
