'use client';

import { FeatureFactoryConfig } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

type PreprocessingConfig = NonNullable<FeatureFactoryConfig['preprocessing']>;

interface PreprocessingPanelProps {
  config?: FeatureFactoryConfig['preprocessing'];
  onChange: (next: PreprocessingConfig) => void;
}

const DEFAULT_PREPROCESSING: PreprocessingConfig = {
  enabled: false,
  mode: 'append',
  winsorization: {
    enabled: true,
    method: 'sigma',
    sigma_k: 3.0,
    quantile_range: [0.01, 0.99],
    apply_to: 'all',
  },
  adf_differencing: {
    enabled: false,
    adf_threshold: 0.05,
    max_diff: 2,
    sample_size: 500,
    apply_to: 'non_stationary',
  },
  fractional_differencing: {
    enabled: false,
    d_range: [0.0, 1.0],
    adf_threshold: 0.05,
    weight_threshold: 1e-5,
    precision: 0.01,
    apply_to: 'non_stationary',
    cache_d_star: true,
  },
  rank_transform: {
    enabled: true,
    window: 252,
    apply_to: 'all',
  },
  gaussian_normalize: {
    enabled: false,
    clip_range: [0.001, 0.999],
    apply_to: 'all',
  },
  adaptive_zscore: {
    enabled: true,
    windows: [100, 252],
    epsilon: 1e-8,
    apply_to: 'all',
  },
};

function mergePreprocessing(
  base: FeatureFactoryConfig['preprocessing'] | undefined,
  patch: Partial<PreprocessingConfig>
): PreprocessingConfig {
  const current: PreprocessingConfig = {
    ...DEFAULT_PREPROCESSING,
    ...(base ?? {}),
    winsorization: {
      ...DEFAULT_PREPROCESSING.winsorization,
      ...(base?.winsorization ?? {}),
      ...(patch.winsorization ?? {}),
    },
    adf_differencing: {
      ...DEFAULT_PREPROCESSING.adf_differencing,
      ...(base?.adf_differencing ?? {}),
      ...(patch.adf_differencing ?? {}),
    },
    fractional_differencing: {
      ...DEFAULT_PREPROCESSING.fractional_differencing,
      ...(base?.fractional_differencing ?? {}),
      ...(patch.fractional_differencing ?? {}),
    },
    rank_transform: {
      ...DEFAULT_PREPROCESSING.rank_transform,
      ...(base?.rank_transform ?? {}),
      ...(patch.rank_transform ?? {}),
    },
    gaussian_normalize: {
      ...DEFAULT_PREPROCESSING.gaussian_normalize,
      ...(base?.gaussian_normalize ?? {}),
      ...(patch.gaussian_normalize ?? {}),
    },
    adaptive_zscore: {
      ...DEFAULT_PREPROCESSING.adaptive_zscore,
      ...(base?.adaptive_zscore ?? {}),
      ...(patch.adaptive_zscore ?? {}),
    },
    ...patch,
  };
  return current;
}

