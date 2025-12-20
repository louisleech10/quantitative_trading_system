/**
 * 最佳結果卡片組件
 *
 * 顯示優化結果的最佳參數、目標值和統計指標
 *
 * Author: Claude (Optuna 優化系統 Phase 3)
 * Date: 2025-12-01
 */

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Copy, PlayCircle, TrendingUp } from "lucide-react"
import { OptimizationResultDetail } from "@/types/optimization"
import { useState } from "react"

interface BestResultCardProps {
  result: OptimizationResultDetail
  onCopyParams?: () => void
  onRetest?: () => void
}

export function BestResultCard({ result, onCopyParams, onRetest }: BestResultCardProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (onCopyParams) {
      onCopyParams()
    }
    // 複製參數到剪貼板
    navigator.clipboard.writeText(JSON.stringify(result.best_params, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // 格式化執行時間
  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`
    return `${(seconds / 3600).toFixed(1)}h`
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-500" />
            <CardTitle>最佳優化結果</CardTitle>
          </div>
          <Badge variant="outline" className="text-sm">
            Trial #{result.best_trial_number}
          </Badge>
        </div>
        <CardDescription>
          共執行 {result.n_trials} 次試驗，耗時 {formatTime(result.optimization_time)}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 最佳目標值 */}
        <div className="space-y-2 p-4 bg-muted rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">最佳目標值</p>
              <p className="text-2xl font-bold text-green-600">
                {result.best_value.toFixed(6)}
              </p>
            </div>
            <Badge variant="secondary" className="text-xs">
              {result.study_direction === 'MAXIMIZE' ? '最大化' : '最小化'}
            </Badge>
          </div>

          {/* 目標值計算說明 */}
          <div className="pt-2 border-t border-border/50">
            <p className="text-xs text-muted-foreground leading-relaxed">
              <span className="font-medium">計算方式：</span>
              {/* 檢測是否為雙密度模式（通過檢查 best_params 中是否有 clustering_weight 或相關參數） */}
              {(() => {
                // 簡化判斷：如果目標值看起來是加權分數（通常 0-1 之間），可能是雙密度模式
                const isDualDensity = result.best_value > 0 && result.best_value < 2

                if (isDualDensity) {
                  return (
                    <>
                      <br />• <span className="text-foreground font-semibold">信號聚集分數 (Clustering Score)</span>
                      <br />&nbsp;&nbsp;= positive_near_far_ratio - 1.0
                      <br />• <span className="text-foreground font-semibold">正反例區分度 (Discrimination Score)</span>
                      <br />&nbsp;&nbsp;= positive_near_far_ratio - negative_near_far_ratio
                      <br />• <span className="text-foreground font-semibold">最終目標值</span>
                      <br />&nbsp;&nbsp;= clustering_score × clustering_weight
                      <br />&nbsp;&nbsp;+ discrimination_score × (1 - clustering_weight)
                      <br />• clustering_weight 預設為 <span className="text-foreground">0.5</span>
                    </>
                  )
                } else {
                  return (
                    <>
                      <br />• <span className="text-foreground font-semibold">正反例信號密度差異 (Separation)</span>
                      <br />&nbsp;&nbsp;= positive_near_far_ratio - negative_near_far_ratio
                      <br />• 越大表示策略區分度越高
                    </>
                  )
                }
              })()}
            </p>
          </div>
        </div>

        {/* 最佳參數 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">最佳參數組合</p>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="h-8 text-xs"
              >
                <Copy className="h-3 w-3 mr-1" />
                {copied ? '已複製' : '複製'}
              </Button>
              {onRetest && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRetest}
                  className="h-8 text-xs"
                >
                  <PlayCircle className="h-3 w-3 mr-1" />
                  重新測試
                </Button>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(result.best_params).map(([key, value]) => (
              <div
                key={key}
                className="flex items-center justify-between p-2 bg-muted rounded border"
              >
                <span className="text-xs text-muted-foreground">{key}</span>
                <span className="text-sm font-mono font-semibold">
                  {typeof value === 'number' ? value.toFixed(2) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 收斂信息（如果有） */}
        {result.convergence_info && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground">
              收斂狀態：
              <span className="ml-2 font-medium text-foreground">
                {result.convergence_info.converged ? '已收斂' : '未收斂'}
              </span>
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
