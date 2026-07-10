'use client';

import { useMemo } from 'react';
import { ICAnalysisConfig, RunInfo } from '@/lib/types';
import { FeatureTierLevel } from '@/lib/types';
import FeatureTierPanel from '@/components/ic-analysis/FeatureTierPanel';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { NumberInput } from '@/components/ui/NumberInput';
import { MultiSelect } from '@/components/ui/MultiSelect';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { formatRunLabel } from '@/lib/runExplorer';

interface ICConfigPanelProps {
  config: ICAnalysisConfig;
  runs?: RunInfo[];
  runsLoading?: boolean;
  runsError?: string | null;
  crossSectionalFeatureCount?: number;
  featureTier: FeatureTierLevel;
  featureToggles: Record<string, boolean>;
  onChangeFeatureTier: (tier: FeatureTierLevel) => void;
  onToggleFeature: (key: string) => void;
  onConfigChange: (next: ICAnalysisConfig) => void;
  onRunAnalysis: () => void;
  isRunning: boolean;
}

type ICConfigPatch = Partial<Omit<ICAnalysisConfig, 'thresholds'>> & {
  thresholds?: Partial<ICAnalysisConfig['thresholds']>;
};

const horizonOptions = [1, 2, 3, 5, 8, 13, 21].map((value) => ({
  value: String(value),
  label: `${value} 根`,
}));

function formatRunLeafLabel(run: RunInfo): string {
  const base = formatRunLabel(run);
  const primary = run.timeframe;
  const training = (run.training_timeframes || []).filter((tf) => tf && tf !== primary);
  if (training.length === 0) {
    return base;
  }
  return `${base} · ${primary}(+${training.join(',')})`;
}

function groupRunsByBatch(runs: RunInfo[]): { key: string; label: string; items: RunInfo[] }[] {
  const buckets = new Map<string, RunInfo[]>();
  for (const run of runs) {
    const batchId = run.batch_id || '__ungrouped__';
    const key = `${batchId}::${run.timeframe}`;
    if (!buckets.has(key)) {
      buckets.set(key, []);
    }
    buckets.get(key)!.push(run);
  }
  return Array.from(buckets.entries())
    .map(([key, items]) => {
      const batchId = key.split('::')[0] ?? '__ungrouped__';
      const timeframe = items[0]?.timeframe ?? '';
      return {
        key,
        label:
          batchId === '__ungrouped__'
            ? `未分組 · ${timeframe}`
            : `${items[0]?.batch_alias || batchId} · ${timeframe}`,
        items,
      };
    })
    .filter((group) => group.items.length >= 2);
}

