'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { TrialRow } from '@/lib/types/optimization'

interface TrialComparisonTableProps {
  trials: TrialRow[]
}

type SortKey = 'trial_number' | 'value' | 'state'

export default function TrialComparisonTable({ trials }: TrialComparisonTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('trial_number')
  const [sortAsc, setSortAsc] = useState(false)
  const [stateFilter, setStateFilter] = useState('')

  const filteredSortedRows = useMemo(() => {
    const filtered = trials.filter((trial) => {
      if (!stateFilter.trim()) {
        return true
      }
      return (trial.state || '').toLowerCase().includes(stateFilter.toLowerCase())
    })

    return [...filtered].sort((left, right) => {
      const leftValue = left[sortKey] ?? ''
      const rightValue = right[sortKey] ?? ''
      if (leftValue < rightValue) {
        return sortAsc ? -1 : 1
      }
      if (leftValue > rightValue) {
        return sortAsc ? 1 : -1
      }
      return 0
    })
  }, [sortAsc, sortKey, stateFilter, trials])

  const onSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((prev) => !prev)
      return
    }
    setSortKey(key)
    setSortAsc(false)
  }

  const onExportCsv = () => {
    const lines = ['trial_number,value,state']
    filteredSortedRows.forEach((row) => {
      lines.push(`${row.trial_number},${row.value},${row.state || ''}`)
    })

    const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `trials_${Date.now()}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="w-full md:w-72">
          <p className="mb-2 text-sm text-slate-300">狀態篩選</p>
          <Input
            placeholder="例如 COMPLETE"
            value={stateFilter}
            onChange={(event) => setStateFilter(event.target.value)}
          />
        </div>
        <Button variant="outline" onClick={onExportCsv}>匯出 CSV</Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="cursor-pointer" onClick={() => onSort('trial_number')}>Trial #</TableHead>
            <TableHead className="cursor-pointer" onClick={() => onSort('value')}>Value</TableHead>
            <TableHead className="cursor-pointer" onClick={() => onSort('state')}>State</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredSortedRows.map((row) => (
            <TableRow key={row.trial_number}>
              <TableCell>{row.trial_number}</TableCell>
              <TableCell>{row.value}</TableCell>
              <TableCell>{row.state || '-'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
