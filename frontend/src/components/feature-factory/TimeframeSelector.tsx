'use client';

import { FeatureFactoryConfig } from '@/lib/types';

interface TimeframeSelectorProps {
  timeframes: FeatureFactoryConfig['timeframes'];
  onChange: (next: FeatureFactoryConfig['timeframes']) => void;
}

const AVAILABLE_TFS = ['1m', '5m', '15m', '30m', '1h', '4h', '12h', '1d', '1w'];

const ALIGNMENT_MODE_OPTIONS = [
  {
    value: 'open_minus',
    label: 'B-b 開盤事件對齊 (open - 1ns)',
    description: '本系統預設。在 T0 開盤時預測，特徵不含 T0 bar 本身資料。',
  },
  {
    value: 'close_time',
    label: 'A / B-a 收盤對齊 (close_time)',
    description: '收盤後決策。特徵可包含當前 bar 完整資料。',
  },
] as const;

export default function TimeframeSelector({ timeframes, onChange }: TimeframeSelectorProps) {
  const primaryTf = timeframes.primary;
  const trainingTfs = Array.from(new Set(timeframes.training));

  const handlePrimaryChange = (nextPrimary: string) => {
    const nextTraining = trainingTfs.includes(nextPrimary)
      ? trainingTfs
      : [...trainingTfs, nextPrimary];

    onChange({
      ...timeframes,
      primary: nextPrimary,
      training: nextTraining,
    });
  };

  const toggleTraining = (tf: string) => {
    if (tf === primaryTf) {
      return;
    }

    const nextTraining = trainingTfs.includes(tf)
      ? trainingTfs.filter((item) => item !== tf)
      : [...trainingTfs, tf];

    onChange({
      ...timeframes,
      training: nextTraining,
    });
  };

  return (
    <div className="space-y-3">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">時間框架</label>
      <div className="space-y-3">
        <div>
          <div className="text-xs text-slate-400 mb-2">主框架</div>
          <select
            value={primaryTf}
            onChange={(event) => handlePrimaryChange(event.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          >
            {AVAILABLE_TFS.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="text-xs text-slate-400 mb-2">訓練框架</div>
          <div className="grid grid-cols-2 gap-2 rounded-xl border border-white/10 bg-white/5 p-3">
            {AVAILABLE_TFS.map((tf) => {
              const active = trainingTfs.includes(tf);
              const isPrimary = tf === primaryTf;
              return (
                <label
                  key={tf}
                  className={`flex items-center gap-2 rounded-lg px-2 py-1 text-xs border transition ${
                    active
                      ? 'bg-amber-400/20 text-amber-100 border-amber-300/40'
                      : 'bg-white/5 text-slate-400 border-white/10 hover:border-amber-300/40'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={active}
                    disabled={isPrimary}
                    onChange={() => toggleTraining(tf)}
                    className="accent-amber-300"
                  />
                  {tf}
                  {isPrimary && <span className="text-[10px] text-slate-300">(primary)</span>}
                </label>
              );
            })}
          </div>
          <div className="mt-2 text-xs text-slate-400">Primary TF 會固定勾選且不可取消</div>
        </div>

        <div>
          <div className="text-xs text-slate-400 mb-2">對齊模式</div>
          <select
            value={timeframes.alignment_mode ?? 'open_minus'}
            onChange={(event) =>
              onChange({
                ...timeframes,
                alignment_mode: event.target.value as 'open_minus' | 'close_time',
              })
            }
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          >
            {ALIGNMENT_MODE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <div className="mt-2 space-y-1">
            {ALIGNMENT_MODE_OPTIONS.map((option) => (
              <p key={option.value} className="text-xs text-slate-400">
                {option.label}: {option.description}
              </p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
