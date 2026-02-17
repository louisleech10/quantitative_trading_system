'use client';

import { useEffect, useMemo, useState } from 'react';
import html2canvas from 'html2canvas';
import { ICFeatureInfo, ICReport } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Download, Loader2 } from 'lucide-react';

interface ExportButtonsProps {
  taskId?: string | null;
  report?: ICReport | null;
  summaryTable?: ICFeatureInfo[];
  targetId?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ExportButtons({ taskId, report, summaryTable, targetId }: ExportButtonsProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const enabledModules = useMemo(() => {
    if (!report?.module_statuses || report.module_statuses.length === 0) {
      return [];
    }
    return report.module_statuses
      .filter((item) => item.status === 'completed')
      .map((item) => item.module_name);
  }, [report?.module_statuses]);

  const [selectedModule, setSelectedModule] = useState<string>('');

  useEffect(() => {
    if (!selectedModule && enabledModules.length > 0) {
      setSelectedModule(enabledModules[0]);
    }
  }, [enabledModules, selectedModule]);

  const canExportData = Boolean(taskId && report);

  const triggerDownload = async (
    format: 'json' | 'ai_json' | 'csv_summary' | 'csv_detailed' | 'markdown' | 'hdf5'
  ) => {
    if (!taskId) {
      return;
    }

    setDownloadError(null);
    setIsDownloading(true);
    try {
      const params = new URLSearchParams();
      if (format === 'csv_detailed') {
        if (!selectedModule) {
          throw new Error('請先選擇 CSV 詳細模組');
        }
        params.set('module', selectedModule);
      }

      const url = `${API_BASE_URL}/api/v1/ic/export/${taskId}/${format}${
        params.toString() ? `?${params.toString()}` : ''
      }`;

      const response = await fetch(url);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || payload?.error || `${format} 匯出失敗`);
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get('content-disposition');
      const fileName = contentDisposition?.match(/filename=([^;]+)/)?.[1] || `ic_export_${Date.now()}`;

      const linkUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = linkUrl;
      link.download = fileName.replace(/"/g, '');
      link.click();
      URL.revokeObjectURL(linkUrl);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : '匯出失敗');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleExportPNG = async () => {
    if (!targetId) {
      return;
    }
    const target = document.getElementById(targetId);
    if (!target) {
      return;
    }

    const canvas = await html2canvas(target, {
      backgroundColor: '#0A0F1C',
      scale: 2,
      useCORS: true,
    });

    const link = document.createElement('a');
    link.href = canvas.toDataURL('image/png');
    link.download = `ic_snapshot_${Date.now()}.png`;
    link.click();
  };

  return (
    <div className="space-y-3 w-full">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="rounded-lg border border-cyan-400/20 p-3 space-y-2">
          <div className="text-xs text-cyan-200 font-medium">📊 數據</div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10"
              onClick={() => triggerDownload('csv_summary')}
              disabled={!canExportData || isDownloading}
            >
              {isDownloading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
              CSV 摘要
            </Button>
            <Button
              variant="outline"
              className="border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10"
              onClick={() => triggerDownload('csv_detailed')}
              disabled={!canExportData || !selectedModule || isDownloading}
            >
              <Download className="mr-2 h-4 w-4" />
              CSV 詳細
            </Button>
            <Button
              variant="outline"
              className="border-cyan-400/30 text-cyan-200 hover:bg-cyan-500/10"
              onClick={() => triggerDownload('hdf5')}
              disabled={!canExportData || isDownloading}
            >
              <Download className="mr-2 h-4 w-4" />
              HDF5
            </Button>
          </div>
          <select
            className="w-full bg-slate-900 border border-cyan-400/20 rounded-md px-2 py-1 text-xs text-slate-200"
            value={selectedModule}
            onChange={(event) => setSelectedModule(event.target.value)}
            disabled={enabledModules.length === 0 || isDownloading}
          >
            <option value="">選擇 CSV 詳細模組</option>
            {enabledModules.map((module) => (
              <option key={module} value={module}>
                {module}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-lg border border-violet-400/20 p-3 space-y-2">
          <div className="text-xs text-violet-200 font-medium">🤖 AI&LLM</div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="border-violet-400/30 text-violet-200 hover:bg-violet-500/10"
              onClick={() => triggerDownload('ai_json')}
              disabled={!canExportData || isDownloading}
            >
              <Download className="mr-2 h-4 w-4" />
              AI JSON
            </Button>
            <Button
              variant="outline"
              className="border-violet-400/30 text-violet-200 hover:bg-violet-500/10"
              onClick={() => triggerDownload('markdown')}
              disabled={!canExportData || isDownloading}
            >
              <Download className="mr-2 h-4 w-4" />
              Markdown
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-emerald-400/20 p-3 space-y-2">
          <div className="text-xs text-emerald-200 font-medium">📈 報告</div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              className="border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/10"
              onClick={() => triggerDownload('json')}
              disabled={!canExportData || isDownloading}
            >
              <Download className="mr-2 h-4 w-4" />
              完整 JSON
            </Button>
            <Button
              variant="outline"
              className="border-emerald-400/30 text-emerald-200 hover:bg-emerald-500/10"
              onClick={handleExportPNG}
              disabled={!targetId || !summaryTable || summaryTable.length === 0}
            >
              <Download className="mr-2 h-4 w-4" />
              全部 PNG
            </Button>
          </div>
        </div>
      </div>

      {downloadError && (
        <div className="text-xs text-rose-300">{downloadError}</div>
      )}
    </div>
  );
}
