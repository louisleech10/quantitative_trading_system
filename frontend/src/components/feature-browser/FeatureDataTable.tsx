'use client';

import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { FeatureBrowserDataTableResponse } from '@/lib/types';


const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';


interface FeatureDataTableProps {
  featuresPath: string;
  selectedFeatures: string[];
}


export default function FeatureDataTable({ featuresPath, selectedFeatures }: FeatureDataTableProps) {
  const [page, setPage] = useState(1);
  const [payload, setPayload] = useState<FeatureBrowserDataTableResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!featuresPath) {
      setPayload(null);
      return;
    }

    const params = new URLSearchParams({
      features_path: featuresPath,
      page: String(page),
      page_size: '100',
    });
    if (selectedFeatures.length > 0) {
      params.set('columns', selectedFeatures.join(','));
    }

    fetch(`${API_BASE_URL}/api/v1/features/data-table?${params.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error(body?.detail || response.statusText);
        }
        return response.json() as Promise<FeatureBrowserDataTableResponse>;
      })
      .then((data) => {
        setPayload(data);
        setError(null);
      })
      .catch((fetchError: unknown) => {
        setError(fetchError instanceof Error ? fetchError.message : '載入資料表失敗');
      });
  }, [featuresPath, page, selectedFeatures]);

  const pageCount = useMemo(() => {
    if (!payload) return 1;
    return Math.max(1, Math.ceil(payload.total_rows / payload.page_size));
  }, [payload]);

  const exportCsv = () => {
    if (!payload || payload.rows.length === 0) {
      return;
    }
    const columns = payload.columns;
    const header = columns.join(',');
    const rows = payload.rows.map((row) => columns.map((column) => String(row[column] ?? '')).join(','));
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_data_page_${page}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">數據表</CardTitle>
        <Button variant="outline" onClick={exportCsv}>匯出 CSV</Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <div className="text-rose-300 text-sm">{error}</div>}
        {!payload && !error && <div className="text-slate-400 text-sm">請先設定 features_path</div>}

        {payload && (
          <>
            <div className="rounded border border-white/10 overflow-auto max-h-[420px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    {payload.columns.map((column) => (
                      <TableHead key={column}>{column}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payload.rows.map((row, rowIndex) => (
                    <TableRow key={rowIndex}>
                      {payload.columns.map((column) => (
                        <TableCell key={`${rowIndex}-${column}`} className="text-xs">
                          {String(row[column] ?? '')}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">第 {payload.page} / {pageCount} 頁</span>
              <div className="flex items-center gap-2">
                <Button variant="outline" disabled={page <= 1} onClick={() => setPage((prev) => prev - 1)}>上一頁</Button>
                <Button variant="outline" disabled={page >= pageCount} onClick={() => setPage((prev) => prev + 1)}>下一頁</Button>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