export default function ICConfigPanel({
  config,
  runs = [],
  runsLoading = false,
  runsError = null,
  crossSectionalFeatureCount = 0,
  featureTier,
  featureToggles,
  onChangeFeatureTier,
  onToggleFeature,
  onConfigChange,
  onRunAnalysis,
  isRunning,
}: ICConfigPanelProps) {
  const horizonValues = useMemo(() => config.horizons.map((value) => String(value)), [config.horizons]);
  const browseReadyRuns = useMemo(() => runs.filter((run) => run.browse_ready), [runs]);
  const batchGroups = useMemo(() => groupRunsByBatch(browseReadyRuns), [browseReadyRuns]);
  const batchOptions = useMemo(
    () =>
      batchGroups.map((group) => ({
        value: group.key,
        label: group.label,
        symbolCount: group.items.length,
      })),
    [batchGroups],
  );

  const selectedRunKey = config.config_hash
    ? `${config.symbol}:${config.timeframe}:${config.config_hash}`
    : undefined;

  const selectedBatchId = useMemo(() => {
    if (!config.cross_sectional_runs?.length) {
      return undefined;
    }
    const anchor = config.cross_sectional_runs[0];
    const match = browseReadyRuns.find(
      (run) => run.symbol === anchor.symbol && run.config_hash === anchor.config_hash,
    );
    return match?.batch_id
      ? `${match.batch_id}::${match.timeframe}`
      : `__ungrouped__::${match?.timeframe ?? ''}`;
  }, [browseReadyRuns, config.cross_sectional_runs]);

  const isCrossSectionalMode = config.mode === 'cross_sectional';
  const crossRuns = config.cross_sectional_runs || [];
  const crossSymbolInsufficient = isCrossSectionalMode && crossRuns.length < 2;
  const crossFeatureOverflow = isCrossSectionalMode && crossSectionalFeatureCount > 50;
  const noAvailableRuns = browseReadyRuns.length === 0;
  const crossBatchInsufficient = isCrossSectionalMode && batchOptions.length === 0;

  const runDisabled =
    isRunning ||
    (isCrossSectionalMode
      ? crossSymbolInsufficient || crossFeatureOverflow || crossBatchInsufficient || noAvailableRuns
      : !config.config_hash || !config.symbol || !config.timeframe);

  const updateConfig = (patch: ICConfigPatch) => {
    onConfigChange({
      ...config,
      ...patch,
      thresholds: {
        ...config.thresholds,
        ...(patch.thresholds || {}),
      },
    });
  };

  const handleSelectRun = (runKey: string) => {
    const run = browseReadyRuns.find(
      (item) => `${item.symbol}:${item.timeframe}:${item.config_hash}` === runKey,
    );
    if (!run) {
      return;
    }
    updateConfig({
      symbol: run.symbol,
      timeframe: run.timeframe,
      config_hash: run.config_hash,
    });
  };

  const handleSelectBatch = (batchKey: string) => {
    const group = batchGroups.find((item) => item.key === batchKey);
    if (!group || group.items.length === 0) {
      return;
    }
    const primaryTf = group.items[0]?.timeframe;
    updateConfig({
      timeframe: primaryTf,
      cross_sectional_runs: group.items.map((run) => ({
        symbol: run.symbol,
        config_hash: run.config_hash,
      })),
      cross_sectional_symbols: group.items.map((run) => run.symbol),
    });
  };

  return (
    <div className="glass-panel rounded-2xl border border-white/10 p-6 space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-cyan-200">IC Gatekeeper</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-100">分析配置</h2>
        <p className="text-sm text-slate-400 mt-1">調整門檻後將自動重新篩選。</p>
      </div>

      <FeatureTierPanel
        featureTier={featureTier}
        featureToggles={featureToggles}
        onChangeTier={onChangeFeatureTier}
        onToggleFeature={onToggleFeature}
        analysisMode={config.mode}
      />

      <div className="space-y-4">
        <div className="rounded-lg border border-white/10 p-3 space-y-3">
          <p className="text-xs text-slate-400">從 Feature Library 選擇 Run</p>
          {runsLoading && <p className="text-xs text-slate-400">載入 runs...</p>}
          {runsError && <p className="text-xs text-rose-300">{runsError}</p>}
          {!runsLoading && !runsError && noAvailableRuns && (
            <p className="text-xs text-amber-300">無可選 run，請先去 Feature Factory 生成</p>
          )}

          {!isCrossSectionalMode ? (
            <Select value={selectedRunKey} onValueChange={handleSelectRun} disabled={noAvailableRuns}>
              <SelectTrigger>
                <SelectValue placeholder="選擇 Run（依批次分組）" />
              </SelectTrigger>
              <SelectContent>
                {batchGroups.map((group) => (
                  <SelectGroup key={group.key}>
                    <SelectLabel>{group.label}</SelectLabel>
                    {group.items.map((run) => {
                      const key = `${run.symbol}:${run.timeframe}:${run.config_hash}`;
                      return (
                        <SelectItem key={key} value={key}>
                          {formatRunLeafLabel(run)}
                        </SelectItem>
                      );
                    })}
                  </SelectGroup>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <div className="space-y-3">
              <Select
                value={selectedBatchId}
                onValueChange={handleSelectBatch}
                disabled={batchOptions.length === 0}
              >
                <SelectTrigger>
                  <SelectValue placeholder={batchOptions.length === 0 ? '無可用批次' : '選擇批次'} />
                </SelectTrigger>
                <SelectContent>
                  {batchOptions.map((batch) => (
                    <SelectItem key={batch.value} value={batch.value}>
                      {batch.label} · {batch.symbolCount} symbols
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <label className="text-sm font-medium text-slate-200">分析模式</label>
        <Select
          value={config.mode}
          onValueChange={(value) => updateConfig({ mode: value as ICAnalysisConfig['mode'] })}
        >
          <SelectTrigger>
            <SelectValue placeholder="選擇模式" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="global">Global 模式</SelectItem>
            <SelectItem value="event">Event-Driven 模式</SelectItem>
            <SelectItem value="cross_sectional">截面 IC</SelectItem>
          </SelectContent>
        </Select>

        {config.mode === 'event' && (
          <Textarea
            placeholder="例如: (close > close_EMA_55) & (close_ADX_14 > 25)"
            value={config.event_query || ''}
            onChange={(event) => updateConfig({ event_query: event.target.value })}
            rows={4}
          />
        )}

        {isCrossSectionalMode && (
          <div className="space-y-2 text-xs">
            {crossSymbolInsufficient && (
              <p className="text-amber-300">請選擇至少含 2 個 Symbol 的批次</p>
            )}
            {crossFeatureOverflow && (
              <p className="text-amber-300">截面 IC 最多支援 50 個因子，請先在 Feature Browser 篩選</p>
            )}
            {crossBatchInsufficient && (
              <p className="text-amber-300">無可用批次</p>
            )}
            {noAvailableRuns && (
              <p className="text-amber-300">無可用標的</p>
            )}
            <p className="text-slate-400">目前預估分析因子數：{crossSectionalFeatureCount}</p>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <NumberInput
          label="IC Mean 最小值"
          value={config.thresholds.ic_mean_min}
          onChange={(value) => updateConfig({ thresholds: { ic_mean_min: value } })}
          min={-1}
          max={1}
          step={0.01}
        />
        <NumberInput
          label="ICIR 最小值"
          value={config.thresholds.icir_min}
          onChange={(value) => updateConfig({ thresholds: { icir_min: value } })}
          min={-2}
          max={3}
          step={0.05}
        />
        <NumberInput
          label="P-Value 最大值"
          value={config.thresholds.p_value_max}
          onChange={(value) => updateConfig({ thresholds: { p_value_max: value } })}
          min={0.001}
          max={0.5}
          step={0.005}
        />
        <NumberInput
          label="單調性分數"
          value={config.thresholds.monotonicity_score_min ?? 0.6}
          onChange={(value) => updateConfig({ thresholds: { monotonicity_score_min: value } })}
          min={0}
          max={1}
          step={0.05}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-200">相關性閾值</label>
          <span className="text-xs text-slate-400">{config.thresholds.correlation_threshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0.3}
          max={0.95}
          step={0.01}
          value={config.thresholds.correlation_threshold}
          onChange={(event) =>
            updateConfig({
              thresholds: { correlation_threshold: Number(event.target.value) },
            })
          }
          className="w-full accent-cyan-400"
        />
      </div>

      <MultiSelect
        label="Horizon 多選"
        options={horizonOptions}
        value={horizonValues}
        onChange={(values) =>
          updateConfig({ horizons: values.map((value) => Number(value)).filter((value) => !Number.isNaN(value)) })
        }
        placeholder="選擇 horizon"
      />

      <Button
        onClick={onRunAnalysis}
        disabled={runDisabled}
        className="w-full bg-cyan-500/20 text-cyan-100 border border-cyan-300/30 hover:bg-cyan-500/30"
      >
        {isRunning ? '分析執行中...' : '啟動 IC 分析'}
      </Button>
    </div>
  );
}
