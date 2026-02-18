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
import type { OverfittingAlertEvent } from '@/lib/types/optimization'

interface OverfittingCheckChartProps {
  alerts: OverfittingAlertEvent[]
}

export default function OverfittingCheckChart({ alerts }: OverfittingCheckChartProps) {
  const points = alerts.map((alert) => ({
    trial: alert.trial_number,
    gap: alert.train_val_gap,
    threshold: alert.threshold,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Overfitting Check (Train-Val Gap)</CardTitle>
      </CardHeader>
      <CardContent className="h-80 text-amber-400">
        {points.length === 0 ? (
          <p className="text-sm text-slate-400">目前無過擬合告警</p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="trial" name="Trial" />
              <YAxis dataKey="gap" name="Train-Val Gap" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={points} fill="currentColor" />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