export default function PreprocessingPanel({ config, onChange }: PreprocessingPanelProps) {
  const { preview } = useFeatureFactoryStore();
  const preprocessing = mergePreprocessing(config, {});

  const update = (patch: Partial<PreprocessingConfig>) => {
    onChange(mergePreprocessing(config, patch));
  };

  const added = preview?.breakdown?.preprocessing_added;

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4 border border-white/10">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-100">前處理層 (Layer 6.5)</div>
          <div className="text-xs text-slate-400">固定順序：Winsor → FracDiff/ADF → Rank → Gaussian → Z-Score</div>
        </div>
        <button
          type="button"
          onClick={() => update({ enabled: !preprocessing.enabled })}
          className={`rounded-lg border px-3 py-1.5 text-xs ${
            preprocessing.enabled
              ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
              : 'bg-white/5 text-slate-400 border-white/10'
          }`}
        >
          {preprocessing.enabled ? '● 已啟用' : '○ 已停用'}
        </button>
      </div>

      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-400">模式</span>
        <button
          type="button"
          onClick={() => update({ mode: 'append' })}
          className={`rounded-md px-2 py-1 border ${
            preprocessing.mode === 'append'
              ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
              : 'bg-white/5 text-slate-400 border-white/10'
          }`}
        >
          Append
        </button>
        <button
          type="button"
          onClick={() => update({ mode: 'replace' })}
          className={`rounded-md px-2 py-1 border ${
            preprocessing.mode === 'replace'
              ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
              : 'bg-white/5 text-slate-400 border-white/10'
          }`}
        >
          Replace
        </button>
        <span className="ml-auto text-slate-500">
          預估新增：{typeof added === 'number' ? added.toLocaleString('en-US') : '—'}
        </span>
      </div>

      <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-300">
        ① Winsorization 🟢 → ② FracDiff/ADF 🔴 → ③ Rank 🟢 → ④ Gaussian 🟡 → ⑤ Z-Score 🟡
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div className="rounded-xl border border-emerald-300/30 bg-emerald-400/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-emerald-200">Winsorization 🟢</span>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.winsorization?.enabled)}
              onChange={(event) =>
                update({ winsorization: { ...preprocessing.winsorization, enabled: event.target.checked } })
              }
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">方法</span>
            <select
              value={preprocessing.winsorization?.method ?? 'sigma'}
              onChange={(event) =>
                update({ winsorization: { ...preprocessing.winsorization, method: event.target.value as 'sigma' | 'quantile' } })
              }
              className="rounded-md border border-white/10 bg-slate-900/60 px-2 py-1 text-slate-200"
            >
              <option value="sigma">sigma</option>
              <option value="quantile">quantile</option>
            </select>
          </div>
        </div>

        <div className="rounded-xl border border-rose-300/30 bg-rose-400/5 p-3 space-y-2" title="高階轉換，可能增加計算時間。">
          <div className="flex items-center justify-between">
            <span className="text-rose-200">Fractional Differencing 🔴</span>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.fractional_differencing?.enabled)}
              onChange={(event) =>
                update({
                  fractional_differencing: {
                    ...preprocessing.fractional_differencing,
                    enabled: event.target.checked,
                  },
                })
              }
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-slate-400">precision</span>
            <input
              type="number"
              min={0.001}
              step={0.001}
              value={preprocessing.fractional_differencing?.precision ?? 0.01}
              onChange={(event) =>
                update({
                  fractional_differencing: {
                    ...preprocessing.fractional_differencing,
                    precision: Number(event.target.value),
                  },
                })
              }
              className="w-24 rounded-md border border-white/10 bg-slate-900/60 px-2 py-1 text-slate-200"
            />
          </div>
          <div className="text-[11px] text-rose-200/80">⚠️ 較慢，建議先小樣本驗證。</div>
        </div>

        <div className="rounded-xl border border-emerald-300/30 bg-emerald-400/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-emerald-200">Rank Transform 🟢</span>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.rank_transform?.enabled)}
              onChange={(event) =>
                update({ rank_transform: { ...preprocessing.rank_transform, enabled: event.target.checked } })
              }
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-slate-400">window</span>
            <input
              type="number"
              min={2}
              value={preprocessing.rank_transform?.window ?? 252}
              onChange={(event) =>
                update({ rank_transform: { ...preprocessing.rank_transform, window: Number(event.target.value) } })
              }
              className="w-24 rounded-md border border-white/10 bg-slate-900/60 px-2 py-1 text-slate-200"
            />
          </div>
        </div>

        <div className="rounded-xl border border-amber-300/30 bg-amber-400/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-amber-200">Gaussian Normalize 🟡</span>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.gaussian_normalize?.enabled)}
              onChange={(event) =>
                update({
                  gaussian_normalize: {
                    ...preprocessing.gaussian_normalize,
                    enabled: event.target.checked,
                  },
                })
              }
            />
          </div>
        </div>

        <div className="rounded-xl border border-amber-300/30 bg-amber-400/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-amber-200">Adaptive Z-Score 🟡</span>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.adaptive_zscore?.enabled)}
              onChange={(event) =>
                update({ adaptive_zscore: { ...preprocessing.adaptive_zscore, enabled: event.target.checked } })
              }
            />
          </div>
        </div>

        <div className="rounded-xl border border-rose-300/30 bg-rose-400/5 p-3 space-y-2" title="高階轉換，可能增加計算時間。">
          <div className="flex items-center justify-between">
            <span className="text-rose-200">ADF Differencing 🔴</span>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.adf_differencing?.enabled)}
              onChange={(event) =>
                update({ adf_differencing: { ...preprocessing.adf_differencing, enabled: event.target.checked } })
              }
            />
          </div>
          <div className="text-[11px] text-rose-200/80">⚠️ 高耗時，通常建議與 FracDiff 擇一。</div>
        </div>
      </div>
    </div>
  );
}
