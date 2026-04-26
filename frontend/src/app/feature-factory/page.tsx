'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Sparkles, Wand2, AlertCircle, PlayCircle } from 'lucide-react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import ConfigPanel from '@/components/feature-factory/ConfigPanel';
import FeatureKlineDownloadPanel from '@/components/feature-factory/FeatureKlineDownloadPanel';
import PreviewPanel from '@/components/feature-factory/PreviewPanel';
import GenerationProgress from '@/components/feature-factory/GenerationProgress';
import AutoResearchPanel from '@/components/feature-factory/AutoResearchPanel';
import ExportButtons from '@/components/feature-factory/ExportButtons';
import PreprocessingPanel from '@/components/feature-factory/PreprocessingPanel';
import LayerPanel from '@/components/feature-factory/LayerPanel';
import FeatureExplorer from '@/components/feature-factory/FeatureExplorer';
import BatchQualityOverview from '@/components/feature-factory/BatchQualityOverview';
import HardwareStatusPanel from '@/components/feature-factory/HardwareStatusPanel';

const DEFAULT_SYMBOL = 'BTCUSDT';
const DEFAULT_TIMEFRAME = '12h';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function parseSymbols(input: string): string[] {
  return Array.from(
    new Set(
      input
        .split(/[\s,]+/)
        .map((item) => item.trim().toUpperCase())
        .filter((item) => item.length > 0)
    )
  );
}

