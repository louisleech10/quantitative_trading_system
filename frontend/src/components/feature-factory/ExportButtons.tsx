'use client';

import { useMemo, useState } from 'react';
import { Download } from 'lucide-react';
import { FeatureFactoryConfig } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { exportChartToPNG } from '@/lib/exportUtils';
import { httpErrorMessage } from '@/lib/httpError';

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
  const [includeDatasource, setIncludeDatasource] = useState(false);
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
          message = httpErrorMessage(payload, message);
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
      if (includeDatasource) {
        query.set('include_datasource', 'true');
      }

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

  const btnBase = 'inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-100 hover:bg-white/10 transition whitespace-nowrap disabled:opacity-50';

  return (
    <div>
      {downloadError && (
        <div className="mx-4 mt-3 rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          {downloadError}
        </div>
      )}
      <div id="feature-factory-export-target" className="px-4 pb-4 space-y-3">

      {/* 按鈕列 */}
      <div className="flex flex-wrap items-center gap-2">
        {/* 設定類 */}
        <button onClick={exportConfig} className={btnBase}>
          <Download className="w-3.5 h-3.5" />匯出 Config
        </button>
        <button onClick={exportFeatureList} disabled={!featureList.length} className={btnBase}>
          <Download className="w-3.5 h-3.5" />匯出特徵清單
        </button>

        <div className="h-4 w-px bg-white/10 mx-1" aria-hidden />

        {/* 數據類（需先完成生成） */}
        <button
          onClick={exportCsv}
          disabled={!canExportData || isDownloading}
          title={canExportData ? '匯出特徵 CSV' : '請先完成特徵生成任務'}
          className={btnBase}
        >
          <Download className="w-3.5 h-3.5" />CSV
        </button>
        <button
          onClick={exportJson}
          disabled={!canExportData || isDownloading}
          title={canExportData ? '匯出 AI JSON' : '請先完成特徵生成任務'}
          className={btnBase}
        >
          <Download className="w-3.5 h-3.5" />AI JSON
        </button>
        <button
          onClick={exportMarkdown}
          disabled={!canExportData || isDownloading}
          title={canExportData ? '匯出 Markdown 報告' : '請先完成特徵生成任務'}
          className={btnBase}
        >
          <Download className="w-3.5 h-3.5" />Markdown
        </button>
        <button
          onClick={exportPng}
          disabled={!canExportData || isDownloading}
          title={canExportData ? '匯出 PNG' : '請先完成特徵生成任務'}
          className={btnBase}
        >
          <Download className="w-3.5 h-3.5" />PNG
        </button>
        {!canExportData && (
          <span className="text-[10px] text-slate-500">（CSV / JSON / Markdown / PNG 需先完成生成）</span>
        )}
      </div>

      {/* 選項列 */}
      <div className="flex flex-wrap gap-x-6 gap-y-2 pt-1 border-t border-white/5">
        {/* CSV 選項 */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] text-slate-400 shrink-0">CSV：</span>
          <select
            value={csvColumns}
            onChange={(e) => setCsvColumns(e.target.value)}
            className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[11px] text-slate-100"
          >
            <option value="all">欄位：全部</option>
            <option value="ms_amihud_illiq_21,ent_shannon_close_return_21,tr_cvar_5pct_21">欄位：示例三欄</option>
          </select>
          <select
            value={csvMaxRows}
            onChange={(e) => setCsvMaxRows(e.target.value)}
            className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[11px] text-slate-100"
          >
            <option value="all">行數：全部</option>
            <option value="100">100 行</option>
            <option value="500">500 行</option>
            <option value="1000">1000 行</option>
          </select>
          <label className="inline-flex items-center gap-1 text-[11px] text-slate-300">
            <input type="checkbox" checked={includeMetadataHeader} onChange={(e) => setIncludeMetadataHeader(e.target.checked)} className="accent-cyan-400" />
            Metadata header
          </label>
          <label className="inline-flex items-center gap-1 text-[11px] text-slate-300">
            <input type="checkbox" checked={includeDatasource} onChange={(e) => setIncludeDatasource(e.target.checked)} className="accent-cyan-400" />
            原始數據源欄位
          </label>
        </div>

        {/* Markdown 選項 */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] text-slate-400 shrink-0">Markdown：</span>
          <span className="text-[11px] text-slate-300 shrink-0">Token {tokenBudget}</span>
          <input
            type="range"
            min={500}
            max={32000}
            step={100}
            value={tokenBudget}
            onChange={(e) => setTokenBudget(Number(e.target.value))}
            className="w-28"
          />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[11px] text-slate-100"
          >
            <option value="zh-TW">zh-TW</option>
            <option value="en">en</option>
          </select>
        </div>
      </div>
      </div>
    </div>
  );
}
