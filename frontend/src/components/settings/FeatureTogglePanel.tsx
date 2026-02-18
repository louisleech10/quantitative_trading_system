import { useEffect, useMemo } from 'react';

import type { FeatureToggle } from '@/lib/types';
import { useFeatureToggleStore } from '@/store/featureToggleStore';

const DIFFICULTY_ORDER: Array<'L1' | 'L2' | 'L3'> = ['L1', 'L2', 'L3'];

const DIFFICULTY_TITLE: Record<'L1' | 'L2' | 'L3', string> = {
  L1: '🟢 基礎必用 (L1)',
  L2: '🟡 中階 (L2)',
  L3: '🔴 高階 (L3)',
};

interface FeatureTogglePanelProps {
  className?: string;
}

function formatSeconds(seconds: number): string {
  if (seconds <= 0) {
    return '≈ 0 min';
  }
  const minutes = Math.ceil(seconds / 60);
  return `≈ ${minutes} min`;
}

function groupByDifficulty(toggles: FeatureToggle[]) {
  return toggles.reduce(
    (acc, item) => {
      acc[item.difficulty].push(item);
      return acc;
    },
    { L1: [] as FeatureToggle[], L2: [] as FeatureToggle[], L3: [] as FeatureToggle[] },
  );
}

export default function FeatureTogglePanel({ className }: FeatureTogglePanelProps) {
  const {
    toggles,
    summary,
    presets,
    activePreset,
    isLoading,
    error,
    fetchToggles,
    updateToggle,
    applyPreset,
  } = useFeatureToggleStore();

  useEffect(() => {
    fetchToggles();
  }, [fetchToggles]);

  const grouped = useMemo(() => groupByDifficulty(toggles), [toggles]);

  return (
    <div className={className ?? 'rounded-lg border bg-white p-4'}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-base font-semibold">🔧 功能開關管理</h3>
        <button
          type="button"
          className="rounded border px-2 py-1 text-sm"
          onClick={() => fetchToggles()}
          disabled={isLoading}
        >
          重新整理
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="text-sm text-gray-600">預設方案:</span>
        {presets.map((preset) => (
          <button
            key={preset}
            type="button"
            className={`rounded border px-2 py-1 text-sm ${activePreset === preset ? 'bg-gray-100 font-medium' : ''}`}
            onClick={() => applyPreset(preset)}
            disabled={isLoading}
          >
            {preset}
          </button>
        ))}
      </div>

      {error ? <div className="mb-4 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">{error}</div> : null}

      {DIFFICULTY_ORDER.map((difficulty) => {
        const items = grouped[difficulty];
        const enabledCount = items.filter((item) => item.is_enabled).length;

        return (
          <div key={difficulty} className="mb-4 rounded border p-3">
            <div className="mb-2 flex items-center justify-between">
              <h4 className="text-sm font-medium">{DIFFICULTY_TITLE[difficulty]}</h4>
              <span className="text-xs text-gray-500">
                {enabledCount}/{items.length} 已啟用
              </span>
            </div>

            {items.length === 0 ? (
              <div className="text-sm text-gray-500">此層級目前沒有可用功能。</div>
            ) : (
              <div className="space-y-2">
                {items.map((item) => (
                  <label key={item.feature_id} className="flex items-start justify-between gap-3 rounded border p-2">
                    <div>
                      <div className="text-sm font-medium">{item.name}</div>
                      <div className="text-xs text-gray-500">{item.feature_id} · {item.description}</div>
                      <div className="text-xs text-gray-500">
                        {item.estimated_time ? `預估 ${item.estimated_time}` : '預估時間：—'}
                        {item.dependencies.length > 0 ? ` · 依賴: ${item.dependencies.join(', ')}` : ''}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {item.is_locked ? <span className="text-xs text-gray-500">🔒 必要</span> : null}
                      <input
                        type="checkbox"
                        checked={item.is_enabled}
                        disabled={item.is_locked || isLoading}
                        onChange={(event) => updateToggle(item.feature_id, event.target.checked)}
                      />
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>
        );
      })}

      <div className="rounded border bg-gray-50 p-3 text-sm">
        <div>啟用: {summary?.enabled ?? 0}/{summary?.total ?? 0}</div>
        <div>預估總時間: {formatSeconds(summary?.estimated_total_seconds ?? 0)}</div>
      </div>
    </div>
  );
}
