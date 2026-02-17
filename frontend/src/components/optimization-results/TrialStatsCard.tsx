/**
 * Trial 執行統計卡片組件
 *
 * 顯示優化過程中 Trial 的執行統計資訊
 * - 總 Trial 數、完成數、剪枝數、失敗數
 * - 完成率百分比和視覺化進度條
 * - Tooltip 說明 PRUNED 原因
 *
 * Author: Claude (Optuna 優化系統 Phase 4 修復)
 * Date: 2025-12-16
 */

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
void Progress;
import {
  CheckCircle2,
  XCircle,
  Scissors,
  BarChart3,
  Info
} from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface TrialStats {
  total: number
  complete: number
  pruned: number
  failed: number
}

interface TrialStatsCardProps {
  stats: TrialStats
}

export function TrialStatsCard({ stats }: TrialStatsCardProps) {
  const completionRate = stats.total > 0 ? (stats.complete / stats.total) * 100 : 0
  const prunedRate = stats.total > 0 ? (stats.pruned / stats.total) * 100 : 0
  const failedRate = stats.total > 0 ? (stats.failed / stats.total) * 100 : 0

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">Trial 執行統計</CardTitle>
        </div>
        <CardDescription>
          優化過程中的 Trial 狀態分佈
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 統計數字 */}
        <div className="grid grid-cols-2 gap-4">
          {/* 總數 */}
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <BarChart3 className="h-3.5 w-3.5" />
              <span>總 Trials</span>
            </div>
            <div className="text-2xl font-semibold">{stats.total}</div>
          </div>

          {/* 完成數 */}
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>完成</span>
            </div>
            <div className="text-2xl font-semibold text-emerald-400">
              {stats.complete}
            </div>
            <div className="text-xs text-muted-foreground">
              {completionRate.toFixed(1)}%
            </div>
          </div>

          {/* 剪枝數 */}
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Scissors className="h-3.5 w-3.5 text-amber-400" />
              <span>剪枝</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs">
                    <div className="space-y-2">
                      <p className="font-semibold">Trial 被剪枝的常見原因：</p>
                      <ul className="text-xs space-y-1 list-disc list-inside">
                        <li><strong>參數驗證失敗</strong>：如 short_period ≥ mid_period</li>
                        <li><strong>MedianPruner 自動剪枝</strong>：表現低於歷史中位數</li>
                        <li><strong>數據異常</strong>：near/far ratio ≤ 0、K線不足</li>
                        <li><strong>策略錯誤</strong>：策略不存在或執行失敗</li>
                      </ul>
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div className="text-2xl font-semibold text-amber-400">
              {stats.pruned}
            </div>
            <div className="text-xs text-muted-foreground">
              {prunedRate.toFixed(1)}%
            </div>
          </div>

          {/* 失敗數 */}
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <XCircle className="h-3.5 w-3.5 text-rose-400" />
              <span>失敗</span>
            </div>
            <div className="text-2xl font-semibold text-rose-400">
              {stats.failed}
            </div>
            <div className="text-xs text-muted-foreground">
              {failedRate.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* 視覺化進度條 */}
        <div className="space-y-2">
          <div className="text-sm font-medium">狀態分佈</div>
            <div className="relative h-3 w-full overflow-hidden rounded-full bg-white/10">
            {/* 完成 */}
            <div
                className="absolute h-full bg-emerald-400 transition-all"
              style={{ width: `${completionRate}%` }}
            />
            {/* 剪枝 */}
            <div
                className="absolute h-full bg-amber-400 transition-all"
              style={{
                left: `${completionRate}%`,
                width: `${prunedRate}%`
              }}
            />
            {/* 失敗 */}
            <div
                className="absolute h-full bg-rose-400 transition-all"
              style={{
                left: `${completionRate + prunedRate}%`,
                width: `${failedRate}%`
              }}
            />
          </div>

          {/* 圖例 */}
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              <div className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              <span className="text-muted-foreground">完成</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2.5 w-2.5 rounded-full bg-amber-400" />
              <span className="text-muted-foreground">剪枝</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2.5 w-2.5 rounded-full bg-rose-400" />
              <span className="text-muted-foreground">失敗</span>
            </div>
          </div>
        </div>

        {/* 說明文字 */}
        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground">
            💡 只有 <strong className="text-emerald-400">COMPLETE</strong> 狀態的 Trial 會用於分析和優化
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
