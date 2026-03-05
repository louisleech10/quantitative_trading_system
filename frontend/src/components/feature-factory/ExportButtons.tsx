'use client';

import { useMemo, useState } from 'react';
import { Download } from 'lucide-react';
import { FeatureFactoryConfig } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { exportChartToPNG } from '@/lib/exportUtils';

interface ExportButtonsProps {
  config: FeatureFactoryConfig | null;
  taskId?: string;
  symbol: string;
  timeframe: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';

export default function ExportButtons({ config, taskId, symbol, timeframe }: ExportButtonsProps) {
  const { featureList, currentTask } = useFeatureFactoryStore();
  const [csvColumns, setCsvColumns] = useState('all');
  const [csvMaxRows, setCsvMaxRows] = useState('all');
  const [includeMetadataHeader, setIncludeMetadataHeader] = useState(true);
  const [tokenBudget, setTokenBudget] = useState(4000);
  const [language, setLanguage] = useState('zh-TW');
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const canExportData = useMemo(() => {
    return Boolean(taskId && (currentTask?.status === 'completed' || featureList.length > 0));
  }, [taskId, currentTask?.status, featureList.length]);

  const buildExportFilename = (extension: string) => {
    const safeTaskId = taskId || 'unknown';
    return `${symbol}_${timeframe}_features_${safeTaskId}.${extension}`;
  };

  const downloadFromApi = async (path: string, filename: string) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600_000); // 10-min guard for large datasets
    try {
      const response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, { signal: controller.signal });
      if (!response.ok) {
        let message = `下載失敗 (${response.status})`;
        try {
          const payload = await response.json();
          message = payload?.detail || message;
        } catch {
          // no-op
        }
        throw new Error(message);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.click();
      window.URL.revokeObjectURL(url);
    } finally {
      clearTimeout(timeoutId);
    }
  };

  const exportConfig = () => {
    if (!config) {
      return;
    }

    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json;charset=utf-8',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_factory_config_${Date.now()}.json`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const exportFeatureList = () => {
    if (!featureList.length) {
      return;
    }

    const blob = new Blob([featureList.join('\n')], {
      type: 'text/plain;charset=utf-8',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_factory_features_${Date.now()}.txt`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const exportCsv = async () => {
    if (!taskId) {
      return;
    }

    setIsDownloading(true);
    setDownloadError(null);
    try {
      const query = new URLSearchParams();
      if (csvColumns !== 'all') {
        query.set('columns', csvColumns);
      }
      if (csvMaxRows !== 'all') {
        query.set('max_rows', csvMaxRows);
      }
      query.set('include_metadata_header', includeMetadataHeader ? 'true' : 'false');

      await downloadFromApi(
        `/export/${taskId}/csv?${query.toString()}`,
        buildExportFilename('csv')
      );
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : 'CSV 匯出失敗');
    } finally {
      setIsDownloading(false);
    }
  };

  const exportJson = async () => {
    if (!taskId) {
      return;
    }

    setIsDownloading(true);
    setDownloadError(null);
    try {
      await downloadFromApi(
        `/export/${taskId}/json?include_sample_data=true&sample_rows=5&include_statistics=true&include_correlation_top_k=10`,
        buildExportFilename('json')
      );
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : 'JSON 匯出失敗');
    } finally {
      setIsDownloading(false);
    }
  };

  const exportMarkdown = async () => {
    if (!taskId) {
      return;
    }

    setIsDownloading(true);
    setDownloadError(null);
    try {
      const query = new URLSearchParams();
      query.set('max_token_budget', String(tokenBudget));
      query.set('language', language);

      await downloadFromApi(
        `/export/${taskId}/markdown?${query.toString()}`,
        buildExportFilename('md')
      );
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : 'Markdown 匯出失敗');
    } finally {
      setIsDownloading(false);
    }
  };

  const exportPng = async () => {
    if (!taskId) {
      return;
    }
    setDownloadError(null);
    try {
      await exportChartToPNG('feature-factory-export-target', 'feature_factory', taskId);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : 'PNG 匯出失敗');
    }
  };

  return (
    <div id="feature-factory-export-target" className="glass-panel rounded-2xl p-6 space-y-4">
      <div>
        <div className="text-lg font-semibold text-slate-100">匯出</div>
        <div className="text-xs text-slate-400">快速保存當前設定與特徵清單</div>
      </div>

      <div className="space-y-3">
        <button
          onClick={exportConfig}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition"
        >
          <Download className="w-4 h-4" />
          匯出 Config
        </button>
        <button
          onClick={exportFeatureList}
          disabled={!featureList.length}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          匯出特徵清單
        </button>

        <div className="text-xs text-slate-400 pt-2">數據（需先完成生成）</div>
        <div className="grid grid-cols-1 gap-2">
          <button
            onClick={exportCsv}
            disabled={!canExportData || isDownloading}
            title={canExportData ? '匯出特徵 CSV' : '請先完成特徵生成任務'}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            匯出特徵 CSV
          </button>
          <button
            onClick={exportJson}
            disabled={!canExportData || isDownloading}
            title={canExportData ? '匯出 AI JSON' : '請先完成特徵生成任務'}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            匯出 AI JSON
          </button>
          <button
            onClick={exportMarkdown}
            disabled={!canExportData || isDownloading}
            title={canExportData ? '匯出 Markdown 報告' : '請先完成特徵生成任務'}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            匯出 Markdown 報告
          </button>
          <button
            onClick={exportPng}
            disabled={!canExportData || isDownloading}
            title={canExportData ? '匯出 PNG' : '請先完成特徵生成任務'}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            匯出 PNG
          </button>
        </div>

        <div className="pt-2 space-y-2">
          <div className="text-xs text-slate-400">CSV 選項</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <select
              value={csvColumns}
              onChange={(event) => setCsvColumns(event.target.value)}
              className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-slate-100"
            >
              <option value="all">欄位：全部</option>
              <option value="ms_amihud_illiq_21,ent_shannon_close_return_21,tr_cvar_5pct_21">欄位：示例三欄</option>
            </select>
            <select
              value={csvMaxRows}
              onChange={(event) => setCsvMaxRows(event.target.value)}
              className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-slate-100"
            >
              <option value="all">行數：全部</option>
              <option value="100">行數：100</option>
              <option value="500">行數：500</option>
              <option value="1000">行數：1000</option>
            </select>
          </div>
          <label className="inline-flex items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={includeMetadataHeader}
              onChange={(event) => setIncludeMetadataHeader(event.target.checked)}
            />
            包含 Metadata header
          </label>
        </div>

        <div className="pt-2 space-y-2">
          <div className="text-xs text-slate-400">Markdown 選項</div>
          <div className="space-y-2">
            <div className="text-xs text-slate-300">Token 預算：{tokenBudget}</div>
            <input
              type="range"
              min={500}
              max={32000}
              step={100}
              value={tokenBudget}
              onChange={(event) => setTokenBudget(Number(event.target.value))}
              className="w-full"
            />
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100"
            >
              <option value="zh-TW">zh-TW</option>
              <option value="en">en</option>
            </select>
          </div>
        </div>

        {downloadError && (
          <div className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
            {downloadError}
          </div>
        )}
      </div>
    </div>
  );
}
