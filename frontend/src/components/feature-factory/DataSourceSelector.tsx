'use client';

interface DataSourceSelectorProps {
  enabledSources: string[];
  availableSources: string[];
  onChange: (sources: string[]) => void;
}

export default function DataSourceSelector({
  enabledSources,
  availableSources,
  onChange,
}: DataSourceSelectorProps) {
  const toggleSource = (source: string) => {
    if (enabledSources.includes(source)) {
      onChange(enabledSources.filter((item) => item !== source));
      return;
    }
    onChange([...enabledSources, source]);
  };

  return (
    <div className="space-y-3">
      <label className="text-xs uppercase tracking-[0.2em] text-slate-400">數據源</label>
      <div className="flex flex-wrap gap-2">
        {availableSources.map((source) => {
          const active = enabledSources.includes(source);
          return (
            <button
              key={source}
              type="button"
              onClick={() => toggleSource(source)}
              className={`px-3 py-1 rounded-full text-xs border transition ${
                active
                  ? 'bg-emerald-400/20 text-emerald-100 border-emerald-300/40'
                  : 'bg-white/5 text-slate-400 border-white/10 hover:border-emerald-300/40'
              }`}
            >
              {source}
            </button>
          );
        })}
      </div>
      {enabledSources.length > 2 && (
        <p className="text-xs text-amber-400/70 mt-1">
          建議最多選 2 個數據源。選擇過多會大幅增加特徵量，可能導致計算時間顯著延長。
        </p>
      )}
    </div>
  );
}
