'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Sparkles, Wand2, AlertCircle, PlayCircle, Database, Layers, ArrowDownUp, Eye, Download, Cpu } from 'lucide-react';
import { getBackendBrowseTaskId } from '@/lib/batchBrowse';
import { useFeatureFactoryStore, readLastBatchTaskId } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import ConfigPanel from '@/components/feature-factory/ConfigPanel';
import FeatureKlineDownloadPanel from '@/components/feature-factory/FeatureKlineDownloadPanel';
import PreviewPanel from '@/components/feature-factory/PreviewPanel';
import GenerationProgress from '@/components/feature-factory/GenerationProgress';
import RunRetentionDialog from '@/components/feature-factory/RunRetentionDialog';
import RunManagerPanel from '@/components/feature-factory/RunManagerPanel';
import ExportButtons from '@/components/feature-factory/ExportButtons';
import PreprocessingPanel from '@/components/feature-factory/PreprocessingPanel';
import LayerPanel from '@/components/feature-factory/LayerPanel';
import FeatureExplorer from '@/components/feature-factory/FeatureExplorer';
import BatchQualityOverview, {
  BatchRecoverableSelect,
  type RecoverableBatchSummary,
} from '@/components/feature-factory/BatchQualityOverview';
import HardwareStatusPanel from '@/components/feature-factory/HardwareStatusPanel';
import SymbolCoverageMatrix from '@/components/feature-factory/SymbolCoverageMatrix';

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

  const setValidationSummaryForTask = useFeatureFactoryStore((state) => state.setValidationSummaryForTask);
  const registryEntries = useFeatureFactoryStore((state) => state.registryEntries);
  const fetchRegistry = useFeatureFactoryStore((state) => state.fetchRegistry);
  const fetchRuns = useFeatureFactoryStore((state) => state.fetchRuns);
  const distinctSymbolCount = useMemo(
    () => new Set(registryEntries.map((entry) => entry.symbol)).size,
    [registryEntries],
  );

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
  const loadedResultTaskRef = useRef<string | null>(null);
  const fetchedRunsForTaskRef = useRef<string | null>(null);
  const fetchedRunsForBatchRef = useRef<string | null>(null);
  // 已下載的 Feature K 線標的（來自 FeatureKlineDownloadPanel 下載的資料）
  const [featureKlineSymbols, setFeatureKlineSymbols] = useState<string[]>([]);
  const [featureKlineSymbolsLoading, setFeatureKlineSymbolsLoading] = useState(false);
  const [configTab, setConfigTab] = useState<'hardware' | 'kline' | 'data' | 'indicators' | 'preprocessing' | 'preview' | null>('data');
  const [restoredBatchExpired, setRestoredBatchExpired] = useState(false);
  // 穩定 reference：傳給 BatchQualityOverview，避免 inline callback 每次 render 變新 → 重打 /quality
  const handleBatchExpired = useCallback(() => setRestoredBatchExpired(true), []);
  const [recoverableBatches, setRecoverableBatches] = useState<RecoverableBatchSummary[]>([]);
  const [recoverableBatchesLoaded, setRecoverableBatchesLoaded] = useState(false);
  const [selectedRecoverableBatchId, setSelectedRecoverableBatchId] = useState<string | null>(
    null,
  );

  // 無 live batchTask 時從 checkpoint 列舉歷史批次（救 R2 之前的舊批次）
  useEffect(() => {
    if (batchTask) {
      setRecoverableBatches([]);
      setRecoverableBatchesLoaded(false);
      setSelectedRecoverableBatchId(null);
      setRestoredBatchExpired(false);
      return;
    }

    let cancelled = false;
    setRecoverableBatchesLoaded(false);

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/features/batch/list`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as { batches?: RecoverableBatchSummary[] };
        if (cancelled) return;
        const batches = json.batches ?? [];
        setRecoverableBatches(batches);
        const persistedId = readLastBatchTaskId();
        const persistedInList = persistedId
          ? batches.find((b) => b.batch_id === persistedId)
          : undefined;
        setSelectedRecoverableBatchId(
          persistedInList?.batch_id ?? batches[0]?.batch_id ?? null,
        );
        setRestoredBatchExpired(false);
      } catch {
        if (!cancelled) {
          setRecoverableBatches([]);
          setSelectedRecoverableBatchId(readLastBatchTaskId());
        }
      } finally {
        if (!cancelled) setRecoverableBatchesLoaded(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [batchTask]);

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

  const activeQualityBatchId =
    batchTask?.status === 'completed' || batchTask?.status === 'partial'
      ? batchTask.task_id
      : !batchTask && !restoredBatchExpired
        ? selectedRecoverableBatchId
        : null;

  const showBatchQualitySection =
    Boolean(batchTask?.status === 'completed' || batchTask?.status === 'partial') ||
    (!batchTask && recoverableBatchesLoaded);

  const showBatchQualityOverview = Boolean(activeQualityBatchId);
  const showBatchExplorer =
    (batchTask?.status === 'completed' || batchTask?.status === 'partial') &&
    batchSuccessSymbols.length > 0;

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
    const backendBrowseTaskId = getBackendBrowseTaskId(batchTask, sym);
    if (backendBrowseTaskId) {
      setBrowseTaskIds((prev) => ({ ...prev, [sym]: backendBrowseTaskId }));
      return;
    }
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
    fetchRegistry().catch(() => undefined);
  }, [fetchRegistry]);

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
    if (currentTask?.status !== 'completed') {
      return;
    }

    if (loadedResultTaskRef.current === currentTask.task_id) {
      return;
    }

    loadedResultTaskRef.current = currentTask.task_id;
    void loadTaskResult(currentTask.task_id);
  }, [currentTask?.status, currentTask?.task_id, loadTaskResult]);

  // 任務完成且 validation_summary 出現後，立即寫入 per-task localStorage 快取，
  // 讓 FeatureExplorer 在 refresh 後瀏覽歷史任務時仍能顯示 L7 KPI 卡片。
  useEffect(() => {
    if (currentTask?.status === 'completed' && currentTask.task_id && currentTask.validation_summary) {
      setValidationSummaryForTask(currentTask.task_id, currentTask.validation_summary);
    }
  }, [currentTask?.task_id, currentTask?.status, currentTask?.validation_summary, setValidationSummaryForTask]);

  // 單次生成完成後自動重整 Run 列表
  useEffect(() => {
    if (currentTask?.status !== 'completed' || !currentTask.task_id) {
      return;
    }
    if (fetchedRunsForTaskRef.current === currentTask.task_id) {
      return;
    }
    fetchedRunsForTaskRef.current = currentTask.task_id;
    void fetchRuns();
  }, [currentTask?.status, currentTask?.task_id, fetchRuns]);

  // 批次生成完成（或 partial）後自動重整 Run 列表
  useEffect(() => {
    const batchDone =
      batchTask?.status === 'completed' || batchTask?.status === 'partial';
    if (!batchDone || !batchTask.task_id) {
      return;
    }
    if (fetchedRunsForBatchRef.current === batchTask.task_id) {
      return;
    }
    fetchedRunsForBatchRef.current = batchTask.task_id;
    void fetchRuns();
  }, [batchTask?.status, batchTask?.task_id, fetchRuns]);

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
    <div>
      <div className="relative px-4 py-6 space-y-4">
        <div className="relative glass-panel rounded-2xl px-6 py-4 border border-white/10 overflow-hidden">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-amber-200 text-xs uppercase tracking-[0.2em]">
                <Sparkles className="w-4 h-4" />
                Alpha Factory
              </div>
              <h1 className="mt-4 text-2xl font-semibold text-slate-100">
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

        {error && (
          <div className="glass-panel rounded-xl p-4 border border-rose-400/30 text-rose-200 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        <div className="glass-panel rounded-xl p-4 border border-sky-400/20 text-sky-100/90 text-sm">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0 text-sky-300" />
            <div className="space-y-1">
              <div className="font-medium text-sky-200">新增 L1/L2/L3/L6.5 組件前請先閱讀開發守則</div>
              <div className="text-sky-100/70">
                類別屬於高稀疏（&gt;80% 零值）或離散標籤時，必須加入
                <code className="mx-1 px-1 rounded bg-white/10 text-sky-100 font-mono text-xs">RATIO_UNSAFE_CATEGORIES</code>
                黑名單；否則 ratio / momentum / WorldQuant 會在 L2/L3 階段產生大量 NaN（見 2026-05-21 事故）。
              </div>
              <div className="flex flex-wrap gap-3 pt-1 text-xs text-sky-300/80">
                <span>📄 docs/FEATURE_DEVELOPER_CHECKLIST.md</span>
                <span>📄 docs/NAN_POISONING_INVESTIGATION.md</span>
              </div>
            </div>
          </div>
        </div>

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

        <div className="glass-panel rounded-2xl border border-white/10 overflow-hidden">
          {/* Tab 導航列 */}
          <div className={`flex ${configTab !== null ? 'border-b border-white/10' : ''}`}>
            <button
              onClick={() => setConfigTab(configTab === 'hardware' ? null : 'hardware')}
              className={`flex items-center gap-2 px-5 py-3 text-sm whitespace-nowrap transition border-b-2 -mb-px ${
                configTab === 'hardware'
                  ? 'border-rose-400 text-rose-200 bg-rose-400/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <Cpu className="w-4 h-4" />
              系統資源
            </button>
            <button
              onClick={() => setConfigTab(configTab === 'kline' ? null : 'kline')}
              className={`flex items-center gap-2 px-5 py-3 text-sm whitespace-nowrap transition border-b-2 -mb-px ${
                configTab === 'kline'
                  ? 'border-emerald-400 text-emerald-200 bg-emerald-400/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <Download className="w-4 h-4" />
              K 線下載
            </button>
            <button
              onClick={() => setConfigTab(configTab === 'data' ? null : 'data')}
              className={`flex items-center gap-2 px-5 py-3 text-sm whitespace-nowrap transition border-b-2 -mb-px ${
                configTab === 'data'
                  ? 'border-blue-400 text-blue-200 bg-blue-400/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <Database className="w-4 h-4" />
              資料
            </button>
            <button
              onClick={() => setConfigTab(configTab === 'indicators' ? null : 'indicators')}
              className={`flex items-center gap-2 px-5 py-3 text-sm whitespace-nowrap transition border-b-2 -mb-px ${
                configTab === 'indicators'
                  ? 'border-violet-400 text-violet-200 bg-violet-400/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <Layers className="w-4 h-4" />
              指標層
            </button>
            <button
              onClick={() => setConfigTab(configTab === 'preprocessing' ? null : 'preprocessing')}
              className={`flex items-center gap-2 px-5 py-3 text-sm whitespace-nowrap transition border-b-2 -mb-px ${
                configTab === 'preprocessing'
                  ? 'border-cyan-400 text-cyan-200 bg-cyan-400/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <ArrowDownUp className="w-4 h-4" />
              前處理
            </button>
            <button
              onClick={() => setConfigTab(configTab === 'preview' ? null : 'preview')}
              className={`flex items-center gap-2 px-5 py-3 text-sm whitespace-nowrap transition border-b-2 -mb-px ${
                configTab === 'preview'
                  ? 'border-amber-400 text-amber-200 bg-amber-400/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/5'
              }`}
            >
              <Eye className="w-4 h-4" />
              預覽 / 匯出
            </button>
          </div>

          {/* Tab 內容 */}
          {configTab === 'hardware' && (
            <div className="px-4 py-4">
              <HardwareStatusPanel />
            </div>
          )}
          {configTab === 'kline' && (
            <div className="px-4 py-4">
              <FeatureKlineDownloadPanel onDownloadComplete={refreshFeatureKlineSymbols} />
            </div>
          )}
          {configTab === 'data' && (
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
          )}
          {configTab === 'indicators' && <LayerPanel schema={schema} />}
          {configTab === 'preprocessing' && (
            <PreprocessingPanel
              config={config?.preprocessing}
              onChange={(next) => updateConfigPartial({ preprocessing: next })}
            />
          )}
          {configTab === 'preview' && (
            <>
              <PreviewPanel preview={preview} />
              <ExportButtons
                config={config}
                taskId={currentTask?.task_id}
                symbol={normalizedSymbols[0] ?? symbol}
                timeframe={timeframe}
              />
            </>
          )}
        </div>
        <FeatureExplorer taskId={currentTask?.task_id} taskStatus={currentTask?.status} validationSummary={currentTask?.validation_summary} />
        {(showBatchQualitySection || showBatchExplorer) && (
            <>
              {showBatchQualitySection && !batchTask && (
                <div className="glass-panel rounded-xl p-4 border border-white/10 space-y-3">
                  <div className="text-sm font-medium text-slate-300">批次品質 — 歷史批次</div>
                  {recoverableBatches.length > 0 ? (
                    <BatchRecoverableSelect
                      batches={recoverableBatches}
                      value={selectedRecoverableBatchId ?? ''}
                      onChange={(id) => {
                        setSelectedRecoverableBatchId(id);
                        setRestoredBatchExpired(false);
                      }}
                    />
                  ) : recoverableBatchesLoaded ? (
                    <p className="text-xs text-slate-500">無歷史批次（尚無可恢復的 checkpoint）</p>
                  ) : (
                    <p className="text-xs text-slate-500">載入歷史批次…</p>
                  )}
                </div>
              )}
              {showBatchQualityOverview && activeQualityBatchId && (
                <BatchQualityOverview
                  batchTaskId={activeQualityBatchId}
                  onBatchExpired={handleBatchExpired}
                />
              )}
              {showBatchExplorer && (
              <>
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
            </>
          )}

        <RunRetentionDialog />
        <RunManagerPanel />
        <div className="glass-panel rounded-xl p-4 border border-white/10 space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">跨 Symbol Coverage Matrix</div>
            <p className="text-xs text-slate-500 mt-1">
              比對多個 Symbol 在同一 timeframe 下各 feature 的覆蓋率（= 非 NaN 比率 = 1 − NaN 比率，越高越好），找出跨標的不穩定的特徵。需先在 Feature Factory 生成至少 2 個 Symbol 的特徵。
            </p>
          </div>
          {distinctSymbolCount >= 2 ? (
            <SymbolCoverageMatrix entries={registryEntries} />
          ) : (
            <div className="rounded-md border border-white/10 bg-slate-950/40 p-3 text-sm text-slate-400">
              需至少 2 個 Symbol 的特徵資料，請先生成更多 Symbol 的特徵。
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
