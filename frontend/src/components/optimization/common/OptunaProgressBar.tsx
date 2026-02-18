'use client'

import { Progress } from '@/components/ui/progress'

interface OptunaProgressBarProps {
  completedTrials: number
  totalTrials: number
  bestValue?: number | null
}

export default function OptunaProgressBar({
  completedTrials,
  totalTrials,
  bestValue,
}: OptunaProgressBarProps) {
  const safeTotal = totalTrials > 0 ? totalTrials : 1
  const percentage = Math.min((completedTrials / safeTotal) * 100, 100)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm text-slate-300">
        <span>優化進度</span>
        <span>{completedTrials} / {totalTrials} ({percentage.toFixed(1)}%)</span>
      </div>
      <Progress value={percentage} />
      {bestValue !== null && bestValue !== undefined && (
        <p className="text-xs text-slate-400">目前最佳值：{bestValue.toFixed(6)}</p>
      )}
    </div>
  )
}
