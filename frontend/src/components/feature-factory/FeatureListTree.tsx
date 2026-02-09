'use client';

interface FeatureListTreeProps {
  features: string[];
}

export default function FeatureListTree({ features }: FeatureListTreeProps) {
  if (!features.length) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
        生成完成後將顯示特徵清單與摘要。
      </div>
    );
  }

  const preview = features.slice(0, 20);

  return (
    <div className="space-y-3">
      <div className="text-sm text-slate-200">特徵清單 (前 20 筆)</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-300">
        {preview.map((name) => (
          <div key={name} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
            {name}
          </div>
        ))}
      </div>
    </div>
  );
}
