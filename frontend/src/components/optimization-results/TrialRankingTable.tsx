/**
 * Trial 排名表格組件
 *
 * 顯示 Top N trials 的詳細信息，支援排序和匯出
 *
 * Author: Claude (Optuna 優化系統 Phase 3)
 * Date: 2025-12-01
 */

'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Download, Trophy, ArrowUpDown } from "lucide-react"
import { TrialDetail } from "@/types/optimization"
import { useState } from "react"

interface TrialRankingTableProps {
  trials: TrialDetail[]
  onExport?: () => void
}

type SortField = 'rank' | 'value' | 'trial_number'
type SortDirection = 'asc' | 'desc'

export function TrialRankingTable({ trials, onExport }: TrialRankingTableProps) {
  const [sortField, setSortField] = useState<SortField>('rank')
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  // 排序處理
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  // 排序數據
  const sortedTrials = [...trials].sort((a, b) => {
    let aVal, bVal
    switch (sortField) {
      case 'rank':
        aVal = a.rank
        bVal = b.rank
        break
      case 'value':
        aVal = a.value
        bVal = b.value
        break
      case 'trial_number':
        aVal = a.trial_number
        bVal = b.trial_number
        break
      default:
        return 0
    }

    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1
    } else {
      return aVal < bVal ? 1 : -1
    }
  })

  // 匯出 CSV
  const handleExportCSV = () => {
    if (onExport) {
      onExport()
      return
    }

    // 獲取 user_attrs 欄位名稱（從第一個有 user_attrs 的 trial 取得）
    const userAttrKeys = trials[0]?.user_attrs ? Object.keys(trials[0].user_attrs) : []

    // 默認匯出邏輯（包含 user_attrs 統計數據）
    const headers = [
      'Rank', 'Trial #', 'Value', 'State',
      ...Object.keys(trials[0]?.params || {}),
      ...userAttrKeys
    ]
    const rows = trials.map(trial => [
      trial.rank,
      trial.trial_number,
      trial.value != null ? trial.value.toFixed(6) : 'N/A',
      trial.state || 'COMPLETE',
      ...Object.values(trial.params).map(v => typeof v === 'number' ? v.toFixed(4) : String(v)),
      ...userAttrKeys.map(key => {
        const val = trial.user_attrs?.[key]
        return val != null ? (typeof val === 'number' ? val.toFixed(6) : String(val)) : ''
      })
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `optimization_trials_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  // 渲染排序按鈕
  const SortButton = ({ field, label }: { field: SortField; label: string }) => (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => handleSort(field)}
      className="h-8 px-2 text-xs font-medium"
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  )

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Trial 排名</CardTitle>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCSV}
            className="h-8 text-xs"
          >
            <Download className="h-3 w-3 mr-1" />
            匯出 CSV
          </Button>
        </div>
        <CardDescription>
          Top {trials.length} trials 詳細信息
        </CardDescription>
      </CardHeader>
      <CardContent>
        {trials.length === 0 ? (
          <div className="flex items-center justify-center h-[200px] text-muted-foreground">
            暫無數據
          </div>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[80px]">
                    <SortButton field="rank" label="排名" />
                  </TableHead>
                  <TableHead className="w-[100px]">
                    <SortButton field="trial_number" label="Trial #" />
                  </TableHead>
                  <TableHead className="w-[140px]">
                    <SortButton field="value" label="目標值" />
                  </TableHead>
                  <TableHead>參數</TableHead>
                  <TableHead className="w-[100px]">統計</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedTrials.map((trial) => (
                  <TableRow key={trial.trial_number}>
                    {/* 排名 */}
                    <TableCell className="font-medium">
                      {trial.rank === 1 && (
                        <Badge variant="default" className="bg-yellow-500 text-white">
                          🏆 #{trial.rank}
                        </Badge>
                      )}
                      {trial.rank === 2 && (
                        <Badge variant="secondary">
                          🥈 #{trial.rank}
                        </Badge>
                      )}
                      {trial.rank === 3 && (
                        <Badge variant="outline">
                          🥉 #{trial.rank}
                        </Badge>
                      )}
                      {trial.rank > 3 && (
                        <span className="text-sm text-muted-foreground">
                          #{trial.rank}
                        </span>
                      )}
                    </TableCell>

                    {/* Trial 編號 */}
                    <TableCell className="font-mono text-xs">
                      {trial.trial_number}
                    </TableCell>

                    {/* 目標值 */}
                    <TableCell className="font-mono text-sm font-semibold text-green-600">
                      {trial.value !== null && trial.value !== undefined 
                        ? trial.value.toFixed(6) 
                        : 'N/A'}
                    </TableCell>

                    {/* 參數 */}
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(trial.params).map(([key, value]) => (
                          <Badge key={key} variant="outline" className="text-xs">
                            {key}: {typeof value === 'number' ? value.toFixed(2) : String(value)}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>

                    {/* 統計指標 */}
                    <TableCell className="text-xs">
                      {trial.user_attrs && (
                        <div className="space-y-0.5">
                          {trial.user_attrs.p_value !== undefined && (
                            <div className={trial.user_attrs.p_value < 0.05 ? "text-green-500" : trial.user_attrs.p_value < 0.1 ? "text-yellow-500" : "text-muted-foreground"}>
                              p: {trial.user_attrs.p_value.toFixed(4)}
                            </div>
                          )}
                          {trial.user_attrs.cohens_d !== undefined && (
                            <div className={trial.user_attrs.cohens_d > 0.8 ? "text-green-500" : trial.user_attrs.cohens_d > 0.5 ? "text-yellow-500" : "text-muted-foreground"}>
                              d: {trial.user_attrs.cohens_d.toFixed(3)}
                            </div>
                          )}
                          {trial.user_attrs.stability_cv !== undefined && (
                            <div className={trial.user_attrs.stability_cv < 0.3 ? "text-green-500" : trial.user_attrs.stability_cv < 0.5 ? "text-yellow-500" : "text-muted-foreground"}>
                              cv: {trial.user_attrs.stability_cv.toFixed(3)}
                            </div>
                          )}
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* 說明文字 */}
        <div className="mt-4 pt-4 border-t">
          <p className="text-xs text-muted-foreground">
            💡 點擊欄位標題可排序 · 點擊「匯出 CSV」可下載完整數據
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