export default function FeatureFactoryPage() {
  const {
    config,
    preview,
    presets,
    dataSources,
    schema,
    currentTask,
    batchTask,
    isGenerating,
    error,
    setError,
    setCurrentTask,
    setBatchTask,
    updateConfigPartial,
  } = useFeatureFactoryStore();

  const {
    loadInitial,
    previewConfig,
    startGeneration,
    startBatchGeneration,
    loadTaskResult,
  } = useFeatureFactory();

  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [timeframe, setTimeframe] = useState(DEFAULT_TIMEFRAME);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedBatchSymbol, setSelectedBatchSymbol] = useState<string | null>(null);
  const [browseTaskIds, setBrowseTaskIds] = useState<Record<string, string>>({});
  const [registeringSymbol, setRegisteringSymbol] = useState<string | null>(null);
  // 已下載的 Feature K 線標的（來自 FeatureKlineDownloadPanel 下載的資料）
  const [featureKlineSymbols, setFeatureKlineSymbols] = useState<string[]>([]);
  const [featureKlineSymbolsLoading, setFeatureKlineSymbolsLoading] = useState(false);

  const refreshFeatureKlineSymbols = useCallback(async () => {
    setFeatureKlineSymbolsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/feature-data/kline/list`);
      if (res.ok) {
        const data = await res.json();
        const symbols = Array.from(
          new Set<string>((data.entries ?? []).map((e: { symbol: string }) => e.symbol))
        ) as string[];
        setFeatureKlineSymbols(symbols);
      }
    } catch {
      // 靜默失敗，不影響主功能
    } finally {
      setFeatureKlineSymbolsLoading(false);
    }
  }, []);

  // 頁面載入時抓一次；FeatureKlineDownloadPanel 下載完成後也會刷新
  useEffect(() => { refreshFeatureKlineSymbols(); }, [refreshFeatureKlineSymbols]);

  const batchResults = batchTask?.results ?? {};
  const batchSuccessSymbols = Object.keys(batchResults);

  // 批次完成後自動選擇第一個成功的 symbol
  useEffect(() => {
    if (
      (batchTask?.status === 'completed' || batchTask?.status === 'partial') &&
      batchSuccessSymbols.length > 0 &&
      !selectedBatchSymbol
    ) {
      setSelectedBatchSymbol(batchSuccessSymbols[0]);
    }
  }, [batchTask?.status, batchSuccessSymbols, selectedBatchSymbol]);

  const handleSelectBatchSymbol = async (sym: string) => {
    setSelectedBatchSymbol(sym);
    if (browseTaskIds[sym]) return; // 已登錄，無需重複呼叫
    const hdf5Path = batchResults[sym];
    if (!hdf5Path) return;
    setRegisteringSymbol(sym);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/features/browse/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: sym, timeframe, hdf5_path: hdf5Path }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json() as { task_id: string };
      setBrowseTaskIds((prev) => ({ ...prev, [sym]: data.task_id }));
    } catch (err) {
      setError(err instanceof Error ? err.message : `登錄 ${sym} 失敗`);
    } finally {
      setRegisteringSymbol(null);
    }
  };

  const normalizedSymbols = useMemo(() => parseSymbols(symbol), [symbol]);
  const isBatchMode = normalizedSymbols.length > 1;

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    if (!config) {
      return;
    }

    const timer = setTimeout(() => {
      previewConfig(config);
    }, 400);

    return () => clearTimeout(timer);
  }, [config, previewConfig]);

  useEffect(() => {
    if (currentTask?.status === 'completed') {
      loadTaskResult(currentTask.task_id);
    }
  }, [currentTask, loadTaskResult]);

  const handleGenerate = async () => {
    if (!config) {
      setError('尚未載入設定，請稍後再試');
      return;
    }

    if (normalizedSymbols.length === 0) {
      setError('請輸入至少一個標的');
      return;
    }

    setIsSubmitting(true);
    try {
      if (normalizedSymbols.length === 1) {
        setBatchTask(null);
        await startGeneration(normalizedSymbols[0], timeframe, config, startDate || undefined, endDate || undefined);
      } else {
        setCurrentTask(null);
        await startBatchGeneration({
          symbols: normalizedSymbols,
          timeframe,
          config_override: config as unknown as Record<string, unknown>,
          force_regenerate: true,
          max_workers: 4,
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '生成任務啟動失敗';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="relative px-6 py-8 max-w-[1400px] mx-auto space-y-6">
        <div className="absolute -top-24 -right-24 h-72 w-72 rounded-full bg-gradient-to-br from-amber-400/20 via-transparent to-emerald-400/20 blur-3xl" />
        <div className="absolute -bottom-28 left-10 h-60 w-60 rounded-full bg-gradient-to-br from-cyan-400/20 via-transparent to-amber-400/20 blur-3xl" />

        <div className="relative glass-panel rounded-2xl p-6 border border-white/10 overflow-hidden">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-amber-200 text-xs uppercase tracking-[0.2em]">
                <Sparkles className="w-4 h-4" />
                Alpha Factory
              </div>
              <h1 className="mt-4 text-3xl lg:text-4xl font-semibold text-slate-100">
                Feature Factory 控制中樞
              </h1>
              <p className="mt-2 text-slate-400 max-w-2xl">
                以「配置即實驗」驅動特徵生成，這裡整合預覽、自然語言設定、進度追蹤與自動研究模式。
              </p>
            </div>

            <div className="flex flex-col gap-3 min-w-[240px]">
              <button
                onClick={handleGenerate}
                disabled={isGenerating || isSubmitting}
                className="inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 bg-amber-400/20 text-amber-100 border border-amber-300/30 hover:bg-amber-400/30 transition disabled:opacity-50"
              >
                <PlayCircle className="w-5 h-5" />
                {isSubmitting ? '啟動中...' : isBatchMode ? '啟動批次生成' : '啟動生成'}
              </button>
              <div className="text-xs text-slate-400 flex items-center gap-2">
                <Wand2 className="w-4 h-4" />
                支援多標的批次、多時間框架與自動對齊
              </div>
            </div>
          </div>

          {(currentTask || batchTask) && (
            <GenerationProgress task={currentTask} batchTask={batchTask} symbols={normalizedSymbols} naked />
          )}
        </div>

        <HardwareStatusPanel />

        {error && (
          <div className="glass-panel rounded-xl p-4 border border-rose-400/30 text-rose-200 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        {currentTask?.status === 'completed' && currentTask.validation_summary && (
          (() => {
            const v = currentTask.validation_summary;
            const coveragePct = (v.coverage * 100).toFixed(2);
            const infRatioPct = (v.inf_ratio * 100).toFixed(4);
            const hasIssue = v.has_inf || v.coverage < 0.95;
            const borderCls = v.has_inf
              ? 'border-rose-400/40'
              : v.coverage < 0.95
                ? 'border-amber-400/30'
                : 'border-emerald-400/30';
            const titleCls = v.has_inf
              ? 'text-rose-300'
              : v.coverage < 0.95
                ? 'text-amber-300'
                : 'text-emerald-300';
            return (
              <div className={`glass-panel rounded-xl p-4 border ${borderCls} space-y-3`}>
                <div className={`flex items-center gap-2 font-medium ${titleCls}`}>
                  <AlertCircle className="w-5 h-5" />
                  <span>
                    L7 資料品質摘要 {hasIssue ? '— 偵測到輸入病理性訊號' : '— 通過'}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  <div className="rounded-lg border border-white/10 bg-[#141b2d]/60 p-3">
                    <div className="text-xs text-slate-400">Coverage</div>
                    <div className="mt-1 text-lg font-semibold text-slate-100">{coveragePct}%</div>
                    <div className="text-xs text-slate-500 mt-0.5">非 NaN 比例</div>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-[#141b2d]/60 p-3">
                    <div className="text-xs text-slate-400">Inf Count</div>
                    <div
                      className={`mt-1 text-lg font-semibold ${v.inf_count > 0 ? 'text-rose-300' : 'text-emerald-300'}`}
                    >
                      {v.inf_count.toLocaleString()}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">Float32 溢位次數</div>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-[#141b2d]/60 p-3">
                    <div className="text-xs text-slate-400">Inf Ratio</div>
                    <div
                      className={`mt-1 text-lg font-semibold ${v.inf_ratio > 0 ? 'text-rose-300' : 'text-emerald-300'}`}
                    >
                      {infRatioPct}%
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">Inf / 總值</div>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-[#141b2d]/60 p-3">
                    <div className="text-xs text-slate-400">Groups w/ Inf</div>
                    <div
                      className={`mt-1 text-lg font-semibold ${v.groups_with_inf > 0 ? 'text-amber-300' : 'text-emerald-300'}`}
                    >
                      {v.groups_with_inf}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">受影響 group 數</div>
                  </div>
                </div>
                {v.has_inf && (
                  <div className="text-xs text-rose-200/80">
                    💡 Inf 通常源自比值類指標分母趨近 0 或回歸視窗常數。已套用 epsilon mask
                    + 1e30 cap，並由 L6.5 winsorization 進一步處理。詳細位置見後端 log 的 Top-5 offending groups。
                  </div>
                )}
              </div>
            );
          })()
        )}

        {currentTask?.status === 'completed' &&
          currentTask.compute_warnings &&
          currentTask.compute_warnings.length > 0 && (
            <div className="glass-panel rounded-xl p-4 border border-amber-400/30 space-y-2">
              <div className="flex items-center gap-2 font-medium text-amber-300">
                <AlertCircle className="w-5 h-5" />
                <span>計算警告（{currentTask.compute_warnings.length} 項）— 部分指標因數據源缺失而降級或跳過</span>
              </div>
              <ul className="space-y-1 text-sm text-amber-100/80">
                {currentTask.compute_warnings.map((w, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0 text-amber-400">•</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

        <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
          <div className="space-y-6">
            <FeatureKlineDownloadPanel onDownloadComplete={refreshFeatureKlineSymbols} />
            <ConfigPanel
              config={config}
              presets={presets}
              dataSources={dataSources}
              importedSymbols={featureKlineSymbols}
              isImportedSymbolsLoading={featureKlineSymbolsLoading}
              lockSymbolInput={false}
              symbol={symbol}
              timeframe={timeframe}
              startDate={startDate}
              endDate={endDate}
              onSymbolChange={setSymbol}
              onTimeframeChange={setTimeframe}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
            />
            <PreprocessingPanel
              config={config?.preprocessing}
              onChange={(next) => updateConfigPartial({ preprocessing: next })}
            />
          </div>

          <div className="space-y-6">
            <LayerPanel schema={schema} />
            <PreviewPanel preview={preview} />
            <ExportButtons
              config={config}
              taskId={currentTask?.task_id}
              symbol={normalizedSymbols[0] ?? symbol}
              timeframe={timeframe}
            />
            <FeatureExplorer taskId={currentTask?.task_id} taskStatus={currentTask?.status} />
            {(batchTask?.status === 'completed' || batchTask?.status === 'partial') &&
              batchSuccessSymbols.length > 0 && (
                <>
                  <BatchQualityOverview batchTaskId={batchTask.task_id} />
                  {/* 批次模式 Symbol 選擇器 */}
                  <div className="glass-panel rounded-xl p-4 border border-white/10 space-y-3">
                    <div className="text-sm font-medium text-slate-300">Feature Explorer — 選擇標的</div>
                    <div className="flex flex-wrap gap-2">
                      {batchSuccessSymbols.map((sym) => (
                        <button
                          key={sym}
                          onClick={() => handleSelectBatchSymbol(sym)}
                          disabled={registeringSymbol === sym}
                          className={`rounded-full px-3 py-1 text-xs border transition ${
                            selectedBatchSymbol === sym
                              ? 'bg-cyan-400/20 border-cyan-300/40 text-cyan-200'
                              : 'border-white/10 text-slate-400 hover:text-slate-200 hover:bg-white/5'
                          } disabled:opacity-50`}
                        >
                          {registeringSymbol === sym ? (
                            <span className="flex items-center gap-1">
                              <span className="inline-block w-3 h-3 rounded-full border-2 border-cyan-400/60 border-t-cyan-300 animate-spin" />
                              {sym}
                            </span>
                          ) : sym}
                        </button>
                      ))}
                    </div>
                    {selectedBatchSymbol && browseTaskIds[selectedBatchSymbol] && (
                      <FeatureExplorer taskId={browseTaskIds[selectedBatchSymbol]} />
                    )}
                    {selectedBatchSymbol && !browseTaskIds[selectedBatchSymbol] && registeringSymbol === selectedBatchSymbol && (
                      <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
                        <span className="inline-block w-3 h-3 rounded-full border-2 border-amber-400/60 border-t-amber-300 animate-spin" />
                        載入 {selectedBatchSymbol} 特徵資料中…
                      </div>
                    )}
                  </div>
                </>
              )}
          </div>
        </div>

        <AutoResearchPanel />
      </div>
    </div>
  );
}
