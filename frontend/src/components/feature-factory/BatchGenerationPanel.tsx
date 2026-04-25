'use client';

import { useMemo, useState } from 'react';
import { ListPlus, Loader2 } from 'lucide-react';
import { BatchGenerateRequest, FeatureFactoryConfig } from '@/lib/types';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { useSearchStore } from '@/store/searchStore';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useAvailableSymbols } from '@/hooks/useAvailableSymbols';

interface BatchGenerationPanelProps {
  timeframe: string;
  config: FeatureFactoryConfig | null;
  onSymbolsCommitted?: (symbols: string[]) => void;
}

const DEFAULT_MAX_WORKERS = 4;

function normalizeSymbols(input: string[]): string[] {
  return Array.from(
    new Set(
      input
        .map((symbol) => symbol.trim().toUpperCase())
        .filter((symbol) => symbol.length > 0)
    )
  );
}

export default function BatchGenerationPanel({
  timeframe,
  config,
  onSymbolsCommitted,
}: BatchGenerationPanelProps) {
  const { startBatchGeneration } = useFeatureFactory();
  const { currentResult } = useSearchStore();
  const { symbols: availableSymbols, isLoading: isLoadingSymbols } = useAvailableSymbols();
  const { error, setError } = useFeatureFactoryStore();

  const [manualSymbols, setManualSymbols] = useState('');
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [maxWorkers, setMaxWorkers] = useState(DEFAULT_MAX_WORKERS);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const searchSymbols = useMemo(() => {
    if (!currentResult?.cases?.length) {
      return [];
    }
    return normalizeSymbols(currentResult.cases.map((item) => item.symbol));
  }, [currentResult]);

  const mergedSelection = useMemo(() => normalizeSymbols(selectedSymbols), [selectedSymbols]);

  const importFromSearch = () => {
    setSelectedSymbols((prev) => normalizeSymbols([...prev, ...searchSymbols]));
  };

  const importFromManual = () => {
    const parsed = manualSymbols
      .split(',')
      .map((symbol) => symbol.trim())
      .filter((symbol) => symbol.length > 0);
    setSelectedSymbols((prev) => normalizeSymbols([...prev, ...parsed]));
  };

  const importFromAvailable = () => {
    setSelectedSymbols((prev) => normalizeSymbols([...prev, ...availableSymbols]));
  };

  const toggleSymbol = (symbol: string) => {
    setSelectedSymbols((prev) => {
      if (prev.includes(symbol)) {
        return prev.filter((item) => item !== symbol);
      }
      return normalizeSymbols([...prev, symbol]);
    });
  };

  const handleStart = async () => {
    const symbols = mergedSelection;
    if (symbols.length === 0) {
      setError('請先選擇至少一個標的');
      return;
    }

    setIsSubmitting(true);
    const request: BatchGenerateRequest = {
      symbols,
      timeframe,
      config_override: (config as unknown as Record<string, unknown>) ?? undefined,
      max_workers: maxWorkers,
      force_regenerate: true,
    };

    const taskId = await startBatchGeneration(request);
    setIsSubmitting(false);

    if (taskId) {
      onSymbolsCommitted?.(symbols);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4 border border-white/10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-lg font-semibold text-slate-100">批次特徵生成</div>
          <div className="text-xs text-slate-400">來源：搜尋結果 / 手動輸入 / 可用標的清單</div>
        </div>
        <button
          type="button"
          onClick={handleStart}
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 rounded-xl px-4 py-2 bg-emerald-400/20 text-emerald-100 border border-emerald-300/30 disabled:opacity-50"
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ListPlus className="w-4 h-4" />}
          {isSubmitting ? '啟動中...' : '啟動批次生成'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">匯入來源</div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={importFromSearch}
              className="rounded-lg px-3 py-1 text-xs border border-white/15 text-slate-200 hover:border-amber-300/40"
            >
              從搜尋結果匯入 ({searchSymbols.length})
            </button>
            <button
              type="button"
              onClick={importFromAvailable}
              disabled={isLoadingSymbols}
              className="rounded-lg px-3 py-1 text-xs border border-white/15 text-slate-200 hover:border-amber-300/40 disabled:opacity-50"
            >
              匯入可用標的 ({availableSymbols.length})
            </button>
          </div>

          <div className="space-y-2">
            <label className="text-xs text-slate-400">手動輸入（逗號分隔）</label>
            <textarea
              value={manualSymbols}
              onChange={(event) => setManualSymbols(event.target.value.toUpperCase())}
              className="w-full min-h-20 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
              placeholder="BTCUSDT, ETHUSDT, SOLUSDT"
            />
            <button
              type="button"
              onClick={importFromManual}
              className="rounded-lg px-3 py-1 text-xs border border-white/15 text-slate-200 hover:border-amber-300/40"
            >
              加入手動標的
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">執行參數</div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-3 space-y-3">
            <div className="text-xs text-slate-300">主時間框架：{timeframe}</div>
            <div>
              <div className="flex items-center justify-between text-xs text-slate-300 mb-2">
                <span>Max Workers</span>
                <span>{maxWorkers}</span>
              </div>
              <input
                type="range"
                min={1}
                max={8}
                step={1}
                value={maxWorkers}
                onChange={(event) => setMaxWorkers(Number(event.target.value))}
                className="w-full"
              />
            </div>
            <div className="text-xs text-slate-400">範圍 1-8，預設 4</div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">已選標的</div>
          <div className="text-xs text-slate-300">{mergedSelection.length} 個</div>
        </div>
        <div className="max-h-44 overflow-auto rounded-xl border border-white/10 bg-white/5 p-3 grid grid-cols-2 md:grid-cols-3 gap-2">
          {availableSymbols.slice(0, 120).map((symbol) => {
            const checked = mergedSelection.includes(symbol);
            return (
              <label key={symbol} className="flex items-center gap-2 text-xs text-slate-200">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleSymbol(symbol)}
                  className="accent-amber-300"
                />
                <span>{symbol}</span>
              </label>
            );
          })}
          {availableSymbols.length === 0 && !isLoadingSymbols && (
            <div className="text-xs text-slate-400">目前沒有可用標的</div>
          )}
        </div>
      </div>

      {error && <div className="text-xs text-rose-300">{error}</div>}
    </div>
  );
}
