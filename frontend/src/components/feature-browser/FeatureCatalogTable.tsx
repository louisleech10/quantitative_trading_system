'use client';

import { useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

import { FeatureBrowserCatalogItem } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';


interface FeatureCatalogTableProps {
  items: FeatureBrowserCatalogItem[];
  selectedFeatures: string[];
  onSelectFeature: (feature: string) => void;
  onSelectFeatures: (features: string[]) => void;
}

type SortField = 'name' | 'category' | 'source' | 'layer' | 'family' | 'coverage' | 'mean' | 'std' | 'nan_pct';
type SortDirection = 'asc' | 'desc';


export default function FeatureCatalogTable({
  items,
  selectedFeatures,
  onSelectFeature,
  onSelectFeatures,
}: FeatureCatalogTableProps) {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('coverage');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [scrollTop, setScrollTop] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  const rowHeight = 42;
  const containerHeight = 520;
  const overscan = 8;

  const categories = useMemo(() => {
    return Array.from(new Set(items.map((item) => item.category).filter(Boolean)));
  }, [items]);

  const filteredAndSorted = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    const filtered = items.filter((item) => {
      const keywordMatched = !keyword || item.name.toLowerCase().includes(keyword);
      const categoryMatched = categoryFilter === 'all' || item.category === categoryFilter;
      return keywordMatched && categoryMatched;
    });

    const direction = sortDirection === 'asc' ? 1 : -1;
    const sorted = [...filtered].sort((left, right) => {
      const leftValue = left[sortField];
      const rightValue = right[sortField];

      if (typeof leftValue === 'number' || typeof rightValue === 'number') {
        const leftNumber = typeof leftValue === 'number' ? leftValue : Number.NEGATIVE_INFINITY;
        const rightNumber = typeof rightValue === 'number' ? rightValue : Number.NEGATIVE_INFINITY;
        return (leftNumber - rightNumber) * direction;
      }

      return String(leftValue ?? '').localeCompare(String(rightValue ?? '')) * direction;
    });

    return sorted;
  }, [categoryFilter, items, search, sortDirection, sortField]);

  const totalRows = filteredAndSorted.length;
  const visibleCount = Math.ceil(containerHeight / rowHeight);
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const endIndex = Math.min(totalRows, startIndex + visibleCount + overscan * 2);
  const topSpacerHeight = startIndex * rowHeight;
  const bottomSpacerHeight = Math.max(0, (totalRows - endIndex) * rowHeight);
  const visibleRows = filteredAndSorted.slice(startIndex, endIndex);

  const updateSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortField(field);
    setSortDirection('desc');
  };

  const sortIndicator = (field: SortField) => {
    if (field !== sortField) return '↕';
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  const exportCsv = () => {
    const header = 'name,category,source,layer,family,coverage,mean,std,nan_pct';
    const rows = filteredAndSorted.map((item) => [
      item.name,
      item.category,
      item.source,
      item.layer,
      item.family,
      item.coverage,
      item.mean ?? '',
      item.std ?? '',
      item.nan_pct,
    ].join(','));
    const content = [header, ...rows].join('\n');
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_catalog_${Date.now()}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardHeader className="space-y-3">
        <CardTitle className="text-base">特徵目錄</CardTitle>
        <div className="flex flex-col lg:flex-row gap-3">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜尋特徵（例如 RSI）" />
          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            className="h-9 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
          >
            <option value="all">全部類別</option>
            {categories.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
          <Button variant="outline" onClick={exportCsv}>匯出 CSV</Button>
          <Button
            onClick={() => {
              const params = new URLSearchParams();
              if (selectedFeatures.length > 0) {
                params.set('include_features', selectedFeatures.join(','));
              }
              router.push(`/ic-analysis?${params.toString()}`);
            }}
            disabled={selectedFeatures.length === 0}
          >
            以選中因子啟動 IC 分析
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div
          ref={scrollContainerRef}
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
          className="rounded border border-white/10 overflow-auto"
          style={{ maxHeight: `${containerHeight}px` }}
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[40px]">選</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('name')}>name {sortIndicator('name')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('category')}>category {sortIndicator('category')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('source')}>source {sortIndicator('source')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('layer')}>layer {sortIndicator('layer')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('family')}>family {sortIndicator('family')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('coverage')}>coverage {sortIndicator('coverage')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('mean')}>mean {sortIndicator('mean')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('std')}>std {sortIndicator('std')}</TableHead>
                <TableHead className="cursor-pointer" onClick={() => updateSort('nan_pct')}>nan% {sortIndicator('nan_pct')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {topSpacerHeight > 0 && (
                <TableRow>
                  <TableCell colSpan={10} style={{ height: `${topSpacerHeight}px`, padding: 0 }} />
                </TableRow>
              )}

              {visibleRows.map((item) => (
                <TableRow key={item.name} onClick={() => onSelectFeature(item.name)} className="cursor-pointer">
                  <TableCell onClick={(event) => event.stopPropagation()}>
                    <Checkbox
                      checked={selectedFeatures.includes(item.name)}
                      onCheckedChange={(checked) => {
                        if (Boolean(checked)) {
                          onSelectFeatures(Array.from(new Set([...selectedFeatures, item.name])));
                          return;
                        }
                        onSelectFeatures(selectedFeatures.filter((feature) => feature !== item.name));
                      }}
                    />
                  </TableCell>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>{item.category}</TableCell>
                  <TableCell>{item.source}</TableCell>
                  <TableCell>{item.layer}</TableCell>
                  <TableCell>{item.family}</TableCell>
                  <TableCell>{(item.coverage * 100).toFixed(2)}%</TableCell>
                  <TableCell>{item.mean?.toFixed(6) ?? '--'}</TableCell>
                  <TableCell>{item.std?.toFixed(6) ?? '--'}</TableCell>
                  <TableCell>{item.nan_pct.toFixed(2)}%</TableCell>
                </TableRow>
              ))}

              {bottomSpacerHeight > 0 && (
                <TableRow>
                  <TableCell colSpan={10} style={{ height: `${bottomSpacerHeight}px`, padding: 0 }} />
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        <div className="mt-2 text-xs text-slate-400">共 {totalRows} 筆（虛擬卷軸已啟用）</div>
      </CardContent>
    </Card>
  );
}
