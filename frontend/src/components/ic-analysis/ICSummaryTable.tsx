'use client';

import { useMemo, useState } from 'react';
import { ICFeatureInfo } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ArrowUpDown } from 'lucide-react';

interface ICSummaryTableProps {
  data: ICFeatureInfo[];
  selectedFeature?: string | null;
  onSelectFeature?: (featureName: string) => void;
}

type SortField = 'rank' | 'ic_mean' | 'icir' | 'p_value' | 'monotonicity_score';

type SortDirection = 'asc' | 'desc';

export default function ICSummaryTable({
  data,
  selectedFeature,
  onSelectFeature,
}: ICSummaryTableProps) {
  const [sortField, setSortField] = useState<SortField>('icir');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const sortedData = useMemo(() => {
    const cloned = [...data];
    cloned.sort((a, b) => {
      const aVal = a[sortField] ?? 0;
      const bVal = b[sortField] ?? 0;
      if (aVal === bVal) return 0;
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      }
      return aVal < bVal ? 1 : -1;
    });
    return cloned;
  }, [data, sortDirection, sortField]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortButton = ({ field, label }: { field: SortField; label: string }) => (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => handleSort(field)}
      className="h-8 px-2 text-xs"
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">IC 排名總覽</CardTitle>
        <CardDescription>點擊特徵即可更新右側圖表</CardDescription>
      </CardHeader>
      <CardContent>
        {sortedData.length === 0 ? (
          <div className="flex items-center justify-center h-[200px] text-slate-400">
            暫無分析結果
          </div>
        ) : (
          <div className="rounded-md border border-white/10">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[70px]">排名</TableHead>
                  <TableHead>特徵</TableHead>
                  <TableHead className="w-[120px]">
                    <SortButton field="ic_mean" label="IC Mean" />
                  </TableHead>
                  <TableHead className="w-[120px]">
                    <SortButton field="icir" label="ICIR" />
                  </TableHead>
                  <TableHead className="w-[120px]">
                    <SortButton field="p_value" label="P-Value" />
                  </TableHead>
                  <TableHead className="w-[140px]">
                    <SortButton field="monotonicity_score" label="單調性" />
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedData.map((item, index) => {
                  const isSelected = item.feature_name === selectedFeature;
                  return (
                    <TableRow
                      key={`${item.feature_name}-${index}`}
                      className={isSelected ? 'bg-cyan-500/10' : ''}
                      onClick={() => onSelectFeature?.(item.feature_name)}
                    >
                      <TableCell className="text-sm text-slate-300">#{item.rank ?? index + 1}</TableCell>
                      <TableCell className="font-medium text-slate-100">
                        {item.feature_name}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-200">
                        {item.ic_mean?.toFixed(4)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-emerald-300">
                        {item.icir?.toFixed(3)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        {item.p_value?.toFixed(4)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-slate-300">
                        {item.monotonicity_score?.toFixed(2) ?? '--'}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
