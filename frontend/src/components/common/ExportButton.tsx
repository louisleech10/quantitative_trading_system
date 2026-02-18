'use client';

import { useState } from 'react';
import { Download } from 'lucide-react';

interface ExportButtonProps {
  modelTaskId: string;
  scope: string;
  availableFormats: ('csv' | 'json' | 'markdown')[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ExportButton({ modelTaskId, scope, availableFormats }: ExportButtonProps) {
  const [format, setFormat] = useState<'csv' | 'json' | 'markdown'>(availableFormats[0] ?? 'json');
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    if (!modelTaskId) {
      return;
    }

    setError(null);
    setIsExporting(true);
    try {
      const query = new URLSearchParams({ format, scope });
      const url = `${API_BASE_URL}/api/v1/export/${modelTaskId}?${query.toString()}`;
      const response = await fetch(url);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || '匯出失敗');
      }

      const blob = await response.blob();
      const linkUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const filename = `${modelTaskId}_${scope}.${format === 'markdown' ? 'md' : format}`;
      link.href = linkUrl;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(linkUrl);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : '匯出失敗');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <select
        value={format}
        onChange={(event) => setFormat(event.target.value as 'csv' | 'json' | 'markdown')}
        className="h-9 rounded-md border border-input bg-background px-2 text-sm"
        disabled={isExporting}
      >
        {availableFormats.map((item) => (
          <option key={item} value={item}>
            {item.toUpperCase()}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={handleExport}
        disabled={isExporting}
        className="inline-flex h-9 items-center gap-2 rounded-md border border-input px-3 text-sm hover:bg-accent disabled:opacity-50"
      >
        <Download className="h-4 w-4" />
        {isExporting ? '匯出中...' : '匯出'}
      </button>
      {error && <span className="text-xs text-rose-500">{error}</span>}
    </div>
  );
}
