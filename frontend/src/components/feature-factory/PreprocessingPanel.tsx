'use client';

import type { FeatureFactoryConfig } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

type PreprocessingConfig = NonNullable<FeatureFactoryConfig['preprocessing']>;

interface PreprocessingPanelProps {
  config?: FeatureFactoryConfig['preprocessing'];
  onChange: (next: PreprocessingConfig) => void;
}

const DEFAULT_PREPROCESSING: PreprocessingConfig = {
  enabled: true,
  mode: 'replace',
  winsorization: {
    enabled: true,
    method: 'quantile',
    sigma_k: 3.0,
    quantile_range: [0.01, 0.99],
    apply_to: 'all',
  },
  adf_differencing: {
    enabled: false,
    adf_threshold: 0.10,
    max_diff: 2,
    sample_size: 500,
    apply_to: 'non_stationary',
  },
  fractional_differencing: {
    enabled: false,
    d_range: [0.0, 1.0],
    adf_threshold: 0.10,
    weight_threshold: 1e-5,
    precision: 0.02,
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

export const PREPROCESSING_WARNINGS = {
  fracdiffAdfCoexist:
    'FracDiff 與 ADF 可以同時開啟；系統會避免對已由 FracDiff 處理的欄位再做 ADF。ADF 不是 FracDiff 的高 NaN fallback，高 NaN 欄位會被略過。',
  fracdiffSlowLayerFilter:
    'FracDiff 是 L6.5 最慢的子模組；optimized profile 預設只套用 L1/L2，L3/L4 僅能透過 expert env override 恢復。',
  eightGbFullRunEstimate:
    '若透過 expert env 將 FracDiff 擴到全 layer 並同時全開 ADF，8GB 機器預估約 18-20 小時。',
} as const;

/** 每張卡片的說明文字（懸停顯示） */
const TOOLTIPS = {
  winsorization: `【Winsorization — 剪掉極端值】
把超出範圍的數值壓回邊界，避免一兩個離群值扭曲後續全部計算。
例如（quantile 模式）：把最低 1% 以下和最高 1% 以上的數值，
分別壓回 Q1% 和 Q99%，讓資料更穩定。
💡 建議永遠開啟，且選 quantile（比 sigma 不易被離群值影響）。`,

  fractional_differencing: `【Fractional Differencing — 去除長期趨勢】
EMA_89 這類長週期均線幾乎永遠在漲或跌，ML 模型看到的是「永遠在某個方向移動的數字」，
無法學到真正有用的高低對比。

d* 概念（用煞車比喻）：
把 EMA 想像成一列高速列車，永遠朝同一方向跑。
d* 是「讓列車速度波動夠隨機」所需的最小煞車力道。
• EMA_5（靈活）→ 輕踩煞車（d*≈0.5）就夠了
• EMA_89（像大船）→ 需要用力踩（d*≈1.0）
煞車後，模型看到的是「比昨天快了多少」而不是「現在跑多快」，
更能學到有意義的交易訊號。

可與 ADF 同時開啟；ADF 不是 FracDiff 的高 NaN fallback，高 NaN 欄位會被略過。`,

  adf_differencing: `【ADF Differencing — 整數差分（整數版煞車）】
功能與 FracDiff 相同，但只能選整數（差分 1 次或 2 次），像是「要嘛不踩、要嘛踩死」。
FracDiff 可以踩 0.73 次這種中間值，保留更多市場記憶，通常效果更好。
建議使用 FracDiff，除非速度是優先考量。

可與 FracDiff 同時開啟；已由 FracDiff 處理的欄位不會再套用 ADF。`,

  rank_transform: `【Rank Transform — 百分位排名】
把數字轉成「在過去 window 天中的名次」（0 到 1 之間）。

例子：
BTC 的 EMA_50 今天差分結果是 +2300，在過去 252 天排第 73 名 → 輸出 0.73
SOL 的 EMA_50 今天差分結果是 +1.5，在過去 252 天排第 41 名 → 輸出 0.41

不管 BTC 數字多大、SOL 數字多小，都轉成 0~1，
ML 模型可以公平地跨標的比較。`,

  gaussian_normalize: `【Gaussian Normalize — 轉成鐘形分佈】
把 Rank 的 0~1 結果，再轉換成標準常態分佈（鐘形曲線）。
讓中間段的差距被放大、兩端被壓縮，
對部分線性 ML 模型的預測精度有幫助。
通常和 Rank 一起開，不單獨使用。`,

  adaptive_zscore: `【Adaptive Z-Score — 滾動標準化】
公式：(今天數值 - 過去 N 天平均) ÷ 過去 N 天標準差

消除「這段時間整體偏高或偏低」的偏移。
例如：牛市期間所有 EMA 都偏高沒有意義，
Z-Score 讓模型只學「現在相對自己近期是高還是低」，
而不是「現在的絕對水位」。
windows=[100,252]：同時輸出 100 天尺度和 252 天尺度（約一年）兩個版本。`,
};

function InfoTooltip({ content }: { content: string }) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center justify-center w-4 h-4 rounded-full border border-slate-500 text-slate-400 text-[10px] cursor-help select-none hover:border-slate-300 hover:text-slate-200 transition-colors">
            ?
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs whitespace-pre-line text-xs leading-relaxed">
          {content}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default function PreprocessingPanel({ config, onChange }: PreprocessingPanelProps) {
  const { preview } = useFeatureFactoryStore();
  const preprocessing = mergePreprocessing(config, {});

  const update = (patch: Partial<PreprocessingConfig>) => {
    onChange(mergePreprocessing(config, patch));
  };

  const added = preview?.breakdown?.preprocessing_added;

  const fracEnabled = Boolean(preprocessing.fractional_differencing?.enabled);
  const adfEnabled = Boolean(preprocessing.adf_differencing?.enabled);
  const showCoexistWarning = fracEnabled && adfEnabled;

  return (
    <div>
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="text-xs text-slate-400">固定接力順序：Winsor → FracDiff/ADF → Rank → Gaussian → Z-Score</div>
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
      <div className="px-6 pb-6 space-y-4">

      {/* 輸出模式 */}
      <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 space-y-2">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">輸出模式</span>
          <button
            type="button"
            onClick={() => update({ mode: 'replace' })}
            className={`rounded-md px-2 py-1 border text-xs ${
              preprocessing.mode === 'replace'
                ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                : 'bg-white/5 text-slate-400 border-white/10'
            }`}
          >
            Replace（建議）
          </button>
          <button
            type="button"
            onClick={() => update({ mode: 'append' })}
            className={`rounded-md px-2 py-1 border text-xs ${
              preprocessing.mode === 'append'
                ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                : 'bg-white/5 text-slate-400 border-white/10'
            }`}
          >
            Append
          </button>
          <span className="ml-auto text-slate-500 text-xs">
            預估新增：{typeof added === 'number' ? added.toLocaleString('en-US') : '—'}
          </span>
        </div>
        {preprocessing.mode === 'replace' ? (
          <div className="text-[11px] text-slate-400 leading-relaxed">
            <span className="text-cyan-300">Replace 模式</span>：每步直接覆蓋上一步結果，欄位名稱全程不變。
            多標的訓練時欄位對齊，為業界標準。
          </div>
        ) : (
          <div className="text-[11px] text-amber-300/80 leading-relaxed">
            <span className="text-amber-300">Append 模式</span>：每步長出新欄位（如 _fracdiff、_rank）。
            不同標的可能欄位名稱不同，多標的訓練時可能出現欄位錯位。
          </div>
        )}
      </div>

      {(showCoexistWarning || fracEnabled) && (
        <Alert
          data-testid="preprocessing-warnings"
          className="border-yellow-200 bg-yellow-50 text-yellow-900"
        >
          <AlertDescription className="space-y-2 text-xs leading-relaxed">
            {showCoexistWarning && <p>{PREPROCESSING_WARNINGS.fracdiffAdfCoexist}</p>}
            {fracEnabled && <p>{PREPROCESSING_WARNINGS.fracdiffSlowLayerFilter}</p>}
            {fracEnabled && <p>{PREPROCESSING_WARNINGS.eightGbFullRunEstimate}</p>}
          </AlertDescription>
        </Alert>
      )}

      {/* 六張計算卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">

        {/* Winsorization */}
        <div className="rounded-xl border border-emerald-300/30 bg-emerald-400/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-emerald-200 font-medium">Winsorization</span>
              <InfoTooltip content={TOOLTIPS.winsorization} />
            </div>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.winsorization?.enabled)}
              onChange={(e) =>
                update({ winsorization: { ...preprocessing.winsorization, enabled: e.target.checked } })
              }
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">方法</span>
            <select
              value={preprocessing.winsorization?.method ?? 'quantile'}
              onChange={(e) =>
                update({ winsorization: { ...preprocessing.winsorization, method: e.target.value as 'sigma' | 'quantile' } })
              }
              className="rounded-md border border-white/10 bg-slate-900/60 px-2 py-1 text-slate-200"
            >
              <option value="quantile">quantile（建議）</option>
              <option value="sigma">sigma</option>
            </select>
          </div>
        </div>

        {/* Fractional Differencing */}
        <div className="rounded-xl border border-rose-300/30 bg-rose-400/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-rose-200 font-medium">Fractional Differencing</span>
              <InfoTooltip content={TOOLTIPS.fractional_differencing} />
            </div>
            <input
              type="checkbox"
              checked={fracEnabled}
              onChange={(e) =>
                update({ fractional_differencing: { ...preprocessing.fractional_differencing, enabled: e.target.checked } })
              }
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-slate-400">precision</span>
            <input
              type="number"
              min={0.001}
              step={0.001}
              value={preprocessing.fractional_differencing?.precision ?? 0.02}
              onChange={(e) =>
                update({ fractional_differencing: { ...preprocessing.fractional_differencing, precision: Number(e.target.value) } })
              }
              className="w-24 rounded-md border border-white/10 bg-slate-900/60 px-2 py-1 text-slate-200"
            />
          </div>
          <div className="text-[11px] text-rose-200/70">速度較慢但資訊保留更多 · optimized 預設 L1/L2</div>
        </div>

        {/* Rank Transform */}
        <div className="rounded-xl border border-emerald-300/30 bg-emerald-400/5 p-3 space-y-2 transition-opacity opacity-40 pointer-events-none">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-emerald-200 font-medium">Rank Transform</span>
              <InfoTooltip content={TOOLTIPS.rank_transform} />
            </div>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.rank_transform?.enabled)}
              onChange={(e) =>
                update({ rank_transform: { ...preprocessing.rank_transform, enabled: e.target.checked } })
              }
            />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-slate-400">window（天）</span>
            <input
              type="number"
              min={2}
              value={preprocessing.rank_transform?.window ?? 252}
              onChange={(e) =>
                update({ rank_transform: { ...preprocessing.rank_transform, window: Number(e.target.value) } })
              }
              className="w-24 rounded-md border border-white/10 bg-slate-900/60 px-2 py-1 text-slate-200"
            />
          </div>
          <div className="text-[10px] text-amber-300/70">生成階段略過，請在 IC Analysis 頁面套用</div>
        </div>

        {/* Gaussian Normalize */}
        <div className="rounded-xl border border-amber-300/30 bg-amber-400/5 p-3 space-y-2 transition-opacity opacity-40 pointer-events-none">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-amber-200 font-medium">Gaussian Normalize</span>
              <InfoTooltip content={TOOLTIPS.gaussian_normalize} />
            </div>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.gaussian_normalize?.enabled)}
              onChange={(e) =>
                update({ gaussian_normalize: { ...preprocessing.gaussian_normalize, enabled: e.target.checked } })
              }
            />
          </div>
          <div className="text-[10px] text-amber-300/70">生成階段略過，請在 IC Analysis 頁面套用</div>
        </div>

        {/* Adaptive Z-Score */}
        <div className="rounded-xl border border-amber-300/30 bg-amber-400/5 p-3 space-y-2 transition-opacity opacity-40 pointer-events-none">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-amber-200 font-medium">Adaptive Z-Score</span>
              <InfoTooltip content={TOOLTIPS.adaptive_zscore} />
            </div>
            <input
              type="checkbox"
              checked={Boolean(preprocessing.adaptive_zscore?.enabled)}
              onChange={(e) =>
                update({ adaptive_zscore: { ...preprocessing.adaptive_zscore, enabled: e.target.checked } })
              }
            />
          </div>
          <div className="text-[10px] text-amber-300/70">生成階段略過，請在 IC Analysis 頁面套用</div>
        </div>

        {/* ADF Differencing */}
        <div className="rounded-xl border border-rose-300/30 bg-rose-400/5 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-rose-200 font-medium">ADF Differencing</span>
              <InfoTooltip content={TOOLTIPS.adf_differencing} />
            </div>
            <input
              type="checkbox"
              checked={adfEnabled}
              onChange={(e) =>
                update({ adf_differencing: { ...preprocessing.adf_differencing, enabled: e.target.checked } })
              }
            />
          </div>
          <div className="text-[11px] text-rose-200/70">速度較快但差分較粗糙 · 不作為 FracDiff fallback</div>
        </div>

      </div>

      </div>
    </div>
  );
}
