'use client';

import { useEffect, useState } from 'react';
import { Sparkles, Wand2, AlertCircle, PlayCircle } from 'lucide-react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import ConfigPanel from '@/components/feature-factory/ConfigPanel';
import PreviewPanel from '@/components/feature-factory/PreviewPanel';
import NLInputBox from '@/components/feature-factory/NLInputBox';
import GenerationProgress from '@/components/feature-factory/GenerationProgress';
import AutoResearchPanel from '@/components/feature-factory/AutoResearchPanel';
import ExportButtons from '@/components/feature-factory/ExportButtons';
import PreprocessingPanel from '@/components/feature-factory/PreprocessingPanel';
import LayerPanel from '@/components/feature-factory/LayerPanel';
import FeatureExplorer from '@/components/feature-factory/FeatureExplorer';
import BatchGenerationPanel from '@/components/feature-factory/BatchGenerationPanel';
import BatchProgressPanel from '@/components/feature-factory/BatchProgressPanel';

const DEFAULT_SYMBOL = 'BTCUSDT';
const DEFAULT_TIMEFRAME = '12h';

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
    updateConfigPartial,
  } = useFeatureFactoryStore();

  const {
    loadInitial,
    previewConfig,
    startGeneration,
    requestNL2Config,
    loadTaskResult,
  } = useFeatureFactory();

  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [timeframe, setTimeframe] = useState(DEFAULT_TIMEFRAME);
  const [batchSymbols, setBatchSymbols] = useState<string[]>([]);

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

    try {
      await startGeneration(symbol, timeframe, config);
    } catch (err) {
      const message = err instanceof Error ? err.message : '生成任務啟動失敗';
      setError(message);
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
                disabled={isGenerating}
                className="inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 bg-amber-400/20 text-amber-100 border border-amber-300/30 hover:bg-amber-400/30 transition disabled:opacity-50"
              >
                <PlayCircle className="w-5 h-5" />
                {isGenerating ? '生成中...' : '啟動生成'}
              </button>
              <div className="text-xs text-slate-400 flex items-center gap-2">
                <Wand2 className="w-4 h-4" />
                支援多時間框架與自動對齊
              </div>
            </div>
          </div>

          {currentTask && (
            <GenerationProgress task={currentTask} naked />
          )}
        </div>

        {error && (
          <div className="glass-panel rounded-xl p-4 border border-rose-400/30 text-rose-200 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
          <div className="space-y-6">
            <ConfigPanel
              config={config}
              presets={presets}
              dataSources={dataSources}
              symbol={symbol}
              timeframe={timeframe}
              onSymbolChange={setSymbol}
              onTimeframeChange={setTimeframe}
            />
            <PreprocessingPanel
              config={config?.preprocessing}
              onChange={(next) => updateConfigPartial({ preprocessing: next })}
            />
          </div>

          <div className="space-y-6">
            <BatchGenerationPanel
              timeframe={timeframe}
              config={config}
              onSymbolsCommitted={setBatchSymbols}
            />
            <BatchProgressPanel batchTask={batchTask} symbols={batchSymbols} />
            <LayerPanel schema={schema} />
            <PreviewPanel preview={preview} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <NLInputBox onSubmit={requestNL2Config} />
              <ExportButtons
                config={config}
                taskId={currentTask?.task_id}
                symbol={symbol}
                timeframe={timeframe}
              />
            </div>
            {currentTask?.status === 'completed' && (
              <FeatureExplorer taskId={currentTask.task_id} />
            )}
          </div>
        </div>

        <AutoResearchPanel />
      </div>
    </div>
  );
}
